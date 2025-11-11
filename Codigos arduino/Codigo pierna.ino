#include <ArduinoBLE.h>
#include <Arduino_LSM9DS1.h>

const char* SVC_UUID = "19b10000-e8f2-537e-4f6c-d104768a1214";
const char* CHR_UUID = "19b10001-e8f2-537e-4f6c-d104768a1214";

const int MUESTRAS_POR_SESION = 40;   // 2 s a 20 Hz
const int PAUSA_ENTRE_SESIONES = 5000;
const int PERIODO_MS = 50;

BLEService svc(SVC_UUID);
BLECharacteristic chr(CHR_UUID, BLERead | BLENotify, 96);

float ax, ay, az, gx, gy, gz;
char line[96];

void setup() {
  Serial.begin(115200);
  delay(300);

  if (!BLE.begin()) { Serial.println("BLE ERR"); while (1); }
  if (!IMU.begin()) { Serial.println("IMU ERR"); while (1); }

  BLE.setLocalName("NanoSense33-Pierna");
  BLE.setAdvertisedService(svc);
  svc.addCharacteristic(chr);
  BLE.addService(svc);
  BLE.advertise();

  Serial.println("Pierna lista (CSV, 2s/5s)...");
}

void loop() {
  BLEDevice central = BLE.central();
  if (!central) return;

  Serial.print("Pierna conectada a: "); Serial.println(central.address());

  while (central.connected()) {
    Serial.println("--- Inicio de captura (pierna) ---");
    for (int i = 0; i < MUESTRAS_POR_SESION && central.connected(); i++) {
      if (IMU.accelerationAvailable()) IMU.readAcceleration(ax, ay, az);
      if (IMU.gyroscopeAvailable())    IMU.readGyroscope(gx, gy, gz);

      // CSV: ax,ay,az,gx,gy,gz
      int n = snprintf(line, sizeof(line), "%.3f,%.3f,%.3f,%.3f,%.3f,%.3f\n",
                       ax, ay, az, gx, gy, gz);

      if (n > 0) {
        chr.writeValue((uint8_t*)line, n);  // notificación BLE
        Serial.write((uint8_t*)line, n);    // depuración serie
      }
      delay(PERIODO_MS);
    }
    Serial.println("--- Pausa (5s) ---");
    delay(PAUSA_ENTRE_SESIONES);
  }

  Serial.println("Central desconectado");
  BLE.advertise();
}