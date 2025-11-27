"""
train_cnn_imu_6ch.py

Entrena una 1D-CNN usando únicamente las primeras 6 columnas de los archivos
SisFall (ADXL345 ax,ay,az + ITG3200 gx,gy,gz).

Este script es una copia ligera del script genérico pero fija los canales
por defecto a 0..5 y guarda el modelo en `modelo_cnn_imu_6ch.h5`.
"""

import argparse
from pathlib import Path
import re
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report
import matplotlib.pyplot as plt
import seaborn as sns
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Dropout, Flatten, Dense, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping


def parse_file(path: Path):
    rx = re.compile(r'-?\d+\.?\d*')
    nums = []
    try:
        with path.open('r', encoding='latin-1') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                found = rx.findall(line)
                if not found:
                    continue
                nums.append([float(x) for x in found])
    except Exception as e:
        print(f"Error leyendo {path}: {e}")
        return None
    if not nums:
        return None
    arr = np.array(nums, dtype=np.float32)
    if arr.shape[1] < 6:
        return None
    return arr


def load_dataset(data_dir: Path):
    files = list(data_dir.rglob('*.txt'))
    X_list = []
    y_list = []
    for p in files:
        name = p.name
        if len(name) < 1 or name[0] not in ('D','F'):
            continue
        arr = parse_file(p)
        if arr is None:
            continue
        label = 1 if name[0] == 'F' else 0
        X_list.append(arr)
        y_list.append(label)
    return X_list, y_list


def create_windows(X_list, y_list, window_size=200, overlap=100, channels=None):
    data = []
    labels = []
    step = window_size - overlap
    for arr, label in zip(X_list, y_list):
        arr_use = arr[:, channels] if channels is not None else arr
        if arr_use.shape[0] < window_size:
            continue
        for start in range(0, arr_use.shape[0] - window_size + 1, step):
            win = arr_use[start:start + window_size]
            data.append(win)
            labels.append(label)
    if not data:
        return None, None
    return np.stack(data).astype(np.float32), np.array(labels, dtype=np.int32)


def build_model(input_shape):
    model = Sequential([
        Conv1D(32, kernel_size=5, activation='relu', input_shape=input_shape),
        BatchNormalization(),
        MaxPooling1D(2),
        Dropout(0.3),
        Conv1D(64, kernel_size=3, activation='relu'),
        BatchNormalization(),
        MaxPooling1D(2),
        Dropout(0.3),
        Flatten(),
        Dense(64, activation='relu'),
        Dropout(0.4),
        Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=str, default=str(Path(__file__).parent.parent / 'Codigos y datos'))
    parser.add_argument('--window', type=int, default=200)
    parser.add_argument('--overlap', type=int, default=100)
    parser.add_argument('--test-size', type=float, default=0.2)
    parser.add_argument('--epochs', type=int, default=40)
    parser.add_argument('--batch', type=int, default=32)
    parser.add_argument('--save', type=str, default='modelo_cnn_imu_6ch.h5')
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise SystemExit(f"Directorio no encontrado: {data_dir}")

    X_files, y_files = load_dataset(data_dir)
    if not X_files:
        raise SystemExit('No se encontraron archivos válidos')

    channels = [0,1,2,3,4,5]
    X, y = create_windows(X_files, y_files, window_size=args.window, overlap=args.overlap, channels=channels)
    if X is None:
        raise SystemExit('No se crearon ventanas; prueba reducir window o overlap')

    print(f"Ventanas: {X.shape}, etiquetas: {np.unique(y, return_counts=True)}")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=args.test_size, random_state=42, stratify=y)

    tf.keras.backend.clear_session()
    model = build_model((X.shape[1], X.shape[2]))
    model.summary()

    early = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
    history = model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=args.epochs, batch_size=args.batch, callbacks=[early])

    loss, acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"Test loss={loss:.4f} acc={acc:.4f}")

    y_pred = (model.predict(X_test) > 0.5).astype(int)
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(6,5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Normal','Caida'], yticklabels=['Normal','Caida'])
    plt.xlabel('Predicción')
    plt.ylabel('Real')
    plt.tight_layout()
    plt.savefig('matriz_confusion_6ch.png', dpi=150)
    print('matriz_confusion_6ch.png guardada')

    print('\nReporte:')
    print(classification_report(y_test, y_pred, target_names=['Normal','Caida']))

    model.save(args.save)
    print(f'Modelo guardado en {args.save}')


if __name__ == '__main__':
    main()
