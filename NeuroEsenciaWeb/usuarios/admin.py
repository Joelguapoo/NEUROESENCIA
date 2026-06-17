from django.contrib import admin
from .models import Rol, Modulo, PermisoRol, Empleado, Paciente

admin.site.register(Rol)
admin.site.register(Modulo)
admin.site.register(PermisoRol)
admin.site.register(Empleado)
admin.site.register(Paciente)