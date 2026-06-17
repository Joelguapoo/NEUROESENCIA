from django.db import models
from django.conf import settings 
from usuarios.models import Paciente 
import uuid
from django.db import models
from django.conf import settings


class HistorialClinico(models.Model):
    paciente = models.OneToOneField(Paciente, on_delete=models.CASCADE, related_name='historial') 
    antecedentes_personales = models.TextField(blank=True, null=True)
    antecedentes_familiares = models.TextField(blank=True, null=True)
    
    resumen_historial_ia = models.TextField(
        blank=True, 
        help_text="Resumen global generado por IA para que el psicólogo lea el caso rápido."
    )
    
    fecha_apertura = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Historial de: {self.paciente.nombre_completo}"




class Tratamiento(models.Model):
    ESTADOS = [
        ('Activo', 'Activo'), 
        ('Finalizado', 'Finalizado'), 
        ('Suspendido', 'Suspendido'), 
        ('Derivado', 'Derivado')
    ]
    
    historial = models.ForeignKey(
        HistorialClinico, 
        on_delete=models.CASCADE,
        related_name='tratamientos'
    )
    
    # Especialista asignado (Crucial para que no salga vacío en la tabla)
    psicologo = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT,
        verbose_name="Especialista a Cargo",
        null=True, 
        blank=True
    )
    
    diagnostico = models.CharField(max_length=255, verbose_name="Diagnóstico Principal")
    enfoque_terapeutico = models.CharField(max_length=100, blank=True, null=True)
    objetivos_tratamiento = models.TextField()
    
    # --- CAMPOS IA ---
    sugerencias_enfoque_ia = models.TextField(
        blank=True, 
        help_text="Recomendaciones de la IA basadas en el diagnóstico y objetivos."
    )
    
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(blank=True, null=True)
    estado_tratamiento = models.CharField(max_length=20, choices=ESTADOS, default='Activo')

    class Meta:
        verbose_name = "Tratamiento"
        verbose_name_plural = "Tratamientos"

    def __str__(self):
        return f"{self.diagnostico} - {self.historial.paciente.nombre_completo}"

class Cita(models.Model):
    ESTADOS = [
        ('Programada', 'Programada'), 
        ('Asistida', 'Asistida'), 
        ('Cancelada', 'Cancelada'), 
        ('No Asistió', 'No Asistió')
    ]
    MODALIDADES = [('Presencial', 'Presencial'), ('Virtual', 'Virtual')]
    
    # Le agregamos blank=True para que Django sepa que está bien si llega vacío al principio
    codigo_cita = models.CharField(max_length=20, unique=True, blank=True) 
    fecha_cita = models.DateField()
    hora_cita = models.TimeField()
    modalidad = models.CharField(max_length=20, choices=MODALIDADES)
    estado_cita = models.CharField(max_length=20, choices=ESTADOS, default='Programada')
    
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    psicologo = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self):
        return f"Cita {self.codigo_cita} - {self.paciente.nombre_completo}"

    def save(self, *args, **kwargs):
        if not self.codigo_cita:
            codigo_generado = str(uuid.uuid4())[:6].upper()
            self.codigo_cita = f"CIT-{codigo_generado}"
            
        super().save(*args, **kwargs)









class EvolucionSesion(models.Model):
    ANIMO_CHOICES = [
        ('Aburrimiento', 'Aburrimiento'), ('Aceptacion', 'Aceptación'),
        ('Admiracion', 'Admiración'), ('Alegria', 'Alegría'),
        ('Alivio', 'Alivio'), ('Amor', 'Amor'),
        ('Ansiedad', 'Ansiedad'), ('Apatia', 'Apatía'),
        ('Asombro', 'Asombro'), ('Calma', 'Calma'),
        ('Culpa', 'Culpa'), ('Decepcion', 'Decepción'),
        ('Entusiasmo', 'Entusiasmo'), ('Frustracion', 'Frustración'),
        ('Gratitud', 'Gratitud'), ('Inseguridad', 'Inseguridad'),
        ('Ira', 'Ira'), ('Irritabilidad', 'Irritabilidad'),
        ('Miedo', 'Miedo'), ('Soledad', 'Soledad'),
        ('Tristeza', 'Tristeza'),
    ]

    NIVEL_RIESGO_CHOICES = [
        ('Riesgo Alto', 'Riesgo Alto'),
        ('Riesgo Medio', 'Riesgo Medio'),
        ('Riesgo Bajo', 'Riesgo Bajo'),
        ('Sin Riesgo', 'Sin Riesgo'),
    ]

    AFECTO_CHOICES = [
        ('Congruente', 'Congruente con el relato'),
        ('Aplanado', 'Aplanado/Embotado'),
        ('Labil', 'Lábil (cambios bruscos)'),
        ('Incongruente', 'Incongruente'),
    ]

    cita = models.OneToOneField('Cita', on_delete=models.CASCADE, related_name='evolucion')
    tratamiento = models.ForeignKey('Tratamiento', on_delete=models.CASCADE, null=True, blank=True)
    motivo_consulta = models.TextField(help_text="Razón de la sesión de hoy")
    estado_animo = models.CharField(max_length=30, choices=ANIMO_CHOICES)
    estresores_recientes = models.TextField(blank=True, help_text="Eventos vitales desde la última cita")
    afecto_observado = models.CharField(max_length=30, choices=AFECTO_CHOICES, default='Congruente')
    nivel_energia = models.IntegerField(default=5, help_text="Escala del 1 al 10")
    sueno_alterado = models.BooleanField(default=False)
    apetito_alterado = models.BooleanField(default=False)
    ideacion_suicida = models.BooleanField(default=False, verbose_name="¿Presenta ideación suicida?")
    riesgo = models.CharField(max_length=30, choices=NIVEL_RIESGO_CHOICES)
    descripcion_sesion = models.TextField(help_text="Detalle de lo ocurrido en la sesión")
    evidencia = models.CharField(max_length=250, help_text="Signos clínicos que sustentan el diagnóstico")
    diagnostico_sesion = models.CharField(max_length=255, blank=True, help_text="CIE-10 / DSM-5 o Hipótesis")
    objetivo = models.CharField(max_length=200)
    recomendaciones = models.TextField(blank=True)
    proximo_paso = models.TextField(blank=True, null=True, help_text="Tareas o temas para la siguiente sesión")
    
    analisis_sentimiento_ia = models.CharField(
        max_length=100, blank=True, 
        help_text="Análisis automático de congruencia entre el relato y el afecto observado."
    )
    resumen_ia = models.TextField(
        blank=True, 
        help_text="Resumen ejecutivo estructurado por la IA."
    )
    alertas_riesgo_ia = models.JSONField(
        default=dict, blank=True,
        help_text="Detección automática de palabras clave de riesgo en la descripción."
    )
    
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evolución Cita: {self.cita.codigo_cita} - {self.cita.paciente.nombre_completo}"