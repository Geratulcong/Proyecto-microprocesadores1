"""
Script de prueba para verificar conexión con Firebase
Envía una alerta de prueba a la base de datos
"""
import requests
from datetime import datetime
import json

# URL de Firebase
FIREBASE_URL = "https://detector-de-caidas-360-default-rtdb.firebaseio.com/alertas.json"

print("╔════════════════════════════════════════════════╗")
print("║     Test de Conexión Firebase                 ║")
print("╚════════════════════════════════════════════════╝\n")

# Datos de prueba
alerta_prueba = {
    "timestamp": datetime.now().isoformat(),
    "probabilidad": 0.97,
    "tipo": "TEST",
    "sensor_cadera": {
        "ax": 0.123, "ay": -0.456, "az": 0.987,
        "gx": 1.23, "gy": -4.56, "gz": 7.89
    },
    "sensor_pierna": {
        "ax": 0.234, "ay": -0.567, "az": 1.012,
        "gx": 2.34, "gy": -5.67, "gz": 8.90
    }
}

print("📤 Enviando alerta de prueba...")
print(f"   URL: {FIREBASE_URL}")
print(f"   Datos: {json.dumps(alerta_prueba, indent=2)}\n")

try:
    response = requests.post(FIREBASE_URL, json=alerta_prueba, timeout=10)
    
    print(f"📊 Código de respuesta: {response.status_code}")
    
    if response.status_code == 200:
        resultado = response.json()
        alerta_id = resultado.get('name', 'N/A')
        
        print("✅ ¡Alerta enviada exitosamente!")
        print(f"   🔑 ID de la alerta: {alerta_id}")
        print(f"\n🔗 Ver en Firebase:")
        print(f"   https://console.firebase.google.com/project/detector-de-caidas-360/database")
        print(f"\n📍 Ruta completa:")
        print(f"   /alertas/{alerta_id}")
        
    else:
        print("❌ Error al enviar alerta")
        print(f"   Respuesta: {response.text}")
        
except requests.exceptions.Timeout:
    print("⏱️  Error: Timeout - Firebase no respondió")
    
except requests.exceptions.ConnectionError:
    print("❌ Error de conexión a Internet")
    print("   Verifica tu conexión y prueba de nuevo")
    
except Exception as e:
    print(f"❌ Error inesperado: {e}")

print("\n" + "─" * 60)
print("💡 Notas:")
print("   - Si funciona, verás la alerta en Firebase Console")
print("   - Puedes eliminar esta alerta de prueba desde la consola")
print("   - El sistema enviará alertas reales con este mismo formato")
