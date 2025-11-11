#include <Arduino_LSM9DS1.h>

// Variables para sensores
float ax, ay, az;     // Aceleración en g
float gx, gy, gz;     // Giroscopio en °/s

// Configuración de captura
const int MUESTRAS_POR_SESION = 40;  // 40 muestras × 50ms = 2 segundos
const int PAUSA_ENTRE_SESIONES = 5000;  // 5 segundos de pausa

void setup() {
  Serial.begin(9600);
  while (!Serial);
  
  Serial.println("=== Captura de IMU - Arduino Nano 33 BLE Sense ===");
  
  // Inicializar IMU
  if (!IMU.begin()) {
    Serial.println("❌ Error iniciando IMU!");
    while (1);
  }
  
  Serial.println("✅ IMU iniciado correctamente");
  Serial.println("\nFormato: ax,ay,az,gx,gy,gz");
  Serial.println("Captura: 2s de datos, 5s de pausa\n");
  
  delay(1000);
}

void loop() {
  // Capturar una sesión de datos (2 segundos)
  Serial.println("--- Inicio de captura ---");
  
  for (int i = 0; i < MUESTRAS_POR_SESION; i++) {
    // Leer acelerómetro
    if (IMU.accelerationAvailable()) {
      IMU.readAcceleration(ax, ay, az);
    }
    
    // Leer giroscopio
    if (IMU.gyroscopeAvailable()) {
      IMU.readGyroscope(gx, gy, gz);
    }
    
    // Imprimir en formato CSV
    Serial.print(ax, 3);
    Serial.print(",");
    Serial.print(ay, 3);
    Serial.print(",");
    Serial.print(az, 3);
    Serial.print(",");
    Serial.print(gx, 3);
    Serial.print(",");
    Serial.print(gy, 3);
    Serial.print(",");
    Serial.println(gz, 3);
    
    delay(50);  // 20Hz
  }
  
  // Pausa entre sesiones
  Serial.println("--- Pausa (5s) ---\n");
  delay(PAUSA_ENTRE_SESIONES);
}
