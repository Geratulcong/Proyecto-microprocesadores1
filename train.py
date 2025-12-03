import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, Dropout
from tensorflow.keras.optimizers import Adam

# ---------------- CONFIGURACIÓN ----------------
DATOS_DIR = Path(__file__).parent / "datos_capturados"
WINDOW_SIZE = 40
OVERLAP = 20
TEST_SIZE = 0.2
EPOCHS = 30
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

print("X shape:", X.shape)  
print("y shape:", y.shape)

# ------------------------------------------------
# 3) Train-test split
# ------------------------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, shuffle=True, random_state=42
)

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
# 6) Guardar modelo
# ------------------------------------------------
model.save("modelo_cnn_imu.h5")
print("Modelo guardado como modelo_cnn_imu.h5")
