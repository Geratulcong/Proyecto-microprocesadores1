import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, Dropout
from tensorflow.keras.utils import to_categorical

# --- CONFIGURACIÓN ---
DATOS_DIR = Path(__file__).parent / "datos_capturados"
WINDOW_SIZE = 40
OVERLAP = 20
TEST_SIZE = 0.2
EPOCHS = 30
BATCH_SIZE = 16

# --- CARGA DE DATOS ---
caidas = pd.read_csv("Codigos_raspberry\datos_capturados\datos_capturados_caidas (1).csv")
normales = pd.read_csv("Codigos_raspberry\datos_capturados\datos_capturados_normales.csv")

# Convertir a numpy
X_caidas = caidas.values
X_normales = normales.values

# Función para crear ventanas
def crear_ventanas(data, etiqueta):
    ventanas, labels = [], []
    for i in range(0, len(data) - WINDOW_SIZE, OVERLAP):
        ventana = data[i:i+WINDOW_SIZE]
        ventanas.append(ventana)
        labels.append(etiqueta)
    return np.array(ventanas), np.array(labels)

Xc, yc = crear_ventanas(X_caidas, 1)
Xn, yn = crear_ventanas(X_normales, 0)

# Concatenar
X = np.concatenate([Xc, Xn], axis=0)
y = np.concatenate([yc, yn], axis=0)

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
model.save(DATOS_DIR / "modelo_caidas.h5")

#MAtrz de confusión
from sklearn.metrics import confusion_matrix    
y_pred = (model.predict(X_test) > 0.5).astype("int32")
cm = confusion_matrix(y_test, y_pred)
print("Matriz de confusión:")
print(cm)

#Perdidas y precisión
import matplotlib.pyplot as plt 
plt.figure(figsize=(12, 4))
plt.subplot(1, 2, 1)