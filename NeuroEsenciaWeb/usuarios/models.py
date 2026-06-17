from django.db import models

class Rol(models.Model):
    ESTADOS = [('Activo', 'Activo'), ('Inactivo', 'Inactivo')]
    
    nombre_rol = models.CharField(max_length=50, unique=True)
    es_superadmin = models.BooleanField(default=False)
    estado_rol = models.CharField(max_length=10, choices=ESTADOS, default='Activo')

    def __str__(self):
        return self.nombre_rol

class Modulo(models.Model):
    nombre_modulo = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.nombre_modulo

class PermisoRol(models.Model):
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE)
    puede_crear = models.BooleanField(default=False)
    puede_leer = models.BooleanField(default=False)
    puede_editar = models.BooleanField(default=False)
    puede_eliminar = models.BooleanField(default=False)

    class Meta:
        unique_together = ('rol', 'modulo')

class Empleado(models.Model):
    DOC_CHOICES = [('CC', 'CC'), ('TI', 'TI'), ('CE', 'CE'), ('PPT', 'PPT'), ('Pasaporte', 'Pasaporte')]
    
    tipo_documento = models.CharField(max_length=15, choices=DOC_CHOICES)
    dni_empleado = models.CharField(max_length=15, unique=True)
    nombre_completo = models.CharField(max_length=100)
    correo = models.EmailField(max_length=100, unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    usuario = models.CharField(max_length=50, unique=True)
    contrasena = models.CharField(max_length=255)
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT)
    estado_empleado = models.CharField(max_length=10, choices=[('Activo', 'Activo'), ('Inactivo', 'Inactivo')], default='Activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre_completo

class Paciente(models.Model):
    DOC_CHOICES = [('CC', 'CC'), ('TI', 'TI'), ('RC', 'RC'), ('CE', 'CE'), ('PPT', 'PPT'), ('Pasaporte', 'Pasaporte')]
    GENERO_CHOICES = [('Masculino', 'Masculino'), ('Femenino', 'Femenino'), ('Otro', 'Otro')]
    CIVIL_CHOICES = [('SOLTERO','Soltero/a'),('CASADO','Casado/a'),('DIVORCIADO','Divorciado/a'),('VIUDO','Viudo/a'),('UNION LIBRE','Unión Libre / Unión Marital de Hecho'),('SEPARADO','Separado/a Legalmente')]
    
    tipo_documento = models.CharField(max_length=15, choices=DOC_CHOICES)
    dni_paciente = models.CharField(max_length=15, unique=True)
    nombre_completo = models.CharField(max_length=200)
    fecha_nacimiento = models.DateField()
    genero = models.CharField(max_length=15, choices=GENERO_CHOICES)
    direccion = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20)
    estado_civil = models.CharField(max_length=25, choices = CIVIL_CHOICES)
    ocupacion = models.CharField(max_length = 200)
    lugar_origen = models.CharField(max_length = 50)
    residencia = models.CharField(max_length = 50)
    correo = models.EmailField(max_length=100, unique=True, blank=True, null=True)
    usuario = models.CharField(max_length=50, unique=True, blank=True, null=True)
    contrasena = models.CharField(max_length=255, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    estado_paciente = models.CharField(max_length=10, choices=[('Activo', 'Activo'), ('Inactivo', 'Inactivo')], default='Activo')

    def __str__(self):
        return f"{self.nombre_completo} - {self.dni_paciente}"