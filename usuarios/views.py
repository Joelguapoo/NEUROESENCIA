import threading
import uuid
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import User, Group
from .models import Paciente, Empleado, Rol
from .forms import PacienteForm, StaffForm
from clinica.models import Cita, EvolucionSesion
from facturacion.models import Factura, MetodoPago
from datetime import timedelta
from facturacion.models import Paciente
from django.db import transaction
import pandas as pd
from django.db import transaction
from .forms import RolForm


def inicio(request):
    """Vista de la Landing Page principal de la clínica"""
    return render(request, 'usuarios/inicio.html')

@login_required
def bienvenido(request):
    hora = timezone.now().hour
    if hora < 12:
        saludo = "¡Buenos días!"
    elif hora < 18:
        saludo = "¡Buenas tardes!"
    else:
        saludo = "¡Buenas noches!"
        
    total_pacientes = Paciente.objects.count()
    citas_pendientes = Cita.objects.filter(estado_cita='Programada').count()
    citas_asistidas = Cita.objects.filter(estado_cita='Asistida').count()
    citas_canceladas = Cita.objects.filter(estado_cita__in=['Cancelada', 'No Asistió']).count()
    
    actividad_reciente = Cita.objects.all().order_by('-id')[:4]
    hoy = timezone.localdate()
    citas_hoy = Cita.objects.filter(fecha_cita=hoy).order_by('hora_cita')
    
    modalidad_virtual = Cita.objects.filter(modalidad='Virtual').count()
    modalidad_presencial = Cita.objects.filter(modalidad='Presencial').count()
    total_modalidad = modalidad_virtual + modalidad_presencial
    
    porcentaje_virtual = int((modalidad_virtual / total_modalidad) * 100) if total_modalidad > 0 else 0
    porcentaje_presencial = int((modalidad_presencial / total_modalidad) * 100) if total_modalidad > 0 else 0

    return render(request, 'usuarios/bienvenido.html', {
        'saludo': saludo,
        'nombre': request.user.first_name if request.user.first_name else request.user.username,
        'total_pacientes': total_pacientes,
        'citas_pendientes': citas_pendientes,
        'citas_asistidas': citas_asistidas,
        'citas_canceladas': citas_canceladas,
        'actividad_reciente': actividad_reciente,
        'citas_hoy': citas_hoy,
        'porcentaje_virtual': porcentaje_virtual,
        'porcentaje_presencial': porcentaje_presencial,
        'modalidad_virtual': modalidad_virtual,
        'modalidad_presencial': modalidad_presencial
    })

@login_required
def lista_pacientes(request):
    busqueda = request.GET.get('search')
    filtro_estado = request.GET.get('estado', 'todos')
    hace_60_dias = timezone.localdate() - timedelta(days=60)
    pacientes_a_inactivar = Paciente.objects.filter(estado_paciente='Activo').exclude(
        Q(cita__fecha_cita__gte=hace_60_dias) | Q(fecha_registro__gte=hace_60_dias)
    ).distinct()
    
    if pacientes_a_inactivar.exists():
        pacientes_a_inactivar.update(estado_paciente='Inactivo')

    query = Q()
    if busqueda:
        query &= (Q(nombre_completo__icontains=busqueda) | Q(dni_paciente__icontains=busqueda))
        
    if filtro_estado == 'activos':
        query &= Q(estado_paciente='Activo')
    elif filtro_estado == 'inactivos':
        query &= Q(estado_paciente='Inactivo')

    pacientes = Paciente.objects.filter(query)

    contexto = {
        'pacientes': pacientes, 
        'total_pacientes': Paciente.objects.count(),
        'citas_agendadas': Cita.objects.filter(estado_cita='Programada').count(),
        'sesiones_hoy': Cita.objects.filter(fecha_cita=timezone.localdate()).count(),
        'busqueda': busqueda,
        'filtro_estado': filtro_estado
    }
    return render(request, 'usuarios/lista_pacientes.html', contexto)

def enviar_correo_en_segundo_plano(asunto, mensaje, destinatario):
    try:
        send_mail(
            asunto, 
            mensaje, 
            settings.EMAIL_HOST_USER, 
            [destinatario]
        )
    except Exception as e:
        print(f"Error enviando correo en segundo plano: {e}")


def crear_paciente(request):
    if request.method == 'POST':
        form = PacienteForm(request.POST)
        if form.is_valid():
            paciente = form.save() 
            host = request.get_host()
            esquema = request.scheme
            url_activacion = f"{esquema}://{host}/activar/{paciente.dni_paciente}/"
            
            mensaje = f"""Estimado/a {paciente.nombre_completo},

Nos llena de alegría darte la bienvenida a NeuroEsencia. Tu expediente clínico digital ha sido creado exitosamente en nuestro sistema.

Para finalizar tu registro y acceder a tu portal de paciente —donde podrás agendar tus sesiones, consultar tus facturas y llevar un seguimiento de tu proceso— es necesario activar tu cuenta.

Por favor, ingresa al siguiente enlace seguro para crear tus credenciales de acceso:
🔗 {url_activacion}

Por protocolos de privacidad y protección de datos médicos, te recomendamos no compartir este enlace con nadie. Si no esperabas este correo, puedes ignorarlo de manera segura.

Atentamente,

El equipo de NeuroEsencia
Ciencia y Bienestar integral
"""
            
            # ---> NUEVA LÓGICA DE CORREO <---
            hilo = threading.Thread(
                target=enviar_correo_en_segundo_plano, 
                args=('Bienvenido a NeuroEsencia', mensaje, paciente.correo)
            )
            hilo.start() # Esto lanza el correo y continúa sin esperar
            
            messages.success(request, f"Paciente {paciente.nombre_completo} creado. El correo de activación está en camino.")
            return redirect('lista_pacientes')
    else:
        form = PacienteForm()
    return render(request, 'usuarios/crear_paciente.html', {'form': form, 'editando': False})

@login_required
def editar_paciente(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    if not (request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()):
        messages.error(request, "Acceso denegado.")
        return redirect('lista_pacientes')

    if request.method == 'POST':
        form = PacienteForm(request.POST, instance=paciente)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos actualizados.")
            return redirect('lista_pacientes')
    else:
        form = PacienteForm(instance=paciente)
    return render(request, 'usuarios/crear_paciente.html', {'form': form, 'editando': True, 'paciente': paciente})

@login_required
def inactivar_paciente(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    
    if request.method == 'POST':
        if paciente.estado_paciente == 'Activo':
            paciente.estado_paciente = 'Inactivo'
            accion = "inactivado"
        else:
            paciente.estado_paciente = 'Activo'
            accion = "reactivado"
            
        paciente.save()
        
        return JsonResponse({'status': 'success', 'mensaje': f'El paciente {paciente.nombre_completo} ha sido {accion} correctamente.'})
    
    return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=400)

def mis_citas_paciente(request):
    p_id = request.session.get('paciente_id')
    if not p_id: return redirect('iniciar_sesion')
    
    paciente = get_object_or_404(Paciente, id=p_id)
    citas = Cita.objects.filter(paciente=paciente).order_by('-fecha_cita')
    return render(request, 'usuarios/mis_citas_paciente.html', {'paciente': paciente, 'citas': citas})

def dashboard_paciente(request):
    p_id = request.session.get('paciente_id')
    if not p_id: return redirect('iniciar_sesion')
    
    paciente = get_object_or_404(Paciente, id=p_id)
    ultima_evolucion = EvolucionSesion.objects.filter(cita__paciente=paciente).order_by('-fecha_registro').first()
    facturas = Factura.objects.filter(paciente=paciente).order_by('-id')[:5]

    contexto = {
        'paciente': paciente,
        'proximas_citas': Cita.objects.filter(paciente=paciente, fecha_cita__gte=timezone.localdate()).order_by('fecha_cita')[:3],
        'datos_progreso': [5, 7, 6, 8, 9], 
        'etiquetas_progreso': ["Ene", "Feb", "Mar", "Abr", "May"],
        'saludo': "Bienvenido",
        'ultima_evolucion': ultima_evolucion,
        'facturas': facturas,
    }
    return render(request, 'usuarios/dashboard_paciente.html', contexto)


def agendar_cita_paciente(request):
    p_id = request.session.get('paciente_id')
    if not p_id: return redirect('iniciar_sesion')
    paciente = get_object_or_404(Paciente, pk=p_id)

    if request.method == 'POST':
        psico_id = request.POST.get('psicologo')
        fecha = request.POST.get('fecha')
        hora = request.POST.get('hora')
        
        if psico_id and fecha and hora:
            try:
                # --- NUEVA VALIDACIÓN DE LÍMITE (Backend) ---
                if Cita.objects.filter(
                    paciente=paciente, 
                    fecha_cita=fecha
                ).exclude(estado_cita__in=['Cancelada', 'No Asistió']).exists():
                    messages.error(request, "Por políticas de la clínica, solo puedes agendar una cita por día. Por favor selecciona otra fecha.")
                    return redirect('agendar_cita_paciente')
                # -------------------------------------------

                especialista_empleado = get_object_or_404(Empleado, pk=psico_id)
                usuario_psicologo = User.objects.get(username=especialista_empleado.usuario)
                codigo_generado = f"CIT-{str(uuid.uuid4().hex[:6]).upper()}"

                # Bloque transaccional: Si falla la factura o el correo, no se crea la cita vacía
                with transaction.atomic():
                    cita_nueva = Cita.objects.create(
                        paciente=paciente, psicologo=usuario_psicologo, fecha_cita=fecha,
                        hora_cita=hora, codigo_cita=codigo_generado, modalidad='Virtual', estado_cita='Programada'
                    )
                    
                    # LÍNEA MÁGICA: Obliga a Django a convertir los textos en objetos Fecha/Hora
                    cita_nueva.refresh_from_db()
                    
                    metodo_defecto, _ = MetodoPago.objects.get_or_create(nombre_metodo='Por Definir')
                    
                    # --- AQUÍ ESTÁ LA CORRECCIÓN DEL NRO_FACTURA ---
                    nueva_factura = Factura.objects.create(
                        nro_factura=f"FAC-{uuid.uuid4().hex[:8].upper()}",
                        cita=cita_nueva, paciente=paciente, metodo=metodo_defecto,
                        subtotal=50000, impuestos=0, total=50000, estado_pago='Pendiente'
                    )
                
                    # --- IMPORTACIÓN LOCAL PARA EVITAR CONFLICTOS ---
                    from clinica.views import enviar_confirmacion_cita
                    
                    # ---> APLICAMOS EL HILO PARA EVITAR EL ERROR 500 EN RAILWAY <---
                    hilo_correo = threading.Thread(
                        target=enviar_confirmacion_cita, 
                        args=(cita_nueva,)
                    )
                    hilo_correo.start()
                    
                # Respondemos de inmediato al paciente
                messages.success(request, "¡Cita reservada! La confirmación y el PDF se están enviando a tu correo en segundo plano.")
                return redirect('detalle_factura', factura_id=nueva_factura.id) 
                
            except Exception as e:
                messages.error(request, f"Error al agendar la cita: {e}")
                return redirect('agendar_cita_paciente')
        else:
            messages.error(request, "Faltan datos en el formulario.")
            return redirect('agendar_cita_paciente')

    psicologos = Empleado.objects.filter(rol__nombre_rol='Psicologo', estado_empleado='Activo') 
    return render(request, 'usuarios/agendar_cita_paciente.html', {'psicologos': psicologos})


def verificar_limite_paciente(request):
    """Verifica si el paciente ya tiene una cita el día seleccionado (Devuelve JSON)"""
    
    # 1. Seguridad: Verificar que sea un paciente logueado o un administrador
    if 'paciente_id' not in request.session and not request.user.is_authenticated:
        return JsonResponse({'error': 'No autorizado'}, status=401)

    paciente_id = request.GET.get('paciente_id')
    fecha = request.GET.get('fecha')
    tiene_cita = False
    
    if paciente_id and fecha:
        tiene_cita = Cita.objects.filter(
            paciente_id=paciente_id, 
            fecha_cita=fecha
        ).exclude(estado_cita__in=['Cancelada', 'No Asistió']).exists()
        
    return JsonResponse({'tiene_cita': tiene_cita})

@login_required
def mis_facturas(request):
    try:
        paciente_actual = Paciente.objects.get(usuario=request.user)
        request.session['paciente_id'] = paciente_actual.id 
        
        facturas = Factura.objects.filter(paciente=paciente_actual).order_by('-fecha_emision')
        
        return render(request, 'facturacion/mis_facturas.html', {
            'facturas': facturas, 
            'paciente': paciente_actual
        })
        
    except Paciente.DoesNotExist:
        return redirect('iniciar_sesion')


def iniciar_sesion(request):
    if request.user.is_authenticated: return redirect('bienvenido')
    if 'paciente_id' in request.session: return redirect('dashboard_paciente')

    if request.method == 'POST':
        usuario = request.POST.get('username')
        clave = request.POST.get('password')
        
        user = authenticate(request, username=usuario, password=clave)
        if user:
            login(request, user)
            return redirect('bienvenido')
            
        try:
            paciente = Paciente.objects.get(usuario=usuario)
            
            if paciente.estado_paciente == 'Inactivo':
                messages.error(request, "Tu cuenta se encuentra inactiva. Por favor, comunícate con la clínica.")
                return render(request, 'usuarios/login.html', {'ocultar_sidebar': True})
            
            if check_password(clave, paciente.contrasena):
                request.session['paciente_id'] = paciente.id
                return redirect('dashboard_paciente')
            messages.error(request, "Contraseña incorrecta")
            
        except Paciente.DoesNotExist:
            messages.error(request, "El usuario no existe")
            
    return render(request, 'usuarios/login.html', {'ocultar_sidebar': True})

def cerrar_sesion(request):
    logout(request)
    request.session.flush()
    return redirect('iniciar_sesion')

def activar_cuenta(request, dni):
    paciente = get_object_or_404(Paciente, dni_paciente=dni)
    if request.method == 'POST':
        paciente.usuario = request.POST.get('usuario')
        paciente.contrasena = make_password(request.POST.get('password'))
        paciente.save()
        return render(request, 'usuarios/activacion_exitosa.html')
    return render(request, 'usuarios/crear_credenciales.html', {'paciente': paciente})

@login_required
def lista_staff(request):
    if not (request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()): 
        return redirect('lista_pacientes')
    
    busqueda = request.GET.get('search')
    filtro_estado = request.GET.get('estado', 'todos')
    
    query = Q()
    if busqueda:
        query &= (Q(nombre_completo__icontains=busqueda) | Q(dni_empleado__icontains=busqueda))
        
    if filtro_estado == 'activos':
        query &= Q(estado_empleado='Activo')
    elif filtro_estado == 'inactivos':
        query &= Q(estado_empleado='Inactivo')
        
    equipo = Empleado.objects.filter(query).order_by('nombre_completo')
    
    contexto = {
        'equipo': equipo,
        'busqueda': busqueda,
        'filtro_estado': filtro_estado,
        'total_staff': Empleado.objects.count()
    }
    return render(request, 'usuarios/lista_staff.html', contexto)

@login_required
def crear_staff(request):
    if not (request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()): 
        return redirect('lista_pacientes')
        
    if request.method == 'POST':
        form = StaffForm(request.POST)
        rol_id = request.POST.get('rol') 

        if form.is_valid() and rol_id:
            try:
                user = form.save(commit=False)
                nombre_completo = request.POST.get('nombre_completo', '')
                partes_nombre = nombre_completo.split(' ', 1)
                user.first_name = partes_nombre[0]
                if len(partes_nombre) > 1:
                    user.last_name = partes_nombre[1]
                user.save() 
                
                rol_db = get_object_or_404(Rol, pk=rol_id)
                grupo, _ = Group.objects.get_or_create(name=rol_db.nombre_rol)
                user.groups.add(grupo)
                
                Empleado.objects.create(
                    tipo_documento=request.POST.get('tipo_documento'),
                    dni_empleado=request.POST.get('dni_empleado'),
                    nombre_completo=nombre_completo,
                    correo=user.email,
                    telefono=request.POST.get('telefono', ''),
                    usuario=user.username,
                    contrasena=user.password, 
                    rol=rol_db
                )
                
                messages.success(request, f"Colaborador {user.username} creado con éxito.")
                return redirect('lista_staff')
                
            except Exception as e:
                if user.id:
                    user.delete() 
                messages.error(request, f"Error de base de datos: {e}")
        else:
            messages.error(request, "El formulario no se pudo guardar:")
            if not rol_id:
                messages.error(request, "➜ Te faltó seleccionar un 'Rol en el Sistema'.")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"➜ Campo '{field}': {error}")
    else:
        form = StaffForm()
        
    roles_disponibles = Rol.objects.filter(estado_rol='Activo')
    return render(request, 'usuarios/crear_staff.html', {
        'form': form,
        'roles_disponibles': roles_disponibles
    })
    
@login_required
def editar_staff(request, user_id):
    if not (request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()):
        return redirect('lista_pacientes')
    
    user = get_object_or_404(User, id=user_id)
    empleado = Empleado.objects.filter(usuario=user.username).first()
    
    if request.method == 'POST':
        form = StaffForm(request.POST, instance=user)
        rol_id = request.POST.get('rol')
        
        if form.is_valid() and rol_id:
            user = form.save(commit=False)
            nombre_completo = request.POST.get('nombre_completo', '')
            partes = nombre_completo.split(' ', 1)
            user.first_name = partes[0]
            user.last_name = partes[1] if len(partes) > 1 else ''
            user.save()
            
            rol_db = get_object_or_404(Rol, pk=rol_id)
            user.groups.clear()
            grupo, _ = Group.objects.get_or_create(name=rol_db.nombre_rol)
            user.groups.add(grupo)

            if not empleado:
                empleado = Empleado(usuario=user.username)
                
            empleado.nombre_completo = nombre_completo
            empleado.dni_empleado = request.POST.get('dni_empleado')
            empleado.tipo_documento = request.POST.get('tipo_documento')
            empleado.telefono = request.POST.get('telefono', '')
            empleado.correo = user.email
            empleado.rol = rol_db
            empleado.save()
            
            messages.success(request, f"Personal {user.username} actualizado.")
            return redirect('lista_staff')
    else:
        form = StaffForm(instance=user)
    
    roles_disponibles = Rol.objects.filter(estado_rol='Activo')
    return render(request, 'usuarios/crear_staff.html', {
        'form': form,
        'roles_disponibles': roles_disponibles,
        'editando': True,
        'empleado': empleado
    })

@login_required
def inactivar_staff(request, empleado_id):
    if not (request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()):
        return JsonResponse({'status': 'error', 'mensaje': 'No tienes permisos para esta acción.'}, status=403)
    
    empleado = get_object_or_404(Empleado, id=empleado_id)
    user_django = get_object_or_404(User, username=empleado.usuario)

    if user_django == request.user:
        return JsonResponse({'status': 'error', 'mensaje': 'No puedes inactivar tu propia cuenta de administrador.'}, status=400)

    if request.method == 'POST':
        if empleado.estado_empleado == 'Activo':
            empleado.estado_empleado = 'Inactivo'
            user_django.is_active = False
            accion = "inactivado"
        else:
            empleado.estado_empleado = 'Activo'
            user_django.is_active = True
            accion = "reactivado"
            
        empleado.save()
        user_django.save()
        
        return JsonResponse({'status': 'success', 'mensaje': f'El colaborador {empleado.nombre_completo} ha sido {accion}.'})
    
    return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=400)
    
def obtener_disponibilidad(request):
    """Devuelve las horas ocupadas de un psicólogo en formato JSON para el paciente."""
    
    # 1. Seguridad: Verificar que quien consulta sea un paciente logueado o personal administrativo
    if 'paciente_id' not in request.session and not request.user.is_authenticated:
        return JsonResponse({'error': 'No autorizado'}, status=401)

    psicologo_id = request.GET.get('psicologo_id')
    ocupados = []

    if psicologo_id:
        try:
            # 2. Obtener el Empleado que seleccionó el paciente
            empleado = get_object_or_404(Empleado, pk=psicologo_id)
            
            # 3. CONVERSIÓN VITAL: Obtener el ID del Usuario Django asociado a ese empleado
            user_id = User.objects.get(username=empleado.usuario).id
            
            # 4. Filtrar las citas usando el ID del Usuario (igual que en el módulo administrativo)
            citas = Cita.objects.filter(psicologo_id=user_id).exclude(estado_cita__in=['Cancelada', 'No Asistió'])
            
            for cita in citas:
                fecha_str = cita.fecha_cita.strftime('%Y-%m-%d') if hasattr(cita.fecha_cita, 'strftime') else str(cita.fecha_cita)
                hora_str = cita.hora_cita.strftime('%H:%M') if hasattr(cita.hora_cita, 'strftime') else str(cita.hora_cita)[:5]
                ocupados.append({'fecha': fecha_str, 'hora': hora_str})
                
        except (Empleado.DoesNotExist, User.DoesNotExist, Exception) as e:
            # Si hay un error interno, capturarlo e imprimirlo en la consola del servidor
            # Devolvemos un JSON vacío en lugar de romper la app para evitar el "Error de conexión"
            print(f"Error interno al obtener disponibilidad: {e}")
            return JsonResponse({'ocupados': []})

    return JsonResponse({'ocupados': ocupados})

def configuracion_sistema(request):
    """Renderiza la página de personalización de colores y fuentes."""
    return render(request, 'usuarios/configuracion.html')


@login_required
def perfil_usuario(request):
    """Maneja el perfil dinámico para Pacientes, Staff y Superusuarios de Consola."""
    es_paciente = 'paciente_id' in request.session
    perfil_obj = None
    es_superuser_consola = False

    if es_paciente:
        perfil_obj = get_object_or_404(Paciente, id=request.session['paciente_id'])
    else:
        # Intentamos buscar el empleado
        empleado = Empleado.objects.filter(usuario=request.user.username).first()
        if empleado:
            perfil_obj = empleado
        else:
            # SOLUCIÓN AL 404: Si no hay empleado (creado por consola), usamos el User nativo de Django
            perfil_obj = request.user
            es_superuser_consola = True

    if request.method == 'POST':
        if es_superuser_consola:
            # Actualizamos los datos básicos del superusuario de consola
            perfil_obj.first_name = request.POST.get('nombre_completo', '')
            perfil_obj.email = request.POST.get('correo', '')
            perfil_obj.save()
        else:
            # Actualizamos al empleado o paciente
            perfil_obj.nombre_completo = request.POST.get('nombre_completo')
            perfil_obj.correo = request.POST.get('correo')
            perfil_obj.telefono = request.POST.get('telefono')
            
            if not es_paciente:
                # Sincronizamos con el User nativo de Django
                user_django = request.user
                user_django.email = perfil_obj.correo
                nombres = perfil_obj.nombre_completo.split(' ')
                user_django.first_name = nombres[0] if nombres else ''
                user_django.save()
                
            perfil_obj.save()
            
        messages.success(request, "¡Tu perfil se ha actualizado bajo estrictos protocolos de seguridad!")
        return redirect('perfil_usuario')

    return render(request, 'usuarios/perfil.html', {
        'perfil': perfil_obj,
        'es_paciente': es_paciente,
        'es_superuser_consola': es_superuser_consola
    })
from django.urls import reverse

def recuperar_password(request):
    """Paso 1: Valida el correo y envía el link único"""
    if request.method == 'POST':
        email_input = request.POST.get('email')
        paciente = Paciente.objects.filter(correo=email_input).first()
        
        if paciente:
            host = request.get_host()
            link_recuperacion = f"{request.scheme}://{host}/restablecer-clave/{paciente.dni_paciente}/"
            
            asunto = "Restablece tu acceso a NeuroEsencia"
            mensaje = f"Hola {paciente.nombre_completo},\n\nHemos recibido una solicitud para restablecer tu contraseña. Haz clic en el siguiente enlace para continuar:\n\n{link_recuperacion}\n\nSi no fuiste tú, ignora este mensaje."
            
            hilo = threading.Thread(
                target=enviar_correo_en_segundo_plano, 
                args=(asunto, mensaje, email_input)
            )
            hilo.start()
            
            messages.success(request, "¡Enlace enviado! Revisa tu correo electrónico.")
        else:
            messages.error(request, "Este correo no está registrado en nuestro sistema.")
            
    return render(request, 'usuarios/recuperar_password.html')

def restablecer_password(request, dni):
    """Paso 2: La página moderna y grande para cambiar la clave"""
    paciente = get_object_or_404(Paciente, dni_paciente=dni)
    
    if request.method == 'POST':
        nueva_clave = request.POST.get('password')
        confirmar_clave = request.POST.get('confirm_password')
        
        if nueva_clave == confirmar_clave:
            paciente.contrasena = make_password(nueva_clave)
            paciente.save()
            messages.success(request, "¡Excelente! Tu contraseña ha sido actualizada. Ya puedes entrar.")
            return redirect('iniciar_sesion')
        else:
            messages.error(request, "Las contraseñas no coinciden. Inténtalo de nuevo.")
            
    return render(request, 'usuarios/restablecer_password.html', {'paciente': paciente})


@login_required
def importar_pacientes_excel(request):
    if not (request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()):
        return redirect('lista_pacientes')

    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        archivo = request.FILES['archivo_excel']
        
        try:
            df = pd.read_excel(archivo)
            df.columns = df.columns.str.strip().str.lower()

            # 1. Definimos campos obligatorios para procesar (DNI y Fecha son vitales)
            if 'dni' not in df.columns or 'fecha_nacimiento' not in df.columns:
                messages.error(request, "El Excel debe tener al menos 'dni' y 'fecha_nacimiento'.")
                return redirect('importar_pacientes_excel')

            creados = 0
            with transaction.atomic():
                for _, row in df.iterrows():
                    # --- FUNCIÓN DE LIMPIEZA INTERNA ---
                    # Si el valor es nulo o vacío, devuelve "SIN INFORMACIÓN"
                    def limpiar(valor, default="SIN INFORMACIÓN"):
                        if pd.isna(valor) or str(valor).strip() == "" or str(valor).lower() == "nan":
                            return default
                        return str(valor).strip()

                    # Tratamiento especial para la fecha (No puede ser "Sin información")
                    fecha_raw = row.get('fecha_nacimiento')
                    if pd.isna(fecha_raw):
                        fecha_dt = datetime(2000, 1, 1).date() # Fecha por defecto si no hay nada
                    elif isinstance(fecha_raw, str):
                        fecha_dt = datetime.strptime(fecha_raw, '%Y-%m-%d').date()
                    else:
                        fecha_dt = fecha_raw

                    # --- GUARDADO CON VALORES POR DEFECTO ---
                    Paciente.objects.update_or_create(
                        dni_paciente=str(row['dni']),
                        defaults={
                            'tipo_documento': limpiar(row.get('tipo_documento'), "CC"),
                            'nombre_completo': limpiar(row.get('nombre_completo')),
                            'fecha_nacimiento': fecha_dt,
                            'genero': limpiar(row.get('genero'), "Otro"),
                            'telefono': limpiar(row.get('telefono'), "0000000"),
                            'estado_civil': limpiar(row.get('estado_civil'), "SOLTERO").upper(),
                            'ocupacion': limpiar(row.get('ocupacion')),
                            'lugar_origen': limpiar(row.get('lugar_origen')),
                            'residencia': limpiar(row.get('residencia')),
                            'correo': row.get('correo') if pd.notnull(row.get('correo')) else None,
                            'estado_paciente': 'Activo'
                        }
                    )
                    creados += 1

            messages.success(request, f"¡Importación Exitosa! Se procesaron {creados} registros.")
            return redirect('lista_pacientes')

        except Exception as e:
            messages.error(request, f"Error técnico al procesar: {e}")
            
    return render(request, 'usuarios/importar_pacientes.html')

from .forms import RolForm

@login_required
def lista_roles(request):
    roles = Rol.objects.all()
    return render(request, 'usuarios/lista_roles.html', {'roles': roles})

@login_required
def crear_rol(request):
    if request.method == 'POST':
        form = RolForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Nuevo rol administrativo creado.")
            return redirect('lista_roles')
    else:
        form = RolForm()
    return render(request, 'usuarios/crear_rol.html', {'form': form})

# --- Añadir al final de tu views.py ---

@login_required
def editar_rol(request, rol_id):
    # Opcional: Seguridad para que solo administradores editen roles
    if not (request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()):
        messages.error(request, "No tienes permisos para editar roles.")
        return redirect('lista_roles')
        
    rol = get_object_or_404(Rol, id=rol_id)
    
    if request.method == 'POST':
        form = RolForm(request.POST, instance=rol)
        if form.is_valid():
            form.save()
            messages.success(request, f"El rol '{rol.nombre_rol}' ha sido actualizado correctamente.")
            return redirect('lista_roles')
        else:
            messages.error(request, "Revisa los errores del formulario.")
    else:
        form = RolForm(instance=rol)
        
    return render(request, 'usuarios/crear_rol.html', {'form': form, 'editando': True, 'rol': rol})

@login_required
def cambiar_estado_rol(request, rol_id):
    """Vista que responde al fetch de SweetAlert2 en JavaScript"""
    if not (request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()):
        return JsonResponse({'status': 'error', 'mensaje': 'No tienes permisos para esta acción.'}, status=403)
        
    rol = get_object_or_404(Rol, id=rol_id)
    
    if request.method == 'POST':
        if rol.estado_rol == 'Activo':
            rol.estado_rol = 'Inactivo'
            accion = "inactivado"
        else:
            rol.estado_rol = 'Activo'
            accion = "reactivado"
            
        rol.save()
        return JsonResponse({
            'status': 'success', 
            'mensaje': f'El rol {rol.nombre_rol} ha sido {accion} exitosamente.'
        })
        
    return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=400)
