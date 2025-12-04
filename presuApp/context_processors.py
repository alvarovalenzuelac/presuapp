from app_finanzas.models import Alerta

def contador_alertas(request):
    if request.user.is_authenticated:
        # Contamos solo las NO leídas
        count = Alerta.objects.filter(usuario=request.user, leida=False).count()
        # Traemos las ultimas 5 para mostrar en el dropdown (opcional)
        alertas_recientes = Alerta.objects.filter(usuario=request.user, leida=False).order_by('-fecha_creacion')[:5]
        
        return {
            'notificaciones_count': count,
            'notificaciones_list': alertas_recientes
        }
    return {'notificaciones_count': 0}