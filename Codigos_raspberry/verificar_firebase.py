"""
Script de ayuda para configurar Firebase
Te guía paso a paso para obtener tus credenciales
"""
import os
import json
from pathlib import Path

def verificar_credenciales():
    """Verifica si el archivo de credenciales existe y es válido"""
    script_dir = Path(__file__).parent
    cred_path = script_dir / "firebase-credentials.json"
    
    print("=" * 70)
    print("🔥 VERIFICADOR DE CREDENCIALES DE FIREBASE")
    print("=" * 70)
    
    if not cred_path.exists():
        print("\n❌ NO se encontró el archivo 'firebase-credentials.json'\n")
        print("📋 PASOS PARA OBTENER TUS CREDENCIALES:\n")
        print("1️⃣  Abre tu navegador y ve a:")
        print("    👉 https://console.firebase.google.com/\n")
        print("2️⃣  Si no tienes un proyecto, créalo:")
        print("    • Haz clic en 'Agregar proyecto'")
        print("    • Dale un nombre (ej: 'detector-caidas')")
        print("    • Sigue los pasos de configuración\n")
        print("3️⃣  En tu proyecto, haz clic en el ícono de ⚙️ (Configuración)\n")
        print("4️⃣  Selecciona 'Configuración del proyecto'\n")
        print("5️⃣  Ve a la pestaña 'Cuentas de servicio'\n")
        print("6️⃣  Haz clic en 'Generar nueva clave privada'\n")
        print("7️⃣  Se descargará un archivo JSON (ej: proyecto-123abc-firebase.json)\n")
        print("8️⃣  Copia ese archivo a esta carpeta y renómbralo a:")
        print(f"    👉 {cred_path}\n")
        print("9️⃣  Ejecuta este script de nuevo para verificar\n")
        print("=" * 70)
        
        # Preguntar si quiere crear un archivo de ejemplo
        respuesta = input("\n¿Quieres crear un archivo de ejemplo? (s/n): ").lower()
        if respuesta == 's':
            crear_ejemplo(cred_path)
        
        return False
    
    # Si existe, verificar que sea un JSON válido
    try:
        with open(cred_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Verificar campos requeridos
        campos_requeridos = [
            'type',
            'project_id',
            'private_key_id',
            'private_key',
            'client_email'
        ]
        
        faltantes = [campo for campo in campos_requeridos if campo not in data]
        
        if faltantes:
            print(f"\n⚠️  El archivo existe pero le faltan campos: {', '.join(faltantes)}")
            print("    Asegúrate de haber descargado el archivo correcto desde Firebase\n")
            return False
        
        print("\n✅ Archivo de credenciales encontrado y válido!\n")
        print(f"📁 Ubicación: {cred_path}")
        print(f"🔑 Project ID: {data['project_id']}")
        print(f"📧 Client Email: {data['client_email']}")
        print(f"📝 Type: {data['type']}\n")
        print("=" * 70)
        print("🎉 ¡Todo listo! Puedes ejecutar 'simular_caida_firebase.py'\n")
        return True
        
    except json.JSONDecodeError:
        print("\n❌ El archivo existe pero no es un JSON válido")
        print("    Verifica que descargaste el archivo correcto desde Firebase\n")
        return False
    except Exception as e:
        print(f"\n❌ Error al leer el archivo: {e}\n")
        return False


def crear_ejemplo(ruta):
    """Crea un archivo de ejemplo para referencia"""
    ejemplo_path = ruta.parent / "firebase-credentials.example.json"
    ejemplo = {
        "type": "service_account",
        "project_id": "tu-proyecto-id-123abc",
        "private_key_id": "abc123def456...",
        "private_key": "-----BEGIN PRIVATE KEY-----\\n...TU_CLAVE_AQUI...\\n-----END PRIVATE KEY-----\\n",
        "client_email": "firebase-adminsdk-xxxxx@tu-proyecto.iam.gserviceaccount.com",
        "client_id": "123456789...",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
    }
    
    try:
        with open(ejemplo_path, 'w', encoding='utf-8') as f:
            json.dump(ejemplo, f, indent=2)
        print(f"\n✅ Archivo de ejemplo creado: {ejemplo_path.name}")
        print("    (Este es solo un ejemplo, necesitas el archivo real de Firebase)\n")
    except Exception as e:
        print(f"\n❌ No se pudo crear el ejemplo: {e}\n")


def verificar_firestore():
    """Verifica que Firestore esté habilitado en Firebase"""
    print("\n" + "=" * 70)
    print("📊 VERIFICAR FIRESTORE DATABASE")
    print("=" * 70)
    print("\n⚠️  Además de las credenciales, necesitas tener Firestore habilitado:\n")
    print("1. Ve a tu proyecto en Firebase Console")
    print("2. En el menú lateral, busca 'Firestore Database'")
    print("3. Si no está creado, haz clic en 'Crear base de datos'")
    print("4. Selecciona el modo:")
    print("   • Modo de producción (con reglas de seguridad)")
    print("   • Modo de prueba (sin autenticación por 30 días) ⬅️ RECOMENDADO PARA EMPEZAR")
    print("5. Selecciona la ubicación (ej: us-central)")
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    if verificar_credenciales():
        print("💡 Siguiente paso: Ejecuta 'python simular_caida_firebase.py'\n")
    else:
        print("⏳ Una vez tengas el archivo, vuelve a ejecutar este script\n")
    
    verificar_firestore()
