/*
  BLE_Central_IMU.ino

  Arduino central que recibe datos de acelerómetro y giroscopio
  desde un dispositivo periférico BLE y lee también sus propios sensores.
  
  Este código puede recibir datos de OTRO Arduino Nano 33 BLE Sense
  que esté ejecutando el código periférico.
  
  Hardware: Arduino Nano 33 BLE Sense (Central)
*/

#include <ArduinoBLE.h>
#include <Arduino_LSM9DS1.h>

// UUIDs del servicio periférico a buscar
const char* deviceServiceUuid = "19b10000-e8f2-537e-4f6c-d104768a1214";
const char* deviceServiceCharacteristicUuid = "19b10001-e8f2-537e-4f6c-d104768a1214";

// Variables para datos locales (este Arduino)
float ax_local, ay_local, az_local;
float gx_local, gy_local, gz_local;

// Variables para datos remotos (del periférico)
float ax_remote, ay_remote, az_remote;
float gx_remote, gy_remote, gz_remote;

void setup() {
  Serial.begin(9600);
  while (!Serial);
  
  // Inicializar LEDs
  pinMode(LEDR, OUTPUT);
  pinMode(LEDG, OUTPUT);
  pinMode(LEDB, OUTPUT);
  
  digitalWrite(LEDR, HIGH);
  digitalWrite(LEDG, HIGH);
  digitalWrite(LEDB, HIGH);
  
  // Inicializar IMU local
  if (!IMU.begin()) {
    Serial.println("❌ Error inicializando IMU local!");
    digitalWrite(LEDR, LOW);
    while (1);
  }
  
  Serial.println("✅ IMU local inicializado");
  
  // Inicializar BLE
  if (!BLE.begin()) {
    Serial.println("❌ Error inicializando BLE!");
    digitalWrite(LEDR, LOW);
    while (1);
  }
  
  BLE.setLocalName("NanoSense33-Central"); 
  BLE.advertise();

  Serial.println("╔════════════════════════════════════════╗");
  Serial.println("║  Arduino Nano 33 BLE (Central)        ║");
  Serial.println("║  Buscando dispositivo periférico...   ║");
  Serial.println("╚════════════════════════════════════════╝");
  Serial.println();
}

void loop() {
  connectToPeripheral();
}

void connectToPeripheral() {
  BLEDevice peripheral;
  
  Serial.println("🔍 Buscando dispositivo periférico...");
  digitalWrite(LEDB, LOW);  // LED azul = buscando

  do {
    BLE.scanForUuid(deviceServiceUuid);
    peripheral = BLE.available();
  } while (!peripheral);
  
  if (peripheral) {
    Serial.println("✅ Dispositivo periférico encontrado!");
    Serial.print("   MAC: ");
    Serial.println(peripheral.address());
    Serial.print("   Nombre: ");
    Serial.println(peripheral.localName());
    Serial.print("   Servicio: ");
    Serial.println(peripheral.advertisedServiceUuid());
    Serial.println();
    
    BLE.stopScan();
    controlPeripheral(peripheral);
  }
  
  digitalWrite(LEDB, HIGH);
}

void controlPeripheral(BLEDevice peripheral) {
  Serial.println("🔗 Conectando al periférico...");

  if (peripheral.connect()) {
    Serial.println("✅ Conectado!");
    digitalWrite(LEDG, LOW);  // LED verde = conectado
    Serial.println();
  } else {
    Serial.println("❌ Falló la conexión");
    Serial.println();
    return;
  }

  Serial.println("🔍 Descubriendo características...");
  if (peripheral.discoverAttributes()) {
    Serial.println("✅ Características descubiertas!");
    Serial.println();
  } else {
    Serial.println("❌ Error descubriendo características");
    Serial.println();
    peripheral.disconnect();
    return;
  }

  BLECharacteristic imuCharacteristic = peripheral.characteristic(deviceServiceCharacteristicUuid);
    
  if (!imuCharacteristic) {
    Serial.println("❌ No se encontró la característica IMU");
    peripheral.disconnect();
    return;
  } else if (!imuCharacteristic.canRead()) {
    Serial.println("❌ La característica no es legible");
    peripheral.disconnect();
    return;
  }
  
  // Suscribirse a notificaciones
  if (imuCharacteristic.canSubscribe()) {
    imuCharacteristic.subscribe();
    Serial.println("✅ Suscrito a notificaciones IMU");
  }
  
  Serial.println();
  Serial.println("╔════════════════════════════════════════════════════════════════╗");
  Serial.println("║  Recibiendo datos de 2 sensores:                              ║");
  Serial.println("║  - LOCAL: IMU de este Arduino                                  ║");
  Serial.println("║  - REMOTO: IMU del Arduino periférico                          ║");
  Serial.println("╚════════════════════════════════════════════════════════════════╝");
  Serial.println();
  Serial.println("Formato: LOCAL | REMOTO");
  Serial.println("─────────────────────────────────────────────────────────────────");
  
  unsigned long lastPrint = 0;
  
  while (peripheral.connected()) {
    // Leer datos locales
    if (IMU.accelerationAvailable() && IMU.gyroscopeAvailable()) {
      IMU.readAcceleration(ax_local, ay_local, az_local);
      IMU.readGyroscope(gx_local, gy_local, gz_local);
    }
    
    // Leer datos remotos si hay actualización
    if (imuCharacteristic.valueUpdated()) {
      char buffer[256];
      int length = imuCharacteristic.readValue(buffer, sizeof(buffer) - 1);
      buffer[length] = '\0';
      
      // Parsear JSON simple
      // Formato: {"ax":0.123,"ay":-0.456,"az":0.789,"gx":1.234,"gy":-5.678,"gz":9.012}
      sscanf(buffer, "{\"ax\":%f,\"ay\":%f,\"az\":%f,\"gx\":%f,\"gy\":%f,\"gz\":%f}",
             &ax_remote, &ay_remote, &az_remote, &gx_remote, &gy_remote, &gz_remote);
    }
    
    // Mostrar datos combinados cada 500ms
    if (millis() - lastPrint > 500) {
      lastPrint = millis();
      
      Serial.println();
      Serial.println("📊 DATOS ACTUALES:");
      Serial.println("─────────────────────────────────────────────");
      
      // Acelerómetro
      Serial.print("Aceleración (g):");
      Serial.println();
      Serial.print("  LOCAL  -> ax:");
      Serial.print(ax_local, 3);
      Serial.print(" ay:");
      Serial.print(ay_local, 3);
      Serial.print(" az:");
      Serial.println(az_local, 3);
      
      Serial.print("  REMOTO -> ax:");
      Serial.print(ax_remote, 3);
      Serial.print(" ay:");
      Serial.print(ay_remote, 3);
      Serial.print(" az:");
      Serial.println(az_remote, 3);
      
      // Giroscopio
      Serial.println();
      Serial.print("Giroscopio (°/s):");
      Serial.println();
      Serial.print("  LOCAL  -> gx:");
      Serial.print(gx_local, 2);
      Serial.print(" gy:");
      Serial.print(gy_local, 2);
      Serial.print(" gz:");
      Serial.println(gz_local, 2);
      
      Serial.print("  REMOTO -> gx:");
      Serial.print(gx_remote, 2);
      Serial.print(" gy:");
      Serial.print(gy_remote, 2);
      Serial.print(" gz:");
      Serial.println(gz_remote, 2);
      
      Serial.println("─────────────────────────────────────────────");
    }
  }
  
  Serial.println();
  Serial.println("❌ Periférico desconectado");
  digitalWrite(LEDG, HIGH);
}
