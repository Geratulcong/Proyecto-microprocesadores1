from uuid import uuid4

from bleak import BleakScanner, BleakClient
import asyncio
import json
import time

from services.notification_service import NotificationService
from database.usuario.contacto_db import ContactoDB
from services.raspberry_service import RaspberryService
from database.evento.evento_raspberry_db import EventoRaspberryDB
from database.dispositivos.raspberry_db import RaspberryDB
from services.emergency_service import EmergencyService

DEVICE_NAME = "Sensor-Cadera"

CHARACTERISTIC_UUID = "19b10001-0000-1000-8000-00805f9b34fb"


class BLEService:

    COOLDOWN_CAIDA = 30 * 60  # 30 minutos

    def __init__(self):
        self.client = None
        self.last_data_time = time.time()
        self.modelo_caida_service = None
        self.ultima_alerta_caida = 0
        self.ultima_alerta_desconexion = 0
        self.COOLDOWN_DESCONEXION = 5 * 60  # 5 minutos
        self.notification_service = NotificationService()
        self.contacto_db = ContactoDB()
        self.usuario_id = None

    
    async def enviar_mensaje_caida(self, probabilidad):

        print("Enviando mensaje de caída...")
        contactos = self.contacto_db.obtener_contactos_activos(
            self.usuario_id
        )

        for contacto in contactos:

            contacto_id = contacto[0]
            telefono = contacto[3]

            await self.notification_service.enviar_whatsapp(
                contacto_id=contacto_id,
                telefono=telefono,
                mensaje=f"ALERTA: Se detectó una caída.",
                evento_id = None
            )

    async def notification_handler(self, sender, data):

        try:
            self.last_data_time = time.time()

            mensaje = data.decode()
            sensor_data = json.loads(mensaje)

            # Manejar alerta manual enviada desde Arduino
            if isinstance(sensor_data, dict) and sensor_data.get("manual_alert"):
                print("Alerta manual recibida desde sensor")
                try:
                    emergency = EmergencyService()
                    await emergency.activar_alerta_manual(self.usuario_id)
                except Exception as e:
                    print(f"Error manejando alerta manual: {e}")
                return

            datos_sensor = [
                sensor_data["ax"],
                sensor_data["ay"],
                sensor_data["az"],
                sensor_data["gx"],
                sensor_data["gy"],
                sensor_data["gz"]
            ]

            resultado = self.modelo_caida_service.predecir(datos_sensor)

            if resultado is None:
                print("Llenando ventana del modelo...")
                return

            print(f"Probabilidad caída: {resultado['probabilidad']:.2f}")

            if resultado["caida"]:

                tiempo_actual = time.time()

                if tiempo_actual - self.ultima_alerta_caida < self.COOLDOWN_CAIDA:
                    print("Caída detectada, pero alerta bloqueada por 30 minutos")
                    return

                self.ultima_alerta_caida = tiempo_actual

                print("CAÍDA DETECTADA")

                await self.enviar_mensaje_caida(
                    resultado["probabilidad"]
                )

        except Exception as e:
            print(f"Error BLE: {e}")

    async def conectar(self, modelo_caida_service, usuario_id):

        self.modelo_caida_service = modelo_caida_service
        self.usuario_id = usuario_id

        while True:

            try:
                print("Buscando Arduino...")

                devices = await BleakScanner.discover()

                target = None

                for device in devices:
                    if device.name == DEVICE_NAME:
                        target = device
                        break

                if target is None:
                    print("Arduino no encontrado")
                    await asyncio.sleep(5)
                    continue

                print(f"Conectando a {target.address}")

                self.client = BleakClient(target.address)

                await self.client.connect()

                print("BLE conectado")

                await self.client.start_notify(
                    CHARACTERISTIC_UUID,
                    self.notification_handler
                )

                while self.client.is_connected:

                    await asyncio.sleep(1)

                    tiempo_sin_datos = time.time() - self.last_data_time

                    if tiempo_sin_datos > 10:
                            print("Sensor desconectado")
                            tiempo_actual = time.time()

                            if tiempo_actual - self.ultima_alerta_desconexion >= self.COOLDOWN_DESCONEXION:
                                self.ultima_alerta_desconexion = tiempo_actual
                                try:
                                    await self.enviar_mensaje_desconexion()
                                except Exception as e:
                                    print(f"Error enviando notificación de desconexión: {e}")
                            else:
                                print("Alerta de desconexión en cooldown")

                            await self.client.disconnect()

            except Exception as e:
                print(f"Error conexión BLE: {e}")

            print("Reintentando conexión...")

            await asyncio.sleep(5)

    async def desconectar(self):
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            self.client = None
            print("BLE desconectado")

    async def enviar_mensaje_desconexion(self):

        print("Enviando mensaje de desconexión...")

        contactos = self.contacto_db.obtener_contactos_activos(
            self.usuario_id
        )

        evento_id = str(uuid4())

        # Registrar evento en BD y actualizar estado del dispositivo
        raspberry_id = RaspberryService.obtener_id()

        try:
            if raspberry_id:
                evento_db = EventoRaspberryDB()
                evento_db.registrar_evento(
                    evento_raspberry_id=evento_id,
                    raspberry_id=raspberry_id,
                    evento_tipo="Desconexión"
                )

                raspberry_db = RaspberryDB()
                try:
                    raspberry_db.actualizar_estado(
                        raspberry_id=raspberry_id,
                        estado_arduino="Desconectado",
                        estado_pagina_web="Desconectado",
                        nivel_bateria=0
                    )
                except Exception:
                    pass

        except Exception as e:
            print(f"Error registrando evento de desconexión: {e}")

        for contacto in contactos:

            contacto_id = contacto[0]
            telefono = contacto[3]

            await self.notification_service.enviar_whatsapp(
                contacto_id=contacto_id,
                telefono=telefono,
                mensaje=f"ALERTA: Se detectó desconexión del sensor.",
                evento_id=None,
                evento_raspberry_id=evento_id
            )