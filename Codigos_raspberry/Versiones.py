import pandas as pd

# Cargar el CSV
df = pd.read_csv("Codigos_raspberry\datos_capturados\datos_capturados_caidas (1).csv")

# Agregar columna 'state' con valor 0
df["state"] = 1

# Guardar nuevamente
df.to_csv("Caidas.csv", index=False)

print("Columna 'state' agregada correctamente.")
