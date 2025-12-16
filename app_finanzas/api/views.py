from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q,Sum
from django.db.models.functions import ExtractDay
from app_finanzas.models import Categoria, Transaccion, Presupuesto
from .serializers import CategoriaSerializer, TransaccionSerializer, PresupuestoSerializer
from app_finanzas.models import WhatsAppLog
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from app_finanzas.services import WhatsAppService
import logging
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone


# VISTA API: CATEGORÍAS
class CategoriaViewSet(viewsets.ModelViewSet):
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated] # Solo usuarios logueados (con Token)

    def get_queryset(self):
        # Si es una vista falsa (generación de docu), retornamos vacío para no romper nada. SWAGGER
        if getattr(self, 'swagger_fake_view', False):
            return Categoria.objects.none()
        # La App solo debe ver categorías Globales (None) o del Usuario
        return Categoria.objects.filter(
            Q(usuario=None) | Q(usuario=self.request.user)
        ).order_by('categoria_padre__nombre', 'nombre')

    def perform_create(self, serializer):
        # Al crear una categoría desde la App, se asigna al usuario dueño del Token
        serializer.save(usuario=self.request.user)

# VISTA API: TRANSACCIONES
class TransaccionViewSet(viewsets.ModelViewSet):
    serializer_class = TransaccionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # PARCHE PARA SWAGGER
        if getattr(self, 'swagger_fake_view', False):
            return Transaccion.objects.none()
        # El usuario solo ve SUS gastos
        return Transaccion.objects.filter(usuario=self.request.user).order_by('-fecha')
    
    # Asignar usuario al crear
    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

# VISTA API: PRESUPUESTOS
class PresupuestoViewSet(viewsets.ModelViewSet):
    serializer_class = PresupuestoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # SWAGGER
        if getattr(self, 'swagger_fake_view', False):
            return Presupuesto.objects.none()
        return Presupuesto.objects.filter(usuario=self.request.user).order_by('-anio', '-mes')
    # Asignar usuario al crear
    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

logger = logging.getLogger(__name__)

class WhatsAppWebhookView(APIView):
    # Permitimos acceso sin Token, porque Meta no usa nuestros JWT
    permission_classes = [AllowAny] 

    # 1. VERIFICACIÓN (Meta te pregunta: "¿Eres tú?")
    def get(self, request):
        # Este token lo inventas tú y lo configuras en el panel de Facebook después
        VERIFY_TOKEN = settings.WHATSAPP_VERIFY_TOKEN
        
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode and token:
            if mode == 'subscribe' and token == VERIFY_TOKEN:
                # return Response(int(challenge), status=status.HTTP_200_OK)
                return HttpResponse(challenge, content_type="text/plain", status=200)
            else:
                # return Response("Token inválido", status=status.HTTP_403_FORBIDDEN)
                return HttpResponse("Token inválido", status=403)
            
        
        # return Response("Faltan parámetros", status=status.HTTP_400_BAD_REQUEST)
        return HttpResponse("Faltan parámetros", status=400)

    # 2. RECEPCIÓN DE MENSAJES
    def post(self, request):
        try:
            data = request.data
            
            # 1. Guardar Log
            log = WhatsAppLog.objects.create(payload=data)
            
            # 2. Procesar (Disparar el cerebro)
            service = WhatsAppService()
            service.procesar_log(log.id)

            return Response({"status": "received"}, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error en Webhook: {e}")
            return Response({"status": "error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DashboardDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        usuario = request.user
        hoy = timezone.now()
        
        # Filtros de fecha (por defecto mes actual)
        mes = int(request.query_params.get('mes', hoy.month))
        anio = int(request.query_params.get('anio', hoy.year))

        # Transacciones del mes
        transacciones = Transaccion.objects.filter(
            usuario=usuario,
            fecha__month=mes,
            fecha__year=anio
        )

        # 1. TOTALES (Tarjetas)
        ingresos = transacciones.filter(tipo='INGRESO').aggregate(Sum('monto'))['monto__sum'] or 0
        gastos = transacciones.filter(tipo='GASTO').aggregate(Sum('monto'))['monto__sum'] or 0

        presupuesto_global = 0
        presu_obj = Presupuesto.objects.filter(
            usuario=usuario,
            mes=mes,
            anio=anio,
            categorias=None # Esto define al global
        ).first()
        
        if presu_obj:
            presupuesto_global = presu_obj.monto_limite

        # El saldo ahora es: Meta Global - Gastos Totales
        saldo_disponible = presupuesto_global - gastos

    

        # 2. DATOS PARA GRÁFICO DE TORTA (Gastos por Categoría)
        # Agrupamos manualmente para simplificar la respuesta JSON
        gastos_query = transacciones.filter(tipo='GASTO').select_related('categoria')
        data_torta = {}
        
        for g in gastos_query:
            # Usamos el nombre del Padre si existe, o el nombre de la categoría
            nombre = "Otros"
            if g.categoria:
                if g.categoria.categoria_padre:
                    nombre = g.categoria.categoria_padre.nombre
                else:
                    nombre = g.categoria.nombre
            
            data_torta[nombre] = data_torta.get(nombre, 0) + float(g.monto)

        # Formato lista para Flutter: [{"name": "Comida", "value": 5000}, ...]
        lista_torta = [{"name": k, "value": v} for k, v in data_torta.items()]

        # 3. DATOS PARA GRÁFICO DE LÍNEA (Gastos por Día)
        gastos_dia = transacciones.filter(tipo='GASTO')\
            .annotate(dia=ExtractDay('fecha'))\
            .values('dia')\
            .annotate(total=Sum('monto'))\
            .order_by('dia')
            
        # Creamos un mapa de días {1: 0, 2: 500, ... 31: 0}
        mapa_dias = {d: 0 for d in range(1, 32)}
        for item in gastos_dia:
            mapa_dias[item['dia']] = float(item['total'])
            
        # Formato lista simple para el gráfico: [0, 500, 200, 0, ...]
        lista_dias = [mapa_dias[d] for d in sorted(mapa_dias.keys())]

        return Response({
            "totales": {
                "ingresos": ingresos, # Lo mandamos por si quieres usarlo luego
                "gastos": gastos,
                "presupuesto_global": presupuesto_global, # NUEVO
                "saldo": saldo_disponible # ACTUALIZADO (Meta - Gastos)
            },
            "grafico_torta": lista_torta, # Asegúrate de tener las variables lista_torta
            "grafico_linea": lista_dias   # y lista_dias definidas como antes
        })