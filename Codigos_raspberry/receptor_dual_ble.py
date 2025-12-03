"""
Cliente BLE para conectar DOS Arduinos Nano 33 BLE Sense
Recibe datos de cadera y pierna simultáneamente
Usa modelo CNN para detectar caídas en tiempo real
Envía alertas a Firebase cuando detecta caída
"""
import asyncio
import json
import numpy as np
import requests
from pathlib import Path
from bleak import BleakClient, BleakScanner
from datetime import datetime, timezone, timedelta
from tensorflow import keras
from collections import deque
import time
import os

# --- CONFIGURACIÓN ---
DEVICE_CADERA = "Sensor-Cadera"
DEVICE_PIERNA = "Sensor-Pierna"

# UUIDs de características
CHAR_CADERA = "19b10001-0000-1000-8000-00805f9b34fb"
CHAR_PIERNA = "19b20001-0000-1000-8000-00805f9b34fb"

# Modelo y ventana de detección
MODEL_PATH = "modelo_cnn_imu.h5"
WINDOW_SIZE = 80  # 2 segundos a 40Hz
UMBRAL_CAIDA = 0.95  # 95% de confianza requerida

# Firebase Firestore (REST API)
FIREBASE_PROJECT_ID = "detector-de-caidas-360"
PERSONA = "Vicente"
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/Historial/Personas/{PERSONA}"
CONFIG_DOC_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/Historial/Personas/{PERSONA}/_config"
COOLDOWN_ALERTAS = 10.0  # Segundos entre alertas (evitar sobreposición)

# Configuración WhatsApp (vía servidor local)
SERVER_ALERT_URL = os.environ.get("ALERT_SERVER_URL", "http://localhost:5000/send-alert")
CALLMEBOT_PHONE = os.environ.get("CALLMEBOT_PHONE")
CALLMEBOT_APIKEY = os.environ.get("CALLMEBOT_APIKEY")
_CONFIG_CACHE = {"phone": None, "apiCode": None, "ts": 0}

def _timestamp_firestore_now():
    """Devuelve un dict timestampValue en UTC compatible con Firestore REST."""
    chile_tz = timezone(timedelta(hours=-3))
    ahora_chile = datetime.now(chile_tz)
    ahora_utc = ahora_chile.astimezone(timezone.utc)
    epoch_seconds = int(ahora_utc.timestamp())
    epoch_nanos = int((ahora_utc.timestamp() - epoch_seconds) * 1e9)
    return {"timestampValue": f"{ahora_utc.strftime('%Y-%m-%dT%H:%M:%S')}.{epoch_nanos:09d}Z"}

def enviar_whatsapp_via_servidor(message: str) -> bool:
    """Envía WhatsApp usando el servidor local. Requiere CALLMEBOT_PHONE y CALLMEBOT_APIKEY.
    Retorna True si se envió correctamente.
    """
    # Usa variables de entorno si existen; si no, fallback a los valores locales
    phone = CALLMEBOT_PHONE
    apikey = CALLMEBOT_APIKEY

    # Si no hay env vars, intentar obtener desde Firestore (_config)
    if not phone or not apikey:
        phone_fs, apikey_fs = fetch_config_from_firestore()
        phone = phone or phone_fs
        apikey = apikey or apikey_fs
    # Fallback final (desarrollo)
    phone = phone or "+56948094351"
    apikey = apikey or "9733456"

    if not phone or not apikey:
        print("⚠️  WhatsApp no configurado (CALLMEBOT_PHONE / CALLMEBOT_APIKEY). Se omite envío.")
        return False
def fetch_config_from_firestore():
    """Obtiene (phone, apiCode) desde Firestore _config con caché de 60s."""
    try:
        now = time.time()
        if now - _CONFIG_CACHE.get("ts", 0) < 60 and _CONFIG_CACHE.get("phone") and _CONFIG_CACHE.get("apiCode"):
            return _CONFIG_CACHE["phone"], _CONFIG_CACHE["apiCode"]

        r = requests.get(CONFIG_DOC_URL, timeout=4)
        if r.status_code == 200:
            data = r.json()
            fields = data.get("fields", {})
            phone = (fields.get("phone", {}).get("stringValue") or
                     fields.get("phone", {}).get("integerValue") or
                     fields.get("phone", {}).get("doubleValue"))
            apiCode = (fields.get("apiCode", {}).get("stringValue") or
                       fields.get("apiCode", {}).get("integerValue") or
                       fields.get("apiCode", {}).get("doubleValue"))
            if phone:
                phone = str(phone)
            if apiCode:
                apiCode = str(apiCode)
            _CONFIG_CACHE.update({"phone": phone, "apiCode": apiCode, "ts": now})
            print("⚙️  Config de WhatsApp cargada desde Firestore")
            return phone, apiCode
        else:
            print(f"ℹ️ No se pudo obtener config Firestore ({r.status_code})")
            return None, None
    except Exception as e:
        print(f"ℹ️ Error obteniendo config Firestore: {e}")
        return None, None

    try:
        payload = {"phone": phone, "apiCode": apikey, "message": message}
        print(f"📱 Enviando WhatsApp vía servidor: {SERVER_ALERT_URL} …")
        r = requests.post(SERVER_ALERT_URL, json=payload, timeout=6)
        data = {}
        try:
            data = r.json()
        except Exception:
            pass
        if r.status_code == 200 and data.get("status") == "ok":
            print("✅ WhatsApp enviado correctamente")
            return True
        else:
            print(f"❌ Error al enviar WhatsApp: {data.get('message') or r.text[:200]}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de red al enviar WhatsApp: {e}")
        return False

def actualizar_estado_documento(doc_id: str, enviado: bool, error_msg: str | None = None):
    """Actualiza el documento en Firestore con el estado del envío de WhatsApp."""
    try:
        doc_name = f"projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/Historial/Personas/Vicente/{doc_id}"
        url = f"https://firestore.googleapis.com/v1/{doc_name}?updateMask.fieldPaths=estado&updateMask.fieldPaths=mensaje_enviado&updateMask.fieldPaths=hora_envio&updateMask.fieldPaths=error_envio"
        body = {
            "fields": {
                "estado": {"stringValue": "Enviada" if enviado else "Error al enviar"},
                "mensaje_enviado": {"booleanValue": bool(enviado)},
                "hora_envio": _timestamp_firestore_now(),
            }
        }
        if not enviado and error_msg:
            body["fields"]["error_envio"] = {"stringValue": error_msg[:300]}

        r = requests.patch(url, json=body, timeout=5)
        if r.status_code == 200:
            print("📝 Documento actualizado con estado de envío")
        else:
            print(f"⚠️  No se pudo actualizar el documento: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        print(f"⚠️  Error actualizando documento: {e}")

# --- VARIABLES GLOBALES ---
datos_cadera = {"ax": 0, "ay": 0, "az": 0, "gx": 0, "gy": 0, "gz": 0}
datos_pierna = {"ax": 0, "ay": 0, "az": 0, "gx": 0, "gy": 0, "gz": 0}
contador = 0
ultima_alerta = 0  # Timestamp de la última alerta enviada

# Buffer circular para ventana deslizante
ventana = deque(maxlen=WINDOW_SIZE)
modelo = None

print("╔════════════════════════════════════════════════╗")
print("║   Detector de Caídas - Dual BLE + CNN        ║")
print("║   + Alertas Firestore                         ║")
print("╚════════════════════════════════════════════════╝")
print(f"📍 Firestore: Historial/Personas/Vicente")
print(f"⏱️  Cooldown alertas: {COOLDOWN_ALERTAS}s")
print(f"🎯 Umbral detección: {UMBRAL_CAIDA*100:.0f}%\n")

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

# --- ENVIAR ALERTA A FIRESTORE ---
def enviar_a_firestore(probabilidad, datos_cadera, datos_pierna):
    """Envía alerta de caída a Firestore (Historial/Personas/Vicente)"""
    global ultima_alerta
    
    # Verificar cooldown de 5 segundos
    tiempo_actual = time.time()
    if tiempo_actual - ultima_alerta < COOLDOWN_ALERTAS:
        tiempo_restante = COOLDOWN_ALERTAS - (tiempo_actual - ultima_alerta)
        print(f"   ⏳ Cooldown activo - {tiempo_restante:.1f}s restantes")
        return False
    
    try:
        # Timestamp en formato Firestore - Hora de Chile (UTC-3) convertida a UTC
        timestamp_firestore = _timestamp_firestore_now()
        
        # Preparar documento en formato Firestore REST API
        documento = {
            "fields": {
                "hora_caida": timestamp_firestore,
                "tipo": {"stringValue": "Caída detectada - Sistema dual"},
                "confianza": {"doubleValue": float(probabilidad)},
                "ubicacion": {"stringValue": "Detectado por sensores"},
                "estado": {"stringValue": "Pendiente"},
                "sensor": {"stringValue": "Dual (Cadera + Pierna)"},
                "probabilidad": {"doubleValue": float(probabilidad)},
                # Datos sensor cadera
                "cadera_ax": {"doubleValue": float(datos_cadera["ax"])},
                "cadera_ay": {"doubleValue": float(datos_cadera["ay"])},
                "cadera_az": {"doubleValue": float(datos_cadera["az"])},
                "cadera_gx": {"doubleValue": float(datos_cadera["gx"])},
                "cadera_gy": {"doubleValue": float(datos_cadera["gy"])},
                "cadera_gz": {"doubleValue": float(datos_cadera["gz"])},
                # Datos sensor pierna
                "pierna_ax": {"doubleValue": float(datos_pierna["ax"])},
                "pierna_ay": {"doubleValue": float(datos_pierna["ay"])},
                "pierna_az": {"doubleValue": float(datos_pierna["az"])},
                "pierna_gx": {"doubleValue": float(datos_pierna["gx"])},
                "pierna_gy": {"doubleValue": float(datos_pierna["gy"])},
                "pierna_gz": {"doubleValue": float(datos_pierna["gz"])},
            }
        }
        
        # Enviar a Firestore REST API
        response = requests.post(FIRESTORE_URL, json=documento, timeout=5)
        
        if response.status_code == 200:
            ultima_alerta = tiempo_actual
            doc_data = response.json()
            doc_id = doc_data.get('name', '').split('/')[-1]
            print(f"   ✅ Alerta enviada a Firestore")
            print(f"   🔗 ID: {doc_id}")
            print(f"   📍 Ruta: Historial/Personas/Vicente/{doc_id}")

            # Componer mensaje WhatsApp
            porcentaje = f"{float(probabilidad)*100:.1f}%"
            fecha_local = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            mensaje = (
                "🚨 ALERTA DE CAÍDA DETECTADA\n\n"
                f"👤 Persona: Vicente\n"
                f"📅 Fecha: {fecha_local}\n"
                f"🎯 Confianza: {porcentaje}\n"
                f"🆔 ID: {doc_id}\n\n"
                "Verifica el estado de la persona inmediatamente."
            )

            enviado = enviar_whatsapp_via_servidor(mensaje)
            if enviado:
                actualizar_estado_documento(doc_id, True)
            else:
                actualizar_estado_documento(doc_id, False, "No se pudo enviar WhatsApp desde receptor_dual_ble.py")

            return True
        else:
            print(f"   ❌ Error Firestore: {response.status_code}")
            print(f"   Respuesta: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"   ⏱️ Timeout al conectar con Firestore")
        return False
    except Exception as e:
        print(f"   ❌ Error enviando a Firebase: {e}")
        return False

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
                    # Enviar a Firestore con cooldown de 5 segundos
                    enviar_a_firestore(prob_caida, datos_cadera, datos_pierna)
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
