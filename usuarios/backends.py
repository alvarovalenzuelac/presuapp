from django.contrib.auth.backends import ModelBackend
from django.utils import timezone

class BloqueoBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # 1. Intentamos autenticar con la lógica normal de Django
        user = super().authenticate(request, username, password, **kwargs)
        
        # 2. Si las credenciales son válidas, hacemos el chequeo extra
        if user:
            # Si el usuario tiene una fecha de bloqueo y esa fecha es FUTURA
            if user.bloqueado_hasta and user.bloqueado_hasta > timezone.now():
                # Retornamos None para que Django piense que falló el login
                print(f"⛔ Acceso denegado a {user.email}: Cuenta bloqueada temporalmente.")
                return None
            
            # Si no está bloqueado, lo dejamos pasar
            return user
            
        return None