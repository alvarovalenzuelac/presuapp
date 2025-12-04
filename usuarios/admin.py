from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import UsuarioCustom

# Register your models here.
class CustomUserAdmin(UserAdmin):
    model = UsuarioCustom
    # Agregamos 'phone_number' y 'role' a los fieldsets para que aparezcan en el formulario
    fieldsets = UserAdmin.fieldsets + (
        ('Información Extra', {'fields': ('numero_telefono', 'rol')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información Extra', {'fields': ('numero_telefono', 'rol')}),
    )

admin.site.register(UsuarioCustom, CustomUserAdmin)