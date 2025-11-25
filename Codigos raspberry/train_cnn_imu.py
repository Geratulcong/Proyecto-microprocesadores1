"""
Entrenamiento CNN 1D para datos IMU (binario: 0 normal, 1 caída)

Uso:
    python train_cnn_imu.py --window 40 --overlap 20 --gyro-scale 4.0 --epochs 50

El script lee archivos en la carpeta `datos_limpios` junto al script (igual que el proyecto),
crea ventanas con solapamiento, aplica escalado al giroscopio si se solicita, entrena una CNN 1D
y guarda el modelo + gráficas.
"""

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report
import matplotlib.pyplot as plt
import seaborn as sns

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Dropout, Flatten, Dense
from tensorflow.keras.callbacks import EarlyStopping


def find_data_files(datos_dir: Path):
    if not datos_dir.exists():
        raise FileNotFoundError(f"Directorio de datos no encontrado: {datos_dir}")
    files = list(datos_dir.glob("*.csv"))
    if not files:
        files = list(datos_dir.glob("*.txt"))
    return files


def load_and_window(file_path: Path, cols, window_size, overlap, gyro_scale=1.0, etiqueta=None):
    df = pd.read_csv(file_path)
    # aplicar escalado giroscopio
    if gyro_scale != 1.0:
        gyro_cols = [c for c in cols if 'gx' in c or 'gy' in c or 'gz' in c]
        if gyro_cols:
            df[gyro_cols] = df[gyro_cols] * gyro_scale
    ventanas = []
    etiquetas = []
    for i in range(0, len(df) - window_size + 1, overlap):
        vent = df.iloc[i:i+window_size][cols].values.astype(np.float32)
        ventanas.append(vent)
        etiquetas.append(etiqueta)
    return ventanas, etiquetas


def detect_label_from_name(fname: str):
    name = fname.lower()
    if 'caida' in name or 'fall' in name or name.startswith('f'):
        return 1
    if 'normal' in name or name.startswith('d'):
        # Note: ADL files are Dxx => normal (0)
        return 0
    # fallback: ask or assume 0
    return 0


def build_model(window_size, num_features):
    model = Sequential([
        Conv1D(32, kernel_size=3, activation='relu', input_shape=(window_size, num_features)),
        MaxPooling1D(2),
        Dropout(0.5),
        Flatten(),
        Dense(32, activation='relu'),
        Dropout(0.5),
        Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model


def main():
    p = argparse.ArgumentParser(description='Entrena CNN 1D para IMU (binario)')
    p.add_argument('--window', type=int, default=40, help='Tamaño de ventana (muestras)')
    p.add_argument('--overlap', type=int, default=20, help='Solapamiento entre ventanas')
    p.add_argument('--gyro-scale', type=float, default=1.0, help='Factor para escalar columnas de giroscopio (gx,gy,gz)')
    p.add_argument('--epochs', type=int, default=50)
    p.add_argument('--batch-size', type=int, default=16)
    p.add_argument('--test-size', type=float, default=0.2)
    p.add_argument('--data-dir', type=str, default=str(Path(__file__).parent / 'datos_limpios'))
    p.add_argument('--output-model', type=str, default='modelo_cnn_imu1d.h5')
    args = p.parse_args()

    datos_dir = Path(args.data_dir)
    files = find_data_files(datos_dir)
    print(f"Archivos detectados en {datos_dir}: {len(files)}")

    X_list = []
    y_list = []

    for f in files:
        print(f"Procesando: {f.name}")
        etiqueta = detect_label_from_name(f.name)
        try:
            df = pd.read_csv(f)
        except Exception as e:
            print(f"  No se pudo leer {f.name}: {e}")
            continue
        cols = df.columns.tolist()
        # seleccionar columnas (6 o 12)
        if 'cadera_ax' in cols and 'pierna_ax' in cols:
            sel = [
                'cadera_ax','cadera_ay','cadera_az','cadera_gx','cadera_gy','cadera_gz',
                'pierna_ax','pierna_ay','pierna_az','pierna_gx','pierna_gy','pierna_gz'
            ]
        elif 'cadera_ax' in cols:
            sel = ['cadera_ax','cadera_ay','cadera_az','cadera_gx','cadera_gy','cadera_gz']
        elif 'ax' in cols and 'gx' in cols:
            sel = ['ax','ay','az','gx','gy','gz']
        else:
            print(f"  Columnas no reconocidas en {f.name}: {cols[:10]} ... saltando")
            continue

        ventanas, etiquetas = load_and_window(f, sel, args.window, args.overlap, gyro_scale=args.gyro_scale, etiqueta=etiqueta)
        X_list.extend(ventanas)
        y_list.extend(etiquetas)
        print(f"  Ventanas creadas: {len(ventanas)}")

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int32)

    if len(X) == 0:
        print("No se generaron ventanas. Revisa tus datos.")
        return

    print(f"Total ventanas: {len(X)} | Forma X: {X.shape}")

    # train/test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=args.test_size, random_state=42, stratify=y)
    print(f"Train: {len(X_train)} | Test: {len(X_test)}")

    num_features = X.shape[2]
    model = build_model(args.window, num_features)
    model.summary()

    early_stop = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
    history = model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=args.epochs, batch_size=args.batch_size, callbacks=[early_stop])

    # evaluar
    loss, acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"Test loss: {loss:.4f} | Test acc: {acc:.4f}")

    # predicciones
    y_pred = (model.predict(X_test) > 0.5).astype(int)
    print(classification_report(y_test, y_pred, target_names=['Normal','Caida']))

    # matriz de confusión
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(5,4))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Normal','Caida'], yticklabels=['Normal','Caida'])
    plt.xlabel('Predicción')
    plt.ylabel('Real')
    plt.title('Matriz de confusión')
    plt.tight_layout()
    plt.savefig('matriz_confusion_cnn_imu.png', dpi=150)
    print('Guardada: matriz_confusion_cnn_imu.png')

    # guardar modelo
    model.save(args.output_model)
    print(f"Modelo guardado: {args.output_model}")

    # plot entrenamiento
    plt.figure(figsize=(10,4))
    plt.subplot(1,2,1)
    plt.plot(history.history['loss'], label='train')
    plt.plot(history.history['val_loss'], label='val')
    plt.title('Loss')
    plt.legend()

    plt.subplot(1,2,2)
    plt.plot(history.history['accuracy'], label='train')
    plt.plot(history.history['val_accuracy'], label='val')
    plt.title('Accuracy')
    plt.legend()
    plt.tight_layout()
    plt.savefig('entrenamiento_cnn_imu.png', dpi=150)
    print('Guardada: entrenamiento_cnn_imu.png')


if __name__ == '__main__':
    main()
