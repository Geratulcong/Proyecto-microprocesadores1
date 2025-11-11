"""
Simulador de caídas con envío a Firebase Firestore
Estructura: Historial > Personas > Vicente > [documentos de caídas]
"""
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import random
import time
import os
from pathlib import Path

# 🔧 CONFIGURACIÓN DE FIREBASE
# Buscar el archivo de credenciales en diferentes ubicaciones
SCRIPT_DIR = Path(__file__).parent
POSSIBLE_PATHS = [
    SCRIPT_DIR / "firebase-credentials.json",
    Path.cwd() / "firebase-credentials.json",
    Path.cwd() / "Codigos raspberry" / "firebase-credentials.json",
]

FIREBASE_CREDENTIALS_PATH = None
for path in POSSIBLE_PATHS:
    if path.exists():
        FIREBASE_CREDENTIALS_PATH = str(path)
        break

# Inicializar Firebase
if FIREBASE_CREDENTIALS_PATH is None:
    print("❌ No se encontró el archivo de credenciales de Firebase\n")
    print("📝 INSTRUCCIONES PARA OBTENER TUS CREDENCIALES:\n")
    print("1. Ve a https://console.firebase.google.com/")
    print("2. Selecciona tu proyecto (o crea uno nuevo)")
    print("3. Haz clic en ⚙️ 'Configuración del proyecto'")
    print("4. Ve a la pestaña 'Cuentas de servicio'")
    print("5. Haz clic en 'Generar nueva clave privada'")
    print("6. Se descargará un archivo JSON\n")
    print("7. Guarda el archivo como 'firebase-credentials.json' en:")
    print(f"   → {SCRIPT_DIR}\n")
    print("8. Vuelve a ejecutar este script\n")
    print("⚠️ IMPORTANTE: Este archivo contiene datos sensibles, no lo subas a GitHub")
    print("   (Ya está protegido en .gitignore)\n")
    exit(1)

try:
    cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print(f"✅ Conexión a Firebase establecida")
    print(f"📁 Usando credenciales: {Path(FIREBASE_CREDENTIALS_PATH).name}\n")
except Exception as e:
    print(f"❌ Error al inicializar Firebase: {e}\n")
    print("� Posibles causas:")
    print("   - El archivo JSON está corrupto")
    print("   - Las credenciales son inválidas")
    print("   - No tienes permisos en el proyecto de Firebase\n")
    exit(1)


def simular_caida(persona="Vicente", tipo_caida="Frontal"):
    """
    Simula una caída y la registra en Firebase
    
    Args:
        persona: Nombre de la persona (subcarpeta en Historial/Personas)
        tipo_caida: Tipo de caída (Frontal, Lateral, Posterior, etc.)
    """
    print("=" * 60)
    print("🚨 SIMULANDO CAÍDA")
    print("=" * 60)
    
    # Generar datos simulados de la caída
    timestamp = datetime.now()
    datos_caida = {
        "hora_caida": timestamp,
        "confianza": round(random.uniform(0.85, 0.99), 2),  # Simular confianza del modelo
        "estado": "Pendiente",  # Pendiente, Atendido, Falsa alarma
        "timestamp_servidor": firestore.SERVER_TIMESTAMP
    }
    
    try:
        # Ruta: Historial > Personas > Vicente > [nuevo documento]
        doc_ref = db.collection("Historial").document("Personas").collection(persona).document()
        
        # Guardar en Firestore
        doc_ref.set(datos_caida)
        
        # Obtener el ID generado
        doc_id = doc_ref.id
        
        print(f"\n✅ Caída registrada exitosamente en Firebase!")
        print(f"📍 Ruta: Historial/Personas/{persona}/{doc_id}")
        print(f"📅 Hora: {timestamp.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"🔴 Tipo: {tipo_caida}")
        print(f"📊 Confianza: {datos_caida['confianza']*100:.0f}%")
        print(f"📍 Ubicación: {datos_caida['ubicacion']}")
        print(f"⚡ Aceleración máxima: {datos_caida['aceleracion_max']} G")
        print("\n" + "=" * 60 + "\n")
        
        return doc_id
        
    except Exception as e:
        print(f"\n❌ Error al guardar en Firebase: {e}\n")
        return None


def listar_caidas(persona="Vicente", limite=10):
    """
    Lista las últimas caídas registradas para una persona
    """
    print(f"\n📋 ÚLTIMAS {limite} CAÍDAS DE {persona.upper()}")
    print("=" * 80)
    
    try:
        # Obtener documentos ordenados por fecha
        docs = db.collection("Historial").document("Personas") \
                 .collection(persona) \
                 .order_by("hora_caida", direction=firestore.Query.DESCENDING) \
                 .limit(limite) \
                 .stream()
        
        contador = 0
        for doc in docs:
            contador += 1
            data = doc.to_dict()
            
            # Formatear hora
            if isinstance(data['hora_caida'], datetime):
                hora = data['hora_caida'].strftime('%d/%m/%Y %H:%M:%S')
            else:
                hora = str(data['hora_caida'])
            
            print(f"\n{contador}. ID: {doc.id}")
            print(f"   📅 Hora: {hora}")
            print(f"   🔴 Tipo: {data.get('tipo', 'N/A')}")
            print(f"   📊 Confianza: {data.get('confianza', 0)*100:.0f}%")
            print(f"   📍 Ubicación: {data.get('ubicacion', 'N/A')}")
            print(f"   ⚡ Aceleración: {data.get('aceleracion_max', 'N/A')} G")
            print(f"   🏥 Estado: {data.get('estado', 'N/A')}")
        
        if contador == 0:
            print("No hay caídas registradas para esta persona.")
        
        print("\n" + "=" * 80 + "\n")
        
    except Exception as e:
        print(f"❌ Error al listar caídas: {e}\n")


def menu_interactivo():
    """
    Menú interactivo para simular caídas
    """
    tipos_caida = ["Frontal", "Lateral", "Posterior", "Mareo", "Tropiezo"]
    
    while True:
        print("\n" + "="*60)
        print("🏥 SIMULADOR DE CAÍDAS - FIREBASE")
        print("="*60)
        print("1. Simular caída única")
        print("2. Simular múltiples caídas")
        print("3. Listar caídas registradas")
        print("4. Simular caída para otra persona")
        print("5. Salir")
        print("="*60)
        
        opcion = input("\n👉 Selecciona una opción (1-5): ").strip()
        
        if opcion == "1":
            print("\nTipos de caída disponibles:")
            for i, tipo in enumerate(tipos_caida, 1):
                print(f"  {i}. {tipo}")
            
            tipo_idx = input("\n👉 Selecciona tipo de caída (1-5): ").strip()
            try:
                tipo = tipos_caida[int(tipo_idx) - 1]
                simular_caida("Vicente", tipo)
            except (ValueError, IndexError):
                print("❌ Opción inválida")
        
        elif opcion == "2":
            cantidad = input("👉 ¿Cuántas caídas quieres simular?: ").strip()
            try:
                num = int(cantidad)
                print(f"\n🔄 Simulando {num} caídas...\n")
                for i in range(num):
                    tipo = random.choice(tipos_caida)
                    simular_caida("Vicente", tipo)
                    if i < num - 1:
                        time.sleep(1)  # Esperar 1 segundo entre caídas
                print(f"✅ {num} caídas simuladas exitosamente!")
            except ValueError:
                print("❌ Cantidad inválida")
        
        elif opcion == "3":
            limite = input("👉 ¿Cuántas caídas quieres ver? (default: 10): ").strip()
            try:
                num = int(limite) if limite else 10
                listar_caidas("Vicente", num)
            except ValueError:
                listar_caidas("Vicente", 10)
        
        elif opcion == "4":
            persona = input("👉 Nombre de la persona: ").strip()
            if persona:
                tipo = random.choice(tipos_caida)
                simular_caida(persona, tipo)
            else:
                print("❌ Nombre inválido")
        
        elif opcion == "5":
            print("\n👋 ¡Hasta luego!\n")
            break
        
        else:
            print("❌ Opción inválida. Intenta de nuevo.")


if __name__ == "__main__":
    print("\n╔════════════════════════════════════════════════╗")
    print("║   Simulador de Caídas con Firebase           ║")
    print("╚════════════════════════════════════════════════╝\n")
    
    # Simular caída automáticamente
    print("🚨 Simulando caída...\n")
    simular_caida("Vicente", "Caída detectada")
    
    # Mostrar últimas 5 caídas registradas
    print("\n")
    listar_caidas("Vicente", 5)
