"""
Script para entrenar CNN 1D con datos capturados del Arduino
Lee archivos limpios, crea ventanas y entrena modelo
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Dropout, Flatten, Dense
from tensorflow.keras.callbacks import EarlyStopping
import matplotlib.pyplot as plt
import seaborn as sns

# --- CONFIGURACIÓN ---
DATOS_DIR = Path(__file__).parent / "datos_limpios"
WINDOW_SIZE = 40  # 40 muestras = 2 segundos a 20Hz
OVERLAP = 20  # Solapamiento de ventanas (50%)
TEST_SIZE = 0.2
EPOCHS = 15
BATCH_SIZE = 16


# Rutas absolutas (AJUSTA ESTO A TU INSTALACIÓN)
RUTA_NORMAL = Path("/home/runner/work/Proyecto-microprocesadores1/Proyecto-microprocesadores1/Codigos_raspberry/datos_limpios/datos_capturados_normales.csv")
RUTA_CAIDA  = Path("/home/runner/work/Proyecto-microprocesadores1/Proyecto-microprocesadores1/Codigos_raspberry/datos_limpios/datos_capturados_caidas.csv")

archivos = [
    (RUTA_NORMAL, 0),   # etiqueta 0 → NORMAL
    (RUTA_CAIDA,  1)    # etiqueta 1 → CAÍDA
]

datos_totales = []
etiquetas_totales = []

print("📂 Cargando archivos fijos...")

for ruta, etiqueta in archivos:
    print(f"\n📄 Archivo: {ruta.name}  → Etiqueta: {etiqueta}")

    if not ruta.exists():
        print(f"❌ ERROR: No existe el archivo: {ruta}")
        exit(1)

    # Cargar CSV
    df = pd.read_csv(ruta)
    columnas = df.columns.tolist()

    # Detectar columnas disponibles
    if 'cadera_ax' in columnas and 'pierna_ax' in columnas:
        cols = [
            'cadera_ax','cadera_ay','cadera_az','cadera_gx','cadera_gy','cadera_gz',
            'pierna_ax','pierna_ay','pierna_az','pierna_gx','pierna_gy','pierna_gz'
        ]
        print("   → Usando datos de CADERA + PIERNA (12 features)")
    elif 'cadera_ax' in columnas:
        cols = ['cadera_ax','cadera_ay','cadera_az','cadera_gx','cadera_gy','cadera_gz']
        print("   → Usando datos del sensor CADERA (6 features)")
    else:
        cols = ['ax','ay','az','gx','gy','gz']
        print("   → Usando sensor único (6 features)")

    print(f"   → Total muestras: {len(df)}")

    # Escalar giroscopio
    cols_giro = [c for c in cols if 'gx' in c or 'gy' in c or 'gz' in c]
    df[cols_giro] = df[cols_giro] * 4.0
    print(f"   → Giroscopio escalado x4: {cols_giro}")

    # Crear ventanas
    ventanas_creadas = 0
    for i in range(0, len(df) - WINDOW_SIZE + 1, OVERLAP):
        ventana = df.iloc[i:i+WINDOW_SIZE][cols].values
        datos_totales.append(ventana)
        etiquetas_totales.append(etiqueta)
        ventanas_creadas += 1

    print(f"   → Ventanas creadas: {ventanas_creadas}")

# Convertir a arrays
X = np.array(datos_totales, dtype=np.float32)
y = np.array(etiquetas_totales, dtype=np.int32)

print(f"\n📊 Datos preparados:")
print(f"   Total de ventanas: {len(X)}")
print(f"   Forma de X: {X.shape}")
print(f"   Distribución de clases:")
unique, counts = np.unique(y, return_counts=True)
for clase, count in zip(unique, counts):
    nombre = "Normal" if clase == 0 else "Caída"
    print(f"      {nombre}: {count} ventanas ({count/len(y)*100:.1f}%)")

# --- 2. TRAIN/TEST SPLIT ---
print(f"\n✂️ Dividiendo datos (test={TEST_SIZE*100:.0f}%)...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, random_state=42, stratify=y
)
print(f"   Train: {len(X_train)} ventanas")
print(f"   Test: {len(X_test)} ventanas")

# --- 3. CREAR MODELO CNN SIMPLIFICADO ---
# Detectar número de features automáticamente
num_features = X.shape[2]  # Puede ser 6 o 12
print(f"\n🧠 Creando modelo CNN 1D para {num_features} features...")
print("   Modelo simplificado (menos parámetros, más regularización)\n")

model = Sequential([
    Conv1D(32, 3, activation='relu', padding='same', input_shape=(WINDOW_SIZE, num_features)),
    MaxPooling1D(2),
    
    Conv1D(64, 3, activation='relu', padding='same'),
    MaxPooling1D(2),
    Dropout(0.4),
    
    Flatten(),
    Dense(64, activation='relu'),
    Dropout(0.5),
    
    Dense(1, activation='sigmoid')
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
model.summary()

# --- 4. ENTRENAR ---
print("\n🚀 Entrenando modelo...")
print("💡 Modelo simplificado para reducir overfitting:")
print("   - Solo 1 capa Conv1D (en vez de 2)")
print("   - 16 filtros (en vez de 32+64)")
print("   - Dense de 32 neuronas (en vez de 64)")
print("   - Dropout aumentado a 0.5\n")

early_stop = EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True)

history = model.fit(
    X_train, y_train,
    validation_data=(X_test, y_test),
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    callbacks=[early_stop],
    verbose=1
)

# --- 5. EVALUAR ---
print("\n📈 Evaluando modelo...")
loss, acc = model.evaluate(X_test, y_test)
print(f"\n✅ Pérdida: {loss:.4f} | Precisión: {acc:.4f}")

# Predicciones
y_pred = (model.predict(X_test) > 0.5).astype(int)

# Matriz de confusión
cm = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(6,5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['Normal', 'Caída'],
            yticklabels=['Normal', 'Caída'])
plt.xlabel("Predicción")
plt.ylabel("Real")
plt.title("Matriz de Confusión")
plt.tight_layout()
plt.savefig('matriz_confusion_arduino.png', dpi=150)
print("💾 Matriz guardada: matriz_confusion_arduino.png")

# Reporte
print("\n📋 Reporte de clasificación:")
print(classification_report(y_test, y_pred, target_names=['Normal', 'Caída']))

# --- 6. GUARDAR MODELO ---
MODEL_PATH = "modelo_cnn_imu.h5"
model.save(MODEL_PATH)
print(f"\n💾 Modelo guardado: {MODEL_PATH}")

# Gráfico de entrenamiento
plt.figure(figsize=(12,4))
plt.subplot(1,2,1)
plt.plot(history.history['loss'], label='Train')
plt.plot(history.history['val_loss'], label='Val')
plt.title('Pérdida')
plt.xlabel('Época')
plt.ylabel('Loss')
plt.legend()
plt.grid(True)

plt.subplot(1,2,2)
plt.plot(history.history['accuracy'], label='Train')
plt.plot(history.history['val_accuracy'], label='Val')
plt.title('Precisión')
plt.xlabel('Época')
plt.ylabel('Accuracy')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig('entrenamiento_arduino.png', dpi=150)
print(f"💾 Gráfico guardado: entrenamiento_arduino.png")

print("\n✅ ¡Entrenamiento completado!")
