from django.db import models
from django.conf import settings

# Create your models here.
class Categoria(models.Model):
    nombre = models.CharField(max_length=50)
    icono = models.CharField(max_length=50, blank=True, null=True)
    # Si usuario es null, es una categoría "global" (ej: Comida). 
    # Si tiene usuario, es una que el usuario creó (ej: "Clases de Piano").
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)

    categoria_padre = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subcategorias'
    )
    class Meta:
        # Ordenamos por padre y luego por nombre para que se vea ordenado
        ordering = ['categoria_padre__nombre', 'nombre'] 
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'

    def __str__(self):
        if self.categoria_padre:
            return f"{self.categoria_padre.nombre} > {self.nombre}"
        return self.nombre

class Presupuesto(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # Si categoria es NULL, es el presupuesto GENERAL del mes
    categorias = models.ManyToManyField(Categoria, blank=True)
    monto_limite = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Definimos el periodo
    mes = models.IntegerField() 
    anio = models.IntegerField()

    nombre = models.CharField(max_length=50, default="Presupuesto Mensual")

    nivel_alerta_enviado = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.nombre} ({self.mes}/{self.anio})"
    

class Transaccion(models.Model):
    TIPO_CHOICES = [('INGRESO', 'Ingreso'), ('GASTO', 'Gasto')]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    monto = models.DecimalField(max_digits=15, decimal_places=2)
    descripcion = models.CharField(max_length=255, blank=True)
    fecha = models.DateField() 
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.descripcion} - ${self.monto}"
    

class Alerta(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=100)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titulo}"

class WhatsAppLog(models.Model):
    # Guardamos el JSON completo tal cual llega
    payload = models.JSONField(default=dict) 
    
    # Fecha de recepción
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    # Flags de control
    procesado = models.BooleanField(default=False)
    error = models.TextField(blank=True, null=True) # Para guardar si falló el análisis

    def __str__(self):
        return f"Log {self.id} - {self.fecha_creacion}"
    
class WhatsAppSession(models.Model):
    ESTADOS = [
        ('INICIO', 'Inicio'),
        ('ESPERANDO_MONTO', 'Esperando Monto'),
        ('ESPERANDO_CATEGORIA_PADRE', 'Esperando Categoria Padre'),
        ('ESPERANDO_CATEGORIA_HIJA', 'Esperando Categoria Hija'),
    ]

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=20)
    estado = models.CharField(max_length=50, choices=ESTADOS, default='INICIO')
    
    # Aquí guardamos datos temporales (ej: {'monto': 5000})
    datos_temporales = models.JSONField(default=dict)
    
    ultimo_mensaje = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Sesión de {self.usuario}"