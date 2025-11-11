#include <ArduinoBLE.h> 
#include <Arduino_LSM9DS1.h>

// UUIDs para servicio y característica BLE
const char* deviceServiceUuid = "19b10000-e8f2-537e-4f6c-d104768a1214";
const char* deviceServiceCharacteristicUuid = "19b10001-e8f2-537e-4f6c-d104768a1214";

BLEService sensorService(deviceServiceUuid);
BLECharacteristic sensorCharacteristic(deviceServiceCharacteristicUuid, BLERead | BLENotify, 256);

// Variables para sensores (2 sensores: cadera y pierna)
// Nota: Como solo tenemos 1 Arduino, el segundo sensor puede ser simulado
// o puedes usar dos Arduinos. Para este ejemplo usaremos el mismo sensor
// con nombres diferentes.
float cadera_ax, cadera_ay, cadera_az;
float cadera_gx, cadera_gy, cadera_gz;
float pierna_ax, pierna_ay, pierna_az;
float pierna_gx, pierna_gy, pierna_gz;
char jsonBuffer[512];  // Buffer más grande para 12 valores

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
  
  // Configurar BLE
  BLE.setLocalName("NanoSense33-Caidas");
  BLE.setAdvertisedService(sensorService);
  sensorService.addCharacteristic(sensorCharacteristic);
  BLE.addService(sensorService);
  
  sensorCharacteristic.writeValue("Esperando conexión...");
  
  BLE.advertise();
  Serial.println("📡 Esperando conexión BLE...");
}

void loop() {
  BLEDevice central = BLE.central();

  if (central) {
    Serial.print("✅ Conectado a: ");
    Serial.println(central.address());

    while (central.connected()) {
      // Leer sensores del IMU (simularemos ambos sensores)
      if (IMU.accelerationAvailable()) {
        IMU.readAcceleration(cadera_ax, cadera_ay, cadera_az);
        // Si tienes 2 Arduinos, lee el segundo aquí
        // Por ahora, usamos los mismos valores para ambos
        pierna_ax = cadera_ax;
        pierna_ay = cadera_ay;
        pierna_az = cadera_az;
      }
      
      if (IMU.gyroscopeAvailable()) {
        IMU.readGyroscope(cadera_gx, cadera_gy, cadera_gz);
        // Si tienes 2 Arduinos, lee el segundo aquí
        // Por ahora, usamos los mismos valores para ambos
        pierna_gx = cadera_gx;
        pierna_gy = cadera_gy;
        pierna_gz = cadera_gz;
      }

      // Crear JSON con los 12 valores (cadera + pierna)
      snprintf(jsonBuffer, sizeof(jsonBuffer),
               "{\"cadera_ax\":%.4f,\"cadera_ay\":%.4f,\"cadera_az\":%.4f,"
               "\"cadera_gx\":%.4f,\"cadera_gy\":%.4f,\"cadera_gz\":%.4f,"
               "\"pierna_ax\":%.4f,\"pierna_ay\":%.4f,\"pierna_az\":%.4f,"
               "\"pierna_gx\":%.4f,\"pierna_gy\":%.4f,\"pierna_gz\":%.4f}",
               cadera_ax, cadera_ay, cadera_az, cadera_gx, cadera_gy, cadera_gz,
               pierna_ax, pierna_ay, pierna_az, pierna_gx, pierna_gy, pierna_gz);

      // Enviar por BLE
      sensorCharacteristic.writeValue(jsonBuffer);

      // Debug por Serial
      Serial.println(jsonBuffer);

      // Frecuencia: 20Hz (50ms) - igual que tus datos de entrenamiento
      delay(50);
    }

    Serial.print("❌ Desconectado de: ");
    Serial.println(central.address());
  }
}
