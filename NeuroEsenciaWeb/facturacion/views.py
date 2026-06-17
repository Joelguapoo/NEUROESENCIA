import uuid
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

from clinica.models import Cita
from .models import Factura, MetodoPago, Paciente
from .forms import FacturaForm
from django.core.mail import EmailMessage
from django.conf import settings

@login_required
def lista_facturas(request):
    facturas = Factura.objects.all().order_by('-fecha_emision')
    return render(request, 'facturacion/lista_facturas.html', {'facturas': facturas})


@login_required
def crear_factura(request):
    if request.method == 'POST':
        form = FacturaForm(request.POST)
        if form.is_valid():
            factura = form.save(commit=False)
            
            # Blindaje: Si el formulario no generó un número, lo creamos aquí
            if not factura.nro_factura:
                factura.nro_factura = f"FAC-{uuid.uuid4().hex[:8].upper()}"
                
            factura.total = factura.subtotal + factura.impuestos
            factura.save()
            messages.success(request, f"Factura {factura.nro_factura} generada con éxito.")
            return redirect('lista_facturas')
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
        nro_factura=f"FAC-{uuid.uuid4().hex[:8].upper()}", # <-- Corrección de seguridad aplicada aquí
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
        
        # 3. Enviar el correo de Recibo de Pago
        try:
            # Aquí generamos el PDF del recibo usando tu vista existente
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
            
            messages.success(request, f"¡Pago procesado con {obj_metodo.nombre_metodo}! El recibo ha sido enviado al paciente.")
        except Exception as e:
            messages.warning(request, f"Pago registrado, pero hubo un error enviando el correo: {e}")
            
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