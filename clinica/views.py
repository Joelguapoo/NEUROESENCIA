import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from xhtml2pdf import pisa
from .models import Cita, EvolucionSesion, HistorialClinico
from .forms import CitaForm, EvolucionForm, HistorialClinicoForm
from usuarios.models import Empleado
from django.contrib.auth.models import User
from facturacion.models import Factura, MetodoPago, Paciente
from django.core.mail import EmailMessage
from io import BytesIO
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse, JsonResponse
from .models import Tratamiento
from .forms import TratamientoForm


@login_required
def lista_citas(request):
    citas = Cita.objects.select_related('paciente', 'psicologo').all().order_by('fecha_cita', 'hora_cita')
    return render(request, 'clinica/lista_citas.html', {'citas': citas})


@login_required
def agendar_cita(request):
    psicologos = Empleado.objects.filter(rol__nombre_rol='Psicologo', estado_empleado='Activo')
    
    if request.method == 'POST':
        datos_post = request.POST.copy()
        empleado_id = datos_post.get('psicologo')
        
        if empleado_id:
            try:
                empleado = Empleado.objects.get(id=empleado_id)
                user = User.objects.get(username=empleado.usuario)
                datos_post['psicologo'] = user.id
            except (Empleado.DoesNotExist, User.DoesNotExist):
                pass 

        form = CitaForm(datos_post)
        
        if form.is_valid():
            try:
                paciente_id = form.cleaned_data.get('paciente')
                fecha_cita = form.cleaned_data.get('fecha_cita')
                
                if Cita.objects.filter(
                    paciente=paciente_id, 
                    fecha_cita=fecha_cita
                ).exclude(estado_cita__in=['Cancelada', 'No Asistió']).exists():
                    messages.error(request, "Violación de regla: El paciente ya tiene una cita agendada para este día.")
                    return render(request, 'clinica/agendar_cita.html', {'form': form, 'psicologos': psicologos, 'editando': False})

                if Cita.objects.filter(
                    psicologo=form.cleaned_data.get('psicologo'),
                    fecha_cita=fecha_cita,
                    hora_cita=form.cleaned_data.get('hora_cita')
                ).exclude(estado_cita__in=['Cancelada', 'No Asistió']).exists():
                    messages.error(request, "Horario ocupado. Elige otro.")
                    return render(request, 'clinica/agendar_cita.html', {'form': form, 'psicologos': psicologos, 'editando': False})

                with transaction.atomic():
                    cita = form.save() 
                    metodo_defecto, _ = MetodoPago.objects.get_or_create(nombre_metodo='Por Definir')
                    Factura.objects.create(
                        nro_factura=f"FAC-{uuid.uuid4().hex[:8].upper()}",
                        cita=cita, paciente=cita.paciente, metodo=metodo_defecto,
                        subtotal=50000, impuestos=0, total=50000, estado_pago='Pendiente'
                    )
            
                    # ---> LANZAMOS EL HILO PARA EL PDF Y CORREO EN SEGUNDO PLANO <---
                    hilo_correo = threading.Thread(
                        target=enviar_confirmacion_cita, 
                        args=(cita,)
                    )
                    hilo_correo.start()
                    
                    # Respondemos inmediatamente al usuario sin esperar el correo
                    messages.success(request, f"Cita {cita.codigo_cita} agendada. Se está generando el PDF y enviando al paciente en segundo plano.")
                        
                return redirect('lista_citas')
            
            except Exception as e:
                messages.error(request, f"Error de base de datos: {e}")
        else:
            messages.error(request, "Revisa los datos del formulario.")
    else:
        form = CitaForm()
    
    return render(request, 'clinica/agendar_cita.html', {'form': form, 'psicologos': psicologos, 'editando': False})


@login_required
def editar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id)
    
    if not (request.user.is_superuser or request.user.groups.filter(name='Psicologo') or request.user.groups.filter(name='Administrador').exists()):
        messages.error(request, "Solo el personal administrativo puede reprogramar citas.")
        return redirect('lista_citas')

    if request.method == 'POST':
        datos_post = request.POST.copy()
        
        empleado_id = datos_post.get('psicologo')
        if empleado_id:
            try:
                empleado = Empleado.objects.get(id=empleado_id)
                user_psico = User.objects.get(username=empleado.usuario)
                datos_post['psicologo'] = user_psico.id
            except (Empleado.DoesNotExist, User.DoesNotExist):
                pass 

        form = CitaForm(datos_post, instance=cita)
        if form.is_valid():
            form.save()
            messages.success(request, f"La cita {cita.codigo_cita} ha sido reprogramada con éxito.")
            return redirect('lista_citas')
        else:
            messages.error(request, "Hubo un error al actualizar la cita. Revisa los datos.")
    else:
        try:
            empleado_actual = Empleado.objects.get(usuario=cita.psicologo.username)
            form = CitaForm(instance=cita, initial={'psicologo': empleado_actual.id})
        except Empleado.DoesNotExist:
            form = CitaForm(instance=cita)
        
    psicologos = Empleado.objects.filter(rol__nombre_rol='Psicologo', estado_empleado='Activo')
    
    return render(request, 'clinica/agendar_cita.html', {
        'form': form, 
        'editando': True, 
        'psicologos': psicologos,
        'cita': cita
    })

@login_required
def registrar_evolucion(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id)
    if request.method == 'POST':
        form = EvolucionForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                evolucion = form.save(commit=False)
                evolucion.cita = cita
                evolucion.save()
                cita.estado_cita = 'Asistida'
                cita.save()
            messages.success(request, "Evolución registrada.")
            return redirect('lista_citas')
    else:
        form = EvolucionForm()
    return render(request, 'clinica/registrar_evolucion.html', {'form': form, 'cita': cita})

@login_required
def editar_evolucion(request, pk):
    evolucion = get_object_or_404(EvolucionSesion, pk=pk)
    
    cita = evolucion.cita
    
    if request.method == 'POST':
        form = EvolucionForm(request.POST, instance=evolucion)
        
        if form.is_valid():
            form.save()
            messages.success(request, f"La evolución de la cita {cita.codigo_cita} ha sido actualizada.")
            
            return redirect('ver_historial', paciente_id=cita.paciente.id)
        else:
            messages.error(request, "Hubo un error al actualizar la evolución. Revisa los campos.")
    else:
        form = EvolucionForm(instance=evolucion)
        
    contexto = {
        'form': form,
        'cita': cita,
        'evolucion': evolucion 
    }
    
    return render(request, 'clinica/registrar_evolucion.html', contexto)

@login_required
def ver_historial(request, paciente_id):
    """Muestra el historial clínico completo de un paciente."""
    paciente = get_object_or_404(Paciente, id=paciente_id)
    antecedentes = HistorialClinico.objects.filter(paciente=paciente).first()
    evoluciones = EvolucionSesion.objects.filter(cita__paciente=paciente).order_by('-fecha_registro')
    
    return render(request, 'clinica/lista_historial.html', {
        'paciente': paciente,
        'antecedentes': antecedentes,
        'historiales': evoluciones
    })

@login_required
def exportar_evolucion_pdf(request, evolucion_id):
    """Genera un reporte PDF profesional de una sesión específica."""
    evolucion = get_object_or_404(EvolucionSesion, id=evolucion_id)
    contexto = {
        'evolucion': evolucion,
        'fecha_hoy': timezone.now(),
    }
    html = render_to_string('clinica/pdf_evolucion.html', contexto)
    response = HttpResponse(content_type='application/pdf')
    
    filename = f"Evolucion_{evolucion.cita.paciente.dni_paciente}_{evolucion.fecha_registro.strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Error técnico al generar el PDF', status=500)
    return response

@login_required
def actualizar_estado_cita(request, cita_id):
    """Actualiza el estado de la cita desde el combobox de la lista principal."""
    if request.method == 'POST':
        cita = get_object_or_404(Cita, id=cita_id)
        nuevo_estado = request.POST.get('nuevo_estado')
        estados_permitidos = ['Cancelada', 'No Asistió', 'Programada']
        
        if nuevo_estado in estados_permitidos:
            cita.estado_cita = nuevo_estado
            cita.save()
            messages.success(request, f"La cita fue actualizada a estado: {nuevo_estado}.")
        else:
            messages.error(request, "Estado no válido.")
            
    return redirect('lista_citas')

@login_required
def editar_antecedentes(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    historial, created = HistorialClinico.objects.get_or_create(paciente=paciente)

    if request.method == 'POST':
        form = HistorialClinicoForm(request.POST, instance=historial)
        if form.is_valid():
            form.save()
            messages.success(request, f"Antecedentes de {paciente.nombre_completo} guardados correctamente.")
            return redirect('ver_historial', paciente_id=paciente.id)
    else:
        form = HistorialClinicoForm(instance=historial)

    return render(request, 'clinica/form_historial.html', {
        'form': form, 
        'paciente': paciente
    })

def enviar_confirmacion_cita(cita):
    try:
        fecha_texto = cita.fecha_cita.strftime('%d/%m/%Y') 
        hora_texto = cita.hora_cita.strftime('%H:%M %p')

        contexto_pdf = {
            'cita': cita,
            'fecha_formateada': fecha_texto,
            'hora_formateada': hora_texto
        }
        
        html_pdf = render_to_string('clinica/pdf_cita_adjunto.html', contexto_pdf)
        result = BytesIO()
        pisa.pisaDocument(BytesIO(html_pdf.encode("UTF-8")), result)
        pdf_final = result.getvalue()

        from django.utils import timezone
        ahora = timezone.now().strftime('%d/%m/%Y %H:%M')
        asunto = f"Confirmación Cita #{cita.codigo_cita} - NeuroEsencia ({ahora})"
        cuerpo_html = render_to_string('clinica/correo_cita.html', {'cita': cita})
        
        email = EmailMessage(
            asunto,
            cuerpo_html,
            settings.EMAIL_HOST_USER,
            [cita.paciente.correo]
        )
        email.content_subtype = "html"
        email.attach(f"Cita_{cita.codigo_cita}.pdf", pdf_final, 'application/pdf')
        email.send(fail_silently=False)
        
        # Imprimimos en la consola de Railway para confirmar que todo salió bien
        print(f"ÉXITO: Correo y PDF de cita {cita.codigo_cita} enviado en segundo plano.")
        
    except Exception as e:
        # Si algo falla (como la contraseña bloqueada de Google), lo veremos en los Logs
        print(f"ERROR enviando confirmación de cita en segundo plano: {e}")

@login_required
def obtener_disponibilidad(request):
    """Devuelve las horas ocupadas de un psicólogo en formato JSON"""
    psicologo_id = request.GET.get('psicologo_id')
    ocupados = []
    
    if psicologo_id:
        empleado = get_object_or_404(Empleado, pk=psicologo_id)
        user_id = User.objects.get(username=empleado.usuario).id
        
        citas = Cita.objects.filter(psicologo_id=user_id).exclude(estado_cita__in=['Cancelada', 'No Asistió'])
        for cita in citas:
            ocupados.append({
                'fecha': cita.fecha_cita.strftime('%Y-%m-%d'),
                'hora': cita.hora_cita.strftime('%H:%M') # Formato exacto 08:00
            })
            
    return JsonResponse({'ocupados': ocupados})

@login_required
def verificar_limite_paciente(request):
    """Verifica si el paciente ya tiene una cita el día seleccionado"""
    paciente_id = request.GET.get('paciente_id')
    fecha = request.GET.get('fecha')
    tiene_cita = False
    
    if paciente_id and fecha:
        tiene_cita = Cita.objects.filter(
            paciente_id=paciente_id, 
            fecha_cita=fecha
        ).exclude(estado_cita__in=['Cancelada', 'No Asistió']).exists()
        
    return JsonResponse({'tiene_cita': tiene_cita})

from .models import Tratamiento
from .forms import TratamientoForm

@login_required
def lista_tratamientos(request):
    tratamientos = Tratamiento.objects.all().select_related('historial__paciente')
    return render(request, 'clinica/lista_tratamientos.html', {'tratamientos': tratamientos})

@login_required
def crear_tratamiento(request):
    if request.method == 'POST':
        form = TratamientoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Plan de tratamiento iniciado con éxito.")
            return redirect('lista_tratamientos')
        else:
            # 1. Imprime los errores en la terminal para que los puedas debugear
            print("Errores del formulario:", form.errors)
            
            # 2. Envía un mensaje de error a la interfaz
            messages.error(request, "Hubo un error al guardar. Por favor revisa los campos.")
    else:
        form = TratamientoForm()
        
    return render(request, 'clinica/crear_tratamiento.html', {'form': form})
