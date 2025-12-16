from rest_framework import serializers
from app_finanzas.models import Categoria, Transaccion, Presupuesto
from django.db.models import Sum, Q

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

    gastado = serializers.SerializerMethodField()
    porcentaje = serializers.SerializerMethodField()
    
    class Meta:
        model = Presupuesto
        fields = ['id', 'nombre', 'monto_limite', 'mes', 'anio', 'categorias', 'categorias_detalle','gastado', 'porcentaje']
    
    def get_gastado(self, obj):
        # 1. Filtramos gastos del usuario y del periodo del presupuesto
        gastos = Transaccion.objects.filter(
            usuario=obj.usuario,
            tipo='GASTO',
            fecha__year=obj.anio,
            fecha__month=obj.mes
        )
        
        # 2. Filtramos por categorías asociadas (si existen)
        cats = obj.categorias.all()
        if cats.exists():
            gastos = gastos.filter(
                Q(categoria__in=cats) | 
                Q(categoria__categoria_padre__in=cats)
            )
            
        # 3. Sumamos
        total = gastos.aggregate(Sum('monto'))['monto__sum'] or 0
        return total

    def get_porcentaje(self, obj):
        limit = obj.monto_limite
        if limit <= 0:
            return 0
        
        # Reutilizamos la lógica de gasto (o llamamos a self.get_gastado(obj))
        # Para eficiencia, aquí repetimos la llamada rápida o calculamos sobre el valor ya obtenido
        gastado = self.get_gastado(obj) 
        
        return int((gastado * 100) / limit)

    def create(self, validated_data):
        usuario = self.context['request'].user
        validated_data['usuario'] = usuario
        return super().create(validated_data)