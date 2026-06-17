from django import forms
from django.contrib.auth.models import User
from .models import Paciente
from django.core.exceptions import ValidationError
from django import forms
from .models import Rol

class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = [
            'tipo_documento', 'dni_paciente', 'nombre_completo', 
            'fecha_nacimiento', 'genero', 'direccion', 'telefono', 
            'estado_civil', 'ocupacion', 'lugar_origen', 'residencia', 'correo'
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        self.fields['tipo_documento'].widget.attrs.update({'class': 'form-select'})
        self.fields['genero'].widget.attrs.update({'class': 'form-select'})

        if self.instance and self.instance.pk:
            self.fields['tipo_documento'].disabled = True
            self.fields['dni_paciente'].disabled = True
            self.fields['dni_paciente'].help_text = "El documento de identidad no puede ser modificado."

class StaffForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password'] 
        labels = {
            'username': 'Nombre de Usuario',
            'email': 'Correo Electrónico',
            'password': 'Contraseña',
        }
        widgets = {
            'password': forms.PasswordInput(render_value=False),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        if self.instance and self.instance.pk:
            self.fields['username'].disabled = True
            self.fields['password'].required = False
            self.fields['password'].help_text = "Deje en blanco para mantener la contraseña actual."
            self.fields['password'].label = "Nueva Contraseña (opcional)"

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Este correo ya está registrado por otro usuario.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        
        user.is_staff = True 
        if commit:
            user.save()
        return user
    
class RolForm(forms.ModelForm):
    class Meta:
        model = Rol
        fields = ['nombre_rol', 'es_superadmin', 'estado_rol']
        widgets = {
            'nombre_rol': forms.TextInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'Ej: Secretaria, Practicante...'}),
            'estado_rol': forms.Select(attrs={'class': 'form-select rounded-pill'}),
            'es_superadmin': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }