import json
import requests
from django.conf import settings
from django.utils import timezone
from usuarios.models import UsuarioCustom
from app_finanzas.models import Transaccion, WhatsAppLog, WhatsAppSession, Categoria

class WhatsAppService:
    def __init__(self):
        self.api_url = settings.WHATSAPP_API_URL
        self.headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }

    def procesar_log(self, log_id):
        log = WhatsAppLog.objects.get(id=log_id)
        
        try:
            payload = log.payload
            entry = payload.get('entry', [])[0]
            changes = entry.get('changes', [])[0]
            value = changes.get('value', {})
            messages = value.get('messages', [])
            
            if not messages: return 

            mensaje = messages[0]
            telefono = mensaje.get('from') 
            
            # 1. Identificar Usuario
            try:
                usuario = UsuarioCustom.objects.get(numero_telefono=telefono)
            except UsuarioCustom.DoesNotExist:
                # Si no existe, podrías enviar un mensaje de error opcional aquí
                return

            # 2. Obtener Sesión
            sesion, created = WhatsAppSession.objects.get_or_create(
                usuario=usuario, defaults={'telefono': telefono}
            )

            # 3. Detectar qué escribió o presionó
            tipo_msg = mensaje.get('type')
            texto = ""
            if tipo_msg == 'text':
                texto = mensaje.get('text', {}).get('body', '').strip()
            elif tipo_msg == 'interactive':
                int_data = mensaje.get('interactive')
                if int_data['type'] == 'button_reply':
                    texto = int_data['button_reply']['id']
                elif int_data['type'] == 'list_reply':
                    texto = int_data['list_reply']['id']

            # 4. Comandos de Salida
            if texto.lower() in ['hola', 'menu', 'cancelar', 'inicio']:
                self.resetear(sesion)
                self.enviar_menu(telefono, usuario.first_name)
                return

            # 5. Máquina de Estados
            self.manejar_flujo(sesion, texto, telefono)

        except Exception as e:
            log.error = str(e)
            log.save()

    def manejar_flujo(self, sesion, input_usuario, telefono):
        
        if sesion.estado == 'INICIO':
            if input_usuario == 'BTN_NUEVO_GASTO':
                sesion.estado = 'ESPERANDO_MONTO'
                sesion.datos_temporales = {'tipo': 'GASTO'}
                sesion.save()
                self.enviar_mensaje(telefono, "💰 Ingresa el monto (solo números):")
            elif input_usuario == 'BTN_VER_SALDO':
                # Aquí podrías calcular saldo real
                self.enviar_mensaje(telefono, "📊 Tu saldo es... (Próximamente)")
            else:
                self.enviar_mensaje(telefono, "Usa el menú para comenzar.")

        elif sesion.estado == 'ESPERANDO_MONTO':
            if input_usuario.isdigit():
                datos = sesion.datos_temporales
                datos['monto'] = int(input_usuario)
                sesion.datos_temporales = datos
                sesion.estado = 'ESPERANDO_CATEGORIA'
                sesion.save()
                self.enviar_lista_categorias(telefono, sesion.usuario)
            else:
                self.enviar_mensaje(telefono, "🔢 Por favor ingresa solo números.")

        elif sesion.estado == 'ESPERANDO_CATEGORIA':
            if input_usuario.startswith('cat_'):
                cat_id = input_usuario.split('_')[1]
                if cat_id == 'null': cat_id = None
                
                datos = sesion.datos_temporales
                Transaccion.objects.create(
                    usuario=sesion.usuario,
                    tipo=datos['tipo'],
                    monto=datos['monto'],
                    fecha=timezone.now().date(),
                    categoria_id=cat_id,
                    descripcion="WhatsApp Bot"
                )
                self.enviar_mensaje(telefono, f"✅ Gasto de ${datos['monto']} guardado.")
                self.resetear(sesion)
            else:
                self.enviar_mensaje(telefono, "Selecciona una categoría de la lista.")

    def resetear(self, sesion):
        sesion.estado = 'INICIO'
        sesion.datos_temporales = {}
        sesion.save()

    # --- ENVÍOS A META ---
    def enviar_mensaje(self, telefono, texto):
        data = {"messaging_product": "whatsapp", "to": telefono, "type": "text", "text": {"body": texto}}
        requests.post(self.api_url, headers=self.headers, json=data)

    def enviar_menu(self, telefono, nombre):
        data = {
            "messaging_product": "whatsapp", "to": telefono, "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": f"Hola {nombre}, ¿qué deseas hacer?"},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "BTN_NUEVO_GASTO", "title": "Registrar Gasto"}},
                        {"type": "reply", "reply": {"id": "BTN_VER_SALDO", "title": "Ver Saldo"}}
                    ]
                }
            }
        }
        requests.post(self.api_url, headers=self.headers, json=data)

    def enviar_lista_categorias(self, telefono, usuario):
        cats = Categoria.objects.filter(usuario=usuario)[:8]
        rows = [{"id": f"cat_{c.id}", "title": c.nombre} for c in cats]
        rows.append({"id": "cat_null", "title": "General"})
        
        data = {
            "messaging_product": "whatsapp", "to": telefono, "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": "Categorías"},
                "body": {"text": "Selecciona una categoría"},
                "action": {
                    "button": "Ver Lista",
                    "sections": [{"title": "Tus Categorías", "rows": rows}]
                }
            }
        }
        requests.post(self.api_url, headers=self.headers, json=data)