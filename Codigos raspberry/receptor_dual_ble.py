"""
Cliente BLE para conectar DOS Arduinos Nano 33 BLE Sense
Recibe datos de cadera y pierna simultáneamente
Usa modelo CNN para detectar caídas en tiempo real
"""
import asyncio
import json
import numpy as np
from pathlib import Path
from bleak import BleakClient, BleakScanner
from datetime import datetime
from tensorflow import keras
from collections import deque

# --- CONFIGURACIÓN ---
DEVICE_CADERA = "Sensor-Cadera"
DEVICE_PIERNA = "Sensor-Pierna"

# UUIDs de características
CHAR_CADERA = "19b10001-0000-1000-8000-00805f9b34fb"
CHAR_PIERNA = "19b20001-0000-1000-8000-00805f9b34fb"

# Modelo y ventana de detección
MODEL_PATH = "modelo_caidas_arduino.h5"
WINDOW_SIZE = 40  # 2 segundos a 20Hz
UMBRAL_CAIDA = 0.5

# --- VARIABLES GLOBALES ---
datos_cadera = {"ax": 0, "ay": 0, "az": 0, "gx": 0, "gy": 0, "gz": 0}
datos_pierna = {"ax": 0, "ay": 0, "az": 0, "gx": 0, "gy": 0, "gz": 0}
contador = 0

# Buffer circular para ventana deslizante
ventana = deque(maxlen=WINDOW_SIZE)
modelo = None

print("╔════════════════════════════════════════════════╗")
print("║   Detector de Caídas - Dual BLE + CNN        ║")
print("╚════════════════════════════════════════════════╝\n")

# --- CARGAR MODELO ---
def cargar_modelo():
    """Carga el modelo CNN entrenado"""
    global modelo
    try:
        modelo = keras.models.load_model(MODEL_PATH)
        num_features = modelo.input_shape[2]
        print(f"✅ Modelo cargado: {MODEL_PATH}")
        print(f"   📊 Entrada: (batch, {WINDOW_SIZE}, {num_features})")
        return num_features
    except Exception as e:
        print(f"❌ Error cargando modelo: {e}")
        exit(1)

# --- BUSCAR DISPOSITIVOS ---
async def find_devices():
    """Busca ambos Arduinos y retorna sus direcciones"""
    print("🔍 Buscando dispositivos BLE...")
    devices = await BleakScanner.discover(timeout=10.0)
    
    cadera_addr = None
    pierna_addr = None
    
    for device in devices:
        if device.name == DEVICE_CADERA:
            cadera_addr = device.address
            print(f"✅ Encontrado CADERA: {device.name} ({device.address})")
        elif device.name == DEVICE_PIERNA:
            pierna_addr = device.address
            print(f"✅ Encontrado PIERNA: {device.name} ({device.address})")
    
    if not cadera_addr or not pierna_addr:
        raise Exception(f"❌ No se encontraron ambos dispositivos")
    
    return cadera_addr, pierna_addr

# --- HANDLERS DE NOTIFICACIONES ---
def handler_cadera(sender, data):
    """Maneja datos del sensor de cadera"""
    global datos_cadera
    try:
        json_str = data.decode("utf-8")
        lectura = json.loads(json_str)
        datos_cadera = {
            "ax": lectura["ax"], "ay": lectura["ay"], "az": lectura["az"],
            "gx": lectura["gx"], "gy": lectura["gy"], "gz": lectura["gz"]
        }
    except Exception as e:
        print(f"⚠️ Error en cadera: {e}")

def handler_pierna(sender, data):
    """Maneja datos del sensor de pierna"""
    global datos_pierna
    try:
        json_str = data.decode("utf-8")
        lectura = json.loads(json_str)
        datos_pierna = {
            "ax": lectura["ax"], "ay": lectura["ay"], "az": lectura["az"],
            "gx": lectura["gx"], "gy": lectura["gy"], "gz": lectura["gz"]
        }
    except Exception as e:
        print(f"⚠️ Error en pierna: {e}")

# --- PREDECIR CAÍDA ---
def predecir_caida():
    """Usa el modelo CNN para predecir si hay caída"""
    global ventana, modelo
    
    if len(ventana) < WINDOW_SIZE:
        return None  # No hay suficientes datos aún
    
    # Convertir ventana a numpy array
    X = np.array(list(ventana))  # Shape: (40, 12)
    X = X.reshape(1, WINDOW_SIZE, -1)  # Shape: (1, 40, 12)
    
    # Predecir
    pred = modelo.predict(X, verbose=0)[0][0]
    return pred

# --- DETECTAR CAÍDAS EN TIEMPO REAL ---
async def detectar_caidas():
    """Detecta caídas en tiempo real sin guardar CSV"""
    global contador, ventana
    
    print("\n📡 Iniciando detección en tiempo real...")
    print("─" * 120)
    print(f"{'Seq':<6} {'Cadera (ax,ay,az | gx,gy,gz)':<55} {'Pierna (ax,ay,az | gx,gy,gz)':<40} {'Estado':<15}")
    print("─" * 120)
    
    while True:
        contador += 1
        
        # Combinar datos de ambos sensores (12 features)
        # Escalar giroscopio x4 (mismo factor usado en entrenamiento)
        muestra = [
            datos_cadera["ax"], datos_cadera["ay"], datos_cadera["az"],
            datos_cadera["gx"] * 4.0, datos_cadera["gy"] * 4.0, datos_cadera["gz"] * 4.0,
            datos_pierna["ax"], datos_pierna["ay"], datos_pierna["az"],
            datos_pierna["gx"] * 4.0, datos_pierna["gy"] * 4.0, datos_pierna["gz"] * 4.0
        ]
        
        # Agregar a ventana deslizante
        ventana.append(muestra)
        
        # Predecir cada 5 muestras
        estado = "⚪ Normal"
        if contador % 5 == 0:
            prob_caida = predecir_caida()
            
            if prob_caida is not None:
                if prob_caida > UMBRAL_CAIDA:
                    estado = f"🔴 CAÍDA ({prob_caida*100:.1f}%)"
                else:
                    estado = f"✅ OK ({prob_caida*100:.1f}%)"
            
            print(f"{contador:<6} "
                  f"({datos_cadera['ax']:6.3f},{datos_cadera['ay']:6.3f},{datos_cadera['az']:6.3f} | "
                  f"{datos_cadera['gx']:6.3f},{datos_cadera['gy']:6.3f},{datos_cadera['gz']:6.3f})  "
                  f"({datos_pierna['ax']:6.3f},{datos_pierna['ay']:6.3f},{datos_pierna['az']:6.3f} | "
                  f"{datos_pierna['gx']:6.3f},{datos_pierna['gy']:6.3f},{datos_pierna['gz']:6.3f})  {estado}")
        
        await asyncio.sleep(0.05)  # 50ms = 20Hz

# --- CONEXIÓN DUAL ---
async def conectar_dispositivos():
    """Conecta a ambos dispositivos simultáneamente"""
    cadera_addr, pierna_addr = await find_devices()
    
    print(f"\n🔗 Conectando a ambos dispositivos...")
    
    async with BleakClient(cadera_addr, timeout=30.0) as client_cadera, \
               BleakClient(pierna_addr, timeout=30.0) as client_pierna:
        
        print(f"✅ Conectado a CADERA: {cadera_addr}")
        print(f"✅ Conectado a PIERNA: {pierna_addr}")
        
        # Suscribirse a notificaciones de ambos
        await client_cadera.start_notify(CHAR_CADERA, handler_cadera)
        await client_pierna.start_notify(CHAR_PIERNA, handler_pierna)
        
        print("\n📡 Recibiendo datos de ambos sensores...")
        
        # Iniciar detección de caídas
        tarea_deteccion = asyncio.create_task(detectar_caidas())
        
        try:
            # Mantener conexión activa
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            tarea_deteccion.cancel()
            await client_cadera.stop_notify(CHAR_CADERA)
            await client_pierna.stop_notify(CHAR_PIERNA)
            raise

# --- LOOP PRINCIPAL ---
async def main_loop():
    """Bucle con reconexión automática"""
    retry_delay = 5
    
    while True:
        try:
            await conectar_dispositivos()
        except KeyboardInterrupt:
            print("\n\n🚪 Detenido por el usuario")
            break
        except Exception as e:
            print(f"\n\n❌ Error: {e}")
            print(f"🔄 Reintentando en {retry_delay} segundos...")
            await asyncio.sleep(retry_delay)

# --- EJECUTAR ---
if __name__ == "__main__":
    # Cargar modelo primero
    num_features = cargar_modelo()
    
    if num_features != 12:
        print(f"⚠️ ADVERTENCIA: El modelo espera {num_features} features, pero enviamos 12")
        print(f"   Entrena el modelo con datos de 12 columnas (cadera + pierna)")
    
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n👋 Programa finalizado")
