import pandas as pd

# ---------------------------------------------------------
# 1. Pfad zu articles.csv
# ---------------------------------------------------------
PATH_IN = "data_raw/articles.csv"
PATH_OUT = "data_processed/articles_filtered.csv"

# ---------------------------------------------------------
# 2. Kategorien definieren
#    -> Diese werden BEHALTEN (inkl. optional)
# ---------------------------------------------------------

keep_categories = [
    # TOPS
    "Hoodie",
    "Sweater",
    "Top",
    "T-shirt",
    "Shirt",
    "Polo shirt",
    "Blouse",
    "Cardigan",
    "Vest top",
    "Sweatshirt",
    "Long sleeve top",
    "Longsleeve",

    # BOTTOMS
    "Trousers",
    "Jeans",
    "Shorts",
    "Skirt",
    "Leggings/Tights",

    # OUTERWEAR
    "Jacket",
    "Coat",
    "Blazer",

    # SHOES
    "Sneakers",
    "Boots",
    "Bootie",
    "Ballerinas",
    "Moccasins",
    "Pumps",
    "Heels",
    "Heeled sandals",
    "Sandals",
    "Flat shoe",
    "Flat shoes",
    "Flip flop",
    "Other shoe",

    # OPTIONAL ACCESSORIES (von dir bestätigt)
    "Cap",
    "Beanie",
    "Headband",
    "Hat/beanie",
    "Hat/brim",
    "Straw hat",
    "Felt hat",
    "Bucket hat",
    "Bag",        # falls im Datensatz vorhanden
]

# ---------------------------------------------------------
# 3. Kategorien die entfernt werden sollen (Remove)
# ---------------------------------------------------------

remove_categories = [
    "Dog Wear",
    "Slippers",
    "Outdoor overall",
    "Outdoor trousers",
    "Pre-walkers",
    "Sarong",
    "Robe",
    "Dungarees",        # optional entfernt
]

# ---------------------------------------------------------
# 4. Daten einlesen
# ---------------------------------------------------------

usecols = [
    "article_id",
    "prod_name",
    "product_type_name",
    "product_group_name",
    "index_name",
    "colour_group_name",
    "perceived_colour_value_name",
    "perceived_colour_master_name",
    "detail_desc"
]

df = pd.read_csv(PATH_IN, usecols=usecols)

# ---------------------------------------------------------
# 5. Filtern: nur Produkt-Typen, die wir behalten wollen
# ---------------------------------------------------------

df_filtered = df[
    df["product_type_name"].isin(keep_categories)
]

# zusätzlich Remove-Kategorien entfernen:
df_filtered = df_filtered[
    ~df_filtered["product_type_name"].isin(remove_categories)
]

# ---------------------------------------------------------
# 6. Duplikate entfernen (falls nötig)
# ---------------------------------------------------------
df_filtered = df_filtered.drop_duplicates(subset=["article_id"])

# ---------------------------------------------------------
# 7. Ausgabe speichern
# ---------------------------------------------------------
df_filtered.to_csv(PATH_OUT, index=False)

print(f"Fertig! {len(df_filtered)} Artikel gespeichert unter: {PATH_OUT}")
