from django.core.management.base import BaseCommand
from app_finanzas.models import Categoria

class Command(BaseCommand):
    help = 'Carga las categorías y subcategorías iniciales del sistema'

    def handle(self, *args, **kwargs):
        data = [
            ("Comida y bebida", ["Bar, Café", "Restaurant, Delivery", "Supermercado"]),
            ("Compras", ["Regalos", "Mascotas", "Ropa y calzado", "Tiempo Libre"]),
            ("Vivienda", ["Servicios", "Arriendo, Dividendo", "Electricidad, Gas", "Mantenimiento, reparaciones"]),
            ("Transporte", ["Transporte publico", "Taxi, Transporte app"]),
            ("Vehiculos", ["Estacionamiento", "Combustible", "Seguro"]),
            ("Vida y entretenimiento", ["Alcohol, tabaco", "Medico", "Gimnasio", "Educacion", "Libros", "Streaming, Musica y TV"]),
            ("PC, Comunicaciones", ["Internet", "Juegos", "Telefono"]),
            ("Inversiones", ["Ahorros", "Inversiones financieras"]),
            ("Otros", ["Otros"]),
        ]

        contador_padres = 0
        contador_hijos = 0

        for padre_nombre, subcategorias in data:
            # 1. Crear Padre
            padre_obj, created = Categoria.objects.get_or_create(
                nombre=padre_nombre,
                usuario=None,
                categoria_padre=None
            )
            if created:
                contador_padres += 1

            # --- MEJORA: Asegurar que siempre exista una opción "General" ---
            # Si la lista de subcategorías NO incluye ya un "Otros" o "General", lo agregamos.
            if "Otros" not in subcategorias and "General" not in subcategorias:
                subcategorias.append("General") # <--- ESTO SOLUCIONA TU DUDA

            # 2. Crear Hijos
            for sub_nombre in subcategorias:
                sub_obj, sub_created = Categoria.objects.get_or_create(
                    nombre=sub_nombre,
                    categoria_padre=padre_obj,
                    usuario=None
                )
                if sub_created:
                    contador_hijos += 1
        
        self.stdout.write(self.style.SUCCESS(f'¡Listo! Se cargaron/actualizaron {contador_padres} padres y sus subcategorías (incluyendo "General").'))