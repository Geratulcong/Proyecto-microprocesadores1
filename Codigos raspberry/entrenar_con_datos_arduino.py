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
EPOCHS = 50
BATCH_SIZE = 16

print("╔════════════════════════════════════════════════╗")
print("║   Entrenamiento CNN para detección de caídas  ║")
print("╚════════════════════════════════════════════════╝\n")

# --- 1. CARGAR DATOS ---
print("📂 Buscando archivos en:", DATOS_DIR)

if not DATOS_DIR.exists():
    print(f"❌ Error: Ejecuta primero 'limpiar_datos.py'")
    exit(1)

archivos = list(DATOS_DIR.glob("*.txt"))
if not archivos:
    print(f"❌ No se encontraron archivos .txt en '{DATOS_DIR}'")
    exit(1)

print(f"📄 Archivos encontrados: {len(archivos)}\n")

# Clasificar archivos según su nombre
print("🔖 Clasifica tus archivos:")
print("   Escribe 0 para NORMAL (sin caída)")
print("   Escribe 1 para CAÍDA\n")

datos_totales = []
etiquetas_totales = []

for archivo in archivos:
    print(f"📄 {archivo.name}")
    while True:
        etiqueta = input("   Etiqueta (0=normal, 1=caída): ").strip()
        if etiqueta in ['0', '1']:
            etiqueta = int(etiqueta)
            break
        print("   ❌ Valor inválido. Usa 0 o 1")
    
    # Cargar archivo
    try:
        df = pd.read_csv(archivo)
        print(f"   ✅ Cargado: {len(df)} muestras\n")
        
        # Crear ventanas con solapamiento
        for i in range(0, len(df) - WINDOW_SIZE + 1, OVERLAP):
            ventana = df.iloc[i:i+WINDOW_SIZE][['ax','ay','az','gx','gy','gz']].values
            datos_totales.append(ventana)
            etiquetas_totales.append(etiqueta)
    
    except Exception as e:
        print(f"   ❌ Error: {e}\n")

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

# --- 3. CREAR MODELO CNN ---
print("\n🧠 Creando modelo CNN 1D...")
model = Sequential([
    Conv1D(32, kernel_size=3, activation='relu', input_shape=(WINDOW_SIZE, 6)),
    MaxPooling1D(2),
    Dropout(0.3),
    
    Conv1D(64, kernel_size=3, activation='relu'),
    MaxPooling1D(2),
    Dropout(0.3),
    
    Flatten(),
    Dense(64, activation='relu'),
    Dropout(0.4),
    Dense(1, activation='sigmoid')  # Binario: 0=normal, 1=caída
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
model.summary()

# --- 4. ENTRENAR ---
print("\n🚀 Entrenando modelo...")
early_stop = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

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
MODEL_PATH = "modelo_caidas_arduino.h5"
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
