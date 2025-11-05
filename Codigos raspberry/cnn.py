import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Dropout, Flatten, Dense
from tensorflow.keras.callbacks import EarlyStopping
import matplotlib.pyplot as plt
import seaborn as sns

# --- CONFIGURACIÓN ---
CSV_PATH = r"c:\Users\gerol\Downloads\Proyecto Microprocesadores\Proyecto-microprocesadores1\Codigos raspberry\datos_sisfall_caidas.csv"
SEP = ";"                # Cambia a ',' si tu CSV usa comas
WINDOW_SIZE = 10         # Número de lecturas por ventana
TEST_SIZE = 0.2
EPOCHS = 30
BATCH_SIZE = 16

# --- 1. Cargar datos ---
df = pd.read_csv(CSV_PATH, sep=SEP)
print("Datos cargados:", df.shape)
print(df.head())

# --- 2. Limpieza básica ---
if 't' in df.columns:
    df = df.drop(columns=['t'])

# Verificar distribución de clases
print("\n📊 Distribución de clases:")
print(df['state'].value_counts().sort_index())

# --- 3. Normalizar sensores ---
features = ['ax', 'ay', 'az', 'gx', 'gy', 'gz']
df[features] = (df[features] - df[features].mean()) / df[features].std()

# --- 4. Crear ventanas ---
X, y = [], []
for i in range(0, len(df) - WINDOW_SIZE):
    window = df.iloc[i:i+WINDOW_SIZE]
    X.append(window[features].values)
    y.append(window['state'].mode()[0])  # clase más frecuente en la ventana

X = np.array(X)
y = np.array(y)

print("\nForma de X:", X.shape)
print("Forma de y:", y.shape)

# --- 5. Separar train/test ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=TEST_SIZE, random_state=42, stratify=y)

# --- 6. Crear modelo CNN binario ---
model = Sequential([
    Conv1D(64, 3, activation='relu', input_shape=(WINDOW_SIZE, len(features))),
    MaxPooling1D(2),
    Dropout(0.3),

    Conv1D(128, 3, activation='relu'),
    MaxPooling1D(2),
    Dropout(0.3),

    Flatten(),
    Dense(64, activation='relu'),
    Dense(1, activation='sigmoid')  # salida binaria (caída/no caída)
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
model.summary()

# --- 7. Entrenar modelo ---
early_stop = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

history = model.fit(
    X_train, y_train,
    validation_data=(X_test, y_test),
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    callbacks=[early_stop],
    verbose=1
)

# --- 8. Evaluar modelo ---
loss, acc = model.evaluate(X_test, y_test)
print(f"\n✅ Pérdida: {loss:.4f} | Precisión: {acc:.4f}")

# --- 9. Matriz de confusión ---
y_pred = (model.predict(X_test) > 0.5).astype(int)

cm = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(5,4))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['No caída', 'Caída'], yticklabels=['No caída', 'Caída'])
plt.xlabel("Predicción")
plt.ylabel("Real")
plt.title("Matriz de Confusión")
plt.show()

print("\n📋 Reporte de clasificación:")
print(classification_report(y_test, y_pred, target_names=['No caída', 'Caída']))

# --- 10. Guardar modelo ---
model.save("modelo_cnn_caidas.h5")
print("\n💾 Modelo guardado como 'modelo_cnn_caidas.h5'")

# --- 11. (Opcional) Graficar entrenamiento ---
plt.figure(figsize=(10,4))
plt.subplot(1,2,1)
plt.plot(history.history['loss'], label='Entrenamiento')
plt.plot(history.history['val_loss'], label='Validación')
plt.title('Pérdida')
plt.legend()

plt.subplot(1,2,2)
plt.plot(history.history['accuracy'], label='Entrenamiento')
plt.plot(history.history['val_accuracy'], label='Validación')
plt.title('Precisión')
plt.legend()
plt.show()
