from rest_framework import serializers
from app_finanzas.models import Categoria, Transaccion, Presupuesto
from django.db.models import Q

# 1. SERIALIZER DE CATEGORÍAS
class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'icono', 'categoria_padre', 'usuario']
        read_only_fields = ['usuario']
    def validate(self, data):
        # Validar duplicados antes de crear/actualizar
        user = self.context['request'].user
        nombre = data.get('nombre')
        categoria_padre = data.get('categoria_padre')
        
        # 1. Validación: No permitir crear categorías Padre (padre=None)
        # Si es una creación (no tiene instancia) y no tiene padre...
        if not self.instance and not categoria_padre:
             raise serializers.ValidationError({"non_field_errors": ["Solo puedes crear subcategorías dentro de las existentes."]})

        # 2. Validación: Nombre Duplicado en el mismo Padre
        query = Categoria.objects.filter(
            nombre__iexact=nombre,
            categoria_padre=categoria_padre,
            usuario=user
        )
        
        # Si estamos editando, nos excluimos a nosotros mismos de la búsqueda
        if self.instance:
            query = query.exclude(pk=self.instance.pk)

        if query.exists():
            raise serializers.ValidationError({"nombre": [f"Ya tienes una categoría llamada '{nombre}' en este grupo."]})

        return data

# 2. SERIALIZER DE TRANSACCIONES
class TransaccionSerializer(serializers.ModelSerializer):
    # Campos de solo lectura para mostrar nombres bonitos en la App
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    categoria_padre_nombre = serializers.CharField(source='categoria.categoria_padre.nombre', read_only=True, allow_null=True)
    
    class Meta:
        model = Transaccion
        fields = [
            'id', 'tipo', 'monto', 'fecha', 'descripcion', 
            'categoria', # Este campo usa el ID (para escribir/guardar)
            'categoria_nombre', # Este campo muestra el texto (para leer)
            'categoria_padre_nombre'
        ]
        
    def create(self, validated_data):
        # Asignamos el usuario automáticamente desde el request (Token)
        # El usuario no se envía en el JSON, se saca del Token de seguridad
        usuario = self.context['request'].user
        validated_data['usuario'] = usuario
        return super().create(validated_data)

# 3. SERIALIZER DE PRESUPUESTOS
class PresupuestoSerializer(serializers.ModelSerializer):
    # Serializamos las categorías anidadas para ver sus nombres en el detalle
    # read_only=True significa que para CREAR usamos IDs, pero al LEER vemos el objeto completo
    categorias_detalle = CategoriaSerializer(source='categorias', many=True, read_only=True)
    
    class Meta:
        model = Presupuesto
        fields = ['id', 'nombre', 'monto_limite', 'mes', 'anio', 'categorias', 'categorias_detalle']
        
    def create(self, validated_data):
        usuario = self.context['request'].user
        validated_data['usuario'] = usuario
        return super().create(validated_data)