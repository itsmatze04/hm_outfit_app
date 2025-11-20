from pathlib import Path
import pandas as pd

# Basispfade
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW = BASE_DIR / "data_raw"
DATA_PROCESSED = BASE_DIR / "data_processed"
DATA_PROCESSED.mkdir(exist_ok=True)

# Daten laden
articles = pd.read_csv(DATA_RAW / "articles.csv")
transactions = pd.read_csv(DATA_RAW / "transactions_train.csv")

print("Articles:", articles.shape)
print("Transactions:", transactions.shape)

# Top 500 meistverkaufte Artikel
top_ids = transactions["article_id"].value_counts().head(500).index

articles_top = articles[articles["article_id"].isin(top_ids)].copy()

# Auf sinnvolle Produktgruppen einschränken
allowed_groups = ["Garment Upper body", "Trousers", "Shoes", "Outerwear"]
articles_top = articles_top[articles_top["product_group_name"].isin(allowed_groups)].copy()

# Ergebnis speichern
out_path = DATA_PROCESSED / "articles_top.csv"
articles_top.to_csv(out_path, index=False)

print("Gespeicherte Artikel:", articles_top.shape)
print("Datei:", out_path)
