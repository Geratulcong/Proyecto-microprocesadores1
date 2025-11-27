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
MODEL_PATH = "modelo.h5"
# Configurar para 200 Hz (para que coincida con los ficheros SisFall)
SAMPLING_RATE = 200  # Hz
WINDOW_SECONDS = 2.0  # Duración de la ventana en segundos (mantener 2s como antes)
WINDOW_SIZE = int(SAMPLING_RATE * WINDOW_SECONDS)  # muestras por ventana (ej. 400 para 2s a 200Hz)
PREDICT_INTERVAL_SECONDS = 0.25  # cada cuánto tiempo hacemos una predicción aproximada
PREDICT_EVERY_SAMPLES = max(1, int(PREDICT_INTERVAL_SECONDS * SAMPLING_RATE))
SLEEP_INTERVAL = 1.0 / SAMPLING_RATE

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
            print(f"No se pudo actualizar el documento: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        print(f"Error actualizando documento: {e}")

# --- VARIABLES GLOBALES ---
datos_cadera = {"ax": 0, "ay": 0, "az": 0, "gx": 0, "gy": 0, "gz": 0}
datos_pierna = {"ax": 0, "ay": 0, "az": 0, "gx": 0, "gy": 0, "gz": 0}
contador = 0
ultima_alerta = 0  # Timestamp de la última alerta enviada

# Buffer circular para ventana deslizante
ventana = deque(maxlen=WINDOW_SIZE)
modelo = None
SINGLE_MODE = False
SINGLE_SIDE = None  # 'cadera' or 'pierna' when SINGLE_MODE True
MODEL_TIMESTEPS = None
EXPECTED_FEATURES = None
PREFERRED_SENSOR = os.environ.get("PREFERRED_SENSOR", "cadera")  # 'cadera' or 'pierna'

print("╔════════════════════════════════════════════════╗")
print("║   Detector de Caídas - Dual BLE + CNN        ║")
print("║   + Alertas Firestore                         ║")
print("╚════════════════════════════════════════════════╝")
print(f"Firestore: Historial/Personas/Vicente")
print(f"Cooldown alertas: {COOLDOWN_ALERTAS}s")
print(f"Umbral detección: {UMBRAL_CAIDA*100:.0f}%")
print(f"Muestreo receptor: {SAMPLING_RATE} Hz | Window: {WINDOW_SIZE} muestras ({WINDOW_SECONDS}s) | Predict cada ~{PREDICT_INTERVAL_SECONDS}s ({PREDICT_EVERY_SAMPLES} muestras)\n")

# --- CARGAR MODELO ---
def cargar_modelo():
    """Carga el modelo CNN entrenado"""
    global modelo
    global MODEL_TIMESTEPS, EXPECTED_FEATURES
    try:
        modelo = keras.models.load_model(MODEL_PATH)
        # Keras model input_shape suele ser (None, timesteps, features)
        input_shape = modelo.input_shape
        try:
            model_timesteps = int(input_shape[1])
            num_features = int(input_shape[2])
        except Exception:
            # Forma inesperada -> sólo obtener features si es posible
            num_features = modelo.input_shape[-1]
            model_timesteps = None

        print(f"✅ Modelo cargado: {MODEL_PATH}")
        print(f"   📊 Modelo espera entrada: (batch, {model_timesteps}, {num_features})")
        # Guardar valores globales para uso en tiempo de ejecución
        MODEL_TIMESTEPS = model_timesteps
        EXPECTED_FEATURES = num_features

        if model_timesteps is not None and model_timesteps != WINDOW_SIZE:
            print("⚠️ ADVERTENCIA: El tamaño temporal del modelo no coincide con WINDOW_SIZE del receptor.")
            print(f"   Modelo timesteps: {model_timesteps} vs Receptor WINDOW_SIZE: {WINDOW_SIZE}")
            print("   El receptor usará las últimas 'model_timesteps' muestras para la predicción si es menor que WINDOW_SIZE.")

        if num_features not in (6, 12):
            print(f"⚠️ ADVERTENCIA: El modelo espera {num_features} features; el receptor soporta 6 o 12. Ajusta el modelo o el receptor.")

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
    
    # Si no se encuentran ninguno, error
    if not cadera_addr and not pierna_addr:
        raise Exception(f"❌ No se encontraron dispositivos (ni cadera ni pierna)")

    # Si sólo uno está presente, habilitar SINGLE_MODE para poder usar un solo Arduino
    global SINGLE_MODE, SINGLE_SIDE
    if cadera_addr and not pierna_addr:
        SINGLE_MODE = True
        SINGLE_SIDE = 'cadera'
        print("⚠️ Modo single: encontrado solo CADERA. Se usará la misma señal para la pierna (duplicada).")
    elif pierna_addr and not cadera_addr:
        SINGLE_MODE = True
        SINGLE_SIDE = 'pierna'
        print("⚠️ Modo single: encontrado solo PIERNA. Se usará la misma señal para la cadera (duplicada).")

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
    
    # Usar MODEL_TIMESTEPS si está definido; si no, usar WINDOW_SIZE
    timesteps_needed = MODEL_TIMESTEPS or WINDOW_SIZE
    if len(ventana) < timesteps_needed:
        return None  # No hay suficientes datos aún

    # Tomar las últimas 'timesteps_needed' muestras
    recent = list(ventana)[-timesteps_needed:]

    # Construir X según EXPECTED_FEATURES (6 o 12)
    if EXPECTED_FEATURES == 6:
        # Seleccionar las 6 features del sensor preferido
        if PREFERRED_SENSOR == 'pierna' and (SINGLE_MODE and SINGLE_SIDE == 'pierna' or not SINGLE_MODE):
            # Usar pierna
            X_raw = [[
                row[6], row[7], row[8],  # ax, ay, az of pierna
                row[9], row[10], row[11]  # gx, gy, gz of pierna
            ] for row in recent]
        else:
            # Por defecto usar cadera
            X_raw = [[
                row[0], row[1], row[2],  # ax, ay, az of cadera
                row[3], row[4], row[5]   # gx, gy, gz of cadera
            ] for row in recent]
        X = np.array(X_raw).reshape(1, timesteps_needed, 6)
    else:
        # Esperando 12 features
        X = np.array(recent).reshape(1, timesteps_needed, -1)

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
        # Si estamos en SINGLE_MODE se duplica la señal disponible para llenar las 12 features
        if SINGLE_MODE:
            if SINGLE_SIDE == 'cadera':
                datos_pierna_local = datos_cadera.copy()
                datos_cadera_local = datos_cadera
            else:
                datos_cadera_local = datos_pierna.copy()
                datos_pierna_local = datos_pierna
        else:
            datos_cadera_local = datos_cadera
            datos_pierna_local = datos_pierna

        muestra = [
            datos_cadera_local["ax"], datos_cadera_local["ay"], datos_cadera_local["az"],
            datos_cadera_local["gx"], datos_cadera_local["gy"], datos_cadera_local["gz"],
            datos_pierna_local["ax"], datos_pierna_local["ay"], datos_pierna_local["az"],
            datos_pierna_local["gx"], datos_pierna_local["gy"], datos_pierna_local["gz"]
        ]
        
        # Agregar a ventana deslizante
        ventana.append(muestra)

        # Predecir cada PREDICT_EVERY_SAMPLES muestras (aprox cada PREDICT_INTERVAL_SECONDS)
        estado = "⚪ Normal"
        if contador % PREDICT_EVERY_SAMPLES == 0:
            prob_caida = predecir_caida()
            
            if prob_caida is not None:
                if prob_caida > UMBRAL_CAIDA:
                    estado = f"🔴 CAÍDA ({prob_caida*100:.1f}%)"
                    # Enviar a Firestore con cooldown de 5 segundos
                    enviar_a_firestore(prob_caida, datos_cadera, datos_pierna)
                else:
                    estado = f"✅ OK ({prob_caida*100:.1f}%)"
            
            print(f"{contador:<6} "
            f"({datos_cadera_local['ax']:6.3f},{datos_cadera_local['ay']:6.3f},{datos_cadera_local['az']:6.3f} | "
            f"{datos_cadera_local['gx']:6.3f},{datos_cadera_local['gy']:6.3f},{datos_cadera_local['gz']:6.3f})  "
            f"({datos_pierna_local['ax']:6.3f},{datos_pierna_local['ay']:6.3f},{datos_pierna_local['az']:6.3f} | "
            f"{datos_pierna_local['gx']:6.3f},{datos_pierna_local['gy']:6.3f},{datos_pierna_local['gz']:6.3f})  {estado}")
        
    # Esperar el intervalo definido por la tasa de muestreo
    await asyncio.sleep(SLEEP_INTERVAL)

# --- CONEXIÓN DUAL ---
async def conectar_dispositivos():
    """Conecta a ambos dispositivos simultáneamente"""
    cadera_addr, pierna_addr = await find_devices()
    
    print(f"\n🔗 Conectando a ambos dispositivos...")
    # Si ambos dispositivos están presentes, usar el modo dual original
    if not SINGLE_MODE:
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
    else:
        # SINGLE_MODE: conectar sólo al dispositivo disponible
        if SINGLE_SIDE == 'cadera':
            async with BleakClient(cadera_addr, timeout=30.0) as client_cadera:
                print(f"✅ Conectado a CADERA: {cadera_addr} (modo single)")
                await client_cadera.start_notify(CHAR_CADERA, handler_cadera)
                print("\n📡 Recibiendo datos del sensor disponible (CADERA). Se duplicará para PIERNA.")
                tarea_deteccion = asyncio.create_task(detectar_caidas())
                try:
                    while True:
                        await asyncio.sleep(1)
                except asyncio.CancelledError:
                    tarea_deteccion.cancel()
                    await client_cadera.stop_notify(CHAR_CADERA)
                    raise
        else:
            async with BleakClient(pierna_addr, timeout=30.0) as client_pierna:
                print(f"✅ Conectado a PIERNA: {pierna_addr} (modo single)")
                await client_pierna.start_notify(CHAR_PIERNA, handler_pierna)
                print("\n📡 Recibiendo datos del sensor disponible (PIERNA). Se duplicará para CADERA.")
                tarea_deteccion = asyncio.create_task(detectar_caidas())
                try:
                    while True:
                        await asyncio.sleep(1)
                except asyncio.CancelledError:
                    tarea_deteccion.cancel()
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
