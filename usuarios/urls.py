from django.urls import path
from . import views
from . import api

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('login/', views.iniciar_sesion, name='iniciar_sesion'),
    path('logout/', views.cerrar_sesion, name='cerrar_sesion'),
    path('bienvenido/', views.bienvenido, name='bienvenido'),
    path('activar/<str:dni>/', views.activar_cuenta, name='activar_cuenta'),
    path('pacientes/', views.lista_pacientes, name='lista_pacientes'),
    path('pacientes/nuevo/', views.crear_paciente, name='crear_paciente'),
    path('pacientes/editar/<int:paciente_id>/', views.editar_paciente, name='editar_paciente'),
    path('pacientes/inactivar/<int:paciente_id>/', views.inactivar_paciente, name='inactivar_paciente'),
    path('equipo/', views.lista_staff, name='lista_staff'),
    path('equipo/nuevo/', views.crear_staff, name='crear_staff'),
    path('equipo/editar/<int:user_id>/', views.editar_staff, name='editar_staff'),
    path('mi-panel/', views.dashboard_paciente, name='dashboard_paciente'),
    path('mi-panel/citas/', views.mis_citas_paciente, name='mis_citas_paciente'),
    path('mis-facturas/', views.mis_facturas, name='mis_facturas'),
    path('mi-panel/agendar/', views.agendar_cita_paciente, name='agendar_cita_paciente'),
    path('obtener-disponibilidad-paciente/', views.obtener_disponibilidad, name='obtener_disponibilidad_paciente'),
    path('staff/inactivar/<int:empleado_id>/', views.inactivar_staff, name='inactivar_staff'),
    path('perfil/', views.perfil_usuario, name='perfil_usuario'),
    path('configuracion/', views.configuracion_sistema, name='configuracion_sistema'),
    path('recuperar-password/', views.recuperar_password, name='recuperar_password'),
    path('restablecer-clave/<str:dni>/', views.restablecer_password, name='restablecer_password'),
    path('verificar-limite/', views.verificar_limite_paciente, name='verificar_limite_paciente'),
    path('pacientes/importar/', views.importar_pacientes_excel, name='importar_pacientes_excel'),
    path('roles/', views.lista_roles, name='lista_roles'),
    path('roles/nuevo/', views.crear_rol, name='crear_rol'),
    path('api/municipios/', api.buscar_municipios, name="api_municipios"),
    path('roles/editar/<int:rol_id>/', views.editar_rol, name='editar_rol'),
    path('roles/cambiar_estado/<int:rol_id>/', views.cambiar_estado_rol, name='cambiar_estado_rol'),
    path('mi-perfil/', views.perfil_paciente, name='perfil_paciente'),

]
