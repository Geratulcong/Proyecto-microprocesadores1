"""
Script de prueba para verificar el sistema completo
Envía alerta a Firestore y muestra instrucciones
"""
import requests
from datetime import datetime, timezone, timedelta
import time

FIREBASE_PROJECT_ID = "detector-de-caidas-360"
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/Historial/Personas/Vicente"

print("╔═══════════════════════════════════════════════════════════╗")
print("║   Test Completo: Firestore + WhatsApp Automático         ║")
print("╚═══════════════════════════════════════════════════════════╝\n")

print("📋 INSTRUCCIONES:")
print("1. Abre datos.html en el navegador")
print("2. Configura WhatsApp:")
print("   - Teléfono: 56940551619")
print("   - API Key: 4253930")
print("   - Haz clic en 'Guardar'")
print("3. Abre la consola del navegador (F12)")
print("4. Verifica que diga: '✅ Listener activo'")
print("5. Presiona ENTER aquí para enviar la alerta\n")

input("Presiona ENTER cuando estés listo...")

print("\n" + "="*60)

# Timestamp en formato Firestore - Hora de Chile (UTC-3)
import time as time_module
chile_tz = timezone(timedelta(hours=-3))
ahora_chile = datetime.now(chile_tz)
ahora_utc = ahora_chile.astimezone(timezone.utc)
epoch_seconds = int(ahora_utc.timestamp())
epoch_nanos = int((ahora_utc.timestamp() - epoch_seconds) * 1e9)

timestamp_firestore = {
    "timestampValue": f"{ahora_utc.strftime('%Y-%m-%dT%H:%M:%S')}.{epoch_nanos:09d}Z"
}

print(f"\n⏰ Hora Chile: {ahora_chile.strftime('%H:%M:%S')} (UTC-3)")
print(f"⏰ Hora UTC: {ahora_utc.strftime('%H:%M:%S')} (para Firestore)\n")

# Preparar documento de prueba
documento = {
    "fields": {
        "hora_caida": timestamp_firestore,
        "tipo": {"stringValue": "🧪 TEST AUTOMÁTICO - Prueba WhatsApp"},
        "confianza": {"doubleValue": 0.98},  # 98% para que active el envío
        "ubicacion": {"stringValue": "Test desde Python"},
        "estado": {"stringValue": "Prueba"},
        "sensor": {"stringValue": "Dual (Cadera + Pierna)"},
        "probabilidad": {"doubleValue": 0.98},
        # Datos sensor cadera
        "cadera_ax": {"doubleValue": 2.5},
        "cadera_ay": {"doubleValue": -3.2},
        "cadera_az": {"doubleValue": 1.8},
        "cadera_gx": {"doubleValue": 15.5},
        "cadera_gy": {"doubleValue": -20.3},
        "cadera_gz": {"doubleValue": 30.1},
        # Datos sensor pierna
        "pierna_ax": {"doubleValue": 2.8},
        "pierna_ay": {"doubleValue": -2.9},
        "pierna_az": {"doubleValue": 1.5},
        "pierna_gx": {"doubleValue": 18.2},
        "pierna_gy": {"doubleValue": -22.5},
        "pierna_gz": {"doubleValue": 28.7},
    }
}

print("📤 Enviando alerta de prueba a Firestore...")
print(f"   Confianza: 98% (debe activar WhatsApp automático)\n")

try:
    response = requests.post(FIRESTORE_URL, json=documento, timeout=10)
    
    if response.status_code == 200:
        resultado = response.json()
        doc_id = resultado.get('name', '').split('/')[-1]
        
        print("✅ ¡Alerta enviada a Firestore!")
        print(f"   🔑 ID: {doc_id}\n")
        
        print("=" * 60)
        print("\n🔍 AHORA VERIFICA EN EL NAVEGADOR:")
        print("   1. La consola debería mostrar:")
        print("      - '🚨 Nueva alerta detectada'")
        print("      - '📱 Enviando WhatsApp...'")
        print("      - '✅ WhatsApp enviado correctamente'")
        print("\n   2. Deberías ver:")
        print("      - 🔔 Notificación roja en pantalla")
        print("      - 🔊 Sonido beep-beep")
        print("      - 📱 Mensaje de WhatsApp en tu teléfono")
        print("\n   3. Si NO aparece nada:")
        print("      - Verifica que la página esté abierta")
        print("      - Verifica la configuración de WhatsApp")
        print("      - Mira la consola del navegador por errores")
        
        print("\n📱 Mensaje esperado en WhatsApp:")
        print("   ┌─────────────────────────────────────┐")
        print("   │ 🚨 ALERTA DE CAÍDA DETECTADA       │")
        print("   │                                     │")
        print("   │ 👤 Persona: Vicente                │")
        print(f"   │ 📅 Fecha: {ahora_chile.strftime('%d/%m/%Y, %H:%M:%S')}   │")
        print("   │ 🎯 Confianza: 98.0%                │")
        print(f"   │ 📍 ID: {doc_id}... │")
        print("   │                                     │")
        print("   │ Verifica el estado de la persona   │")
        print("   │ inmediatamente.                     │")
        print("   └─────────────────────────────────────┘")
        
    else:
        print(f"❌ Error Firestore: {response.status_code}")
        print(f"   Respuesta: {response.text[:200]}")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("\n💡 TIPS:")
print("   - El listener solo funciona con la página ABIERTA")
print("   - La confianza debe ser ≥95% para enviar WhatsApp")
print("   - Revisa la consola del navegador (F12) por errores")
print("   - Verifica que guardaste la configuración de WhatsApp")
