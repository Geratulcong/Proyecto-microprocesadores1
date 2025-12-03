"""
Script de prueba para verificar envío a Firestore
Envía una alerta de prueba a Historial/Personas/Vicente
"""
import requests
from datetime import datetime, timezone, timedelta

FIREBASE_PROJECT_ID = "detector-de-caidas-360"
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/Historial/Personas/Vicente"

print("╔════════════════════════════════════════════════╗")
print("║     Test de Conexión Firestore                ║")
print("╚════════════════════════════════════════════════╝\n")

# Timestamp en formato Firestore - Hora de Chile (UTC-3)
import time as time_module
# Obtener hora actual en Chile (UTC-3)
chile_tz = timezone(timedelta(hours=-3))
ahora_chile = datetime.now(chile_tz)

# Convertir a UTC para Firestore (que siempre guarda en UTC)
ahora_utc = ahora_chile.astimezone(timezone.utc)
epoch_seconds = int(ahora_utc.timestamp())
epoch_nanos = int((ahora_utc.timestamp() - epoch_seconds) * 1e9)

timestamp_firestore = {
    "timestampValue": f"{ahora_utc.strftime('%Y-%m-%dT%H:%M:%S')}.{epoch_nanos:09d}Z"
}

print(f"Hora Chile: {ahora_chile.strftime('%H:%M:%S')} (UTC-3)")
print(f"Hora UTC: {ahora_utc.strftime('%H:%M:%S')} (para Firestore)")

# Preparar documento de prueba
documento = {
    "fields": {
        "hora_caida": timestamp_firestore,
        "tipo": {"stringValue": "Prueba desde Python"},
        "confianza": {"doubleValue": 0.97},
        "ubicacion": {"stringValue": "Test script"},
        "estado": {"stringValue": "Prueba"},
        "sensor": {"stringValue": "Dual (Cadera + Pierna)"},
        "probabilidad": {"doubleValue": 0.97},
        # Datos sensor cadera
        "cadera_ax": {"doubleValue": 0.123},
        "cadera_ay": {"doubleValue": -2.456},
        "cadera_az": {"doubleValue": 0.987},
        "cadera_gx": {"doubleValue": 1.23},
        "cadera_gy": {"doubleValue": -4.56},
        "cadera_gz": {"doubleValue": 7.89},
        # Datos sensor pierna
        "pierna_ax": {"doubleValue": 0.234},
        "pierna_ay": {"doubleValue": -1.567},
        "pierna_az": {"doubleValue": 1.012},
        "pierna_gx": {"doubleValue": 2.34},
        "pierna_gy": {"doubleValue": -5.67},
        "pierna_gz": {"doubleValue": 8.90},
    }
}

print("📤 Enviando alerta de prueba a Firestore...")
print(f"   URL: {FIRESTORE_URL}")
print(f"   Ruta: Historial/Personas/Vicente")
print(f"   Confianza: 97%\n")

try:
    response = requests.post(FIRESTORE_URL, json=documento, timeout=10)
    
    print(f"📊 Código de respuesta: {response.status_code}")
    
    if response.status_code == 200:
        resultado = response.json()
        doc_path = resultado.get('name', '')
        doc_id = doc_path.split('/')[-1]
        
        print("✅ ¡Alerta enviada exitosamente!")
        print(f"   🔑 ID del documento: {doc_id}")
        print(f"   📍 Ruta completa: {doc_path}")
        print(f"\n🔗 Ver en Firebase Console:")
        print(f"   https://console.firebase.google.com/project/detector-de-caidas-360/firestore/databases/-default-/data/~2FHistorial~2FPersonas~2FVicente~2F{doc_id}")
        
    else:
        print("❌ Error al enviar alerta")
        print(f"   Respuesta: {response.text[:500]}")
        
except requests.exceptions.Timeout:
    print("⏱️  Error: Timeout - Firestore no respondió")
    
except requests.exceptions.ConnectionError:
    print("❌ Error de conexión a Internet")
    print("   Verifica tu conexión y prueba de nuevo")
    
except Exception as e:
    print(f"❌ Error inesperado: {e}")

print("\n" + "─" * 60)
print("💡 Notas:")
print("   - Si funciona, verás la alerta en Firebase Console")
print("   - Ruta: Firestore Database → Historial → Personas → Vicente")
print("   - Puedes eliminar esta alerta de prueba desde la consola")
print("   - El sistema real enviará alertas con este mismo formato")
