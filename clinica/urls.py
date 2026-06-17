from django.urls import path
from . import views

urlpatterns = [
    path('citas/', views.lista_citas, name='lista_citas'),
    path('citas/agendar/', views.agendar_cita, name='agendar_cita'),
    path('citas/<int:cita_id>/evolucion/', views.registrar_evolucion, name='registrar_evolucion'),
    path('historial/<int:paciente_id>/', views.ver_historial, name='ver_historial'),
    path('evolucion/<int:evolucion_id>/pdf/', views.exportar_evolucion_pdf, name='descargar_pdf'),
    path('citas/estado/<int:cita_id>/', views.actualizar_estado_cita, name='actualizar_estado_cita'),
    path('paciente/<int:paciente_id>/antecedentes/', views.editar_antecedentes, name='editar_antecedentes'),
    path('evolucion/<int:pk>/editar/', views.editar_evolucion, name='editar_evolucion'),
    path('editar-cita/<int:cita_id>/', views.editar_cita, name='editar_cita'),
    path('obtener-disponibilidad/', views.obtener_disponibilidad, name='obtener_disponibilidad'),
    path('verificar-limite-paciente/', views.verificar_limite_paciente, name='verificar_limite_paciente'),
    path('tratamientos/', views.lista_tratamientos, name='lista_tratamientos'),
    path('tratamientos/nuevo/', views.crear_tratamiento, name='crear_tratamiento'),
]