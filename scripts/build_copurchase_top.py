from pathlib import Path
import pandas as pd
from itertools import combinations

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW = BASE_DIR / "data_raw"
DATA_PROCESSED = BASE_DIR / "data_processed"

print("Lade articles_top.csv ...")
articles_top = pd.read_csv(DATA_PROCESSED / "articles_top.csv")
top_ids = set(articles_top["article_id"].unique())
print(f"Anzahl Top-Artikel: {len(top_ids)}")

# Nur benötigte Spalten laden
usecols = ["t_dat", "customer_id", "article_id"]
print("Lade transactions_train.csv (nur benötigte Spalten) ...")
transactions = pd.read_csv(DATA_RAW / "transactions_train.csv", usecols=usecols)
print("Transactions:", transactions.shape)

# Optional: Zeitraum einschränken (beschleunigt, kann man auskommentieren)
# transactions["t_dat"] = pd.to_datetime(transactions["t_dat"])
# transactions = transactions[transactions["t_dat"] >= "2019-06-01"]
# print("Gefilterte Transactions:", transactions.shape)

# Nur Transaktionen mit unseren Top-Artikeln
transactions = transactions[transactions["article_id"].isin(top_ids)].copy()
print("Transactions mit Top-Artikeln:", transactions.shape)

# Warenkorb-ID bilden (vereinfachte Annahme: gleicher Kunde + gleiches Datum = ein Warenkorb)
transactions["basket_id"] = transactions["customer_id"].astype(str) + "_" + transactions["t_dat"].astype(str)

print("Baue Co-Purchase-Paare ...")
pairs_counter: dict[tuple[int, int], int] = {}

for _, group in transactions.groupby("basket_id")["article_id"]:
    arts = group.unique()
    if len(arts) < 2:
        continue
    # Alle Kombinationen aus dem Warenkorb
    for a1, a2 in combinations(sorted(arts), 2):
        key = (int(a1), int(a2))
        pairs_counter[key] = pairs_counter.get(key, 0) + 1

print(f"Anzahl verschiedener Artikel-Paare: {len(pairs_counter)}")

rows = []
for (a1, a2), count in pairs_counter.items():
    rows.append({"article_id_1": a1, "article_id_2": a2, "count": count})

copurchase = pd.DataFrame(rows)
copurchase.sort_values("count", ascending=False, inplace=True)

out_path = DATA_PROCESSED / "copurchase_top.csv"
copurchase.to_csv(out_path, index=False)

print("Gespeichert:", out_path)
print("Form:", copurchase.shape)
print(copurchase.head())
