import asyncio
import struct
from datetime import datetime
from bleak import BleakClient, BleakScanner
import numpy as np
from tensorflow import keras
from collections import deque
import os

# Configuración: pon MAC si la conoces, si no deja string vacío para buscar por nombre
CADERA_MAC = "FA:04:1B:E0:65:B1"  # opcional, poner "" para discovery por nombre
DEVICE_NAME = "NanoSense33-Cadera"
CHARACTERISTIC_UUID = "19b10001-0000-1000-8000-00805f9b34fb"

# Modelo y ventana
SCRIPT_DIR = os.path.dirname(__file__)
# Por defecto usar modelo localizado en la misma carpeta que este script: Codigos_raspberry/modelo.h5
MODEL_PATH = os.environ.get("MODEL_PATH", os.path.join(SCRIPT_DIR, "modelo.h5"))
WINDOW_SIZE = int(os.environ.get("WINDOW_SIZE", "200"))  # usar 200 lecturas
PREDICT_INTERVAL = float(os.environ.get("PREDICT_INTERVAL", "0.1"))  # segundos (0.1s)
UMBRAL_PROB = float(os.environ.get("UMBRAL_PROB", "0.95"))

# Estado de conteo para tasa
total_count = 0
last_second_count = 0
_lock = asyncio.Lock()

# Buffer para muestras (cada muestra: [ax,ay,az,gx,gy,gz])
ventana = deque(maxlen=WINDOW_SIZE)
modelo = None

def parse_binary_packet(data: bytes):
    """Parsea paquete little-endian [seq:uint32][6*int16] => 16 bytes."""
    if len(data) < 16:
        return None
    try:
        unpacked = struct.unpack_from("<I6h", data, 0)
        seq = int(unpacked[0])
        ints = unpacked[1:]
        cad = {
            "adxl_x": ints[0], "adxl_y": ints[1], "adxl_z": ints[2],
            "itg_x":  ints[3], "itg_y":  ints[4], "itg_z":  ints[5],
        }
        return {"seq": seq, "cadera": cad}
    except Exception:
        return None

def try_parse_ascii(s: str):
    """
    Intenta parsear ASCII:
      - 6 ints CSV -> cadera counts (adxl3 + itg3)
      - >=6 floats -> toma primeros 6 como cadera (ax,ay,az,gx,gy,gz)
    """
    s = s.strip()
    if not s:
        return None
    parts = [p.strip() for p in s.split(",") if p.strip()!='']
    if len(parts) == 6:
        try:
            ints = [int(float(x)) for x in parts]
            cad = {
                "adxl_x": ints[0], "adxl_y": ints[1], "adxl_z": ints[2],
                "itg_x":  ints[3], "itg_y":  ints[4], "itg_z":  ints[5],
            }
            return {"seq": None, "cadera": cad}
        except Exception:
            return None
    if len(parts) >= 6:
        try:
            vals = [float(x) for x in parts]
            cad = {
                "adxl_x": vals[0], "adxl_y": vals[1], "adxl_z": vals[2],
                "itg_x":  vals[3], "itg_y":  vals[4], "itg_z":  vals[5],
            }
            return {"seq": None, "cadera": cad}
        except Exception:
            return None
    return None

async def notification_handler(sender, data: bytearray):
    """Callback para cada notificación: parsea y muestra por pantalla; actualiza contadores."""
    global total_count, last_second_count
    parsed = parse_binary_packet(bytes(data))
    if parsed is None:
        try:
            s = data.decode('utf-8', errors='ignore')
            parsed = try_parse_ascii(s)
        except Exception:
            parsed = None

    if parsed is None:
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{ts}] Notificación no parseable (len={len(data)} bytes)")
        return

    async with _lock:
        total_count += 1
        last_second_count += 1
        # Añadir muestra a la ventana (ax,ay,az,gx,gy,gz)
        cad_local = parsed.get("cadera")
        if cad_local:
            try:
                sample = [
                    float(cad_local.get("adxl_x", 0)), float(cad_local.get("adxl_y", 0)), float(cad_local.get("adxl_z", 0)),
                    float(cad_local.get("itg_x", 0)),  float(cad_local.get("itg_y", 0)),  float(cad_local.get("itg_z", 0))
                ]
                ventana.append(sample)
            except Exception:
                pass

    seq = parsed.get("seq")
    cad = parsed.get("cadera", {})
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    if seq is not None:
        print(f"[{ts}] seq={seq} cadera={cad}")
    else:
        print(f"[{ts}] cadera={cad}")

async def rate_printer():
    """Imprime la cantidad de mensajes recibidos por segundo."""
    global last_second_count
    while True:
        await asyncio.sleep(1.0)
        async with _lock:
            rate = last_second_count
            last_second_count = 0
            tot = total_count
        print(f"→ Tasa: {rate} mensajes/s  (total={tot})")


def cargar_modelo():
    """Carga el modelo Keras especificado en MODEL_PATH."""
    global modelo
    try:
        if not os.path.exists(MODEL_PATH):
            print(f"⚠️ Modelo no encontrado en '{MODEL_PATH}'. Prepara o coloca el archivo antes de predecir.")
            modelo = None
            return
        modelo = keras.models.load_model(MODEL_PATH)
        print(f"✅ Modelo cargado: {MODEL_PATH}")
    except Exception as e:
        modelo = None
        print(f"❌ Error cargando modelo: {e}")


async def predictor_loop():
    """Cada PREDICT_INTERVAL segundos aplica el modelo sobre las últimas WINDOW_SIZE muestras."""
    global ventana, modelo
    while True:
        await asyncio.sleep(PREDICT_INTERVAL)
        try:
            async with _lock:
                if modelo is None or len(ventana) < WINDOW_SIZE:
                    continue
                recent = list(ventana)[-WINDOW_SIZE:]
            X = np.array(recent).reshape(1, WINDOW_SIZE, 6)
            pred = modelo.predict(X, verbose=0)[0][0]
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            if pred >= UMBRAL_PROB:
                print(f"[{ts}] 🔴 PREDICCIÓN CAÍDA - prob={pred:.3f}")
            else:
                print(f"[{ts}] prob={pred:.3f}")
        except Exception as e:
            print(f"Error en predictor: {e}")

async def find_device_by_name(name, timeout=5.0):
    devices = await BleakScanner.discover(timeout=timeout)
    for d in devices:
        if d.name == name or (d.metadata and d.metadata.get('local_name') == name):
            return d.address
    return None

async def main():
    addr = CADERA_MAC or ""
    print("Iniciando lector BLE (muestra datos y tasa por segundo)...")
    # Cargar modelo antes de iniciar
    cargar_modelo()
    while True:
        try:
            if not addr:
                print(f"Buscando dispositivo por nombre '{DEVICE_NAME}'...")
                found = await find_device_by_name(DEVICE_NAME, timeout=5.0)
                if found:
                    addr = found
                    print(f"Encontrado: {addr}")
                else:
                    print("No encontrado. Reintentando en 3s...")
                    await asyncio.sleep(3)
                    continue

            print(f"Conectando a {addr} ...")
            async with BleakClient(addr, timeout=20.0) as client:
                if not client.is_connected:
                    print("No conectado")
                    raise RuntimeError("Conexion fallida")
                print("Conectado. Suscribiendo notificaciones...")
                await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
                rate_task = asyncio.create_task(rate_printer())
                predictor_task = asyncio.create_task(predictor_loop())
                try:
                    while client.is_connected:
                        await asyncio.sleep(1)
                finally:
                    rate_task.cancel()
                    predictor_task.cancel()
                    try:
                        await client.stop_notify(CHARACTERISTIC_UUID)
                    except Exception:
                        pass
        except Exception as e:
            print(f"Error/conexión: {e}")
        addr = CADERA_MAC  # si se encontró MAC usarla en próximos intentos
        await asyncio.sleep(2)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Detenido por usuario.")
# filepath: c:\xampp\htdocs\Proyecto-microprocesadores1\Codigos y datos\datos