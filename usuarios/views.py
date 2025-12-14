from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegistroUsuarioForm, EditarUsuarioForm
from django.contrib.auth import logout
from django.db.models import Sum
from django.utils import timezone
from django.db.models import Q
from django.db.models.functions import ExtractDay
from app_finanzas.models import Transaccion,Presupuesto
from rest_framework import generics, permissions
from .serializers import UsuarioSerializer
import json
import datetime


# Create your views here.
# Vista de Inicio (Pública)
def home_view(request):
    return render(request, 'inicio.html')

# Vista de Dashboard (Privada)
@login_required
def dashboard_view(request):
    return render(request, 'dashboard.html')

# Vista de Registro
def registro_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST) # El form ya hace la magia del +569
        if form.is_valid():
            nuevo_usuario = form.save() # Aquí se ejecuta el save() modificado
            messages.success(request, f'Cuenta creada para {nuevo_usuario.email}. ¡Ahora puedes ingresar!')
            return redirect('login')
    else:
        form = RegistroUsuarioForm()
    
    return render(request, 'registro.html', {'form': form})

# Vista de Editar Perfil
@login_required
def perfil_view(request):
    if request.method == 'POST':
        form = EditarUsuarioForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tu perfil ha sido actualizado.')
            return redirect('perfil')
    else:
        form = EditarUsuarioForm(instance=request.user)
    
    return render(request, 'perfil.html', {'form': form})

# Vista para Eliminar Cuenta (Cuidado con esta)
@login_required
def eliminar_cuenta_view(request):
    if request.method == 'POST':
        user = request.user
        user.delete()
        messages.warning(request, 'Tu cuenta ha sido eliminada permanentemente.')
        return redirect('inicio')
    return render(request, 'eliminar_cuenta.html')

def cerrar_sesion_view(request):
    logout(request) # Cierra la sesión del usuario
    messages.success(request, 'Has cerrado sesión correctamente. ¡Hasta pronto!')
    return redirect('inicio') # Redirige al inicio

@login_required
def dashboard_view(request):
    # 1. GESTIÓN DE FECHAS Y FILTROS
    hoy = timezone.now().date()
    
    # Obtener mes/año del GET (o usar el actual)
    try:
        mes_seleccionado = int(request.GET.get('mes', hoy.month))
        anio_seleccionado = int(request.GET.get('anio', hoy.year))
    except ValueError:
        mes_seleccionado = hoy.month
        anio_seleccionado = hoy.year

    # Generar opciones para el Combo (Últimos 3 meses)
    opciones_meses = []
    for i in range(3):
        fecha_calc = hoy.replace(day=1) - datetime.timedelta(days=30 * i)
        # Ajuste seguro de mes/año (simplificado)
        mes_iter = fecha_calc.month
        anio_iter = fecha_calc.year
        # Nombre bonito
        nombre_mes = datetime.date(anio_iter, mes_iter, 1).strftime('%B %Y') 
        # Nota: Para nombres en español nativo se requiere locale, 
        # por ahora usaremos diccionario simple o strftime si está configurado.
        opciones_meses.append({
            'val_mes': mes_iter,
            'val_anio': anio_iter,
            'texto': f"{mes_iter}/{anio_iter}" # Formato simple 12/2025
        })

    # 2. FILTRAR TRANSACCIONES DEL MES SELECCIONADO
    transacciones_mes = Transaccion.objects.filter(
        usuario=request.user,
        fecha__month=mes_seleccionado,
        fecha__year=anio_seleccionado
    )

    # 3. KPIS (Tarjetas)
    total_ingresos = transacciones_mes.filter(tipo='INGRESO').aggregate(Sum('monto'))['monto__sum'] or 0
    total_gastos = transacciones_mes.filter(tipo='GASTO').aggregate(Sum('monto'))['monto__sum'] or 0
    saldo_actual = total_ingresos - total_gastos

    presupuesto_global_obj = Presupuesto.objects.filter(
        usuario=request.user,
        mes=mes_seleccionado,
        anio=anio_seleccionado,
        categorias=None # Esto indica que es Global (sin relaciones M2M)
    ).first()

    monto_presupuesto_global = 0
    tiene_presupuesto_global = False

    if presupuesto_global_obj:
        monto_presupuesto_global = presupuesto_global_obj.monto_limite
        tiene_presupuesto_global = True

    saldo_restante_global = monto_presupuesto_global - total_gastos

    # 4. ÚLTIMAS 5 TRANSACCIONES
    ultimas_transacciones = transacciones_mes.order_by('-fecha', '-id')[:5]

    # 5. PRESUPUESTOS CON MAYOR % DE USO
    presupuestos = Presupuesto.objects.filter(usuario=request.user, mes=mes_seleccionado, anio=anio_seleccionado)
    lista_presupuestos = []
    
    for p in presupuestos:
        # Reutilizamos lógica de cálculo
        cats = p.categorias.all()
        gastos_query = transacciones_mes.filter(tipo='GASTO') # Ya está filtrada por fecha
        
        if cats.exists():
            gastos_query = gastos_query.filter(
                Q(categoria__in=cats) | Q(categoria__categoria_padre__in=cats)
            )
        
        gastado = gastos_query.aggregate(Sum('monto'))['monto__sum'] or 0
        porcentaje = int((gastado * 100) / p.monto_limite) if p.monto_limite > 0 else 0
        
        lista_presupuestos.append({
            'nombre': p.nombre,
            'porcentaje': porcentaje,
            'visual': min(porcentaje, 100),
            'estado': 'danger' if porcentaje > 90 else 'warning' if porcentaje > 70 else 'success'
        })
    
    # Ordenamos por porcentaje descendente y tomamos los top 3
    top_presupuestos = sorted(lista_presupuestos, key=lambda x: x['porcentaje'], reverse=True)[:3]

    # 6. DATOS GRÁFICO TORTA (Categorías)
    gastos_query = transacciones_mes.filter(tipo='GASTO').select_related('categoria')
    datos_torta = {}
    for g in gastos_query:
        cat_nombre = "Sin Categoría"
        if g.categoria:
            cat_nombre = g.categoria.categoria_padre.nombre if g.categoria.categoria_padre else g.categoria.nombre
        datos_torta[cat_nombre] = datos_torta.get(cat_nombre, 0) + float(g.monto)

    # 7. DATOS GRÁFICO DIARIO (Línea: Día vs Monto)
    # Agrupamos por día usando ExtractDay
    gastos_por_dia = transacciones_mes.filter(tipo='GASTO')\
        .annotate(dia=ExtractDay('fecha'))\
        .values('dia')\
        .annotate(total=Sum('monto'))\
        .order_by('dia')
    
    # Preparamos ejes (Días 1 al 31)
    labels_dias = []
    data_dias = []
    # Creamos un diccionario rápido {1: 5000, 5: 2000}
    mapa_gastos = {item['dia']: float(item['total']) for item in gastos_por_dia}
    
    # Rellenamos los días para que el gráfico sea continuo
    # (Truco simple: iterar hasta 31, si el mes tiene menos el gráfico igual aguanta)
    ultimo_dia = 31 
    for dia in range(1, ultimo_dia + 1):
        labels_dias.append(str(dia))
        data_dias.append(mapa_gastos.get(dia, 0))

    context = {
        # Filtros
        'opciones_meses': opciones_meses,
        'mes_actual': mes_seleccionado,
        'anio_actual': anio_seleccionado,
        
        # KPIs
        'tiene_presupuesto_global': tiene_presupuesto_global,
        'monto_presupuesto_global': monto_presupuesto_global,
        'total_gastos': total_gastos,
        'saldo_restante_global': saldo_restante_global,
        
        # Listas
        'ultimas_transacciones': ultimas_transacciones,
        'top_presupuestos': top_presupuestos,
        
        # Gráficos
        'labels_torta': json.dumps(list(datos_torta.keys())),
        'data_torta': json.dumps(list(datos_torta.values())),
        'labels_dias': json.dumps(labels_dias),
        'data_dias': json.dumps(data_dias),
    }
    return render(request, 'dashboard.html', context)


class UsuarioLogueadoView(generics.RetrieveAPIView):
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated] # Solo usuarios con Token

    def get_object(self):
        # Retorna tu UsuarioCustom logueado actualmente
        return self.request.user