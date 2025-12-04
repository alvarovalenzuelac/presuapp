from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Categoria, Presupuesto, Transaccion, Alerta

# 1. Configuración para CATEGORÍA
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'categoria_padre', 'usuario')
    list_filter = ('categoria_padre', 'usuario')
    search_fields = ('nombre',)

# 2. Configuración para TRANSACCIÓN
class TransaccionAdmin(admin.ModelAdmin):
    # Mostramos columnas útiles en la lista
    list_display = ('descripcion', 'usuario', 'monto', 'tipo', 'categoria', 'fecha')
    # Filtros laterales para navegar rápido por los datos
    list_filter = ('tipo', 'fecha', 'usuario', 'categoria')
    # Barra de búsqueda
    search_fields = ('descripcion', 'usuario__email') 
    # Ordenar por fecha descendente (lo más nuevo primero)
    ordering = ('-fecha',)

# 3. Configuración para PRESUPUESTO
class PresupuestoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'mostrar_objetivo', 'monto_limite', 'mes', 'anio')
    list_filter = ('mes', 'anio', 'usuario')
    filter_horizontal = ('categorias',)
    # Método personalizado para mostrar en la lista si es General o por Categoría
    def mostrar_objetivo(self, obj):
        # Obtenemos todas las categorías asociadas
        categorias = obj.categorias.all()
        
        if categorias.count() == 0:
            return "GENERAL (Total Mes)"
        
        # Si hay muchas, mostramos las primeras 3 y "..."
        nombres = [c.nombre for c in categorias]
        if len(nombres) > 3:
            return f"{', '.join(nombres[:3])}..."
        
        return ", ".join(nombres)
    
    mostrar_objetivo.short_description = "Objetivo"

# 4. Configuración para ALERTA
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'usuario', 'leida', 'fecha_creacion')
    list_filter = ('leida', 'fecha_creacion')
    readonly_fields = ('fecha_creacion',) # Para que no se pueda editar la fecha manual

# --- Registro final ---
admin.site.register(Categoria, CategoriaAdmin)
admin.site.register(Transaccion, TransaccionAdmin)
admin.site.register(Presupuesto, PresupuestoAdmin)
admin.site.register(Alerta, AlertaAdmin)