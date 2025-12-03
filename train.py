import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, Dropout
from tensorflow.keras.optimizers import Adam
import matplotlib.pyplot as plt

# ---------------- CONFIGURACIÓN ----------------
DATOS_DIR = Path(__file__).parent / "datos_capturados"
WINDOW_SIZE = 40
OVERLAP = 20
TEST_SIZE = 0.2
EPOCHS = 15
BATCH_SIZE = 16
CSV_PATH = "datos.csv"

# ------------------------------------------------
# 1) Cargar CSV
# ------------------------------------------------
df = pd.read_csv(CSV_PATH, dtype=str)

# Columnas
FEATURE_COLS = [
    "cadera_ax","cadera_ay","cadera_az",
    "cadera_gx","cadera_gy","cadera_gz",
    "pierna_ax","pierna_ay","pierna_az",
    "pierna_gx","pierna_gy","pierna_gz"
]
for col in FEATURE_COLS:
    df[col] = pd.to_numeric(df[col], errors='coerce')
df["state"] = pd.to_numeric(df["state"], errors='coerce').astype("Int64")

#NaN
df = df.dropna()
data = df[FEATURE_COLS].astype(float).values
labels = df["state"].astype(int).values

# ------------------------------------------------
# 2) Crear ventanas (sliding windows)
# ------------------------------------------------
def create_windows(data, labels, window_size, overlap):
    X, y = [], []
    step = window_size - overlap

    for i in range(0, len(data) - window_size + 1, step):
        window = data[i:i + window_size]
        X.append(window)

        # La etiqueta de la ventana será la etiqueta mayoritaria
        window_label = labels[i:i + window_size]
        y.append(int(np.round(np.mean(window_label))))

    return np.array(X), np.array(y)

X, y = create_windows(data, labels, WINDOW_SIZE, OVERLAP)

print("\n" + "="*60)
print("INFORMACIÓN DEL DATASET")
print("="*60)
print(f"X shape: {X.shape}")  
print(f"y shape: {y.shape}")
print(f"\n📊 Distribución de clases en dataset completo:")
class_counts = np.bincount(y)
print(f"   Clase 0 (No Caída): {class_counts[0]} ({class_counts[0]/len(y)*100:.1f}%)")
print(f"   Clase 1 (Caída):    {class_counts[1]} ({class_counts[1]/len(y)*100:.1f}%)")

# Gráfico de distribución de clases
fig, axes = plt.subplots(1, 1, figsize=(8, 5))
axes.bar(['No Caída', 'Caída'], class_counts, color=['green', 'red'], width=0.5)
axes.set_title('Distribución de Clases (Dataset Completo)', fontsize=14, fontweight='bold')
axes.set_ylabel('Cantidad', fontsize=12)
for i, v in enumerate(class_counts):
    axes.text(i, v + 20, str(v), ha='center', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig('class_distribution.png', dpi=100)
print("\n✅ Gráfico de distribución guardado: class_distribution.png")
plt.close()

# ------------------------------------------------
# 3) Train-test split
# ------------------------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, shuffle=True, random_state=42
)

print(f"\n🔀 Split Train/Test ({TEST_SIZE*100:.0f}%):")
print(f"   Entrenamiento: {len(X_train)} muestras")
print(f"      Clase 0: {np.sum(y_train==0)} | Clase 1: {np.sum(y_train==1)}")
print(f"   Test: {len(X_test)} muestras")
print(f"      Clase 0: {np.sum(y_test==0)} | Clase 1: {np.sum(y_test==1)}")

# ------------------------------------------------
# 4) Crear modelo CNN 1D
# ------------------------------------------------
model = Sequential([
    Conv1D(32, kernel_size=3, activation='relu', input_shape=(WINDOW_SIZE, 12)),
    MaxPooling1D(pool_size=2),

    Conv1D(64, kernel_size=3, activation='relu'),
    MaxPooling1D(pool_size=2),

    Flatten(),
    Dense(64, activation='relu'),
    Dropout(0.5),

    Dense(1, activation='sigmoid')
])

model.compile(optimizer=Adam(),
              loss='binary_crossentropy',
              metrics=['accuracy'])

model.summary()

# ------------------------------------------------
# 5) Entrenar
# ------------------------------------------------
history = model.fit(
    X_train, y_train,
    validation_data=(X_test, y_test),
    epochs=EPOCHS,
    batch_size=BATCH_SIZE
)

# ------------------------------------------------
# 6) Evaluación en test
# ------------------------------------------------
print("\n" + "="*60)
print("EVALUACIÓN")
print("="*60)

loss, accuracy = model.evaluate(X_test, y_test, verbose=0)
print(f"\n📈 Métricas en Test Set:")
print(f"   Loss:     {loss:.4f}")
print(f"   Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")

# Predicciones
y_pred = (model.predict(X_test, verbose=0) > 0.5).astype(int).flatten()

# Matriz de confusión
cm = confusion_matrix(y_test, y_pred)
print(f"\n🔍 Matriz de Confusión:")
print(f"   [[TN={cm[0,0]} FP={cm[0,1]}]")
print(f"    [FN={cm[1,0]} TP={cm[1,1]}]]")

# Reporte de clasificación
print(f"\n📊 Reporte de Clasificación:")
print(classification_report(y_test, y_pred, target_names=['No Caída', 'Caída']))

# Gráficos de Entrenamiento
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Loss
axes[0].plot(history.history['loss'], label='Train Loss', linewidth=2, marker='o')
axes[0].plot(history.history['val_loss'], label='Val Loss', linewidth=2, marker='s')
axes[0].set_xlabel('Epoch', fontsize=12)
axes[0].set_ylabel('Loss', fontsize=12)
axes[0].set_title('Pérdida (Loss) durante Entrenamiento', fontsize=13, fontweight='bold')
axes[0].legend(fontsize=11)
axes[0].grid(True, alpha=0.3)

# Accuracy
axes[1].plot(history.history['accuracy'], label='Train Accuracy', linewidth=2, marker='o')
axes[1].plot(history.history['val_accuracy'], label='Val Accuracy', linewidth=2, marker='s')
axes[1].set_xlabel('Epoch', fontsize=12)
axes[1].set_ylabel('Accuracy', fontsize=12)
axes[1].set_title('Precisión (Accuracy) durante Entrenamiento', fontsize=13, fontweight='bold')
axes[1].legend(fontsize=11)
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('training_metrics.png', dpi=100)
print("\n✅ Gráfico de métricas de entrenamiento guardado: training_metrics.png")
plt.close()

# Matriz de Confusión Visualizada
fig, ax = plt.subplots(figsize=(8, 6))
im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
ax.figure.colorbar(im, ax=ax)
ax.set(xticks=np.arange(cm.shape[1]),
       yticks=np.arange(cm.shape[0]),
       xticklabels=['No Caída', 'Caída'],
       yticklabels=['No Caída', 'Caída'],
       ylabel='Verdadero',
       xlabel='Predicho',
       title='Matriz de Confusión')

# Añadir texto con valores
for i in range(cm.shape[0]):
    for j in range(cm.shape[1]):
        color = 'white' if cm[i, j] > cm.max() / 2 else 'black'
        ax.text(j, i, format(cm[i, j], 'd'),
                ha="center", va="center", color=color, fontsize=14, fontweight='bold')

plt.tight_layout()
plt.savefig('confusion_matrix.png', dpi=100)
print("✅ Matriz de confusión guardada: confusion_matrix.png\n")
plt.close()


model.save("modelo_cnn_imu.h5")
print("Modelo guardado como modelo_cnn_imu.h5")