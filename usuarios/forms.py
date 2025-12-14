from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import UsuarioCustom
from django.core.validators import RegexValidator


solo_numeros = RegexValidator(r'^\d{8}$', 'Ingresa solo los 8 dígitos de tu número (Ej: 98765432).')

class RegistroUsuarioForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@correo.com'}))
    
    # CAMBIO: Campo teléfono restringido
    numero_telefono = forms.CharField(
        max_length=8,
        min_length=8,
        required=False,
        validators=[solo_numeros],
        label="Teléfono Móvil",
        help_text="Ingresa los 8 dígitos después del +569",
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': '12345678',
            'type': 'tel',      # Activa teclado numérico en móviles
            'pattern': '[0-9]*', # Refuerzo para móviles
            'maxlength': '8'     # Límite visual HTML
        })
    )

    class Meta:
        model = UsuarioCustom
        fields = ['email', 'numero_telefono'] 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Recorremos TODOS los campos (incluidos los de contraseña que hereda UserCreationForm)
        for field_name, field in self.fields.items():
            # Si el campo no tiene la clase form-control, se la agregamos
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
            else:
                # Si ya tiene clases, le concatenamos form-control si no la tiene
                if 'form-control' not in field.widget.attrs['class']:
                    field.widget.attrs['class'] += ' form-control'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        
        # LOGICA PREFIJO: Si el usuario ingresó "12345678", guardamos "+56912345678"
        telefono_limpio = self.cleaned_data['numero_telefono']

        if telefono_limpio:
            if not telefono_limpio.startswith('+'):
                user.numero_telefono = f"+569{telefono_limpio}"
        else:
            # IMPORTANTE: Si lo dejó vacío, guardamos None (NULL)
            # Esto evita el error de "Ya existe un usuario con teléfono en blanco"
            user.numero_telefono = None
            
        if commit:
            user.save()
        return user


class EditarUsuarioForm(forms.ModelForm):
    # Repetimos la validación visual
    numero_telefono = forms.CharField(
        max_length=8,
        min_length=8,
        required=True,
        validators=[solo_numeros],
        label="Teléfono Móvil",
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'type': 'tel', 
            'pattern': '[0-9]*',
            'maxlength': '8'
        })
    )

    class Meta:
        model = UsuarioCustom
        fields = ['email', 'numero_telefono', 'first_name', 'last_name']
        labels = {
            'email': 'Correo Electrónico (No editable)',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'email' in self.fields:
            self.fields['email'].disabled = True
        
        # TRUCO PRO: Si el usuario ya tiene un número guardado (+569...), 
        # se lo quitamos visualmente para que solo vea sus 8 dígitos al editar.
        if self.instance.numero_telefono:
            telefono_db = self.instance.numero_telefono
            if telefono_db.startswith('+569'):
                self.initial['numero_telefono'] = telefono_db[4:] # Quitamos los primeros 4 chars (+569)

    # LOGICA PREFIJO AL GUARDAR EDICIÓN
    def save(self, commit=True):
        user = super().save(commit=False)
        telefono_limpio = self.cleaned_data['numero_telefono']
        
        # Volvemos a agregar el prefijo antes de ir a la BD
        if telefono_limpio and not telefono_limpio.startswith('+'):
            user.numero_telefono = f"+569{telefono_limpio}"
            
        if commit:
            user.save()
        return user