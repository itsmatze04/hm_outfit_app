import pandas as pd
from collections import Counter
from itertools import combinations
import os
import sys

# ---------------------------------------------------------
# Pfade an dein Projekt anpassen (falls nötig)
# ---------------------------------------------------------
PATH_ARTICLES = "data_processed/articles_filtered.csv"
PATH_TRANSACTIONS = "data_raw/transactions_train.csv"
PATH_OUT = "data_processed/copurchase_filtered.csv"

# Optional: nur Paare mit mindestens MIN_COUNT speichern
MIN_COUNT = 2

# Chunk-Größe für das Einlesen der Transaktionen
CHUNK_SIZE = 1_000_000


def load_filtered_article_ids(path_articles: str) -> set:
    """
    Lädt articles_filtered.csv und gibt ein Set aller article_id zurück.
    """
    print(f"Lese gefilterte Artikel aus: {path_articles}")
    df_articles = pd.read_csv(path_articles, usecols=["article_id"])
    df_articles["article_id"] = df_articles["article_id"].astype(int)
    article_ids = set(df_articles["article_id"].unique())
    print(f"Anzahl distinct gefilterte article_id: {len(article_ids)}")
    return article_ids


def count_rows_csv(path_csv: str) -> int:
    """
    Zählt die Zeilen einer CSV-Datei (ohne Header), um eine grobe
    Gesamtzeilenanzahl für die Fortschrittsanzeige zu haben.
    """
    print(f"Zähle Zeilen in {path_csv} für Fortschrittsanzeige ...")
    with open(path_csv, "r", encoding="utf-8") as f:
        # -1 wegen Header
        total = sum(1 for _ in f) - 1
    print(f"Geschätzte Gesamtzeilen (ohne Header): {total}")
    return max(total, 0)


def process_transactions_chunk(df_chunk: pd.DataFrame, valid_article_ids: set, pair_counter: Counter):
    """
    Verarbeitet einen Chunk von transactions_train:
    - Filter auf Artikel im Set valid_article_ids
    - Gruppiert nach (customer_id, t_dat) = Warenkorb
    - Zählt alle Artikelpaare pro Warenkorb in pair_counter
    """
    # Nur relevante Artikel behalten
    df_chunk = df_chunk[df_chunk["article_id"].isin(valid_article_ids)]
    if df_chunk.empty:
        return

    # Sicherstellen, dass article_id int ist
    df_chunk["article_id"] = df_chunk["article_id"].astype(int)

    # Warenkörbe definieren
    # Annahme: gleicher Kunde + gleiches Datum = ein Warenkorb
    grouped = df_chunk.groupby(["customer_id", "t_dat"])["article_id"].unique()

    for (_, _), articles in grouped.items():
        # Nur interessante Körbe: mind. 2 verschiedene Artikel
        if len(articles) < 2:
            continue

        # Alle Kombinationen von 2 Artikeln
        for a1, a2 in combinations(sorted(articles), 2):
            pair_counter[(a1, a2)] += 1


def build_copurchase_matrix(path_transactions: str, valid_article_ids: set,
                            chunk_size: int = 1_000_000) -> pd.DataFrame:
    """
    Lädt transactions_train.csv in Chunks ein,
    baut eine Co-Purchase-Matrix (als Liste von Paaren mit Count) auf
    und gibt sie als DataFrame zurück.
    """
    pair_counter = Counter()

    usecols = ["t_dat", "customer_id", "article_id"]
    print(f"Starte Verarbeitung von: {path_transactions}")

    # Gesamtzeilen für Fortschrittsanzeige ermitteln
    total_rows_estimate = count_rows_csv(path_transactions)

    reader = pd.read_csv(
        path_transactions,
        usecols=usecols,
        chunksize=chunk_size
    )

    total_rows_processed = 0

    for i, chunk in enumerate(reader, start=1):
        rows_in_chunk = len(chunk)
        total_rows_processed += rows_in_chunk

        process_transactions_chunk(chunk, valid_article_ids, pair_counter)

        # Fortschritt berechnen und im gleichen Terminal-Output aktualisieren
        if total_rows_estimate > 0:
            progress = (total_rows_processed / total_rows_estimate) * 100
            msg = (
                f"Chunk {i} verarbeitet, Zeilen im Chunk: {rows_in_chunk}. "
                f"Progress: {progress:6.2f}% "
                f"({total_rows_processed:,} / {total_rows_estimate:,} rows)"
            )
        else:
            msg = f"Chunk {i} verarbeitet, Zeilen im Chunk: {rows_in_chunk}. " \
                  f"Verarbeitete Zeilen: {total_rows_processed:,}"

        # \r = Carriage Return, end="" damit die Zeile überschrieben wird
        print(msg, end="\r", file=sys.stdout, flush=True)

    # Am Ende eine neue Zeile ausgeben, damit die letzte Progress-Zeile "fest" ist
    print()

    print("Transaktionen verarbeitet. Erzeuge DataFrame aus Paaren...")

    # Counter -> DataFrame
    rows = []
    for (a1, a2), cnt in pair_counter.items():
        # Optionaler Filter auf Mindestanzahl
        if cnt >= MIN_COUNT:
            rows.append((a1, a2, cnt))

    df_pairs = pd.DataFrame(rows, columns=["article_id_1", "article_id_2", "count"])

    # Nach Häufigkeit sortieren
    df_pairs = df_pairs.sort_values("count", ascending=False).reset_index(drop=True)
    print(f"Anzahl Co-Purchase-Paare (count >= {MIN_COUNT}): {len(df_pairs)}")

    return df_pairs


def main():
    os.makedirs(os.path.dirname(PATH_OUT), exist_ok=True)

    # 1) Gefilterte Artikel laden
    valid_article_ids = load_filtered_article_ids(PATH_ARTICLES)

    # 2) Co-Purchase-Matrix aufbauen
    df_copurchase = build_copurchase_matrix(
        path_transactions=PATH_TRANSACTIONS,
        valid_article_ids=valid_article_ids,
        chunk_size=CHUNK_SIZE
    )

    # 3) Speichern
    df_copurchase.to_csv(PATH_OUT, index=False)
    print(f"Fertig! Co-Purchase-Datei gespeichert unter: {PATH_OUT}")


if __name__ == "__main__":
    main()
