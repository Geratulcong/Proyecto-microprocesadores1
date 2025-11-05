import pandas as pd
import os
import glob

# Ruta del dataset SisFall
SISFALL_PATH = r"C:\Users\gerol\.cache\kagglehub\datasets\nvnikhil0001\sis-fall-original-dataset\versions\1\SisFall_dataset"

# --- Procesar archivos de SisFall ---
def procesar_sisfall():
    datos_totales = []
    
    # Buscar todas las carpetas de sujetos (SA01, SA02, etc.)
    carpetas_sujetos = glob.glob(os.path.join(SISFALL_PATH, "SA*"))
    
    print(f"📂 Encontradas {len(carpetas_sujetos)} carpetas de sujetos")
    
    for carpeta in carpetas_sujetos:
        sujeto = os.path.basename(carpeta)
        
        # Buscar archivos D01 a D55
        for d_num in range(1, 56):  # D01 a D55
            patron = os.path.join(carpeta, f"D{d_num:02d}_{sujeto}_R*.txt")
            archivos = glob.glob(patron)
            
            for archivo in archivos:
                try:
                    # Leer el archivo (sin encabezado, valores separados por comas)
                    df = pd.read_csv(archivo, header=None, names=['ax1', 'ay1', 'az1', 'ax2', 'ay2', 'az2', 'gx', 'gy', 'gz'])
                    
                    # Usar solo primer acelerómetro (ax1, ay1, az1) y giroscopio (gx, gy, gz)
                    df_limpio = df[['ax1', 'ay1', 'az1', 'gx', 'gy', 'gz']].copy()
                    
                    # Renombrar columnas para que coincidan con tu formato
                    df_limpio.columns = ['ax', 'ay', 'az', 'gx', 'gy', 'gz']
                    
                    # Clasificar: D01-D15 = caída (1), D16-D55 = actividad normal (0)
                    if d_num <= 15:
                        df_limpio['state'] = 1  # Caída
                    else:
                        df_limpio['state'] = 0  # Actividad normal / quieto

                    # Agregar timestamp
                    df_limpio['t'] = range(len(df_limpio))
                    
                    datos_totales.append(df_limpio)
                    
                    print(f"✅ Procesado: {os.path.basename(archivo)} - {len(df_limpio)} muestras")
                    
                except Exception as e:
                    print(f"❌ Error en {archivo}: {e}")
    
    # Combinar todos los datos
    if datos_totales:
        df_final = pd.concat(datos_totales, ignore_index=True)
        
        # Reorganizar columnas
        df_final = df_final[['t', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'state']]
        
        # Guardar CSV
        output_file = r"c:\Users\gerol\Downloads\Proyecto Microprocesadores\Proyecto-microprocesadores1\Codigos raspberry\datos_sisfall_completo.csv"
        df_final.to_csv(output_file, sep=';', index=False)
        
        print(f"\n✅ Dataset guardado en: {output_file}")
        print(f"📊 Total de muestras: {len(df_final)}")
        print(f"📊 Archivos procesados: {len(datos_totales)}")
        print(f"📊 Caídas (state=1): {len(df_final[df_final['state'] == 1])}")
        print(f"📊 Actividades normales (state=0): {len(df_final[df_final['state'] == 0])}")
    else:
        print("❌ No se procesaron datos")

if __name__ == "__main__":
    procesar_sisfall()
