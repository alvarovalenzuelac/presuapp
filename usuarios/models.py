from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# Create your models here.
class UsuarioCustom(AbstractUser):
    # Definimos los roles posibles
    ADMIN = 'admin'
    CLIENTE = 'cliente'
    STAFF = 'staff'
    
    ROLE_CHOICES = [
        (ADMIN, 'Administrador'),
        (CLIENTE, 'Cliente'),
        (STAFF, 'Staff'),
    ]

    email = models.EmailField(unique=True, verbose_name='Correo Electrónico')
    # Campos adicionales
    # Usamos CharField para telefono porque a veces incluyen el simbolo +
    numero_telefono = models.CharField(max_length=20, unique=True, verbose_name='Teléfono WhatsApp',blank=True, null=True)
    rol = models.CharField(max_length=10, choices=ROLE_CHOICES, default=CLIENTE, verbose_name='Rol')
    
    intentos_fallidos = models.IntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)

    # Opcional: Campo para dirección o empresa si lo necesitas para el presupuesto
    # company_name = models.CharField(max_length=100, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'rol']
    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"
    
    def esta_bloqueado(self):
        if self.bloqueado_hasta and self.bloqueado_hasta > timezone.now():
            return True
        return False