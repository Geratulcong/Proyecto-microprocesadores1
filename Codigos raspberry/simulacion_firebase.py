import requests
import json
import asyncio
from bleak import BleakScanner, BleakClient

# URL de la base de datos Firebase del usuario (agregar /sensores.json para la API REST)
url = "https://detector-de-caidas-360-default-rtdb.firebaseio.com/sensores.json"

async def main():
    devices = await BleakScanner.discover()
    for d in devices:
        print(d)

    # Reemplaza con el address de tu Arduino (ejemplo: 'F4:12:FA:AA:BB:CC')
    address = "TU:AD:DR:ES:S"
    async with BleakClient(address) as client:
        print("Conectado:", client.is_connected)
        # Aquí puedes leer/escribir características BLE
    data = {
    "accelerationX": 0,
    "accelerationXY": 0,
    "accelerationXZ": 0,
    "compassX": 0,
    "compassY": 0,
    "compassZ": 0,
    "createAt": "2025-10-23T00:00:00-03:00",
    "gyroscopeX": 0,
    "gyroscopeY": 0,
    "gyroscopeZ": 0,
    "magnetometerX": 0,
    "magnetometerY": 0,
    "magnetometerZ": 111
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, data=json.dumps(data), headers=headers)

    if response.status_code == 200:
        print("Datos enviados correctamente a Firebase.")
    else:
        print("Error al enviar datos:", response.text)

        
asyncio.run(main())

