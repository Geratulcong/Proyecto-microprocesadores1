# 🔥 Configuración de Firebase para la Página Web

## Paso 1: Obtener la configuración web de Firebase

1. Ve a [Firebase Console](https://console.firebase.google.com/)
2. Selecciona tu proyecto: **detector-de-caidas-360**
3. Haz clic en el ícono de ⚙️ **Configuración del proyecto**
4. En la sección **"Tus aplicaciones"**, busca la sección **Web**
5. Si no tienes una app web, haz clic en **"Agregar app"** y selecciona el ícono `</>`
6. Copia la configuración que se ve así:

```javascript
const firebaseConfig = {
  apiKey: "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  authDomain: "detector-de-caidas-360.firebaseapp.com",
  projectId: "detector-de-caidas-360",
  storageBucket: "detector-de-caidas-360.appspot.com",
  messagingSenderId: "123456789012",
  appId: "1:123456789012:web:abcdef123456"
};
```

## Paso 2: Actualizar datos.html

1. Abre el archivo: `Proyecto/dist/datos.html`
2. Busca la línea que dice:
   ```javascript
   const firebaseConfig = {
       apiKey: "TU_API_KEY",
   ```
3. Reemplaza **TODO** el objeto `firebaseConfig` con el que copiaste de Firebase Console

## Paso 3: Configurar reglas de Firestore

Para que la página web pueda leer/escribir en Firestore, necesitas configurar las reglas:

1. Ve a **Firestore Database** en Firebase Console
2. Haz clic en la pestaña **Reglas**
3. Reemplaza las reglas con esto:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Permitir lectura/escritura en Historial/Personas/{persona}
    match /Historial/Personas/{persona}/{document=**} {
      allow read, write: if true;
    }
  }
}
```

⚠️ **IMPORTANTE**: Estas reglas son para desarrollo. En producción deberías agregar autenticación.

4. Haz clic en **Publicar**

## Paso 4: Probar la integración

1. Asegúrate de que el servidor Flask esté corriendo:
   ```bash
   python server.py
   ```

2. Abre la página web:
   ```
   http://localhost:8000/datos.html
   ```

3. La tabla debería mostrar las caídas registradas en Firebase

4. Al hacer clic en "Simular caída":
   - Se envía un mensaje de WhatsApp
   - Se guarda la caída en Firebase
   - La tabla se actualiza automáticamente

## Características de la integración:

✅ **Carga automática**: La página carga las últimas 20 caídas de Firebase al inicio
✅ **Actualización en tiempo real**: Se actualiza cada 30 segundos
✅ **Información detallada**: Muestra fecha, ubicación, confianza, y estado
✅ **Sincronización**: Funciona con el simulador de Python

## Solución de problemas

### Error: "Firebase not defined"
- Verifica que los scripts de Firebase se carguen correctamente
- Abre la consola del navegador (F12) para ver errores

### Error: "Missing or insufficient permissions"
- Verifica que las reglas de Firestore estén configuradas correctamente
- Publica las reglas nuevamente

### No se muestran datos
- Verifica que haya caídas registradas en Firebase Console
- Revisa la ruta: `Historial > Personas > Vicente`
