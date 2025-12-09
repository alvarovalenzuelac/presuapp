from django.contrib.auth.signals import user_login_failed, user_logged_in
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from django.contrib.auth import get_user_model

Usuario = get_user_model()

# 1. SI FALLA EL LOGIN
@receiver(user_login_failed)
def registrar_intento_fallido(sender, credentials, request, **kwargs):
    # Buscamos al usuario por el email que ingresó
    email = credentials.get('username') or credentials.get('email')
    
    if not email:
        return

    try:
        user = Usuario.objects.get(email=email)
        
        # Si ya está bloqueado, no hacemos nada extra
        if user.esta_bloqueado():
            return

        # Incrementamos contador
        user.intentos_fallidos += 1
        user.save()
        
        print(f"⚠️ Intento fallido #{user.intentos_fallidos} para {user.email}")

        # Si llega a 3 intentos -> BLOQUEO
        if user.intentos_fallidos >= 3:
            # Bloquear por 15 minutos
            user.bloqueado_hasta = timezone.now() + timedelta(minutes=15)
            user.save()

            print(f"🚫 BLOQUEADO: {user.email} por 15 minutos.")

            # ENVIAR CORREO DE AVISO
            try:
                asunto = "⚠️ Alerta de Seguridad: Cuenta Bloqueada"
                mensaje = (
                    f"Hola {user.first_name},\n\n"
                    "Detectamos 3 intentos fallidos de acceso a tu cuenta.\n"
                    "Por tu seguridad, hemos bloqueado el acceso por 15 minutos.\n\n"
                    "Si fuiste tú, puedes esperar o restablecer tu contraseña aquí:\n"
                    f"{request.scheme}://{request.get_host()}/reset_password/\n"
                )
                
                send_mail(
                    asunto,
                    mensaje,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Error enviando correo: {e}")

    except Usuario.DoesNotExist:
        # El email no existe en nuestra BD, ignoramos.
        pass

# 2. SI LOGRA ENTRAR (LOGIN EXITOSO)
@receiver(user_logged_in)
def resetear_intentos(sender, request, user, **kwargs):
    if user.intentos_fallidos > 0:
        user.intentos_fallidos = 0
        user.bloqueado_hasta = None
        user.save()
        print(f"✅ Contador reseteado para {user.email}")