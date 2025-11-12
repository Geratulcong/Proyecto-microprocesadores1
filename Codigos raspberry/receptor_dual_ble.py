"""
Cliente BLE para conectar DOS Arduinos Nano 33 BLE Sense
Recibe datos de cadera y pierna simultáneamente
"""
import asyncio
import json
import numpy as np
from pathlib import Path
from bleak import BleakClient, BleakScanner
from datetime import datetime
import csv

# --- CONFIGURACIÓN ---
DEVICE_CADERA = "Sensor-Cadera"
DEVICE_PIERNA = "Sensor-Pierna"

# UUIDs de características
CHAR_CADERA = "19b10001-0000-1000-8000-00805f9b34fb"
CHAR_PIERNA = "19b20001-0000-1000-8000-00805f9b34fb"

# Archivo de salida
OUTPUT_FILE = "datos_dos_sensores.csv"

# --- VARIABLES GLOBALES ---
datos_cadera = {"ax": 0, "ay": 0, "az": 0, "gx": 0, "gy": 0, "gz": 0}
datos_pierna = {"ax": 0, "ay": 0, "az": 0, "gx": 0, "gy": 0, "gz": 0}
contador = 0

print("╔════════════════════════════════════════════════╗")
print("║   Receptor Dual BLE - Cadera + Pierna        ║")
print("╚════════════════════════════════════════════════╝\n")

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

# --- GUARDAR DATOS ---
async def guardar_datos():
    """Guarda los datos combinados cada 50ms (20Hz)"""
    global contador
    
    # Crear archivo CSV si no existe
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'seq', 'cadera_ax', 'cadera_ay', 'cadera_az', 'cadera_gx', 'cadera_gy', 'cadera_gz',
            'pierna_ax', 'pierna_ay', 'pierna_az', 'pierna_gx', 'pierna_gy', 'pierna_gz'
        ])
    
    print(f"\n📝 Guardando datos en: {OUTPUT_FILE}")
    print("─" * 80)
    print(f"{'Seq':<6} {'Cadera (ax,ay,az)':<35} {'Pierna (ax,ay,az)':<35}")
    print("─" * 80)
    
    while True:
        contador += 1
        
        # Combinar datos de ambos sensores
        fila = [
            contador,
            datos_cadera["ax"], datos_cadera["ay"], datos_cadera["az"],
            datos_cadera["gx"], datos_cadera["gy"], datos_cadera["gz"],
            datos_pierna["ax"], datos_pierna["ay"], datos_pierna["az"],
            datos_pierna["gx"], datos_pierna["gy"], datos_pierna["gz"]
        ]
        
        # Guardar en CSV
        with open(OUTPUT_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(fila)
        
        # Mostrar cada 10 muestras
        if contador % 10 == 0:
            print(f"{contador:<6} "
                  f"({datos_cadera['ax']:6.3f},{datos_cadera['ay']:6.3f},{datos_cadera['az']:6.3f})  "
                  f"({datos_pierna['ax']:6.3f},{datos_pierna['ay']:6.3f},{datos_pierna['az']:6.3f})")
        
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
        
        # Iniciar guardado de datos
        tarea_guardado = asyncio.create_task(guardar_datos())
        
        try:
            # Mantener conexión activa
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            tarea_guardado.cancel()
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
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n👋 Programa finalizado")
        print(f"📊 Datos guardados en: {OUTPUT_FILE}")
