import kagglehub
import pandas as pd
import os
import numpy as np

# --- 1. Descargar el dataset ---
print("📥 Descargando dataset SisFall de Kaggle...")
path = kagglehub.dataset_download("nvnikhil0001/sis-fall-original-dataset")
print(f"✅ Dataset descargado en: {path}")

# --- 2. Explorar la estructura del dataset ---
print("\n📂 Archivos en el dataset:")
for root, dirs, files in os.walk(path):
    level = root.replace(path, '').count(os.sep)
    indent = ' ' * 2 * level
    print(f'{indent}{os.path.basename(root)}/')
    subindent = ' ' * 2 * (level + 1)
    for file in files[:5]:  # Mostrar solo los primeros 5 archivos
        print(f'{subindent}{file}')
    if len(files) > 5:
        print(f'{subindent}... y {len(files) - 5} archivos más')
    if level > 2:  # Limitar la profundidad
        break

print(f"\n💡 Usa esta ruta para procesar el dataset: {path}")
