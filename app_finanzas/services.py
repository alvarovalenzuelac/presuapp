import requests
import logging
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, Q # <--- Importante para los cálculos
from usuarios.models import UsuarioCustom
from app_finanzas.models import Transaccion, WhatsAppLog, WhatsAppSession, Categoria

logger = logging.getLogger(__name__)

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
            # ... (Lógica de extracción del mensaje igual que antes) ...
            payload = log.payload
            entry = payload.get('entry', [])[0]
            changes = entry.get('changes', [])[0]
            value = changes.get('value', {})
            messages = value.get('messages', [])
            
            if not messages: return 

            mensaje = messages[0]
            telefono = mensaje.get('from') 
            
            # Búsqueda flexible del usuario (con o sin +)
            usuario = UsuarioCustom.objects.filter(
                Q(numero_telefono=telefono) | Q(numero_telefono=f"+{telefono}")
            ).first()

            if not usuario:
                print(f"⚠️ Usuario no encontrado: {telefono}")
                return

            sesion, created = WhatsAppSession.objects.get_or_create(
                usuario=usuario, defaults={'telefono': telefono}
            )

            # Interpretar texto o selección
            tipo_msg = mensaje.get('type')
            texto_usuario = ""
            if tipo_msg == 'text':
                texto_usuario = mensaje.get('text', {}).get('body', '').strip()
            elif tipo_msg == 'interactive':
                interactivo = mensaje.get('interactive')
                if interactivo.get('type') == 'button_reply':
                    texto_usuario = interactivo['button_reply']['id']
                elif interactivo.get('type') == 'list_reply':
                    texto_usuario = interactivo['list_reply']['id']

            # Comandos globales
            if texto_usuario.lower() in ['hola', 'menu', 'inicio', 'cancelar', 'salir']:
                self.resetear_sesion(sesion)
                self.enviar_menu_principal(telefono, usuario.first_name)
                return

            self.manejar_flujo(sesion, texto_usuario, telefono)
            
            log.procesado = True
            log.save()

        except Exception as e:
            log.error = str(e)
            log.save()
            print(f"Error: {e}")

    def manejar_flujo(self, sesion, input_usuario, telefono):
        
        # --- ESTADO 1: MENÚ PRINCIPAL ---
        if sesion.estado == 'INICIO':
            if input_usuario == 'BTN_NUEVO_GASTO':
                sesion.estado = 'ESPERANDO_MONTO'
                sesion.datos_temporales = {'tipo': 'GASTO'}
                sesion.save()
                self.enviar_mensaje(telefono, "💰 *Registrar Gasto*\nIngresa el monto (solo números):")
            
            elif input_usuario == 'BTN_RESUMEN': # <--- Nuevo nombre
                self.enviar_resumen_mensual(telefono, sesion.usuario)
            
            else:
                self.enviar_menu_principal(telefono, sesion.usuario.first_name)

        # --- ESTADO 2: RECIBIMOS MONTO -> PEDIMOS PADRE ---
        elif sesion.estado == 'ESPERANDO_MONTO':
            if input_usuario.isdigit():
                datos = sesion.datos_temporales
                datos['monto'] = int(input_usuario)
                sesion.datos_temporales = datos
                
                # Avanzamos al siguiente paso
                sesion.estado = 'ESPERANDO_CATEGORIA_PADRE'
                sesion.save()
                
                self.enviar_lista_padres(telefono, sesion.usuario)
            else:
                self.enviar_mensaje(telefono, "🔢 Por favor ingresa un número válido (sin puntos ni signos).")

        # --- ESTADO 3: RECIBIMOS PADRE -> PEDIMOS HIJA ---
        elif sesion.estado == 'ESPERANDO_CATEGORIA_PADRE':
            if input_usuario.startswith('padre_'):
                padre_id = input_usuario.split('_')[1]
                
                # Guardamos el padre seleccionado temporalmente
                datos = sesion.datos_temporales
                datos['padre_id'] = padre_id
                sesion.datos_temporales = datos
                
                # Avanzamos
                sesion.estado = 'ESPERANDO_CATEGORIA_HIJA'
                sesion.save()
                
                self.enviar_lista_hijas(telefono, sesion.usuario, padre_id)
            else:
                self.enviar_mensaje(telefono, "Selecciona una categoría de la lista.")

        # --- ESTADO 4: RECIBIMOS HIJA -> GUARDAMOS ---
        elif sesion.estado == 'ESPERANDO_CATEGORIA_HIJA':
            if input_usuario.startswith('cat_'):
                cat_id_raw = input_usuario.split('_')[1]
                
                cat_final = None
                
                # Lógica para "General"
                if cat_id_raw == 'general':
                    # Buscamos la categoría "General" o "Otros" real en la BD
                    cat_final = Categoria.objects.filter(
                        Q(nombre__iexact="General") | Q(nombre__iexact="Otros")
                    ).first()
                else:
                    # Buscamos la categoría por ID
                    try:
                        cat_final = Categoria.objects.get(id=cat_id_raw)
                    except Categoria.DoesNotExist:
                        cat_final = None # Fallback

                # Guardamos la transacción
                datos = sesion.datos_temporales
                Transaccion.objects.create(
                    usuario=sesion.usuario,
                    tipo=datos.get('tipo', 'GASTO'),
                    monto=datos.get('monto', 0),
                    fecha=timezone.now().date(),
                    categoria=cat_final,
                    descripcion=f"WhatsApp Bot ({cat_final.nombre if cat_final else 'General'})"
                )
                
                texto_cat = cat_final.nombre if cat_final else "General"
                self.enviar_mensaje(telefono, f"✅ *¡Listo!*\nGasto de ${datos['monto']} registrado en *{texto_cat}*.")
                
                # Volvemos al inicio y mostramos menú
                self.resetear_sesion(sesion)
                self.enviar_menu_principal(telefono, sesion.usuario.first_name)

            elif input_usuario == 'VOLVER':
                 # Opción para volver atrás si se equivocó de Padre
                 sesion.estado = 'ESPERANDO_CATEGORIA_PADRE'
                 sesion.save()
                 self.enviar_lista_padres(telefono, sesion.usuario)
            else:
                self.enviar_mensaje(telefono, "Selecciona una opción válida.")

    def resetear_sesion(self, sesion):
        sesion.estado = 'INICIO'
        sesion.datos_temporales = {}
        sesion.save()

    # --- MÉTODOS DE ENVÍO ---

    def enviar_mensaje(self, telefono, texto):
        data = {"messaging_product": "whatsapp", "to": telefono, "type": "text", "text": {"body": texto}}
        self._enviar_api(data)

    def enviar_menu_principal(self, telefono, nombre):
        data = {
            "messaging_product": "whatsapp", "to": telefono, "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": f"Hola {nombre} 👋\n¿Qué deseas hacer hoy?"},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "BTN_NUEVO_GASTO", "title": "Registrar Gasto"}},
                        {"type": "reply", "reply": {"id": "BTN_RESUMEN", "title": "Ver Resumen"}}
                    ]
                }
            }
        }
        self._enviar_api(data)

    def enviar_resumen_mensual(self, telefono, usuario):
        hoy = timezone.now()
        # Calculamos gastos del mes actual
        gastos = Transaccion.objects.filter(
            usuario=usuario,
            tipo='GASTO',
            fecha__month=hoy.month,
            fecha__year=hoy.year
        ).aggregate(Sum('monto'))['monto__sum'] or 0
        
        # Opcional: Calcular Ingresos también
        ingresos = Transaccion.objects.filter(
            usuario=usuario,
            tipo='INGRESO',
            fecha__month=hoy.month,
            fecha__year=hoy.year
        ).aggregate(Sum('monto'))['monto__sum'] or 0
        
        balance = ingresos - gastos

        msg = (
            f"📅 *Resumen de {hoy.strftime('%B')}*\n"
            f"────────────────\n"
            f"📉 *Gastos:* ${gastos:,.0f}\n"
            f"📈 *Ingresos:* ${ingresos:,.0f}\n"
            f"────────────────\n"
            f"💰 *Balance:* ${balance:,.0f}"
        ).replace(",", ".") # Formato CL
        
        self.enviar_mensaje(telefono, msg)
        # Re-enviamos el menú para que siga operando
        self.enviar_menu_principal(telefono, usuario.first_name)

    def enviar_lista_padres(self, telefono, usuario):
        # Buscamos categorías PADRE (categoria_padre=None)
        # Que sean Globales (usuario=None) O del Usuario
        padres = Categoria.objects.filter(
            Q(usuario=None) | Q(usuario=usuario),
            categoria_padre=None
        ).order_by('nombre')[:9] # Límite de WhatsApp: 10 filas

        rows = [{"id": f"padre_{c.id}", "title": c.nombre} for c in padres]
        
        data = {
            "messaging_product": "whatsapp", "to": telefono, "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": "Categoría Principal"},
                "body": {"text": "¿En qué grupo entra este gasto?"},
                "action": {
                    "button": "Seleccionar",
                    "sections": [{"title": "Familias", "rows": rows}]
                }
            }
        }
        self._enviar_api(data)

    def enviar_lista_hijas(self, telefono, usuario, padre_id):
        # Buscamos las HIJAS del padre seleccionado
        hijas = Categoria.objects.filter(
            Q(usuario=None) | Q(usuario=usuario),
            categoria_padre_id=padre_id
        ).order_by('nombre')[:8]

        rows = [{"id": f"cat_{c.id}", "title": c.nombre} for c in hijas]
        
        # Agregamos opciones fijas
        rows.append({"id": "cat_general", "title": "General / Otro"})
        rows.append({"id": "VOLVER", "title": "🔙 Volver Atrás"})

        data = {
            "messaging_product": "whatsapp", "to": telefono, "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": "Detalle"},
                "body": {"text": "Selecciona la subcategoría específica:"},
                "action": {
                    "button": "Seleccionar",
                    "sections": [{"title": "Opciones", "rows": rows}]
                }
            }
        }
        self._enviar_api(data)

    def _enviar_api(self, data):
        try:
            requests.post(self.api_url, headers=self.headers, json=data)
        except Exception as e:
            print(f"Error API: {e}")