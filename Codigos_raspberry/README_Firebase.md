# Sistema de Alertas Firebase - Detector de Caídas

## ✅ Cambios implementados

### 📝 Archivo: `receptor_dual_ble.py`

**Nuevas funcionalidades:**

1. **Integración con Firebase**
   - URL: `https://detector-de-caidas-360-default-rtdb.firebaseio.com/alertas.json`
   - Envía alertas automáticas cuando detecta caída con ≥95% de confianza

2. **Sistema de Cooldown**
   - Evita múltiples alertas de la misma caída
   - Intervalo: **5 segundos** entre alertas
   - Muestra tiempo restante si intenta enviar antes

3. **Umbral de Detección**
   - Configurado al **95%** (antes era 50%)
   - Solo alerta cuando el modelo está muy seguro

### 📊 Datos enviados a Firebase

Cada alerta incluye:
```json
{
  "timestamp": "2025-11-12T13:22:53.893313",
  "probabilidad": 0.97,
  "sensor_cadera": {
    "ax": 0.123, "ay": -0.456, "az": 0.987,
    "gx": 1.23, "gy": -4.56, "gz": 7.89
  },
  "sensor_pierna": {
    "ax": 0.234, "ay": -0.567, "az": 1.012,
    "gx": 2.34, "gy": -5.67, "gz": 8.90
  }
}
```

### ⚙️ Configuración actual

| Parámetro | Valor |
|-----------|-------|
| Umbral de detección | 95% |
| Cooldown entre alertas | 5 segundos |
| Frecuencia de muestreo | 20 Hz (50ms) |
| Frecuencia de predicción | 4 Hz (250ms) |
| Tamaño de ventana | 40 muestras (2 segundos) |

### 🎯 Comportamiento del sistema

**Escenario 1: Primera caída detectada**
```
🔴 CAÍDA (97.3%)
   ✅ Alerta enviada a Firebase
   🔗 ID: -Odss7GfY2E14WxOXR37
```

**Escenario 2: Detección continua (dentro de 5s)**
```
🔴 CAÍDA (98.1%)
   ⏳ Cooldown activo - 3.2s restantes
```

**Escenario 3: Nueva caída (después de 5s)**
```
🔴 CAÍDA (96.5%)
   ✅ Alerta enviada a Firebase
   🔗 ID: -Odss8HgZ3F25YxPZS48
```

### 🧪 Archivos de prueba creados

1. **`test_firebase.py`**
   - Verifica conexión con Firebase
   - Envía alerta de prueba
   - Muestra ID generado

### 🚀 Cómo usar

1. **Probar Firebase:**
   ```powershell
   python test_firebase.py
   ```

2. **Ejecutar detector:**
   ```powershell
   python receptor_dual_ble.py
   ```

3. **Ver alertas en Firebase:**
   - Consola: https://console.firebase.google.com/project/detector-de-caidas-360/database
   - API directa: https://detector-de-caidas-360-default-rtdb.firebaseio.com/alertas.json

### 🔧 Ajustes disponibles

Para modificar la configuración, edita las líneas 26-30 de `receptor_dual_ble.py`:

```python
# Cambiar umbral (50-99%)
UMBRAL_CAIDA = 0.95

# Cambiar cooldown (en segundos)
COOLDOWN_ALERTAS = 5.0

# Cambiar URL de Firebase
FIREBASE_URL = "tu-url.firebaseio.com/alertas.json"
```

### 📱 Próximos pasos sugeridos

- [ ] Agregar envío de WhatsApp cuando se envía a Firebase
- [ ] Crear dashboard web para visualizar alertas en tiempo real
- [ ] Agregar geolocalización a las alertas
- [ ] Implementar historial de caídas por usuario
- [ ] Agregar notificaciones push a app móvil

---

**Fecha de implementación:** 12 de noviembre de 2025  
**Estado:** ✅ Operativo y probado
