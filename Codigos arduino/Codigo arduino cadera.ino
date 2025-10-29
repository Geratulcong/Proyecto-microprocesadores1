#include <ArduinoBLE.h> 
#include <Wire.h>
#include <Arduino_LSM9DS1.h>
#include <QMC5883LCompass.h>

QMC5883LCompass compass;

// UUIDs para servicio y característica BLE
const char* deviceServiceUuid = "19b10000-e8f2-537e-4f6c-d104768a1214";
const char* deviceServiceCharacteristicUuid = "19b10001-e8f2-537e-4f6c-d104768a1214";

BLEService sensorService(deviceServiceUuid);
BLECharacteristic sensorCharacteristic(deviceServiceCharacteristicUuid, BLERead | BLENotify, 200);

void setup() {
  Serial.begin(9600);
  
  if (!BLE.begin()) {
    Serial.println("Error iniciando BLE");
    while(1);
  }
  
  IMU.begin();
  Wire.begin();
  compass.init();

  Serial.println("Iniciando BLE...");
  
  BLE.setLocalName("NanoSense33");
  BLE.setAdvertisedService(sensorService);

  sensorService.addCharacteristic(sensorCharacteristic);
  BLE.addService(sensorService);

  sensorCharacteristic.setValue("Inicializando...");

  BLE.advertise();
  Serial.println("Esperando conexión BLE...");
}

void loop() {
  BLEDevice central = BLE.central();

  if (central) {
    Serial.print("Conectado a central: ");
    Serial.println(central.address());

    while (central.connected()) {
      float ax, ay, az;
      float gx, gy, gz;
      float mx, my, mz;

      IMU.readAcceleration(ax, ay, az);
      IMU.readGyroscope(gx, gy, gz);
      IMU.readMagneticField(mx, my, mz);

      compass.read();
      int x = compass.getX();
      int y = compass.getY();
      int z = compass.getZ();

      // Crear JSON manualmente (mejor usar ArduinoJson para producción)
      String json = "{";
      json += "\"ax\":" + String(ax, 3) + ",";
      json += "\"ay\":" + String(ay, 3) + ",";
      json += "\"az\":" + String(az, 3) + ",";
      json += "\"gx\":" + String(gx, 3) + ",";
      json += "\"gy\":" + String(gy, 3) + ",";
      json += "\"gz\":" + String(gz, 3) + ",";
      json += "\"mx\":" + String(mx, 3) + ",";
      json += "\"my\":" + String(my, 3) + ",";
      json += "\"mz\":" + String(mz, 3) + ",";
      json += "\"qx\":" + String(x) + ",";
      json += "\"qy\":" + String(y) + ",";
      json += "\"qz\":" + String(z);
      json += "}";

      sensorCharacteristic.setValue(json.c_str());

      Serial.println(json);

      delay(300);
    }

    Serial.print("Central desconectada: ");
    Serial.println(central.address());
  }
}
