
from django.contrib import admin
from django.urls import path,include
from django.contrib.auth import views as auth_views
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from usuarios import views as user_views
from app_finanzas import views as finanzas_views
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# Info de la api
schema_view = get_schema_view(
   openapi.Info(
      title="API PresuApp",
      default_version='v1',
      description="Documentación oficial de la API para App Móvil y WhatsApp",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="tu@email.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,), # Permitimos ver la docu a cualquiera (Ojo en producción)
)

def home_view(request):
    return render(request, 'inicio.html')

@login_required # Esto protege la vista: si no estás logueado, te manda al login
def dashboard_view(request):
    return render(request, 'dashboard.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Rutas Principales
    path('', user_views.home_view, name='inicio'),
    path('dashboard/', user_views.dashboard_view, name='dashboard'),
    path('perfil/', user_views.perfil_view, name='perfil'),
    path('eliminar-cuenta/', user_views.eliminar_cuenta_view, name='eliminar_cuenta'),
    
    # Autenticación Personalizada
    path('registro/', user_views.registro_view, name='registro'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
#     path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('logout/', user_views.cerrar_sesion_view, name='logout'),

    # --- RECUPERACIÓN DE CONTRASEÑA (Django Standard) ---
    # Paso 1: Ingresar Email
    path('reset_password/', 
         auth_views.PasswordResetView.as_view(template_name='password_reset.html'), 
         name='password_reset'),
    
    # Paso 2: Mensaje de "Email enviado"
    path('reset_password_sent/', 
         auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), 
         name='password_reset_done'),
    
    # Paso 3: Link con token (El usuario hace clic en el mail)
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), 
         name='password_reset_confirm'),
    
    # Paso 4: Éxito
    path('reset_password_complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), 
         name='password_reset_complete'),
    path('categorias/', finanzas_views.categorias_view, name='categorias'),
    path('mis-gastos/', finanzas_views.mis_gastos_view, name='mis_gastos'),
    path('mis-gastos/nuevo/', finanzas_views.agregar_gasto_view, name='agregar_gasto'),
    path('gastos/mis-gastos/nuevo/', finanzas_views.agregar_gasto_view, name='agregar_gasto'),
    path('ajax/load-subcategorias/', finanzas_views.load_subcategorias, name='ajax_load_subcategorias'),
    path('categorias/editar/<int:id>/', finanzas_views.editar_categoria_view, name='editar_categoria'),
    path('categorias/eliminar/<int:id>/', finanzas_views.eliminar_categoria_view, name='eliminar_categoria'),
    path('gastos/editar/<int:id>/', finanzas_views.editar_gasto_view, name='editar_gasto'),
    path('gastos/eliminar/<int:id>/', finanzas_views.eliminar_gasto_view, name='eliminar_gasto'),
    path('presupuestos/', finanzas_views.lista_presupuestos_view, name='presupuestos'),
    path('presupuestos/nuevo/', finanzas_views.crear_presupuesto_view, name='crear_presupuesto'),
    path('presupuestos/eliminar/<int:id>/', finanzas_views.eliminar_presupuesto_view, name='eliminar_presupuesto'),
    path('presupuestos/editar/<int:id>/', finanzas_views.editar_presupuesto_view, name='editar_presupuesto'),
    # urls para autenticacion de la app movil
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'), # Login (User/Pass -> Token)
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), # Refrescar sesión
    path('api/v1/', include('app_finanzas.api.urls')),
    # urls para documentacion de la api
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
