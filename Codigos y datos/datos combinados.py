import asyncio
import json
from datetime import datetime
from bleak import BleakClient

# Configuración (actualiza la MAC si cambia)
CADERA_MAC = "FA:04:1B:E0:65:B1"
CHARACTERISTIC_UUID = "19b10001-e8f2-537e-4f6c-d104768a1214"

# Archivo de salida
archivo_log = "c:\\xampp\\htdocs\\Proyecto-microprocesadores1\\datos_capturados.csv"

# Buffers y contadores
buffer_datos = []
contador_notificaciones = 0
notif_seq = 0

def guardar_datos():
    """Guarda los datos del buffer en archivo CSV"""
    global buffer_datos
    try:
        with open(archivo_log, 'a') as f:
            for dato in buffer_datos:
                c = dato['cadera']
                p = dato['pierna']
                linea = (f"{dato.get('seq','')},"
                         f"{c['ax']},{c['ay']},{c['az']},"
                         f"{c['gx']},{c['gy']},{c['gz']},"
                         f"{p['ax']},{p['ay']},{p['az']},"
                         f"{p['gx']},{p['gy']},{p['gz']}\n")
                f.write(linea)
        print(f"\n💾 Guardadas {len(buffer_datos)} muestras en {archivo_log}")
        buffer_datos = []
    except Exception as e:
        print(f"❌ Error guardando datos: {e}")

async def notification_handler(sender, data):
    """Procesa datos recibidos del Arduino Cadera (acepta JSON o CSV de 12 valores)"""
    global contador_notificaciones, notif_seq, buffer_datos
    contador_notificaciones += 1
    notif_seq += 1

    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"\n[{timestamp}] 📨 Notificación #{contador_notificaciones} recibida")
    print(f"Tamaño: {len(data)} bytes")
    print(f"Datos raw: {data}")

    try:
        s = data.decode('utf-8', errors='ignore').strip()
        print(f"String decodificado: {s}")

        # Si es JSON, parsear normalmente
        if s.startswith('{') or s.startswith('['):
            json_data = json.loads(s)

        else:
            # Esperamos CSV: 12 valores "c_ax,c_ay,c_az,c_gx,c_gy,c_gz,p_ax,...,p_gz"
            parts = [p.strip() for p in s.split(',') if p.strip() != '']
            if len(parts) < 12:
                raise ValueError(f"Formato CSV inesperado, {len(parts)} campos (se esperan 12)")
            vals = [float(p) for p in parts[:12]]

            json_data = {
                "seq": notif_seq,
                "cadera": {
                    "ax": vals[0], "ay": vals[1], "az": vals[2],
                    "gx": vals[3], "gy": vals[4], "gz": vals[5]
                },
                "pierna": {
                    "ax": vals[6], "ay": vals[7], "az": vals[8],
                    "gx": vals[9], "gy": vals[10], "gz": vals[11]
                }
            }

        # Mostrar datos parseados
        print(f"\n{'='*40}")
        print(f"Secuencia: {json_data.get('seq','-')}")
        c = json_data['cadera']
        p = json_data['pierna']
        print(f"Cadera -> ax:{c['ax']:.3f} ay:{c['ay']:.3f} az:{c['az']:.3f} | gx:{c['gx']:.3f} gy:{c['gy']:.3f} gz:{c['gz']:.3f}")
        print(f"Pierna -> ax:{p['ax']:.3f} ay:{p['ay']:.3f} az:{p['az']:.3f} | gx:{p['gx']:.3f} gy:{p['gy']:.3f} gz:{p['gz']:.3f}")

        # Guardar en buffer y disco como antes
        buffer_datos.append(json_data)
        if len(buffer_datos) >= 10:
            guardar_datos()

    except json.JSONDecodeError as e:
        print(f"❌ Error decodificando JSON: {e}")
        print(f"Datos recibidos: {data}")
    except Exception as e:
        print(f"❌ Error procesando notificación: {e}")
        print(f"String recibido: {data.decode(errors='ignore')}")

async def main():
    print("╔════════════════════════════════════════════════╗")
    print("║   Lector de Datos Combinados (Cadera+Pierna)  ║")
    print("╚════════════════════════════════════════════════╝\n")

    print(f"🔍 Conectando a Arduino Cadera ({CADERA_MAC})...")

    try:
        async with BleakClient(CADERA_MAC, timeout=30.0) as client:
            if not client.is_connected:
                print("❌ No se pudo establecer la conexión BLE")
                return
            print("✅ Conectado!")

            # Obtener servicios y características
            await client.get_services()
            print(f"📡 Servicios disponibles:")
            for service in client.services:
                print(f"  - {service.uuid}")
                for char in service.characteristics:
                    print(f"    • {char.uuid}  prop: {char.properties}")

            # Verificar existencia de la característica
            try:
                char = client.services.get_characteristic(CHARACTERISTIC_UUID)
                print(f"\n✅ Característica encontrada: {CHARACTERISTIC_UUID}")
                print(f"   Propiedades: {char.properties}")
            except Exception as e:
                print(f"\n❌ Característica no encontrada: {e}")
                return

            # Intentar suscribirse con reintentos
            max_attempts = 4
            for attempt in range(1, max_attempts + 1):
                try:
                    print(f"\n📡 Suscribiéndose a notificaciones... (intento {attempt})")
                    await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
                    print("✅ Suscrito correctamente")
                    break
                except Exception as e:
                    print(f"⚠️ start_notify fallo (intento {attempt}): {e}")
                    # si se desconectó, intentar reconectar
                    if not client.is_connected:
                        try:
                            print("🔁 Intentando reconectar al dispositivo...")
                            await client.connect()
                            await client.get_services()
                            print("🔌 Reconectado")
                        except Exception as e2:
                            print(f"❌ Reconexión fallida: {e2}")
                    await asyncio.sleep(1)
            else:
                print("❌ No se pudo suscribir a notificaciones tras varios intentos")
                return

            print(f"\n📥 Esperando datos... (Ctrl+C para detener)\n")

            # Mantener conexión y mostrar progreso
            timeout_counter = 0
            global contador_notificaciones
            while True:
                await asyncio.sleep(1)
                timeout_counter += 1

                if contador_notificaciones == 0 and timeout_counter > 10:
                    print("\n⚠️  No se han recibido notificaciones en 10 segundos")
                    print("Verifica en el Monitor Serial del Arduino que esté enviando datos")
                    # no cerramos inmediatamente, seguimos esperando
                    timeout_counter = 0

                if timeout_counter % 5 == 0 and contador_notificaciones > 0:
                    print(f"\n⏰ {contador_notificaciones} notificaciones recibidas hasta ahora")

    except KeyboardInterrupt:
        print("\n\n⏹️  Deteniendo captura...")
        if buffer_datos:
            guardar_datos()
        print(f"✅ Total de notificaciones recibidas: {contador_notificaciones}")
        print("✅ Datos guardados. ¡Hasta luego!")

    except Exception as e:
        print(f"\n❌ Error de conexión: {e}")
        print("\nVerifica que:")
        print("  1. El Monitor Serial del Arduino esté cerrado (bloquea BLE).")
        print("  2. El Arduino Cadera esté encendido y anunciando.")
        print("  3. El Arduino Cadera esté conectado a la pierna.")
        print("  4. La MAC sea correcta.")

if __name__ == "__main__":
    # Crear archivo CSV con encabezados (sobrescribe)
    with open(archivo_log, 'w') as f:
        f.write("seq,cadera_ax,cadera_ay,cadera_az,cadera_gx,cadera_gy,cadera_gz,"
                "pierna_ax,pierna_ay,pierna_az,pierna_gx,pierna_gy,pierna_gz\n")

    print(f"📝 Archivo de log creado: {archivo_log}\n")
    asyncio.run(main())