# 🔥 Configuración de Firebase para el Proyecto

## Paso 1: Obtener las credenciales de Firebase

1. **Ve a [Firebase Console](https://console.firebase.google.com/)**
2. Selecciona tu proyecto (o crea uno nuevo)
3. Haz clic en el ícono de ⚙️ **Configuración del proyecto**
4. Ve a la pestaña **Cuentas de servicio**
5. Haz clic en **Generar nueva clave privada**
6. Se descargará un archivo JSON

## Paso 2: Guardar las credenciales

1. Guarda el archivo JSON descargado en la carpeta `Codigos raspberry`
2. Renómbralo a **`firebase-credentials.json`**
3. ⚠️ **IMPORTANTE**: No subas este archivo a Git (ya está en .gitignore)

## Paso 3: Verificar la estructura en Firestore

Tu base de datos debe tener esta estructura:

```
Firestore Database/
└── Historial/
    └── Personas/
        └── Vicente/
            ├── documento1 (caída 1)
            ├── documento2 (caída 2)
            └── ...
```

Cada documento de caída contiene:
- `hora_caida`: Timestamp
- `tipo`: Tipo de caída (Frontal, Lateral, etc.)
- `confianza`: Nivel de confianza del modelo (0-1)
- `ubicacion`: Lugar donde ocurrió
- `aceleracion_max`: Aceleración máxima detectada (G's)
- `estado`: Pendiente/Atendido/Falsa alarma
- `sensor`: Nombre del sensor usado
- `timestamp_servidor`: Timestamp del servidor

## Paso 4: Ejecutar el simulador

```bash
python simular_caida_firebase.py
```

## Opciones del menú

1. **Simular caída única**: Simula una caída de un tipo específico
2. **Simular múltiples caídas**: Simula varias caídas aleatorias
3. **Listar caídas registradas**: Muestra las últimas caídas guardadas
4. **Simular caída para otra persona**: Registra caída para otro usuario
5. **Salir**: Cierra el programa

## Integración con el detector en tiempo real

Para que el detector envíe automáticamente a Firebase cuando detecte una caída real:

1. Agrega `import firebase_admin` al inicio de `detector_tiempo_real.py`
2. Copia la función de conexión a Firebase
3. Llama a la función de guardado cuando se detecte una caída con confianza > 80%

## Solución de problemas

### Error: "No such file or directory: firebase-credentials.json"
- Asegúrate de haber descargado y colocado el archivo en la carpeta correcta

### Error: "Permission denied"
- Verifica que el archivo JSON tenga los permisos correctos en Firebase Console

### Error: "Collection/Document not found"
- Crea manualmente la estructura en Firestore Console si no existe
