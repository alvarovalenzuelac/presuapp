from rest_framework import serializers
from app_finanzas.models import Categoria, Transaccion, Presupuesto

# 1. SERIALIZER DE CATEGORÍAS
class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'icono', 'categoria_padre', 'usuario']

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