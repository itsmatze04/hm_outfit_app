import os
import shutil
import pandas as pd

# ---------------------------------------------------------
# Pfade an dein Projekt anpassen (falls nötig)
# ---------------------------------------------------------
PATH_ARTICLES = "data_processed/articles_filtered.csv"
SRC_IMG_ROOT = "data_raw/images"      # Original-H&M-Bilder
DST_IMG_ROOT = "images_sample"        # Zielordner für das Sample

# ---------------------------------------------------------
# 1. Artikel einlesen
# ---------------------------------------------------------
print(f"Lese Artikel aus: {PATH_ARTICLES}")
df = pd.read_csv(PATH_ARTICLES, usecols=["article_id"])

# article_id -> 10-stellige Zeichenkette
df["article_id_str"] = df["article_id"].astype(str).str.zfill(10)
article_ids = df["article_id_str"].unique()

print(f"Anzahl distinct article_id in Filter-Datei: {len(article_ids)}")

# ---------------------------------------------------------
# 2. Bilder kopieren
#    Struktur: data_raw/images/010/0101234567.jpg
#              -> images_sample/010/0101234567.jpg
# ---------------------------------------------------------
copied = 0
missing = 0
already_existing = 0

for art_id_str in article_ids:
    folder = art_id_str[:3]
    filename = f"{art_id_str}.jpg"

    src_path = os.path.join(SRC_IMG_ROOT, folder, filename)
    dst_folder = os.path.join(DST_IMG_ROOT, folder)
    dst_path = os.path.join(dst_folder, filename)

    # Zielordner anlegen
    os.makedirs(dst_folder, exist_ok=True)

    if os.path.exists(src_path):
        if not os.path.exists(dst_path):
            shutil.copy2(src_path, dst_path)
            copied += 1
        else:
            already_existing += 1
    else:
        print(f"Warnung: Bild nicht gefunden für article_id {art_id_str}: {src_path}")
        missing += 1

print("-----------------------------------------------------")
print(f"Fertig.")
print(f"Neu kopierte Bilder:        {copied}")
print(f"Bereits vorhandene Bilder:  {already_existing}")
print(f"Fehlende Bilder:            {missing}")
print(f"Zielverzeichnis:            {DST_IMG_ROOT}")
