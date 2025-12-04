from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum, Q
from .models import Transaccion, Presupuesto, Alerta, Categoria

@receiver(post_save, sender=Transaccion)
def verificar_presupuestos(sender, instance, created, **kwargs):
    """
    Se ejecuta automáticamente cada vez que se guarda una Transacción.
    Verifica si se rompió algún presupuesto asociado.
    """
    # Solo nos interesa si es un GASTO y si fue creado (o editado)
    if instance.tipo != 'GASTO':
        return

    usuario = instance.usuario
    mes = instance.fecha.month
    anio = instance.fecha.year
    monto_gasto = instance.monto
    categoria_gasto = instance.categoria

    # 1. BUSCAR PRESUPUESTOS AFECTADOS
    # Un gasto puede afectar a múltiples presupuestos:
    # a) Presupuesto Global (sin categorías)
    # b) Presupuesto que incluye explícitamente esta categoría
    # c) Presupuesto que incluye al PADRE de esta categoría
    
    presupuestos_afectados = Presupuesto.objects.filter(
        usuario=usuario,
        mes=mes,
        anio=anio
    )

    for presupuesto in presupuestos_afectados:
        es_afectado = False
        cats_presupuesto = presupuesto.categorias.all()

        # A. Chequeo de Global
        if not cats_presupuesto.exists():
            es_afectado = True
        
        # B. Chequeo de Categorías Específicas
        elif categoria_gasto:
            # Si la categoría del gasto está en el presupuesto
            if categoria_gasto in cats_presupuesto:
                es_afectado = True
            # O si el PADRE de la categoría del gasto está en el presupuesto
            elif categoria_gasto.categoria_padre in cats_presupuesto:
                es_afectado = True
        
        if es_afectado:
            verificar_limite(presupuesto, usuario)

def verificar_limite(presupuesto, usuario):
    # 1. Calcular total gastado en ese presupuesto
    cats = presupuesto.categorias.all()
    gastos_query = Transaccion.objects.filter(
        usuario=usuario,
        tipo='GASTO',
        fecha__year=presupuesto.anio,
        fecha__month=presupuesto.mes
    )

    if cats.exists():
        gastos_query = gastos_query.filter(
            Q(categoria__in=cats) | Q(categoria__categoria_padre__in=cats)
        )
    
    total_gastado = gastos_query.aggregate(Sum('monto'))['monto__sum'] or 0

    # 2. Comparar
    if total_gastado > presupuesto.monto_limite:
        diferencia = total_gastado - presupuesto.monto_limite
        
        # 3. Crear o Actualizar Alerta (Para no llenar de spam, buscamos si ya existe una alerta hoy)
        titulo = f"⚠️ Límite Excedido: {presupuesto.nombre}"
        mensaje = (f"Has superado tu presupuesto de ${presupuesto.monto_limite:,.0f} "
                   f"por un monto de ${diferencia:,.0f}. "
                   f"Total gastado: ${total_gastado:,.0f}")

        # Buscamos si ya existe una alerta no leída para este presupuesto
        # (Esto es opcional, evita crear 10 alertas si compras 10 chicles seguidos estando excedido)
        Alerta.objects.create(
            usuario=usuario,
            titulo=titulo,
            mensaje=mensaje,
            leida=False
        )
        print(f"ALERTA GENERADA: {titulo}")