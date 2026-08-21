from uuid import uuid4
from services.notification_service import NotificationService
from database.usuario.contacto_db import ContactoDB
from database.evento.evento_raspberry_db import EventoRaspberryDB
from database.dispositivos.raspberry_db import RaspberryDB
from services.raspberry_service import RaspberryService


class EmergencyService:

    async def activar_alerta_manual(self, usuario_id):

        print("Activando alerta manual...")

        notification_service = NotificationService()
        contacto_db = ContactoDB()

        contactos = contacto_db.obtener_contactos_activos(usuario_id)

        evento_id = str(uuid4())

        # Registrar evento de tipo 'Alerta Manual' y marcar estado Raspberry
        raspberry_id = RaspberryService.obtener_id()

        try:
            if raspberry_id:
                evento_db = EventoRaspberryDB()
                evento_db.registrar_evento(
                    evento_raspberry_id=evento_id,
                    raspberry_id=raspberry_id,
                    evento_tipo="Alerta Manual"
                )

                try:
                    raspberry_db = RaspberryDB()
                    raspberry_db.actualizar_estado(
                        raspberry_id=raspberry_id,
                        estado_arduino="Alerta Manual",
                        estado_pagina_web="Vinculado",
                        nivel_bateria=None
                    )
                except Exception:
                    pass

        except Exception as e:
            print(f"Error registrando evento de alerta manual: {e}")

        for contacto in contactos:

            contacto_id = contacto[0]
            telefono = contacto[3]

            await notification_service.enviar_whatsapp(
                contacto_id=contacto_id,
                telefono=telefono,
                mensaje="ALERTA MANUAL: Se activó una alerta de emergencia manual desde el dispositivo.",
                evento_id=None,
                evento_raspberry_id=evento_id
            )