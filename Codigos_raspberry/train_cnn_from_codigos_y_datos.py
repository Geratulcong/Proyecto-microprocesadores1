"""
train_cnn_from_codigos_y_datos.py

Lee los archivos de la carpeta `Codigos y datos` (recursivo), extrae ventanas
de tamaño configurable y entrena una red 1D-CNN para detección binaria (caída vs ADL).

Uso (ejemplo):
  python train_cnn_from_codigos_y_datos.py --data-dir "..\Codigos y datos" --window 200 --overlap 100

Salida:
  - modelo guardado en `modelo_cnn_imu.h5`
  - gráficos: `entrenamiento_cnn.png`, `matriz_confusion_cnn.png`

Notas:
  - Clasifica archivos cuyo nombre empieza por 'F' como caída (label=1) y
    por 'D' como ADL/normal (label=0).
  - Para parsear cada línea se extraen todos los enteros/decimales con regex
    (funciona con formatos separados por comas y/o con ';' al final).
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
    """Devuelve array numpy (n_samples, n_features) o None si no válido."""
    nums = []
    rx = re.compile(r'-?\d+\.?\d*')
    try:
        with path.open('r', encoding='latin-1') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                found = rx.findall(line)
                if not found:
                    continue
                # convertir a float
                row = [float(x) for x in found]
                nums.append(row)
    except Exception as e:
        print(f"Error leyendo {path}: {e}")
        return None

    if not nums:
        return None

    arr = np.array(nums, dtype=np.float32)
    # Queremos al menos 3 columnas (mínimo razonable) y preferiblemente 9
    if arr.shape[1] < 3:
        return None
    return arr


def load_dataset(data_dir: Path, whitelist_prefixes=('D', 'F')):
    """Carga todos los .txt recursivamente y retorna lista de arrays y labels."""
    files = list(data_dir.rglob('*.txt'))
    X_list = []
    y_list = []
    print(f"Buscando archivos en: {data_dir} -> encontrados {len(files)} .txt")

    for p in files:
        name = p.name
        if len(name) < 1 or name[0] not in whitelist_prefixes:
            # ignorar archivos que no empiecen por D o F
            continue
        arr = parse_file(p)
        if arr is None:
            continue
        label = 1 if name[0] == 'F' else 0
        X_list.append(arr)
        y_list.append(label)

    print(f"Archivos útiles: {len(X_list)}")
    return X_list, y_list


def create_windows(X_list, y_list, window_size=200, overlap=100, selected_channels=None):
    """Convierte cada array de sensores en ventanas con solapamiento.
    selected_channels: lista de índices de columnas a usar (None -> usar todas)
    """
    data = []
    labels = []
    step = window_size - overlap
    for arr, label in zip(X_list, y_list):
        if selected_channels is not None:
            arr_use = arr[:, selected_channels]
        else:
            arr_use = arr
        if arr_use.shape[0] < window_size:
            continue
        for start in range(0, arr_use.shape[0] - window_size + 1, step):
            win = arr_use[start:start + window_size]
            data.append(win)
            labels.append(label)
    if not data:
        return None, None
    X = np.stack(data).astype(np.float32)
    y = np.array(labels, dtype=np.int32)
    return X, y


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
    parser.add_argument('--data-dir', type=str, default=str(Path(__file__).parent.parent / 'Codigos y datos'), help='Carpeta que contiene los .txt')
    parser.add_argument('--window', type=int, default=200, help='Tamaño de ventana (muestras)')
    parser.add_argument('--overlap', type=int, default=100, help='Solapamiento entre ventanas')
    parser.add_argument('--test-size', type=float, default=0.2, help='Fracción test')
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--batch', type=int, default=32)
    parser.add_argument('--channels', type=str, default=None, help='Índices de columnas a usar (coma separada), por ejemplo 0,1,2')
    parser.add_argument('--save', type=str, default='modelo_cnn_imu.h5')
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise SystemExit(f"Directorio no encontrado: {data_dir}")

    X_files, y_files = load_dataset(data_dir)
    if not X_files:
        raise SystemExit("No se han encontrado archivos válidos para entrenar.")

    selected_channels = None
    if args.channels:
        selected_channels = [int(x) for x in args.channels.split(',')]

    X, y = create_windows(X_files, y_files, window_size=args.window, overlap=args.overlap, selected_channels=selected_channels)
    if X is None:
        raise SystemExit("No se pudieron crear ventanas con los parámetros dados (window/overlap demasiado grandes?).")

    print(f"Ventanas creadas: {X.shape} clases: {np.unique(y, return_counts=True)}")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=args.test_size, random_state=42, stratify=y)

    tf.keras.backend.clear_session()
    model = build_model(input_shape=(X.shape[1], X.shape[2]))
    model.summary()

    early = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

    history = model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=args.epochs, batch_size=args.batch, callbacks=[early])

    # Evaluación
    loss, acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"Test loss={loss:.4f} acc={acc:.4f}")

    y_pred = (model.predict(X_test) > 0.5).astype(int)
    cm = confusion_matrix(y_test, y_pred)

    plt.figure(figsize=(6,5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Normal','Caida'], yticklabels=['Normal','Caida'])
    plt.xlabel('Predicción')
    plt.ylabel('Real')
    plt.tight_layout()
    plt.savefig('matriz_confusion_cnn.png', dpi=150)
    print('Matriz de confusión guardada: matriz_confusion_cnn.png')

    print('\nReporte de clasificación:')
    print(classification_report(y_test, y_pred, target_names=['Normal','Caida']))

    model.save(args.save)
    print(f'Modelo guardado en: {args.save}')

    # Gráficos de entrenamiento
    plt.figure(figsize=(10,4))
    plt.subplot(1,2,1)
    plt.plot(history.history.get('loss', []), label='train_loss')
    plt.plot(history.history.get('val_loss', []), label='val_loss')
    plt.legend(); plt.title('Loss')

    plt.subplot(1,2,2)
    plt.plot(history.history.get('accuracy', []), label='train_acc')
    plt.plot(history.history.get('val_accuracy', []), label='val_acc')
    plt.legend(); plt.title('Accuracy')

    plt.tight_layout()
    plt.savefig('entrenamiento_cnn.png', dpi=150)
    print('Gráfico de entrenamiento guardado: entrenamiento_cnn.png')


if __name__ == '__main__':
    main()
