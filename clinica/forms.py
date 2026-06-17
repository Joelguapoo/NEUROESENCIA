from django import forms
from .models import HistorialClinico, Cita, EvolucionSesion
import uuid

class CitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        fields = ['paciente', 'psicologo', 'fecha_cita', 'hora_cita', 'modalidad']
        
        widgets = {
            'fecha_cita': forms.DateInput(
                format='%Y-%m-%d', 
                attrs={'type': 'date', 'class': 'form-control', 'id': 'id_fecha_cita'}
            ),
            'hora_cita': forms.TimeInput(
                format='%H:%M', 
                attrs={'type': 'time', 'class': 'form-control', 'id': 'id_hora_cita'}
            ),
            'modalidad': forms.Select(attrs={'class': 'form-select'}),
            'paciente': forms.Select(attrs={'class': 'form-select', 'id': 'id_paciente'}),
            'psicologo': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['fecha_cita'].initial = self.instance.fecha_cita
            self.fields['hora_cita'].initial = self.instance.hora_cita

class EvolucionForm(forms.ModelForm):
    class Meta:
        model = EvolucionSesion
        exclude = ['cita', 'fecha_registro', 'analisis_sentimiento_ia', 'resumen_ia', 'alertas_riesgo_ia']
        widgets = {
            'nivel_energia': forms.NumberInput(attrs={'class': 'form-range', 'type': 'range', 'min': '1', 'max': '10'}),
            'sueno_alterado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'apetito_alterado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ideacion_suicida': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name not in ['sueno_alterado', 'apetito_alterado', 'ideacion_suicida', 'nivel_energia']:
                field.widget.attrs.update({'class': 'form-control' if not isinstance(field.widget, forms.Select) else 'form-select'})
        self.fields['ideacion_suicida'].label = "¿Presenta ideación suicida?"

class HistorialClinicoForm(forms.ModelForm):
    class Meta:
        model = HistorialClinico
        fields = ['antecedentes_personales', 'antecedentes_familiares']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control', 'rows': 4})

from django import forms
from .models import Tratamiento

class TratamientoForm(forms.ModelForm):
    class Meta:
        model = Tratamiento
        fields = ['historial', 'diagnostico', 'enfoque_terapeutico', 'objetivos_tratamiento', 'fecha_inicio', 'fecha_fin', 'estado_tratamiento']
        widgets = {
            'historial': forms.Select(attrs={'class': 'form-select rounded-pill'}),
            'diagnostico': forms.TextInput(attrs={'class': 'form-control rounded-pill'}),
            'enfoque_terapeutico': forms.TextInput(attrs={'class': 'form-control rounded-pill'}),
            'objetivos_tratamiento': forms.Textarea(attrs={'class': 'form-control rounded-4', 'rows': 3}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control rounded-pill', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control rounded-pill', 'type': 'date'}),
            'estado_tratamiento': forms.Select(attrs={'class': 'form-select rounded-pill'}),
        }