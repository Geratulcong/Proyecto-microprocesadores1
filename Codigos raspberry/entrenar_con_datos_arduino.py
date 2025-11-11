"""
Script para entrenar CNN 1D con datos capturados del Arduino
Lee archivos CSV (cadera + pierna), crea ventanas y entrena modelo
Ventanas de 500 muestras (2.5s a 200Hz según estándar SisFall)
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import confusion_matrix, classification_report, roc_curve, auc, precision_recall_curve, average_precision_score
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Dropout, Flatten, Dense, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam
import matplotlib.pyplot as plt
import seaborn as sns

# --- CONFIGURACIÓN ---
DATOS_DIR = Path(__file__).parent / "datos_capturados"  # Usar datos_capturados directamente
WINDOW_SIZE = 40  # 2.5 segundos a 200Hz (estándar SisFall)
OVERLAP = 0.5    # 50% de solapamiento
STEP_SIZE = int(WINDOW_SIZE * (1 - OVERLAP))
TEST_SIZE = 0.2
EPOCHS = 20
BATCH_SIZE = 32

print("╔════════════════════════════════════════════════╗")
print("║   Entrenamiento CNN para detección de caídas  ║")
print("╚════════════════════════════════════════════════╝\n")

# --- 1. CARGAR DATOS ---
print("📂 Buscando archivos CSV en:", DATOS_DIR)

if not DATOS_DIR.exists():
    print(f"❌ Error: Carpeta '{DATOS_DIR}' no encontrada")
    exit(1)

archivos = list(DATOS_DIR.glob("*.csv"))
if not archivos:
    print(f"❌ No se encontraron archivos .csv en '{DATOS_DIR}'")
    exit(1)

print(f"📄 Archivos encontrados: {len(archivos)}")
for arch in archivos:
    print(f"   • {arch.name}")
print()

# Clasificación automática por nombre de archivo
datos_totales = []
etiquetas_totales = []
features = ['cadera_ax', 'cadera_ay', 'cadera_az', 'cadera_gx', 'cadera_gy', 'cadera_gz',
            'pierna_ax', 'pierna_ay', 'pierna_az', 'pierna_gx', 'pierna_gy', 'pierna_gz']

for archivo in archivos:
    # Clasificar automáticamente por nombre
    if 'caidas' in archivo.name.lower() or 'caida' in archivo.name.lower():
        etiqueta = 1
        tipo = "CAÍDA"
    elif 'normal' in archivo.name.lower():
        etiqueta = 0
        tipo = "NORMAL"
    else:
        print(f"⚠️  {archivo.name} - Nombre ambiguo, se clasifica como NORMAL")
        etiqueta = 0
        tipo = "NORMAL"
    
    print(f"📄 {archivo.name} → {tipo}")
    
    # Cargar archivo
    try:
        df = pd.read_csv(archivo)
        print(f"   ✅ Cargado: {len(df)} muestras")
        
        # Verificar que tenga todas las columnas necesarias
        if not all(col in df.columns for col in features):
            print(f"   ⚠️  Faltan columnas, usando solo las disponibles")
            features_disponibles = [col for col in features if col in df.columns]
        else:
            features_disponibles = features
        
        # Crear ventanas con solapamiento
        ventanas_creadas = 0
        for i in range(0, len(df) - WINDOW_SIZE + 1, STEP_SIZE):
            ventana = df.iloc[i:i+WINDOW_SIZE][features_disponibles].values
            datos_totales.append(ventana)
            etiquetas_totales.append(etiqueta)
            ventanas_creadas += 1
        
        print(f"   📊 Ventanas creadas: {ventanas_creadas}\n")
    
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

# Calcular pesos de clase para balanceo
class_weights = compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
class_weight_dict = {i: class_weights[i] for i in range(len(class_weights))}
print(f"⚖️  Pesos de clase: {class_weight_dict}")

# --- 3. CREAR MODELO CNN ---
print("\n🧠 Creando modelo CNN 1D...")
num_features = X.shape[2]  # Número de sensores (12 con cadera+pierna)

# Modelo más simple para dataset pequeño
model = Sequential([
    Conv1D(32, kernel_size=3, activation='relu', input_shape=(WINDOW_SIZE, num_features)),
    MaxPooling1D(pool_size=2),
    Dropout(0.4),
    
    Conv1D(64, kernel_size=3, activation='relu'),
    MaxPooling1D(pool_size=2),
    Dropout(0.4),
    
    Flatten(),
    Dense(32, activation='relu'),
    Dropout(0.5),
    Dense(1, activation='sigmoid')
])

optimizer = Adam(learning_rate=0.001)
model.compile(optimizer=optimizer, loss='binary_crossentropy', metrics=['accuracy'])
model.summary()

# --- 4. ENTRENAR ---
print("\n🚀 Entrenando modelo...")

# Callbacks
early_stop = EarlyStopping(
    monitor='val_loss',
    patience=10,
    restore_best_weights=True,
    verbose=1
)

reduce_lr = ReduceLROnPlateau(
    monitor='val_loss',
    factor=0.5,
    patience=5,
    min_lr=1e-7,
    verbose=1
)

history = model.fit(
    X_train, y_train,
    validation_data=(X_test, y_test),
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    class_weight=class_weight_dict,  # Balancear clases
    callbacks=[early_stop, reduce_lr],
    verbose=1
)

# --- 5. EVALUAR ---
print("\n📈 Evaluando modelo...")
loss, acc = model.evaluate(X_test, y_test, verbose=0)
print(f"\n✅ Resultados en conjunto de prueba:")
print(f"   • Pérdida (Loss):  {loss:.4f}")
print(f"   • Precisión (Acc): {acc:.4f} ({acc*100:.2f}%)")

# Predicciones
y_pred_proba = model.predict(X_test, verbose=0)
y_pred = (y_pred_proba > 0.5).astype(int).flatten()

# Distribución de predicciones
print(f"\n📊 Distribución de predicciones:")
pred_counts = pd.Series(y_pred).value_counts().sort_index()
for clase in [0, 1]:
    count = pred_counts.get(clase, 0)
    label = "Normal" if clase == 0 else "Caída"
    print(f"   • {label}: {count:,} predicciones")
print(f"\n📊 Probabilidades:")
print(f"   • Mínima:  {y_pred_proba.min():.4f}")
print(f"   • Máxima:  {y_pred_proba.max():.4f}")
print(f"   • Media:   {y_pred_proba.mean():.4f}")

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

# Reporte de clasificación
unique_pred = np.unique(y_pred)
if len(unique_pred) >= 2:
    print("\n📋 Reporte de clasificación:")
    print(classification_report(y_test, y_pred, target_names=['Normal', 'Caída'], digits=4))
else:
    print(f"\n⚠️ ADVERTENCIA: El modelo solo predice clase {unique_pred[0]}")
    print("   Esto indica un problema de entrenamiento.")

# --- CURVAS ROC Y PRECISION-RECALL ---
print("\n📈 Generando curvas ROC y Precision-Recall...")

# Calcular curva ROC
fpr, tpr, thresholds_roc = roc_curve(y_test, y_pred_proba)
roc_auc = auc(fpr, tpr)

# Calcular curva Precision-Recall
precision, recall, thresholds_pr = precision_recall_curve(y_test, y_pred_proba)
avg_precision = average_precision_score(y_test, y_pred_proba)

print(f"   • AUC-ROC: {roc_auc:.4f}")
print(f"   • Average Precision: {avg_precision:.4f}")

# Crear figura con ambas curvas
fig_curves, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Curva ROC
ax1.plot(fpr, tpr, color='darkorange', linewidth=2, label=f'ROC (AUC = {roc_auc:.4f})')
ax1.plot([0, 1], [0, 1], color='navy', linewidth=2, linestyle='--', label='Aleatorio')
ax1.set_xlim([0.0, 1.0])
ax1.set_ylim([0.0, 1.05])
ax1.set_xlabel('Tasa de Falsos Positivos (FPR)', fontweight='bold')
ax1.set_ylabel('Tasa de Verdaderos Positivos (TPR)', fontweight='bold')
ax1.set_title('Curva ROC (Receiver Operating Characteristic)', fontsize=12, fontweight='bold')
ax1.legend(loc="lower right")
ax1.grid(True, alpha=0.3)

# Curva Precision-Recall
ax2.plot(recall, precision, color='green', linewidth=2, label=f'PR (AP = {avg_precision:.4f})')
ax2.axhline(y=0.5, color='navy', linewidth=2, linestyle='--', alpha=0.5, label='Baseline')
ax2.set_xlim([0.0, 1.0])
ax2.set_ylim([0.0, 1.05])
ax2.set_xlabel('Recall (Sensibilidad)', fontweight='bold')
ax2.set_ylabel('Precision', fontweight='bold')
ax2.set_title('Curva Precision-Recall', fontsize=12, fontweight='bold')
ax2.legend(loc="lower left")
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('curvas_evaluacion.png', dpi=150, bbox_inches='tight')
print("💾 Curvas guardadas: curvas_evaluacion.png")

# Encontrar mejor umbral (Youden's J statistic)
j_scores = tpr - fpr
best_threshold_idx = np.argmax(j_scores)
best_threshold = thresholds_roc[best_threshold_idx]
print(f"\n🎯 Mejor umbral (Youden's J): {best_threshold:.4f}")
print(f"   TPR: {tpr[best_threshold_idx]:.4f} | FPR: {fpr[best_threshold_idx]:.4f}")

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
print("\n📊 Archivos generados:")
print("   • modelo_caidas_arduino.h5")
print("   • matriz_confusion_arduino.png")
print("   • curvas_evaluacion.png")
print("   • entrenamiento_arduino.png")
print("\n💡 Interpretación de métricas:")
print("   • AUC-ROC = 1.0: Modelo perfecto (puede ser overfitting)")
print("   • AUC-ROC > 0.9: Excelente")
print("   • AUC-ROC > 0.8: Muy bueno")
print("   • AUC-ROC > 0.7: Bueno")
print("   • AUC-ROC = 0.5: Modelo aleatorio (malo)")
