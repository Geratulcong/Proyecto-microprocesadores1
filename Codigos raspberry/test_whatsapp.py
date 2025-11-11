"""
Script de prueba para verificar el envío de WhatsApp
Ejecuta esto ANTES de probar el detector completo
"""
import requests
from urllib.parse import quote

# 🔧 Configura tus datos (los mismos que en detector_tiempo_real.py):
phone = '56940551619'  # tu número SIN el + (ej: 56998765432)
apikey = '4253930'  # la API Key que te dio CallMeBot
message = '🧪 Mensaje de prueba desde Python - Sistema de detección de caídas funcionando!'

print("╔════════════════════════════════════════════════╗")
print("║     Test de Envío de WhatsApp - CallMeBot     ║")
print("╚════════════════════════════════════════════════╝\n")

print(f"📱 Teléfono: +{phone}")
print(f"🔑 API Key: {apikey}")
print(f"💬 Mensaje: {message}\n")

# Codificar el mensaje para URL
mensaje_codificado = quote(message)
url = f'https://api.callmebot.com/whatsapp.php?phone={phone}&text={mensaje_codificado}&apikey={apikey}'

print("🔗 URL construida:")
print(f"   {url}\n")

print("─" * 60)
print("📤 Enviando mensaje...\n")

try:
    response = requests.get(url, timeout=15)
    
    print(f"📊 Código de respuesta: {response.status_code}")
    print(f"📄 Respuesta del servidor: {response.text}\n")
    
    if response.status_code == 200:
        print("✅ ¡Mensaje enviado exitosamente!")
        print("   Revisa tu WhatsApp para confirmar")
    else:
        print("❌ Error al enviar mensaje")
        print("\n🔍 Posibles causas:")
        print("   1. API Key incorrecta")
        print("   2. Número de teléfono incorrecto")
        print("   3. No activaste CallMeBot (envía 'I allow callmebot to send me messages' al +34 644 28 88 80)")
        print("   4. Límite de mensajes alcanzado (máx 50/día)")
        
except requests.exceptions.Timeout:
    print("⏱️  Error: Timeout - El servidor no respondió a tiempo")
    print("   Intenta de nuevo en unos segundos")
    
except requests.exceptions.ConnectionError:
    print("❌ Error de conexión a Internet")
    print("   Verifica tu conexión y prueba de nuevo")
    
except Exception as e:
    print(f"❌ Error inesperado: {e}")

print("\n" + "─" * 60)
print("💡 Notas:")
print("   - CallMeBot permite máximo 50 mensajes por día")
print("   - El mensaje puede tardar hasta 30 segundos en llegar")
print("   - Si no funciona, verifica que hayas activado CallMeBot primero")
