from django import forms
from .models import Factura, MetodoPago
import uuid

class FacturaForm(forms.ModelForm):
    class Meta:
        model = Factura
        fields = ['nro_factura', 'subtotal', 'impuestos', 'metodo', 'paciente', 'cita', 'estado_pago']
        widgets = {
            'nro_factura': forms.HiddenInput(),
            'subtotal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'impuestos': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'metodo': forms.Select(attrs={'class': 'form-select'}),
            'paciente': forms.Select(attrs={'class': 'form-select'}),
            'cita': forms.Select(attrs={'class': 'form-select'}),
            'estado_pago': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial['nro_factura'] = "FAC-" + str(uuid.uuid4().hex[:5]).upper()