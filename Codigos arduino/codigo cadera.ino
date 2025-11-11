#include <ArduinoBLE.h>
#include <Arduino_LSM9DS1.h>

// --- CONFIG ---
const char* TARGET_NAME = "NanoSense33-Pierna";
const char* SVC_UUID    = "19b10000-e8f2-537e-4f6c-d104768a1214";
const char* CHR_UUID    = "19b10001-e8f2-537e-4f6c-d104768a1214";

const int MUESTRAS_POR_SESION = 40;   // 2 s a 20 Hz
const int PAUSA_ENTRE_SESIONES = 5000;
const int PERIODO_MS = 50;
const unsigned long SCAN_MS = 2000;   // escaneo breve (ms)

// --- BLE OUT (para PC/Raspberry) ---
BLEService svcOut(SVC_UUID);
BLECharacteristic chrOut(CHR_UUID, BLERead | BLENotify, 160);

// --- Variables de IMU y buffers ---
float cax, cay, caz, cgx, cgy, cgz;   // cadera
float pax = 0, pay = 0, paz = 0, pgx = 0, pgy = 0, pgz = 0; // pierna (última recibida)
char piernaBuf[96];
char outLine[160];

BLEDevice piernaDev;
BLECharacteristic piernaChr;

bool parseCSV6(const char* s, float& a1, float& a2, float& a3, float& a4, float& a5, float& a6) {
  return 6 == sscanf(s, "%f,%f,%f,%f,%f,%f", &a1, &a2, &a3, &a4, &a5, &a6);
}

void setup() {
  Serial.begin(115200);
  // No bloquear la ejecución esperando el Monitor Serial.
  // Opcional: esperar un breve timeout si quieres ver mensajes iniciales al abrir el Serial.
  unsigned long t0 = millis();
  while (!Serial && (millis() - t0) < 1000) {
    delay(5); // espera máxima ~1s sin bloquear indefinidamente
  }

  if (!IMU.begin()) {
    // Si no hay Serial abierto, no nos quedamos bloqueados: imprimimos si posible y entramos en fallo seguro.
    if (Serial) Serial.println("❌ IMU no iniciado");
    while (1);
  }
  if (Serial) Serial.println("✅ IMU iniciado");

  if (!BLE.begin()) {
    if (Serial) Serial.println("❌ BLE no iniciado");
    while (1);
  }
  if (Serial) Serial.println("✅ BLE iniciado");

  // Configurar periférico de salida (visible al PC)
  BLE.setLocalName("NanoSense33-Cadera");
  BLE.setAdvertisedService(svcOut);
  svcOut.addCharacteristic(chrOut);
  BLE.addService(svcOut);
  BLE.advertise(); // empezar advertising
  if (Serial) Serial.println("📡 Advertising activo (Cadera)");
}

void intentarConectarPierna() {
  BLE.advertise();
  BLE.scanForName(TARGET_NAME);
  unsigned long t0 = millis();
  bool conectado = false;

  while (millis() - t0 < SCAN_MS) {
    BLEDevice d = BLE.available();
    if (d && d.localName() == TARGET_NAME) {
      if (Serial) {
        Serial.print("🔎 Pierna encontrada: ");
        Serial.println(d.address());
      }
      BLE.stopScan();
      if (d.connect() && d.discoverAttributes()) {
        BLECharacteristic remote = d.characteristic(CHR_UUID);
        if (remote) {
          if (!remote.subscribe()) {
            if (Serial) Serial.println("⚠️  Suscripción a notificaciones de la pierna falló");
            d.disconnect();
            break;
          }
          piernaDev = d;
          piernaChr = remote;
          if (Serial) {
            Serial.print("✅ Conectado a pierna: ");
            Serial.println(d.address());
            BLE.advertise();
          }
          conectado = true;
          break;
        } else {
          if (Serial) Serial.println("❌ Característica en pierna no encontrada");
          d.disconnect();
          break;
        }
      } else {
        if (Serial) Serial.println("❌ Falló conexión a pierna");
        d.disconnect();
        break;
      }
    }
    BLE.poll();
    delay(20);
  }
  BLE.stopScan();
  if (!conectado && Serial) Serial.println("🔁 Pierna no encontrada en este intento");
}

void loop() {
  if (!piernaDev || !piernaDev.connected()) {
    static unsigned long lastTry = 0;
    if (millis() - lastTry > 1000) {
      lastTry = millis();
      intentarConectarPierna();
    }
    BLE.advertise();
    BLE.poll();
    delay(50);
    return;
  }

  if (piernaDev && piernaDev.connected() && piernaChr) {
    if (Serial) Serial.println("--- Inicio de captura (cadera+pierna) ---");
    for (int i = 0; i < MUESTRAS_POR_SESION && piernaDev.connected(); i++) {
      if (piernaChr.valueUpdated()) {
        int len = piernaChr.readValue((uint8_t*)piernaBuf, sizeof(piernaBuf) - 1);
        if (len > 0) {
          piernaBuf[len] = '\0';
          for (int k = len - 1; k >= 0; --k) {
            if (piernaBuf[k] == '\r' || piernaBuf[k] == '\n') piernaBuf[k] = '\0';
            else break;
          }
          if (!parseCSV6(piernaBuf, pax, pay, paz, pgx, pgy, pgz)) {
            if (Serial) Serial.println("⚠️  Formato CSV pierna inválido");
          }
        }
      }

      if (IMU.accelerationAvailable()) IMU.readAcceleration(cax, cay, caz);
      if (IMU.gyroscopeAvailable())    IMU.readGyroscope(cgx, cgy, cgz);

      int n = snprintf(outLine, sizeof(outLine),
                       "%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f\n",
                       cax, cay, caz, cgx, cgy, cgz, pax, pay, paz, pgx, pgy, pgz);

      if (n > 0) {
        chrOut.writeValue((uint8_t*)outLine, n);
        Serial.write((uint8_t*)outLine, n);
      }

      unsigned long tloop = millis();
      while (millis() - tloop < PERIODO_MS) {
        BLE.poll();
        delay(5);
      }
    }

    if (Serial) Serial.println("--- Pausa (5s) ---");
    unsigned long t0 = millis();
    while (millis() - t0 < PAUSA_ENTRE_SESIONES) {
      BLE.advertise();
      BLE.poll();
      delay(50);
    }
  } else {
    if (Serial) Serial.println("⚠️  Se perdió conexión con la pierna, reiniciando búsqueda...");
    if (piernaDev) piernaDev.disconnect();
    piernaDev = BLEDevice();
    BLE.advertise();
    BLE.poll();
    delay(200);
  }
}