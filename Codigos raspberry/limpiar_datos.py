"""
Script para limpiar archivos TXT capturados del Arduino
Elimina líneas con texto, errores o formato incorrecto
Solo mantiene líneas con 6 valores numéricos separados por comas
"""
import os
from pathlib import Path
import re

# --- CONFIGURACIÓN ---
INPUT_DIR = Path(__file__).parent / "datos_capturados"
OUTPUT_DIR = Path(__file__).parent / "datos_limpios"

# Crear carpeta de salida
OUTPUT_DIR.mkdir(exist_ok=True)

print("╔════════════════════════════════════════════════╗")
print("║     Limpieza de archivos TXT del Arduino      ║")
print("╚════════════════════════════════════════════════╝\n")

# Buscar archivos TXT
if not INPUT_DIR.exists():
    print(f"❌ Error: Carpeta '{INPUT_DIR}' no encontrada")
    print(f"   Crea la carpeta y coloca tus archivos .txt ahí\n")
    exit(1)

archivos_txt = list(INPUT_DIR.glob("*.csv")) + list(INPUT_DIR.glob("*.txt"))
if not archivos_txt:
    print(f"❌ No se encontraron archivos .txt en '{INPUT_DIR}'")
    exit(1)

print(f"📂 Carpeta de entrada: {INPUT_DIR}")
print(f"💾 Carpeta de salida: {OUTPUT_DIR}")
print(f"📄 Archivos encontrados: {len(archivos_txt)}\n")

# Patrón para validar líneas: 6 números separados por comas
# Ejemplo válido: 0.123,-0.456,0.789,1.234,-5.678,9.012
patron = re.compile(r'^-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*$')

total_procesados = 0
total_limpiados = 0
total_descartados = 0

for archivo in archivos_txt:
    print(f"🔍 Procesando: {archivo.name}")
    
    lineas_validas = []
    lineas_invalidas = []
    
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            for num_linea, linea in enumerate(f, 1):
                linea = linea.strip()
                
                # Ignorar líneas vacías
                if not linea:
                    continue
                
                # Verificar si la línea coincide con el patrón
                if patron.match(linea):
                    lineas_validas.append(linea)
                else:
                    lineas_invalidas.append((num_linea, linea))
        
        # Guardar archivo limpio
        if lineas_validas:
            output_file = OUTPUT_DIR / archivo.name
            with open(output_file, 'w', encoding='utf-8') as f:
                # Escribir encabezado
                f.write("ax,ay,az,gx,gy,gz\n")
                # Escribir datos válidos
                for linea in lineas_validas:
                    f.write(linea + "\n")
            
            print(f"   ✅ Limpio: {len(lineas_validas)} líneas válidas")
            
            if lineas_invalidas:
                print(f"   ⚠️  Descartadas {len(lineas_invalidas)} líneas:")
                for num, linea in lineas_invalidas[:5]:  # Mostrar solo las primeras 5
                    preview = linea[:60] + "..." if len(linea) > 60 else linea
                    print(f"      Línea {num}: {preview}")
                if len(lineas_invalidas) > 5:
                    print(f"      ... y {len(lineas_invalidas) - 5} más")
            
            total_procesados += 1
            total_limpiados += len(lineas_validas)
            total_descartados += len(lineas_invalidas)
        else:
            print(f"   ❌ Sin datos válidos, archivo omitido")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()

# Resumen
print("═" * 50)
print(f"✅ Archivos procesados: {total_procesados}")
print(f"📊 Total de líneas válidas: {total_limpiados}")
print(f"🗑️  Total de líneas descartadas: {total_descartados}")
print(f"💾 Archivos guardados en: {OUTPUT_DIR}\n")
