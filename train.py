import numpy as np
import pandas as pd
from pathlib import Path
import sklearn
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, Dropout
import matplotlib.pyplot as plt 
from sklearn.metrics import confusion_matrix 
import tensorflow as tf
print(np.__version__)
print(pd.__version__)
print(plt.__version__)
print(sklearn.__version__)
print(tf.__version__)

# --- CONFIGURACIÓN ---
DATOS_DIR = Path(__file__).parent / "datos_capturados"
WINDOW_SIZE = 40
OVERLAP = 20
TEST_SIZE = 0.2
EPOCHS = 30
BATCH_SIZE = 16
CSV_PATH = "datos.csv"  # Archivo CSV unificado con columnas: cadera_ax,...,cadera_gz,pierna_ax,...,pierna_gz,state

# --- CARGA DE DATOS ---
print(f"📂 Leyendo dataset: {CSV_PATH}")
df = pd.read_csv(CSV_PATH)
print(f"   Filas: {len(df)}, Columnas: {df.columns.tolist()}")

# Extraer características (primeras 12 columnas) y etiquetas (última columna 'state')
feature_cols = df.columns[:-1].tolist()  # Todas menos la última
label_col = df.columns[-1]  # Última columna (state)

X_data = df[feature_cols].values  # Array (n_samples, 12)
y_data = df[label_col].values  # Array (n_samples,)

print(f"   Features shape: {X_data.shape}")
print(f"   Labels shape: {y_data.shape}")
print(f"   Distribución: {np.bincount(y_data.astype(int))}")

# Función para crear ventanas deslizantes con overlap
def crear_ventanas(data, labels, window_size, overlap):
    """Crea ventanas deslizantes de datos con etiquetas correspondientes."""
    ventanas, window_labels = [], []
    stride = window_size - overlap
    for i in range(0, len(data) - window_size + 1, stride):
        ventana = data[i:i+window_size]
        # Usar la etiqueta más frecuente en la ventana como etiqueta de la ventana
        etiqueta = int(np.median(labels[i:i+window_size]))
        ventanas.append(ventana)
        window_labels.append(etiqueta)
    return np.array(ventanas), np.array(window_labels)

# Crear ventanas desde los datos completos
X, y = crear_ventanas(X_data, y_data, WINDOW_SIZE, OVERLAP)
print(f"\n📊 Después de crear ventanas:")
print(f"   X shape: {X.shape}")
print(f"   y shape: {y.shape}")
print(f"   Distribución: {np.bincount(y)}")

# Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=TEST_SIZE, random_state=42)

# --- MODELO CNN 1D ---
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

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

# --- ENTRENAMIENTO ---
history = model.fit(X_train, y_train, epochs=EPOCHS, batch_size=BATCH_SIZE,
                    validation_data=(X_test, y_test))

# --- EVALUACIÓN ---
loss, acc = model.evaluate(X_test, y_test)
print(f"Accuracy en test: {acc:.2f}")

# Guardar el modelo
model.save("modelo_caidas.h5")

#MAtrz de confusión
   
y_pred = (model.predict(X_test) > 0.5).astype("int32")
cm = confusion_matrix(y_test, y_pred)
print("Matriz de confusión:")
print(cm)

# Gráficos de pérdida y precisión
plt.figure(figsize=(12, 4))
plt.subplot(1, 2, 1)
plt.plot(history.history['loss'], label='Train Loss')
plt.plot(history.history['val_loss'], label='Val Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.title('Pérdida')

plt.subplot(1, 2, 2)
plt.plot(history.history['accuracy'], label='Train Accuracy')
plt.plot(history.history['val_accuracy'], label='Val Accuracy')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend()
plt.title('Precisión')
plt.tight_layout()
plt.savefig('training_history.png')
print("\n📈 Gráfico guardado en: training_history.png")

# Mostrar matriz de confusión
plt.figure(figsize=(6, 5))
plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
plt.title('Matriz de Confusión')
plt.colorbar()
tick_marks = np.arange(2)
plt.xticks(tick_marks, ['No Caída', 'Caída'])
plt.yticks(tick_marks, ['No Caída', 'Caída'])
plt.ylabel('Verdadero')
plt.xlabel('Predicho')
for i in range(2):
    for j in range(2):
        plt.text(j, i, str(cm[i, j]), ha="center", va="center", color="white" if cm[i, j] > cm.max()/2 else "black")
plt.tight_layout()
plt.savefig('confusion_matrix.png')
print("📊 Matriz de confusión guardada en: confusion_matrix.png\n")