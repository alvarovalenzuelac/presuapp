from django.apps import AppConfig


class AppFinanzasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_finanzas'
    def ready(self):
        import app_finanzas.signals # <--- ESTA LÍNEA CONECTA EL CABLE