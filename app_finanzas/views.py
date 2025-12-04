from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import TransaccionForm, CategoriaForm, PresupuestoForm
from .models import Transaccion, Categoria, Presupuesto
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
import datetime
import calendar
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum


# Create your views here.
@login_required
def mis_gastos_view(request):
    hoy = timezone.now().date()
    # Por defecto: Primer día del mes actual hasta hoy

    filtro = request.GET.get('filtro', 'mes_actual') # 'mes_actual' es el default
    custom_inicio = request.GET.get('fecha_inicio')
    custom_fin = request.GET.get('fecha_fin')

    if filtro == 'ultimo_mes':
        fin = hoy.replace(day=1) - datetime.timedelta(days=1)
        inicio = fin.replace(day=1)
    
    elif filtro == 'ultimos_3':
        primer_dia_actual = hoy.replace(day=1)
        
        # 2. Restamos 1 día para caer en el mes anterior (ej: 30 de Noviembre)
        ultimo_dia_mes_anterior = primer_dia_actual - datetime.timedelta(days=1)
        
        # 3. Nos paramos en el 1 del mes anterior (ej: 1 de Noviembre)
        primer_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)
        
        # 4. Restamos 1 día otra vez para caer dos meses atrás (ej: 31 de Octubre)
        ultimo_dia_hace_2_meses = primer_dia_mes_anterior - datetime.timedelta(days=1)
        
        # 5. Y finalmente fijamos el inicio en el día 1 (ej: 1 de Octubre)
        inicio = ultimo_dia_hace_2_meses.replace(day=1)
        
        _, ultimo_dia = calendar.monthrange(hoy.year, hoy.month)
        fin = hoy.replace(day=ultimo_dia)
        
    elif filtro == 'custom' and custom_inicio and custom_fin:
        try:
            inicio = datetime.datetime.strptime(custom_inicio, '%Y-%m-%d').date()
            fin = datetime.datetime.strptime(custom_fin, '%Y-%m-%d').date()
        except ValueError:
            # Si fallan las fechas, fallback a mes actual
            filtro = 'mes_actual'
            inicio = hoy.replace(day=1)
            _, ultimo_dia = calendar.monthrange(hoy.year, hoy.month)
            fin = hoy.replace(day=ultimo_dia)
    
    else: # Default: Mes Actual
        filtro = 'mes_actual'
        inicio = hoy.replace(day=1)

        _, ultimo_dia = calendar.monthrange(hoy.year, hoy.month)
        fin = hoy.replace(day=ultimo_dia)

    transacciones = Transaccion.objects.filter(
        usuario=request.user,
        fecha__range=[inicio, fin]
    ).order_by('-fecha')
    
    context = {
        'transacciones': transacciones,
        'filtro_actual': filtro,
        'fecha_inicio': inicio.strftime('%Y-%m-%d'), # Para repoblar el input date
        'fecha_fin': fin.strftime('%Y-%m-%d'),
    }
    return render(request, 'finanzas/mis_gastos.html', context)

@login_required
def agregar_gasto_view(request):
    if request.method == 'POST':
        form = TransaccionForm(request.user, request.POST)
        if form.is_valid():
            gasto = form.save(commit=False)
            gasto.usuario = request.user
            gasto.save()
            messages.success(request, 'Transacción registrada correctamente.')
            return redirect('mis_gastos')
    else:
        form = TransaccionForm(request.user)

    return render(request, 'finanzas/agregar_gasto.html', {'form': form})

@login_required
def categorias_view(request):
    # LÓGICA PARA CREAR NUEVA SUBCATEGORÍA
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            nueva_cat = form.save(commit=False)
            nueva_cat.usuario = request.user # Asignamos al usuario actual (es privada)
            nueva_cat.save()
            messages.success(request, f'Subcategoría "{nueva_cat.nombre}" creada correctamente.')
            return redirect('categorias')
    else:
        form = CategoriaForm()

    # LÓGICA PARA LISTAR (Mostrar padres e hijos)
    # Traemos solo los PADRES globales
    categorias_padre = Categoria.objects.filter(categoria_padre=None).order_by('nombre')
    
    # Nota: En el template filtraremos los hijos para mostrar solo 
    # los globales + los del usuario.

    context = {
        'categorias_padre': categorias_padre,
        'form': form
    }
    return render(request, 'finanzas/categorias.html', context)

@login_required
def load_subcategorias(request):
    padre_id = request.GET.get('padre_id')
    
    # Filtramos: Que sean hijas de ese padre Y (que sean globales O del usuario)
    subcategorias = Categoria.objects.filter(
        categoria_padre_id=padre_id
    ).filter(
        Q(usuario=None) | Q(usuario=request.user)
    ).order_by('nombre')
    
    # Retornamos solo los datos necesarios (id y nombre) en formato JSON
    data = list(subcategorias.values('id', 'nombre'))
    return JsonResponse(data, safe=False)

@login_required
def editar_categoria_view(request, id):
    # Solo permitimos editar si la categoría pertenece al usuario (usuario=request.user)
    # Esto evita que intenten editar una Global o la de otro usuario.
    categoria = get_object_or_404(Categoria, id=id, usuario=request.user)

    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría actualizada correctamente.')
            return redirect('categorias')
    else:
        form = CategoriaForm(instance=categoria)

    return render(request, 'finanzas/editar_categoria.html', {'form': form})

@login_required
def eliminar_categoria_view(request, id):
    # 1. Obtener la categoría a eliminar (asegurando que sea del usuario)
    categoria_a_borrar = get_object_or_404(Categoria, id=id, usuario=request.user)
    
    # 2. Buscar la categoría destino ("General" del mismo padre)
    # Buscamos una hermana que se llame "General" o "Otros"
    categoria_destino = Categoria.objects.filter(
        categoria_padre=categoria_a_borrar.categoria_padre,
        nombre__in=["General", "Otros"] # Intentamos buscar cualquiera de las dos
    ).first()

    # Si por alguna razón no existe "General", usamos la Categoría Padre como fallback (opcional)
    # o simplemente no reasignamos (quedarían en NULL si el modelo lo permite).
    
    if categoria_destino:
        # 3. REASIGNACIÓN MASIVA
        # Buscamos todas las transacciones que tenían la categoría vieja
        # y las actualizamos a la categoría destino.
        conteo = Transaccion.objects.filter(categoria=categoria_a_borrar).update(categoria=categoria_destino)
        
        messages.info(request, f'Se reasignaron {conteo} transacciones a "{categoria_destino.nombre}".')
    
    # 4. Eliminar
    categoria_a_borrar.delete()
    messages.success(request, 'Categoría eliminada correctamente.')
    
    return redirect('categorias')

@login_required
def editar_gasto_view(request, id):
    transaccion = get_object_or_404(Transaccion, id=id, usuario=request.user)

    if request.method == 'POST':
        # Pasamos el usuario para que el form filtre las categorías
        form = TransaccionForm(request.user, request.POST, instance=transaccion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transacción actualizada correctamente.')
            return redirect('mis_gastos')
    else:
        form = TransaccionForm(request.user, instance=transaccion)

    return render(request, 'finanzas/editar_gasto.html', {'form': form})

# VISTA ELIMINAR GASTO
@login_required
def eliminar_gasto_view(request, id):
    transaccion = get_object_or_404(Transaccion, id=id, usuario=request.user)
    transaccion.delete()
    messages.success(request, 'Transacción eliminada correctamente.')
    return redirect('mis_gastos')

@login_required
def lista_presupuestos_view(request):
    # Obtenemos los presupuestos del usuario ordenados por fecha
    presupuestos = Presupuesto.objects.filter(usuario=request.user).order_by('-anio', '-mes')
    
    # Creamos una lista auxiliar para mandar al template con los cálculos ya hechos
    datos_presupuestos = []

    for p in presupuestos:
        cats_seleccionadas = p.categorias.all()
        # Definimos el rango de fechas de ese presupuesto (Mes completo)
        # Nota: Usamos una lógica simple de año/mes
        gastos_query = Transaccion.objects.filter(
            usuario=request.user,
            tipo='GASTO',
            fecha__year=p.anio,
            fecha__month=p.mes
        )

        # Filtramos por categoría si es específico
        if cats_seleccionadas.exists():
            # Si seleccionó categorías, filtramos:
            # Gastos que pertenezcan a las seleccionadas DIRECTAMENTE
            # O gastos cuya categoria_padre esté en las seleccionadas
            gastos_query = gastos_query.filter(
                Q(categoria__in=cats_seleccionadas) | 
                Q(categoria__categoria_padre__in=cats_seleccionadas)
            )
        else:
            # Si NO seleccionó ninguna categoría, asumimos que es un 
            # PRESUPUESTO GENERAL (Todos los gastos del mes)
            pass
        
        # Sumamos el total gastado (si es None, lo convertimos a 0)
        total_gastado = gastos_query.aggregate(Sum('monto'))['monto__sum'] or 0
        
        # Calculamos porcentaje para la barra de progreso
        porcentaje = 0
        if p.monto_limite > 0:
            # CAMBIO: Usamos int() para redondear y quitar decimales aquí mismo
            calculo_raw = (total_gastado * 100) / p.monto_limite
            porcentaje = int(calculo_raw)
        
        # Guardamos todo en un diccionario
        datos_presupuestos.append({
            'presupuesto': p,
            'gastado': total_gastado,
            # CAMBIO: Ya no necesitamos min() aquí si queremos saber cuánto se pasó,
            # pero para la barra visual (width) sí necesitamos un tope.
            # Vamos a pasar dos variables: una para la barra y otra real.
            'porcentaje': porcentaje, 
            'porcentaje_visual': min(porcentaje, 100), # Tope visual para el CSS
            'excedido': porcentaje > 100,
            'restante': p.monto_limite - total_gastado
        })

    return render(request, 'finanzas/presupuestos.html', {'datos': datos_presupuestos})

def obtener_jerarquia_categorias(user):
    # Traemos todos los PADRES (Globales o del Usuario)
    # prefetch_related optimiza la consulta de los hijos para no matar la BD
    padres = Categoria.objects.filter(
        Q(usuario=None) | Q(usuario=user),
        categoria_padre=None
    ).prefetch_related('subcategorias').order_by('nombre')
    return padres

@login_required
def crear_presupuesto_view(request):
    categorias_jerarquia = obtener_jerarquia_categorias(request.user)

    if request.method == 'POST':
        form = PresupuestoForm(request.user, request.POST)
        
        # Obtenemos el flag de confirmación (si viene del Modal)
        confirmar_reemplazo = request.POST.get('confirmar_reemplazo') == 'si'

        if form.is_valid():
            # 1. Extraemos datos limpios (sin guardar aún)
            nuevas_cats = set(form.cleaned_data['categorias'])
            mes = form.cleaned_data['mes']
            anio = form.cleaned_data['anio']
            
            # 2. Buscamos presupuestos DEL MISMO MES/AÑO
            existentes = Presupuesto.objects.filter(
                usuario=request.user, 
                mes=mes, 
                anio=anio
            )
            
            presupuesto_conflicto = None
            
            # 3. Lógica de Comparación de Conjuntos (Sets)
            for p in existentes:
                cats_existentes = set(p.categorias.all())
                
                # Si los conjuntos son idénticos (mismas categorías exactas)
                # O si ambos están vacíos (ambos son Presupuesto General)
                if cats_existentes == nuevas_cats:
                    presupuesto_conflicto = p
                    break
            
            # 4. Decisión
            if presupuesto_conflicto and not confirmar_reemplazo:
                # CASO A: Hay conflicto y NO han confirmado -> Mostramos advertencia
                # Renderizamos la misma página pero enviamos el objeto conflicto
                context = {
                    'form': form,
                    'categorias_jerarquia': categorias_jerarquia,
                    'conflicto': presupuesto_conflicto, # <--- ESTO ACTIVARÁ EL MODAL
                    'seleccionadas_ids': [c.id for c in nuevas_cats]
                }
                return render(request, 'finanzas/crear_presupuesto.html', context)
            
            elif presupuesto_conflicto and confirmar_reemplazo:
                # CASO B: Hay conflicto y SI confirmaron -> Reemplazar
                presupuesto_conflicto.delete()
                messages.warning(request, f'Se reemplazó el presupuesto anterior: "{presupuesto_conflicto.nombre}".')

            # CASO C: No había conflicto o ya se borró. Guardamos el nuevo.
            presu = form.save(commit=False)
            presu.usuario = request.user
            presu.save()
            form.save_m2m() # Guardamos las categorías
            
            messages.success(request, 'Meta definida correctamente.')
            return redirect('presupuestos')

    else:
        form = PresupuestoForm(request.user)
    
    context = {
        'form': form,
        'categorias_jerarquia': categorias_jerarquia,
        'seleccionadas_ids': []
    }
    return render(request, 'finanzas/crear_presupuesto.html', context)

# 3. VISTA ELIMINAR PRESUPUESTO
@login_required
def eliminar_presupuesto_view(request, id):
    presupuesto = get_object_or_404(Presupuesto, id=id, usuario=request.user)
    presupuesto.delete()
    messages.success(request, 'Presupuesto eliminado.')
    return redirect('presupuestos')

@login_required
def editar_presupuesto_view(request, id):
    presupuesto = get_object_or_404(Presupuesto, id=id, usuario=request.user)
    categorias_jerarquia = obtener_jerarquia_categorias(request.user)

    # Obtenemos una lista simple de IDs [1, 5, 8] de las categorías que ya tiene este presupuesto
    # Esto sirve para marcar los checkbox como "checked" en el HTML
    seleccionadas_ids = list(presupuesto.categorias.values_list('id', flat=True))

    if request.method == 'POST':
        form = PresupuestoForm(request.user, request.POST, instance=presupuesto)
        if form.is_valid():
            presu = form.save(commit=False)
            presu.usuario = request.user
            presu.save()
            form.save_m2m() # También necesaria al editar
            messages.success(request, 'Presupuesto actualizado.')
            return redirect('presupuestos')
    else:
        form = PresupuestoForm(request.user, instance=presupuesto)
    context = {
        'form': form,
        'categorias_jerarquia': categorias_jerarquia,
        'seleccionadas_ids': seleccionadas_ids  # <--- ¡ESTO ES LO QUE FALTABA!
    }
    return render(request, 'finanzas/editar_presupuesto.html', context)