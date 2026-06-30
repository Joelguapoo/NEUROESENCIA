import uuid
import threading
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.core.mail import EmailMessage
from django.conf import settings
from xhtml2pdf import pisa

from clinica.models import Cita
from .models import Factura, MetodoPago, Paciente
from .forms import FacturaForm

@login_required
def lista_facturas(request):
    facturas = Factura.objects.all().order_by('-fecha_emision')
    return render(request, 'facturacion/lista_facturas.html', {'facturas': facturas})

@login_required
def crear_factura(request):
    if request.method == 'POST':
        datos_post = request.POST.copy()
        
        # 1. Buscamos si la Cita seleccionada ya tiene una factura automática asignada
        cita_id = datos_post.get('cita')
        factura_existente = None
        if cita_id:
            factura_existente = Factura.objects.filter(cita_id=cita_id).first()

        # 2. Asignamos o mantenemos el número de factura
        if not datos_post.get('nro_factura'):
            # Si ya existía, usamos su número original. Si es totalmente nueva, creamos uno.
            datos_post['nro_factura'] = factura_existente.nro_factura if factura_existente else f"FAC-{uuid.uuid4().hex[:8].upper()}"

        # 3. EL TRUCO MAGISTRAL: Si la factura ya existe, le decimos al Formulario que la ACTUALICE (instance)
        # Si no existe, creará una nueva.
        if factura_existente:
            form = FacturaForm(datos_post, instance=factura_existente)
        else:
            form = FacturaForm(datos_post)
        
        if form.is_valid():
            factura = form.save(commit=False)
            factura.total = factura.subtotal + factura.impuestos
            factura.save()
            messages.success(request, f"Factura {factura.nro_factura} procesada y guardada con éxito.")
            return redirect('lista_facturas')
        else:
            # Mostramos en pantalla si falta algo más
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en {field}: {error}")
    else:
        form = FacturaForm()
    
    return render(request, 'facturacion/form_factura.html', {'form': form, 'editando': False})

@login_required
def anular_factura(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    if request.method == 'POST':
        factura.estado_pago = 'Anulada'
        factura.save()
        messages.warning(request, f"La factura {factura.nro_factura} ha sido anulada.")
        return redirect('lista_facturas')
    return render(request, 'facturacion/confirmar_anular.html', {'factura': factura})

@login_required
def pre_facturacion(request, cita_id):
    """Muestra la pantalla de elección de pago con la tarifa plana."""
    cita = get_object_or_404(Cita, id=cita_id)
    context = {
        'cita': cita,
        'valor_plano': 50000,
        'impuesto_calculado': 0
    }
    return render(request, 'facturacion/pre_facturacion.html', context)

@login_required
def generar_pago_automatico(request, cita_id, metodo):
    """Crea la factura real basada en la elección del paciente."""
    cita = get_object_or_404(Cita, id=cita_id)
    valor_fijo = 50000

    obj_metodo, created = MetodoPago.objects.get_or_create(
        nombre_metodo=metodo
    )

    nueva_factura = Factura.objects.create(
        nro_factura=f"FAC-{uuid.uuid4().hex[:8].upper()}", 
        cita=cita,
        paciente=cita.paciente,
        metodo=obj_metodo,
        subtotal=valor_fijo,
        impuestos=0,
        total=valor_fijo,
        estado_pago='Pagada' if metodo == 'virtual' else 'Pendiente'
    )
    
    if metodo == 'virtual':
        messages.success(request, "¡Pago virtual procesado con éxito!")
    else:
        messages.info(request, "Recuerda pagar en recepción al llegar.")
        
    return redirect('lista_facturas')

# ---- FUNCIÓN AUXILIAR PARA EVITAR ERROR 500 EN RAILWAY ----
def enviar_recibo_segundo_plano(factura, obj_metodo):
    try:
        template = get_template('facturacion/factura_pdf.html')
        html = template.render({'factura': factura})
        result = BytesIO()
        pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
        pdf_recibo = result.getvalue()

        asunto = f"Recibo de Pago - Factura {factura.nro_factura} - NeuroEsencia"
        cuerpo = f"Hola {factura.paciente.nombre_completo},\n\nHemos recibido exitosamente tu pago por un valor de ${factura.total} COP mediante {obj_metodo.nombre_metodo}. Adjuntamos el recibo oficial de esta transacción.\n\nGracias por confiar en nosotros."
        
        email = EmailMessage(asunto, cuerpo, settings.EMAIL_HOST_USER, [factura.paciente.correo])
        email.attach(f"Recibo_{factura.nro_factura}.pdf", pdf_recibo, 'application/pdf')
        email.send(fail_silently=False)
        print(f"ÉXITO: Recibo PDF enviado al paciente {factura.paciente.nombre_completo}")
    except Exception as e:
        print(f"Error técnico enviando recibo PDF en segundo plano: {e}")

def detalle_factura(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    
    if request.method == 'POST':
        metodo = request.POST.get('metodo_pago')
        banco = request.POST.get('banco_seleccionado', '')
        
        # 1. Asignar el método real según el formulario
        if metodo == 'efectivo':
            obj_metodo, _ = MetodoPago.objects.get_or_create(nombre_metodo='Efectivo')
        elif metodo == 'tarjeta':
            obj_metodo, _ = MetodoPago.objects.get_or_create(nombre_metodo='Tarjeta Débito/Crédito')
        elif metodo == 'transferencia':
            obj_metodo, _ = MetodoPago.objects.get_or_create(nombre_metodo=f'Transferencia / {banco}')
        
        # 2. Actualizar la factura
        factura.metodo = obj_metodo
        factura.estado_pago = 'Pagada'
        factura.save()
        
        # 3. Lanzar el envío del recibo PDF a un Hilo en segundo plano
        hilo_recibo = threading.Thread(
            target=enviar_recibo_segundo_plano, 
            args=(factura, obj_metodo)
        )
        hilo_recibo.start()
        
        # Respuesta inmediata a la pantalla para evitar el colapso
        messages.success(request, f"¡Pago procesado con {obj_metodo.nombre_metodo}! El recibo se está generando y enviando al paciente.")
        return redirect('lista_facturas')
        
    return render(request, 'facturacion/detalle_factura.html', {'factura': factura})

@login_required
def exportar_factura_pdf(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    template = get_template('facturacion/factura_pdf.html')
    context = {'factura': factura}
    html = template.render(context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

def mis_facturas(request):
    """Vista exclusiva para que el paciente vea su historial de facturas."""
    p_id = request.session.get('paciente_id')
    
    if not p_id: 
        return redirect('iniciar_sesion')
    
    paciente = get_object_or_404(Paciente, id=p_id)
    facturas = Factura.objects.filter(paciente=paciente).order_by('-fecha_emision')
    
    return render(request, 'usuarios/mis_facturas.html', {
        'facturas': facturas, 
        'paciente': paciente
    })

@login_required
def api_citas_pendientes(request):
    """Devuelve JSON con las citas del paciente que NO han sido pagadas"""
    paciente_id = request.GET.get('paciente_id')
    if not paciente_id:
        return JsonResponse({'citas': []})
        
    # Filtramos las citas activas, pero EXCLUIMOS las que ya están pagadas.
    citas_activas = Cita.objects.filter(
        paciente_id=paciente_id,
        estado_cita__in=['Programada', 'Asistida']
    ).exclude(
        factura__estado_pago='Pagada'
    ).order_by('-fecha_cita')

    data = []
    for c in citas_activas:
        fecha_str = c.fecha_cita.strftime('%d/%m/%Y') if c.fecha_cita else "Sin fecha"
        hora_str = c.hora_cita.strftime('%H:%M') if c.hora_cita else "Sin hora"
        
        data.append({
            'id': c.id,
            'fecha': f"{fecha_str} {hora_str}",
            'modalidad': c.modalidad,
            'valor_sugerido': 50000 if c.modalidad == 'Virtual' else 70000 
        })
        
    return JsonResponse({'citas': data})
