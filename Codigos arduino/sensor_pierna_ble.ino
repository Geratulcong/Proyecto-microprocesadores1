#include <ArduinoBLE.h> 
#include <Arduino_LSM9DS1.h>

// UUIDs únicos para el sensor de PIERNA
const char* deviceServiceUuid = "19b20000-0000-1000-8000-00805f9b34fb";
const char* deviceServiceCharacteristicUuid = "19b20001-0000-1000-8000-00805f9b34fb";

BLEService sensorService(deviceServiceUuid);
BLECharacteristic sensorCharacteristic(deviceServiceCharacteristicUuid, BLERead | BLENotify, 256);

// Variables para sensores
float ax, ay, az;
float gx, gy, gz;
char jsonBuffer[256];

void setup() {
  Serial.begin(9600);
  delay(1000);
  
  // Inicializar BLE
  if (!BLE.begin()) {
    Serial.println("❌ Error iniciando BLE");
    while(1);
  }
  
  // Inicializar IMU
  if (!IMU.begin()) {
    Serial.println("❌ Error iniciando IMU");
    while(1);
  }

  Serial.println("✅ BLE e IMU iniciados correctamente");
  
  // Configurar BLE con nombre único para PIERNA
  BLE.setLocalName("Sensor-Pierna");
  BLE.setAdvertisedService(sensorService);
  sensorService.addCharacteristic(sensorCharacteristic);
  BLE.addService(sensorService);
  
  sensorCharacteristic.writeValue("Sensor Pierna - Esperando conexión...");
  
  BLE.advertise();
  Serial.println("📡 Sensor PIERNA - Esperando conexión BLE...");
}

void loop() {
  BLEDevice central = BLE.central();

  if (central) {
    Serial.print("✅ PIERNA conectado a: ");
    Serial.println(central.address());

    while (central.connected()) {
      // Leer sensores
      if (IMU.accelerationAvailable()) {
        IMU.readAcceleration(ax, ay, az);
      }
      
      if (IMU.gyroscopeAvailable()) {
        IMU.readGyroscope(gx, gy, gz);
      }

      // Crear JSON con identificador de sensor
      snprintf(jsonBuffer, sizeof(jsonBuffer),
               "{\"sensor\":\"pierna\",\"ax\":%.4f,\"ay\":%.4f,\"az\":%.4f,\"gx\":%.4f,\"gy\":%.4f,\"gz\":%.4f}",
               ax, ay, az, gx, gy, gz);

      // Enviar por BLE
      sensorCharacteristic.writeValue(jsonBuffer);

      // Debug por Serial
      Serial.println(jsonBuffer);

      // Frecuencia: 20Hz (50ms)
      delay(50);
    }

    Serial.print("❌ PIERNA desconectado de: ");
    Serial.println(central.address());
  }
}
