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
            verificar_niveles_alerta(presupuesto, usuario, mes, anio)

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

def verificar_niveles_alerta(presupuesto, usuario, mes, anio):
    # 1. Calcular total gastado
    cats = presupuesto.categorias.all()
    
    gastos_query = Transaccion.objects.filter(
        usuario=usuario,
        tipo='GASTO',
        fecha__year=anio,   # Usamos las variables pasadas
        fecha__month=mes
    )

    if cats.exists():
        gastos_query = gastos_query.filter(
            Q(categoria__in=cats) | Q(categoria__categoria_padre__in=cats)
        )
    
    total_gastado = gastos_query.aggregate(Sum('monto'))['monto__sum'] or 0

    # 2. Calcular porcentaje
    limite = presupuesto.monto_limite
    if limite <= 0: return

    porcentaje = (total_gastado / limite) * 100
    
    # 3. Determinar nivel actual
    nuevo_nivel = 0
    titulo = ""
    mensaje = ""

    if porcentaje >= 100:
        nuevo_nivel = 3
        titulo = f"🚨 Límite Excedido: {presupuesto.nombre}"
        mensaje = f"Has superado el 100% de tu presupuesto. Total: ${total_gastado:,.0f} / ${limite:,.0f}"
    
    elif porcentaje >= 95:
        nuevo_nivel = 2
        titulo = f"⚠️ Peligro (95%): {presupuesto.nombre}"
        mensaje = f"Estás a punto de agotar tu presupuesto. Llevas gastado ${total_gastado:,.0f}."
    
    elif porcentaje >= 80:
        nuevo_nivel = 1
        titulo = f"📢 Atención (80%): {presupuesto.nombre}"
        mensaje = f"Ya consumiste el 80% de tu presupuesto. Llevas ${total_gastado:,.0f}."

    # 4. Enviar Alerta SOLO si subimos de nivel (Anti-Spam)
    if nuevo_nivel > 0 and nuevo_nivel > presupuesto.nivel_alerta_enviado:
        
        Alerta.objects.create(
            usuario=usuario,
            titulo=titulo,
            mensaje=mensaje,
            leida=False
        )
        
        # Actualizamos el presupuesto para recordar que ya avisamos este nivel
        presupuesto.nivel_alerta_enviado = nuevo_nivel
        presupuesto.save(update_fields=['nivel_alerta_enviado'])
        
        print(f"ALERTA GENERADA NIVEL {nuevo_nivel}: {titulo}")