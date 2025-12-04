from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import UsuarioCustom

# Formulario para Registrarse (Hereda del estándar de Django pero usa tu modelo)
class RegistroUsuarioForm(UserCreationForm):
    # Añadimos email como obligatorio visualmente
    email = forms.EmailField(required=True)

    class Meta:
        model = UsuarioCustom
        # Campos que el usuario llena al registrarse
        fields = ['email'] 
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@correo.com'}),
        }
    def save(self, commit=True):
        user = super().save(commit=False)
        # Como quitamos el campo username del formulario, 
        # le asignamos el valor del email automáticamente.
        user.username = user.email 
        
        if commit:
            user.save()
        return user

# Formulario para Editar Perfil (Sin contraseña)
class EditarUsuarioForm(forms.ModelForm):
    class Meta:
        model = UsuarioCustom
        fields = ['email', 'numero_telefono', 'first_name', 'last_name']
        labels = {
            'email': 'Correo Electrónico (No editable)',
            'numero_telefono': 'Teléfono (WhatsApp)',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
        }
        widgets = {
            'numero_telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+56912345678'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            # El widget de email lo configuramos abajo, pero le damos estilo base aquí
            'email': forms.TextInput(attrs={'class': 'form-control'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Protegemos el email para que sea solo lectura
        if 'email' in self.fields:
            self.fields['email'].disabled = True