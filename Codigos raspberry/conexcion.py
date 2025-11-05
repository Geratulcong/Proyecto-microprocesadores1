import asyncio
import json
import numpy as np
from bleak import BleakClient
from tensorflow.keras.models import load_model

# --- Configura tu dirección BLE y UUID ---
DEVICE_ADDRESS = "FA:04:1B:E0:65:B1"   # Cambia por la dirección MAC de tu Arduino
CHARACTERISTIC_UUID = "19b10001-e8f2-537e-4f6c-d104768a1214"

# --- Carga tu modelo CNN entrenado ---
model = load_model(r"c:\Users\gerol\Downloads\Proyecto Microprocesadores\Proyecto-microprocesadores1\modelo_cnn_imu.h5")

# --- Configura las etiquetas ---
# Asegúrate de que coincidan con el orden de salida de tu modelo
# Tus clases: 1=pararse, 2=sentarse, 3=caminar, 4=caerse, 5=quieto
# Después de y-1: índice 0=pararse, 1=sentarse, 2=caminar, 3=caerse, 4=quieto
labels = ["pararse", "sentarse", "caminar", "caerse", "quieto"]

# --- Normalización con valores del entrenamiento ---
# Estos valores deben coincidir con los del dataset de entrenamiento
# Ejecuta el script cnn.py y obtén estos valores o usa valores aproximados
def normalize_data(data):
    # Usar normalización simple sin estadísticas globales por ahora
    # Esto puede causar problemas de predicción
    return data  # Temporalmente sin normalizar para probar

# --- Función principal BLE ---
async def run_ble():
    async with BleakClient(DEVICE_ADDRESS) as client:
        print("🔗 Conectado al dispositivo BLE")

        def handle_notify(_, data):
            nonlocal buffer
            try:
                json_str = data.decode("utf-8")
                lectura = json.loads(json_str)

                # Guardar solo las variables de interés (sin magnetómetro)
                sample = [
                    lectura["ax"], lectura["ay"], lectura["az"],
                    lectura["gx"], lectura["gy"], lectura["gz"]
                ]
                buffer.append(sample)

                # Mantener solo las últimas 10 lecturas (ventana deslizante)
                if len(buffer) > 10:
                    buffer.pop(0)

                # Hacer predicción cuando tengamos al menos 10 lecturas
                if len(buffer) == 10:
                    X = np.array(buffer).reshape(1, 10, 6)  # Ahora son 6 features en vez de 9
                    X = normalize_data(X)
                    pred = model.predict(X, verbose=0)
                    clase = np.argmax(pred)
                    print(f"🧠 Acción detectada: {labels[clase]} (confianza: {np.max(pred):.2f})")
            except Exception as e:
                print("Error en lectura:", e)

        buffer = []
        await client.start_notify(CHARACTERISTIC_UUID, handle_notify)

        print("📡 Esperando datos... Presiona Ctrl+C para detener.")
        while True:
            await asyncio.sleep(1)

# --- Ejecutar programa ---
if __name__ == "__main__":
    try:
        asyncio.run(run_ble())
    except KeyboardInterrupt:
        print("\n🚪 Conexión finalizada.")
