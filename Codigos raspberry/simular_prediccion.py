"""
Simulador de Predicción de Caídas
Carga el modelo entrenado y predice si una secuencia de datos es caída o normal
"""
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
from pathlib import Path

print("╔════════════════════════════════════════════════╗")
print("║     Simulador de Detección de Caídas          ║")
print("╚════════════════════════════════════════════════╝\n")

# --- CONFIGURACIÓN ---
MODEL_PATH = "modelo_caidas_arduino.h5"
WINDOW_SIZE = 40  # Debe coincidir con el entrenamiento

# --- CARGAR MODELO ---
print("🧠 Cargando modelo entrenado...")
try:
    model = load_model(MODEL_PATH)
    print(f"✅ Modelo cargado: {MODEL_PATH}\n")
except Exception as e:
    print(f"❌ Error cargando modelo: {e}")
    print("   Asegúrate de haber entrenado el modelo primero con 'entrenar_con_datos_arduino.py'")
    exit(1)

# --- OPCIONES ---
print("Opciones:")
print("1. Cargar datos desde archivo CSV")
print("2. Pegar datos manualmente (40 filas)\n")

opcion = input("Selecciona opción (1 o 2): ").strip()

if opcion == "1":
    # Cargar desde archivo
    datos_dir = Path(__file__).parent / "datos_capturados"
    archivos = list(datos_dir.glob("*.csv"))
    
    if not archivos:
        print("❌ No se encontraron archivos CSV")
        exit(1)
    
    print(f"\n📄 Archivos disponibles:")
    for i, arch in enumerate(archivos, 1):
        print(f"   {i}. {arch.name}")
    
    while True:
        try:
            seleccion = int(input(f"\nSelecciona archivo (1-{len(archivos)}): "))
            if 1 <= seleccion <= len(archivos):
                archivo = archivos[seleccion - 1]
                break
            print(f"❌ Número inválido")
        except ValueError:
            print("❌ Ingresa un número válido")
    
    # Cargar archivo
    df = pd.read_csv(archivo)
    print(f"\n✅ Cargado: {archivo.name}")
    print(f"   Total de muestras: {len(df)}")
    
    # Pedir rango de filas
    print(f"\n📊 Selecciona {WINDOW_SIZE} filas consecutivas para analizar")
    print(f"   Rango disponible: 1 a {len(df)}")
    
    while True:
        try:
            inicio = int(input(f"Fila inicial (1-{len(df) - WINDOW_SIZE + 1}): "))
            if 1 <= inicio <= len(df) - WINDOW_SIZE + 1:
                break
            print(f"❌ Debe estar entre 1 y {len(df) - WINDOW_SIZE + 1}")
        except ValueError:
            print("❌ Ingresa un número válido")
    
    # Extraer ventana
    fin = inicio + WINDOW_SIZE - 1
    ventana_df = df.iloc[inicio-1:inicio-1+WINDOW_SIZE]
    
    # Extraer features (columnas 2-13: cadera y pierna)
    features = ['cadera_ax', 'cadera_ay', 'cadera_az', 'cadera_gx', 'cadera_gy', 'cadera_gz',
                'pierna_ax', 'pierna_ay', 'pierna_az', 'pierna_gx', 'pierna_gy', 'pierna_gz']
    
    datos = ventana_df[features].values
    
    print(f"\n📋 Analizando filas {inicio} a {fin}")

elif opcion == "2":
    print(f"\n📋 Pega {WINDOW_SIZE} líneas de datos (formato CSV)")
    print("   Formato: seq,cadera_ax,cadera_ay,cadera_az,cadera_gx,cadera_gy,cadera_gz,pierna_ax,pierna_ay,pierna_az,pierna_gx,pierna_gy,pierna_gz")
    print("   Presiona Enter dos veces cuando termines:\n")
    
    lineas = []
    while len(lineas) < WINDOW_SIZE:
        linea = input(f"Línea {len(lineas)+1}/{WINDOW_SIZE}: ").strip()
        if not linea:
            if len(lineas) >= WINDOW_SIZE:
                break
            else:
                print(f"⚠️  Necesitas al menos {WINDOW_SIZE} líneas")
                continue
        lineas.append(linea)
    
    # Parsear datos
    try:
        datos_list = []
        for linea in lineas[:WINDOW_SIZE]:
            valores = [float(x.strip()) for x in linea.split(',')]
            # Tomar columnas 2-13 (índices 1-12) que son los sensores
            if len(valores) >= 13:
                datos_list.append(valores[1:13])  # cadera + pierna
            elif len(valores) >= 7:
                # Si solo hay cadera, duplicar para pierna (simulado)
                datos_list.append(valores[1:7] + valores[1:7])
            else:
                print(f"⚠️  Línea con formato incorrecto: {linea}")
        
        datos = np.array(datos_list, dtype=np.float32)
        
    except Exception as e:
        print(f"❌ Error parseando datos: {e}")
        exit(1)

else:
    print("❌ Opción inválida")
    exit(1)

# --- PREPARAR DATOS PARA EL MODELO ---
print(f"\n🔢 Preparando datos...")
print(f"   Shape de la ventana: {datos.shape}")

# Verificar shape
if datos.shape[0] != WINDOW_SIZE:
    print(f"⚠️  Advertencia: Se esperaban {WINDOW_SIZE} muestras, pero hay {datos.shape[0]}")
    if datos.shape[0] < WINDOW_SIZE:
        print("❌ Insuficientes datos para predecir")
        exit(1)

# Agregar dimensión de batch
X = np.array([datos], dtype=np.float32)  # Shape: (1, WINDOW_SIZE, num_features)
print(f"   Shape para modelo: {X.shape}")

# --- HACER PREDICCIÓN ---
print("\n🔮 Haciendo predicción...")
try:
    probabilidad = model.predict(X, verbose=0)[0][0]
    
    # Determinar resultado
    es_caida = probabilidad > 0.5
    
    print("\n" + "="*50)
    if es_caida:
        print("🚨 RESULTADO: ¡CAÍDA DETECTADA!")
        print(f"   Probabilidad: {probabilidad:.4f} ({probabilidad*100:.2f}%)")
        print("   Confianza:", "🔴 " * int(probabilidad * 10))
    else:
        print("✅ RESULTADO: MOVIMIENTO NORMAL")
        print(f"   Probabilidad de caída: {probabilidad:.4f} ({probabilidad*100:.2f}%)")
        print("   Confianza:", "🟢 " * int((1-probabilidad) * 10))
    print("="*50)
    
    # Estadísticas de los datos
    print("\n📊 Estadísticas de la ventana analizada:")
    print(f"   Aceleración cadera:")
    print(f"      X: min={datos[:, 0].min():.3f}, max={datos[:, 0].max():.3f}, media={datos[:, 0].mean():.3f}")
    print(f"      Y: min={datos[:, 1].min():.3f}, max={datos[:, 1].max():.3f}, media={datos[:, 1].mean():.3f}")
    print(f"      Z: min={datos[:, 2].min():.3f}, max={datos[:, 2].max():.3f}, media={datos[:, 2].mean():.3f}")
    
    print(f"\n   Giroscopio cadera:")
    print(f"      X: min={datos[:, 3].min():.3f}, max={datos[:, 3].max():.3f}, media={datos[:, 3].mean():.3f}")
    print(f"      Y: min={datos[:, 4].min():.3f}, max={datos[:, 4].max():.3f}, media={datos[:, 4].mean():.3f}")
    print(f"      Z: min={datos[:, 5].min():.3f}, max={datos[:, 5].max():.3f}, media={datos[:, 5].mean():.3f}")
    
    # Magnitud total
    mag_accel = np.sqrt(datos[:, 0]**2 + datos[:, 1]**2 + datos[:, 2]**2)
    mag_gyro = np.sqrt(datos[:, 3]**2 + datos[:, 4]**2 + datos[:, 5]**2)
    
    print(f"\n   Magnitudes (cadera):")
    print(f"      Aceleración total: {mag_accel.max():.3f} g (máx)")
    print(f"      Rotación total: {mag_gyro.max():.3f} °/s (máx)")
    
    # Interpretación
    print("\n💡 Interpretación:")
    if es_caida:
        if probabilidad > 0.9:
            print("   ✅ Alta confianza - Definitivamente es una caída")
        elif probabilidad > 0.7:
            print("   ⚠️  Confianza media - Probablemente es una caída")
        else:
            print("   ⚠️  Baja confianza - Puede ser una caída o movimiento brusco")
    else:
        if probabilidad < 0.1:
            print("   ✅ Alta confianza - Definitivamente es movimiento normal")
        elif probabilidad < 0.3:
            print("   ⚠️  Confianza media - Probablemente es normal")
        else:
            print("   ⚠️  Baja confianza - Cerca del umbral de decisión")
    
except Exception as e:
    print(f"❌ Error en predicción: {e}")
    exit(1)

print("\n✅ Simulación completada!")
