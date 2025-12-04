import re
from django.utils import timezone
from usuarios.models import UsuarioCustom
from app_finanzas.models import Transaccion, WhatsAppLog, Categoria

class WhatsAppService:
    def procesar_log(self, log_id):
        log = WhatsAppLog.objects.get(id=log_id)
        
        try:
            payload = log.payload
            
            # 1. EXTRAER DATOS BÁSICOS DEL JSON DE WHATSAPP
            # La estructura de Meta es anidada y compleja
            entry = payload.get('entry', [])[0]
            changes = entry.get('changes', [])[0]
            value = changes.get('value', {})
            messages = value.get('messages', [])
            
            if not messages:
                log.error = "No message found in payload"
                log.save()
                return

            mensaje = messages[0]
            telefono_origen = mensaje.get('from') # Ej: "56912345678"
            texto_mensaje = mensaje.get('text', {}).get('body', '')

            # 2. IDENTIFICAR AL USUARIO
            # Buscamos quién tiene este número en la BD
            try:
                usuario = UsuarioCustom.objects.get(numero_telefono=telefono_origen)
            except UsuarioCustom.DoesNotExist:
                log.error = f"Usuario no encontrado para el teléfono {telefono_origen}"
                log.save()
                return

            # 3. INTERPRETAR EL TEXTO (PARSING)
            # Esperamos formato: "MONTO DESCRIPCION" (ej: "5000 Pan y bebida")
            # Usamos Expresiones Regulares (Regex)
            # ^(\d+) busca un número al inicio
            # \s+ busca espacios
            # (.+)$ busca el resto del texto
            patron = r"^(\d+)\s+(.+)$"
            match = re.match(patron, texto_mensaje)

            if match:
                monto = match.group(1)
                descripcion = match.group(2)
                
                # Buscamos una categoría "General" por defecto o intentamos adivinar (Mejora futura)
                # Por ahora, lo dejamos sin categoría o buscamos "Otros"
                categoria_default = Categoria.objects.filter(nombre="Otros", usuario=None).first()

                # 4. CREAR LA TRANSACCIÓN
                Transaccion.objects.create(
                    usuario=usuario,
                    tipo='GASTO',
                    monto=monto,
                    descripcion=descripcion,
                    fecha=timezone.now().date(),
                    categoria=categoria_default # Puede ser None
                )
                
                log.procesado = True
                log.save()
                print(f"✅ Gasto creado para {usuario.email}: ${monto} - {descripcion}")
            
            else:
                log.error = "Formato inválido. Use: MONTO DESCRIPCION"
                log.save()

        except Exception as e:
            log.error = str(e)
            log.save()