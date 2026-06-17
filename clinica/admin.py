from django.contrib import admin
from .models import HistorialClinico, Tratamiento, Cita, EvolucionSesion

admin.site.register(HistorialClinico)
admin.site.register(Tratamiento)
admin.site.register(Cita)
admin.site.register(EvolucionSesion)