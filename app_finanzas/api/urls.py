from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoriaViewSet, TransaccionViewSet, PresupuestoViewSet, WhatsAppWebhookView,DashboardDataView

# El Router crea las rutas REST automáticamente
router = DefaultRouter()
router.register(r'categorias', CategoriaViewSet, basename='api_categorias')
router.register(r'transacciones', TransaccionViewSet, basename='api_transacciones')
router.register(r'presupuestos', PresupuestoViewSet, basename='api_presupuestos')

urlpatterns = [
    path('', include(router.urls)),
    path('webhook-whatsapp/', WhatsAppWebhookView.as_view(), name='webhook_whatsapp'),
    path('dashboard-data/', DashboardDataView.as_view(), name='api_dashboard_data'),
]