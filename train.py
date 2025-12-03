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
WINDOW_SIZE = 40   # 40 muestras = 2 segundos a 20Hz
OVERLAP = 20       # Solapamiento (50%)
TEST_SIZE = 0.2
EPOCHS = 50
BATCH_SIZE = 16

print("\n╔══════════════════════════════════════════════╗")
print("║        ENTRENAMIENTO CNN DETECCIÓN CAIDAS    ║")
print("╚══════════════════════════════════════════════╝\n")

# --- 1. CARGAR CSV ---
df = pd.read_csv("datos.csv")
print(f"   ✅ CSV cargado: {len(df)} muestras\n")

# Columnas a usar
cols = [
    'cadera_ax','cadera_ay','cadera_az',
    'cadera_gx','cadera_gy','cadera_gz',
    'pierna_ax','pierna_ay','pierna_az',
    'pierna_gx','pierna_gy','pierna_gz'
]

# Etiqueta
label_col = 'state'

# Escalar giroscopios x4 para resaltar movimientos bruscos
cols_giro = [c for c in cols if 'gx' in c or 'gy' in c or 'gz' in c]
df[cols_giro] = df[cols_giro] * 4.0
print("   ⚙️ Giros escalados x4\n")

# --- 2. CREAR VENTANAS ---
datos_totales = []
etiquetas_totales = []

for i in range(0, len(df) - WINDOW_SIZE + 1, OVERLAP):
    ventana = df.iloc[i:i+WINDOW_SIZE][cols].values
    etiqueta = int(df[label_col].iloc[i:i+WINDOW_SIZE].mean() > 0.5)  # mayoría
    datos_totales.append(ventana)
    etiquetas_totales.append(etiqueta)

print(f" 📊 Ventanas creadas: {len(datos_totales)}\n")

# Convertir a arrays
X = np.array(datos_totales, dtype=np.float32)
y = np.array(etiquetas_totales, dtype=np.int32)

print("📊 Datos preparados:")
print(f"   Total de ventanas: {len(X)}")
print(f"   Forma de X: {X.shape}")

unique, counts = np.unique(y, return_counts=True)
for u, c in zip(unique, counts):
    print(f"   Clase {u}: {c} ({c/len(y)*100:.1f}%)")

# --- 3. TRAIN/TEST SPLIT ---
print("\n✂️ Dividiendo datos...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, stratify=y, random_state=42
)

print(f"   Train: {len(X_train)} ventanas")
print(f"   Test:  {len(X_test)} ventanas\n")

# --- 4. CREAR MODELO CNN ---
num_features = X.shape[2]
print(f"🧠 Modelo CNN (features={num_features})\n")

model = Sequential([
    Conv1D(16, 3, activation='relu', input_shape=(WINDOW_SIZE, num_features)),
    MaxPooling1D(2),
    Dropout(0.5),

    Flatten(),
    Dense(32, activation='relu'),
    Dropout(0.5),
    Dense(1, activation='sigmoid')
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
model.summary()

# --- 5. ENTRENAR ---
print("\n🚀 Entrenando modelo...\n")

early_stop = EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True)

history = model.fit(
    X_train, y_train,
    validation_data=(X_test, y_test),
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    callbacks=[early_stop],
    verbose=1
)

# --- 6. EVALUACIÓN ---
print("\n📈 Evaluando modelo...")
loss, acc = model.evaluate(X_test, y_test)
print(f"   ✔ Loss: {loss:.4f} | Accuracy: {acc:.4f}")

y_pred = (model.predict(X_test) > 0.5).astype(int)

cm = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(6,5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['Normal','Caída'],
            yticklabels=['Normal','Caída'])
plt.title("Matriz de Confusión")
plt.tight_layout()
plt.savefig("confusion_matrix.png", dpi=150)

print("💾 Matriz guardada: confusion_matrix.png")

# Reporte
print("\n📋 Reporte de clasificación:")
print(classification_report(y_test, y_pred, target_names=['Normal','Caída']))

# --- 7. GUARDAR MODELO ---
model.save("modelo_caidas_imu.h5")
print("\n💾 Modelo guardado: modelo_caidas_arduino.h5")

# --- 8. GRÁFICOS DE ENTRENAMIENTO ---
plt.figure(figsize=(12,4))

plt.subplot(1,2,1)
plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title("Pérdida")
plt.legend(['Train','Val'])

plt.subplot(1,2,2)
plt.plot(history.history['accuracy'])
plt.plot(history.history['val_accuracy'])
plt.title("Precisión")
plt.legend(['Train','Val'])

plt.tight_layout()
plt.savefig("training_metrics.png", dpi=150)
print("\n💾 Guardado: training_metrics.png")

print("\n✅ ENTRENAMIENTO COMPLETADO\n")