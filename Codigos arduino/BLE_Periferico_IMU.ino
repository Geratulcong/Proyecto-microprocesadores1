/*
  BLE_Periferico_IMU.ino

  Arduino periférico que envía datos de acelerómetro y giroscopio
  a través de BLE a un dispositivo central.
  
  Usa el sensor LSM9DS1 del Arduino Nano 33 BLE Sense.
  
  Hardware: Arduino Nano 33 BLE Sense (Periférico)
*/

#include <ArduinoBLE.h>
#include <Arduino_LSM9DS1.h>

// UUIDs del servicio y característica
const char* deviceServiceUuid = "19b10000-e8f2-537e-4f6c-d104768a1214";
const char* deviceServiceCharacteristicUuid = "19b10001-e8f2-537e-4f6c-d104768a1214";

// Variables para datos IMU
float ax, ay, az;  // Acelerómetro (g)
float gx, gy, gz;  // Giroscopio (°/s)

// Servicio y característica BLE
BLEService imuService(deviceServiceUuid); 
BLECharacteristic imuCharacteristic(deviceServiceCharacteristicUuid, BLERead | BLENotify, 512);

// Buffer para enviar datos
char jsonBuffer[256];

void setup() {
  Serial.begin(9600);
  while (!Serial);
  
  // Inicializar LEDs
  pinMode(LEDR, OUTPUT);
  pinMode(LEDG, OUTPUT);
  pinMode(LEDB, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT);
  
  digitalWrite(LEDR, HIGH);   // Apagado (activo bajo)
  digitalWrite(LEDG, HIGH);
  digitalWrite(LEDB, HIGH);
  digitalWrite(LED_BUILTIN, LOW);

  // Inicializar sensor IMU
  if (!IMU.begin()) {
    Serial.println("❌ Error inicializando IMU!");
    digitalWrite(LEDR, LOW);  // LED rojo = error
    while (1);
  }
  
  Serial.println("✅ IMU inicializado");
  Serial.print("   Frecuencia acelerómetro: ");
  Serial.print(IMU.accelerationSampleRate());
  Serial.println(" Hz");
  Serial.print("   Frecuencia giroscopio: ");
  Serial.print(IMU.gyroscopeSampleRate());
  Serial.println(" Hz");

  // Inicializar BLE
  if (!BLE.begin()) {
    Serial.println("❌ Error inicializando BLE!");
    digitalWrite(LEDR, LOW);
    while (1);
  }

  // Configurar dispositivo BLE
  BLE.setLocalName("NanoSense33-Periferico");
  BLE.setAdvertisedService(imuService);
  imuService.addCharacteristic(imuCharacteristic);
  BLE.addService(imuService);
  
  // Valor inicial vacío
  imuCharacteristic.writeValue("");
  
  // Iniciar publicidad
  BLE.advertise();

  Serial.println("╔════════════════════════════════════════╗");
  Serial.println("║  Arduino Nano 33 BLE (Periférico)    ║");
  Serial.println("║  Esperando conexión central...        ║");
  Serial.println("╚════════════════════════════════════════╝");
  Serial.println();
  
  // LED azul parpadeante = esperando conexión
  digitalWrite(LEDB, LOW);
}

void loop() {
  BLEDevice central = BLE.central();

  if (central) {
    Serial.println("✅ Dispositivo central conectado!");
    Serial.print("   MAC: ");
    Serial.println(central.address());
    Serial.println();
    
    // LED verde = conectado
    digitalWrite(LEDB, HIGH);
    digitalWrite(LEDG, LOW);

    while (central.connected()) {
      // Leer datos del IMU
      if (IMU.accelerationAvailable() && IMU.gyroscopeAvailable()) {
        IMU.readAcceleration(ax, ay, az);
        IMU.readGyroscope(gx, gy, gz);
        
        // Crear JSON con los datos
        snprintf(jsonBuffer, sizeof(jsonBuffer),
                 "{\"ax\":%.3f,\"ay\":%.3f,\"az\":%.3f,\"gx\":%.2f,\"gy\":%.2f,\"gz\":%.2f}",
                 ax, ay, az, gx, gy, gz);
        
        // Enviar por BLE
        imuCharacteristic.writeValue(jsonBuffer);
        
        // Debug en Serial (opcional, comentar si no se necesita)
        // Serial.println(jsonBuffer);
        
        delay(50);  // 20Hz de envío
      }
    }
    
    Serial.println("❌ Dispositivo central desconectado");
    Serial.println();
    
    // Volver a LED azul = esperando
    digitalWrite(LEDG, HIGH);
    digitalWrite(LEDB, LOW);
  }
}
