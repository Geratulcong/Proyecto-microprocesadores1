"""
Script para probar las notificaciones web en tiempo real
Envía una alerta de prueba a Firebase Realtime Database
"""
import requests
from datetime import datetime
import time

FIREBASE_URL = "https://detector-de-caidas-360-default-rtdb.firebaseio.com/alertas.json"

print("╔════════════════════════════════════════════════╗")
print("║   Test de Notificaciones Web en Tiempo Real   ║")
print("╚════════════════════════════════════════════════╝\n")

print("📋 Instrucciones:")
print("1. Abre datos.html en tu navegador")
print("2. Acepta los permisos de notificación si aparecen")
print("3. Presiona ENTER aquí para enviar una alerta de prueba")
print("4. Deberías ver:")
print("   - 🔔 Notificación en la esquina superior derecha")
print("   - 🔊 Sonido de alerta (beep-beep)")
print("   - 📱 Notificación del navegador (si diste permiso)")
print()

input("Presiona ENTER cuando estés listo...")

# Enviar alerta de prueba
alerta = {
    "timestamp": datetime.now().isoformat(),
    "probabilidad": 0.98,
    "sensor_cadera": {
        "ax": 0.123, "ay": -2.456, "az": 0.987,
        "gx": 1.23, "gy": -4.56, "gz": 7.89
    },
    "sensor_pierna": {
        "ax": 0.234, "ay": -1.567, "az": 1.012,
        "gx": 2.34, "gy": -5.67, "gz": 8.90
    }
}

print("\n📤 Enviando alerta de prueba a Firebase...")
print(f"   Probabilidad: {alerta['probabilidad']*100}%")
print(f"   Timestamp: {alerta['timestamp']}\n")

try:
    response = requests.post(FIREBASE_URL, json=alerta, timeout=10)
    
    if response.status_code == 200:
        resultado = response.json()
        alerta_id = resultado.get('name', 'N/A')
        
        print("✅ ¡Alerta enviada!")
        print(f"   🔑 ID: {alerta_id}")
        print(f"\n🔔 Revisa tu navegador - deberías ver:")
        print(f"   1. Notificación roja en la esquina")
        print(f"   2. Sonido de alerta")
        print(f"   3. Datos de ambos sensores\n")
        
        print("💡 Para probar múltiples alertas:")
        print("   - Presiona ENTER para enviar otra alerta")
        print("   - Presiona Ctrl+C para salir\n")
        
        while True:
            try:
                input("Presiona ENTER para enviar otra alerta (Ctrl+C para salir)...")
                
                # Nueva alerta con datos aleatorios
                import random
                alerta["timestamp"] = datetime.now().isoformat()
                alerta["probabilidad"] = round(random.uniform(0.95, 0.99), 2)
                alerta["sensor_cadera"]["ax"] = round(random.uniform(-3, 3), 3)
                alerta["sensor_cadera"]["ay"] = round(random.uniform(-3, 3), 3)
                
                response = requests.post(FIREBASE_URL, json=alerta, timeout=10)
                if response.status_code == 200:
                    print(f"✅ Alerta enviada (prob: {alerta['probabilidad']*100}%)")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Test finalizado")
                break
        
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "─" * 60)
print("📊 Estadísticas:")
print("   - Las notificaciones aparecen automáticamente")
print("   - Se auto-cierran después de 15 segundos")
print("   - El sonido se reproduce 2 veces (beep-beep)")
print("   - La tabla se actualiza automáticamente")
