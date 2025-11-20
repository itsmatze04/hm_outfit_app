import pandas as pd
from pathlib import Path
import math

# Pfad zur großen Datei
INPUT = Path("data_processed/copurchase_filtered.csv")

# Zielordner
OUT_DIR = Path("data_processed/copurchase_parts_5")
OUT_DIR.mkdir(parents=True, exist_ok=True)

print("Lade große Datei...")
df = pd.read_csv(INPUT)

n = len(df)
parts = 5
rows_per_file = math.ceil(n / parts)

print(f"Gesamtzeilen: {n}")
print(f"-> Teile die Datei in {parts} Stücke á ca. {rows_per_file} Zeilen")

for i in range(parts):
    start = i * rows_per_file
    end = min((i + 1) * rows_per_file, n)
    df_part = df.iloc[start:end]

    out_path = OUT_DIR / f"copurchase_part_{i+1}.csv"
    df_part.to_csv(out_path, index=False)

    print(f"Gespeichert: {out_path}  ({len(df_part)} Zeilen)")

print("Fertig.")
