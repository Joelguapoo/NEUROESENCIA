from django.urls import path
from . import views

urlpatterns = [
    path('facturas/', views.lista_facturas, name='lista_facturas'),
    path('facturas/nueva/', views.crear_factura, name='crear_factura'),
    path('facturas/anular/<int:factura_id>/', views.anular_factura, name='anular_factura'),
    path('pago/opciones/<int:cita_id>/', views.pre_facturacion, name='pre_facturacion'),
    path('pago/confirmar/<int:cita_id>/<str:metodo>/', views.generar_pago_automatico, name='generar_pago'),
    path('factura/<int:factura_id>/', views.detalle_factura, name='detalle_factura'),
    path('mis-facturas/', views.mis_facturas, name='mis_facturas'),
    path('exportar-pdf/<int:factura_id>/', views.exportar_factura_pdf, name='exportar_factura_pdf'),
    path('api/citas_pendientes/', views.api_citas_pendientes, name='api_citas_pendientes'),
]
