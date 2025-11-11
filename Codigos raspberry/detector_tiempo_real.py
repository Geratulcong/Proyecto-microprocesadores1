"""
Cliente BLE para detección de caídas en tiempo real
Usa el modelo entrenado con tus datos del Arduino
"""
import asyncio
import json
import numpy as np
from pathlib import Path
from bleak import BleakClient, BleakScanner
from tensorflow.keras.models import load_model

# --- CONFIGURACIÓN BLE ---
DEVICE_NAME = "NanoSense33-Caidas"
DEVICE_ADDRESS = None  # Se buscará por nombre, o pon tu MAC
CHARACTERISTIC_UUID = "19b10001-e8f2-537e-4f6c-d104768a1214"

# --- CONFIGURACIÓN DEL MODELO ---
BASE_PATH = Path(__file__).parent
MODEL_PATH = BASE_PATH / "modelo_caidas_arduino.h5"
WINDOW_SIZE = 40  # Mismo que en el entrenamiento (2 segundos a 20Hz)

# --- CARGAR MODELO ---
print("╔════════════════════════════════════════════════╗")
print("║   Detector de Caídas en Tiempo Real - BLE    ║")
print("╚════════════════════════════════════════════════╝\n")

if not MODEL_PATH.exists():
    print(f"❌ Error: Modelo no encontrado en {MODEL_PATH}")
    print("   Ejecuta primero 'entrenar_con_datos_arduino.py'\n")
    exit(1)

print("📦 Cargando modelo...")
model = load_model(MODEL_PATH)
print(f"✅ Modelo cargado: {MODEL_PATH.name}")
print(f"⚙️  Ventana: {WINDOW_SIZE} muestras (2s a 20Hz)")
print(f"🎯 Clases: 0=Normal, 1=Caída\n")

# --- BUSCAR DISPOSITIVO BLE ---
async def find_device():
    """Busca el Arduino por nombre o usa MAC configurada"""
    if DEVICE_ADDRESS:
        print(f"🔍 Usando MAC configurada: {DEVICE_ADDRESS}")
        return DEVICE_ADDRESS
    
    print(f"🔍 Buscando dispositivo: {DEVICE_NAME}...")
    devices = await BleakScanner.discover(timeout=10.0)
    
    for device in devices:
        if device.name == DEVICE_NAME:
            print(f"✅ Encontrado: {device.name} ({device.address})\n")
            return device.address
    
    raise Exception(f"❌ Dispositivo '{DEVICE_NAME}' no encontrado")

# --- CLIENTE BLE ---
async def run_detector():
    device_address = await find_device()
    buffer = []
    prediccion_anterior = None
    
    async with BleakClient(device_address, timeout=30.0) as client:
        print(f"🔗 Conectado a {device_address}")
        print(f"📡 Recibiendo datos...\n")
        print("─" * 60)
        
        def handle_notify(sender, data):
            nonlocal buffer, prediccion_anterior
            
            try:
                # Decodificar JSON del Arduino
                json_str = data.decode("utf-8")
                lectura = json.loads(json_str)
                
                # Extraer las features (6 o 12 dependiendo del Arduino)
                if "cadera_ax" in lectura:
                    # Formato con 2 sensores (12 features)
                    sample = [
                        lectura["cadera_ax"], lectura["cadera_ay"], lectura["cadera_az"],
                        lectura["cadera_gx"], lectura["cadera_gy"], lectura["cadera_gz"],
                        lectura["pierna_ax"], lectura["pierna_ay"], lectura["pierna_az"],
                        lectura["pierna_gx"], lectura["pierna_gy"], lectura["pierna_gz"]
                    ]
                
                buffer.append(sample)
                
                # Mantener ventana deslizante
                if len(buffer) > WINDOW_SIZE:
                    buffer.pop(0)
                
                # Mostrar progreso del buffer
                if len(buffer) % 10 == 0 and len(buffer) < WINDOW_SIZE:
                    porcentaje = (len(buffer) / WINDOW_SIZE) * 100
                    barra = "█" * int(porcentaje / 5) + "░" * (20 - int(porcentaje / 5))
                    print(f"\r📊 Llenando buffer: [{barra}] {porcentaje:.0f}%", end="", flush=True)
                
                # Predecir cuando tengamos ventana completa
                if len(buffer) == WINDOW_SIZE:
                    if prediccion_anterior is None:
                        print("\n" + "─" * 60)
                        print("✅ Buffer completo. Iniciando detección...\n")
                    
                    # Preparar datos (detectar automáticamente el número de features)
                    num_features = len(buffer[0])
                    X = np.array(buffer, dtype=np.float32).reshape(1, WINDOW_SIZE, num_features)
                    
                    # Predicción
                    pred = model.predict(X, verbose=0)
                    prob_caida = float(pred[0][0])
                    es_caida = prob_caida > 0.5
                    
                    # Mostrar solo cuando cambia la predicción o es caída con alta confianza
                    if es_caida:
                        if prob_caida > 0.8:
                            print(f"🚨🚨 ¡ALERTA! CAÍDA DETECTADA (confianza: {prob_caida:.1%}) 🚨🚨")
                            # Aquí puedes implementar el envío de alerta (Firebase, API, etc.)
                        elif prediccion_anterior != es_caida:
                            print(f"⚠️  Posible caída (confianza: {prob_caida:.1%})")
                        prediccion_anterior = es_caida
                    else:
                        if prediccion_anterior != es_caida and prediccion_anterior is not None:
                            print(f"✅ Normal (confianza: {(1-prob_caida):.1%})")
                        prediccion_anterior = es_caida
                
            except json.JSONDecodeError as e:
                print(f"\n⚠️  JSON inválido: {data}")
            except KeyError as e:
                print(f"\n⚠️  Clave faltante: {e}")
            except Exception as e:
                print(f"\n❌ Error: {e}")
        
        # Suscribirse a notificaciones
        await client.start_notify(CHARACTERISTIC_UUID, handle_notify)
        
        # Mantener conexión activa
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await client.stop_notify(CHARACTERISTIC_UUID)
            raise

# --- LOOP PRINCIPAL CON RECONEXIÓN ---
async def main_loop():
    """Bucle con reconexión automática"""
    retry_delay = 5
    
    while True:
        try:
            await run_detector()
        except KeyboardInterrupt:
            print("\n\n🚪 Detenido por el usuario")
            break
        except Exception as e:
            print(f"\n\n❌ Error: {e}")
            print(f"🔄 Reintentando en {retry_delay} segundos...")
            await asyncio.sleep(retry_delay)

# --- EJECUTAR ---
if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n👋 Programa finalizado")
