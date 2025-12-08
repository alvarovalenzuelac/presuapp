from django.urls import path
from .views import UsuarioLogueadoView

urlpatterns = [
    # Endpoint para obtener mis propios datos
    path('me/', UsuarioLogueadoView.as_view(), name='usuario_me'),
    
    # ... aquí seguramente tienes tus rutas de login/token ...
]