from django.db import models
from usuarios.models import Paciente
from clinica.models import Cita

class MetodoPago(models.Model):
    nombre_metodo = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre_metodo

class Factura(models.Model):
    ESTADOS = [
        ('Pagada', 'Pagada'), 
        ('Pendiente', 'Pendiente'), 
        ('Anulada', 'Anulada')
    ]

    nro_factura = models.CharField(max_length=20, unique=True)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    impuestos = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    estado_pago = models.CharField(max_length=20, choices=ESTADOS, default='Pagada')

    metodo = models.ForeignKey(MetodoPago, on_delete=models.PROTECT)
    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT)
    cita = models.OneToOneField(Cita, on_delete=models.CASCADE) 

    def __str__(self):
        return f"Factura {self.nro_factura} - Total: ${self.total}"