import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict
import time

# ---------------------------------------------------------
# 1. KONFIGURATION & CSS
# ---------------------------------------------------------
st.set_page_config(
    page_title="H&M Outfit Recommender – Hybrid",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        /* Bilder: Feste Höhe, ganzes Bild sichtbar */
        div[data-testid="stImage"] img {
            height: 280px !important;
            object-fit: contain !important;
            background-color: #ffffff;
            border-radius: 8px;
            padding: 5px;
            border: 1px solid #444;
        }

        /* Allgemeine Button-Basis */
        div[data-testid="stButton"] button {
            height: 50px !important;
            width: 100% !important;
            white-space: pre-wrap !important;
            line-height: 1.1 !important;
            padding: 2px !important;
            overflow: hidden !important;
            font-size: 13px !important;
            margin-top: 5px !important; 
            border-radius: 8px !important;
        }

        /* SECONDARY-Buttons (nicht ausgewählt) */
        div[data-testid="stButton"] button[data-testid="baseButton-secondary"] {
            background-color: #262730 !important;
            color: #ffffff !important;
            border: 1px solid transparent !important;
        }

        div[data-testid="stButton"] button[data-testid="baseButton-secondary"]:hover {
            border: 1px solid #e50010 !important;
            background-color: #e50010 !important;
            color: #ffffff !important;
        }

        /* PRIMARY-Buttons (ausgewählt) – dauerhaft rot */
        div[data-testid="stButton"] button[data-testid="baseButton-primary"] {
            background-color: #e50010 !important;
            color: #ffffff !important;
            border: 1px solid #e50010 !important;
        }

        div[data-testid="stButton"] button[data-testid="baseButton-primary"]:hover {
            background-color: #e50010 !important;
            color: #ffffff !important;
            border: 1px solid #ffffff !important;
        }

        /* Optional: Bild-Hover mit rotem Rahmen */
        div[data-testid="stImage"] img:hover {
            border-color: #e50010 !important;
            box-shadow: 0 0 0 2px #e5001033;
        }

        /* Spinner / Loader Farbe */
        .stSpinner > div {
            border-top-color: #e50010 !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# 2. HILFSFUNKTION: SCROLL TO TOP
# ---------------------------------------------------------
def scroll_to_top():
    js = f"""
    <script>
        function forceScroll() {{
            window.parent.scrollTo(0, 0);
            var doc = window.parent.document.querySelector('[data-testid="stAppViewContainer"]');
            if (doc) doc.scrollTop = 0;
            setTimeout(function() {{
                window.parent.scrollTo(0, 0);
                if (doc) doc.scrollTop = 0;
            }}, 150);
            setTimeout(function() {{
                window.parent.scrollTo(0, 0);
                if (doc) doc.scrollTop = 0;
            }}, 600);
        }}
        forceScroll();
    </script>
    <div style="display:none;">{time.time()}</div>
    """
    from streamlit import components
    components.v1.html(js, height=0)

# ---------------------------------------------------------
# 3. PFAD-KONFIGURATION
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_PROCESSED = BASE_DIR / "data_processed"
IMAGES_BASE_URL = "https://pub-65f13bc76a9245c6b68256fb466fe755.r2.dev"

ARTICLES_FILE = DATA_PROCESSED / "articles_filtered.csv"
COPURCHASE_PARTS_DIR = DATA_PROCESSED / "copurchase_parts_5"

# ---------------------------------------------------------
# 4. MAPPINGS (MACRO-KATEGORIEN, GENDER, STIL)
# ---------------------------------------------------------
PRODUCT_TYPE_TO_MACRO = {
    # TOPS
    "Hoodie": "TOP",
    "Sweater": "TOP",
    "Top": "TOP",
    "T-shirt": "TOP",
    "Shirt": "TOP",
    "Polo shirt": "TOP",
    "Blouse": "TOP",
    "Cardigan": "TOP",
    "Vest top": "TOP",
    "Sweatshirt": "TOP",
    "Long sleeve top": "TOP",
    "Longsleeve": "TOP",

    # BOTTOMS
    "Trousers": "BOTTOM",
    "Jeans": "BOTTOM",
    "Shorts": "BOTTOM",
    "Skirt": "BOTTOM",
    "Leggings/Tights": "BOTTOM",

    # OUTERWEAR
    "Jacket": "OUTERWEAR",
    "Coat": "OUTERWEAR",
    "Blazer": "OUTERWEAR",

    # SHOES
    "Sneakers": "SHOES",
    "Boots": "SHOES",
    "Bootie": "SHOES",
    "Ballerinas": "SHOES",
    "Moccasins": "SHOES",
    "Pumps": "SHOES",
    "Heels": "SHOES",
    "Heeled sandals": "SHOES",
    "Sandals": "SHOES",
    "Flat shoe": "SHOES",
    "Flat shoes": "SHOES",
    "Flip flop": "SHOES",
    "Other shoe": "SHOES",

    # ACCESSORIES
    "Cap": "ACCESSORY",
    "Beanie": "ACCESSORY",
    "Headband": "ACCESSORY",
    "Hat/beanie": "ACCESSORY",
    "Hat/brim": "ACCESSORY",
    "Straw hat": "ACCESSORY",
    "Felt hat": "ACCESSORY",
    "Bucket hat": "ACCESSORY",
    "Bag": "ACCESSORY",
}

MACRO_LABEL_DE = {
    "ACCESSORY": "Kopf / Accessoires",
    "TOP": "Oberteil",
    "OUTERWEAR": "Jacke / Mantel",
    "BOTTOM": "Unterteil",
    "SHOES": "Schuhe",
}

MACRO_DISPLAY_ORDER = ["ACCESSORY", "TOP", "OUTERWEAR", "BOTTOM", "SHOES"]

# --- Gender / grober Stil (für Filter) ---
BUSINESS_TYPES = [
    "Blazer", "Shirt", "Blouse", "Trousers", "Skirt", "Coat",
    "Pumps", "Heels", "Heeled sandals", "Moccasins", "Flat shoe",
    "Bootie", "Boots", "Polo shirt",
]

ANTI_BUSINESS_KEYWORDS = [
    "jogger", "sweat", "runner", "loose", "relaxed", "cargo",
]

SPORT_KEYWORDS = [
    "sport", "running", "training", "gym", "racer", "seamless",
    "leggings", "bra",
]


def assign_gender(idx_name):
    idx = str(idx_name)
    if "Menswear" in idx:
        return "Herren"
    if "Baby" in idx or "Children" in idx:
        return "Kinder"
    return "Damen"


def assign_style(row):
    idx = str(row["index_name"])
    pt = str(row["product_type_name"])
    name = str(row["prod_name"]).lower()

    if "Baby" in idx or "Children" in idx:
        return "Kids"

    if "Sport" in idx:
        return "Sport"
    if pt in ("Sneakers", "Leggings/Tights"):
        return "Sport"
    if any(k in name for k in SPORT_KEYWORDS):
        return "Sport"

    if pt in BUSINESS_TYPES:
        if "Divided" in idx or any(k in name for k in ANTI_BUSINESS_KEYWORDS):
            return "Casual"
        return "Business / Chic"

    return "Casual"

# ---------------------------------------------------------
# 5. FARB-FAMILIEN (für Filter-UI)
# ---------------------------------------------------------
COLOR_FAMILY_MAP_UI = {
    # Beige / Braun
    "beige": "Beige/Brown",
    "dark beige": "Beige/Brown",
    "light beige": "Beige/Brown",
    "greyish beige": "Beige/Brown",
    "yellowish brown": "Beige/Brown",

    # Schwarz / Weiß / Grau
    "black": "Black",
    "white": "White",
    "off white": "White",
    "grey": "Grey",
    "gray": "Grey",
    "dark grey": "Grey",
    "light grey": "Grey",

    # Blau
    "blue": "Blue",
    "dark blue": "Blue",
    "light blue": "Blue",
    "other blue": "Blue",

    # Grün
    "green": "Green",
    "dark green": "Green",
    "light green": "Green",
    "other green": "Green",
    "greenish khaki": "Green",

    # Gelb
    "yellow": "Yellow",
    "dark yellow": "Yellow",
    "light yellow": "Yellow",
    "other yellow": "Yellow",

    # Orange
    "orange": "Orange",
    "dark orange": "Orange",
    "light orange": "Orange",
    "other orange": "Orange",

    # Rot
    "red": "Red",
    "dark red": "Red",
    "light red": "Red",
    "other red": "Red",

    # Pink
    "pink": "Pink",
    "dark pink": "Pink",
    "light pink": "Pink",
    "other pink": "Pink",

    # Lila
    "purple": "Purple",
    "dark purple": "Purple",
    "light purple": "Purple",
    "other purple": "Purple",

    # Türkis
    "turquoise": "Turquoise",
    "dark turquoise": "Turquoise",
    "light turquoise": "Turquoise",
    "other turquoise": "Turquoise",

    # Metallic
    "bronze/copper": "Metallic",
    "gold": "Metallic",
    "silver": "Metallic",

    # Transparent
    "transparent": "Transparent",

    # Sonstiges / Unbekannt
    "other": "Other/Unknown",
    "unknown": "Other/Unknown",
}

def get_color_family_ui(name: str) -> str:
    name = (name or "").strip().lower()
    if not name:
        return "Unbekannt"
    if name in COLOR_FAMILY_MAP_UI:
        return COLOR_FAMILY_MAP_UI[name]
    return name.title()

# ---------------------------------------------------------
# 6. DETAILLIERTE STIL- & FUNKTIONSLOGIK
# ---------------------------------------------------------
STYLE_KEYWORDS = {
    'SPORT': {'sport':3, 'running':3, 'gym':3, 'seamless':2, 'dry':2, 'leggings':1, 'bra':1},
    'ELEGANT': {'blazer':3, 'suit':3, 'tailored':3, 'satin':2, 'silk':2, 'blouse':2, 'pump':3, 'loafer':3},
    'STREETWEAR': {'hoodie':3, 'sweatshirt':3, 'oversized':2, 'relaxed':1, 'cargo':2, 'sneakers':2, 'cap':2, 'bucket':2},
    'SUMMER': {'linen':3, 'bikini':3, 'swim':3, 'shorts':2, 'sandal':3, 'straw':3, 'hat':1},
    'CASUAL': {'denim':2, 'jeans':2, 't-shirt':2, 'basic':2, 'jersey':1, 'cardigan':1, 'knit':1}
}

def get_style_category_v2(row):
    text = " ".join([
        str(row.get('product_type_name','') or ''),
        str(row.get('prod_name','') or ''),
        str(row.get('detail_desc','') or ''),
        str(row.get('index_name','') or ''),
    ]).lower()

    scores = {k: 0.0 for k in STYLE_KEYWORDS}
    for style, tokens in STYLE_KEYWORDS.items():
        for token, weight in tokens.items():
            if token in text:
                scores[style] += weight

    best_style = max(scores, key=scores.get)
    if scores[best_style] == 0:
        return 'CASUAL'
    return best_style

def get_functional_type(row):
    p_type = str(row.get('product_type_name', '')).lower()
    desc = str(row.get('detail_desc', '')).lower()

    if p_type in ['coat']:
        return 'HEAVY_OUTER'
    if p_type == 'jacket':
        if any(x in desc for x in ['padded', 'down', 'wool', 'warm', 'lined', 'puffer', 'heavy', 'faux fur', 'shearling']):
            return 'HEAVY_OUTER'

    if p_type in ['beanie', 'hat/beanie', 'scarf', 'gloves']:
        return 'WINTER_ACC'
    if p_type in ['boots', 'bootie']:
        return 'WINTER_SHOES'
    if p_type in ['sweater', 'cardigan']:
        if any(x in desc for x in ['wool', 'cashmere', 'knit', 'heavy', 'warm', 'mohair']):
            return 'WINTER_TOP'

    if p_type in ['sandals', 'flip flop', 'heeled sandals', 'mules']:
        return 'SUMMER_SHOES'
    if p_type in ['straw hat', 'cap', 'bucket hat', 'visor']:
        return 'SUMMER_ACC'
    if p_type in ['shorts', 'vest top', 'crop top', 'bikini', 'swimsuit']:
        return 'SUMMER_WEAR'
    if p_type == 'skirt':
        if 'linen' in desc or 'short' in desc or 'mini' in desc:
            return 'SUMMER_WEAR'
    if p_type == 'dress':
        if any(x in desc for x in ['linen', 'sleeveless', 'straps', 'viscose', 'beach']):
            return 'SUMMER_WEAR'

    if 'linen' in desc:
        return 'SUMMER_WEAR'

    if 'leggings' in p_type or 'tights' in p_type:
        return 'LEGGINGS'
    if p_type in ['blazer', 'suit']:
        return 'FORMAL_LAYER'

    return 'STANDARD'

def compute_functional_penalty(base_row, cand_row):
    type_a = get_functional_type(base_row)
    type_b = get_functional_type(cand_row)

    if type_a == 'STANDARD' or type_b == 'STANDARD':
        return 0.0

    pair = {type_a, type_b}

    winter_group = {'HEAVY_OUTER', 'WINTER_ACC', 'WINTER_SHOES', 'WINTER_TOP'}
    summer_group = {'SUMMER_SHOES', 'SUMMER_ACC', 'SUMMER_WEAR'}

    if (type_a in winter_group and type_b in summer_group) or \
       (type_b in winter_group and type_a in summer_group):
        return -10.0

    if 'LEGGINGS' in pair:
        if 'HEAVY_OUTER' in pair:
            return -10.0
        if 'SUMMER_SHOES' in pair:
            return -5.0
        if 'FORMAL_LAYER' in pair:
            return -3.0

    if type_a == 'HEAVY_OUTER' and type_b == 'HEAVY_OUTER':
        return -10.0

    if 'WINTER_SHOES' in pair and 'SUMMER_WEAR' in pair:
        return -5.0

    return 0.0

def compute_style_score(base_style, cand_style):
    if base_style == cand_style:
        return 5.0

    matches = {
        ('ELEGANT', 'CASUAL'): 3.0,
        ('CASUAL', 'ELEGANT'): 3.0,
        ('SPORT', 'STREETWEAR'): 4.0,
        ('STREETWEAR', 'SPORT'): 4.0,
        ('STREETWEAR', 'CASUAL'): 4.0,
        ('CASUAL', 'STREETWEAR'): 4.0,
        ('SUMMER', 'CASUAL'): 3.0,
        ('CASUAL', 'SUMMER'): 3.0,
        ('SUMMER', 'STREETWEAR'): 2.0,
        ('STREETWEAR', 'SUMMER'): 2.0,
        ('ELEGANT', 'SPORT'): -10.0,
        ('SPORT', 'ELEGANT'): -10.0,
        ('ELEGANT', 'SUMMER'): -5.0,
        ('SUMMER', 'ELEGANT'): -5.0,
    }
    return matches.get((base_style, cand_style), 0.0)

# ---------------------------------------------------------
# 7. FARB-LOGIK FÜR MATCHING
# ---------------------------------------------------------
COLOR_FAMILY_MAP_MATCH = {
    'greenish khaki': 'olive',
    'khaki': 'olive',
    'olive': 'olive',
    'yellowish green': 'olive',
    'lime': 'olive',

    'bluish green': 'turquoise',
    'turquoise': 'turquoise',
    'teal': 'turquoise',
    'aqua': 'turquoise',

    'yellowish brown': 'brown',
    'bronze': 'orange',
    'copper': 'orange',
    'gold': 'yellow',
    'mustard': 'yellow',
    'lilac': 'purple',
    'mole': 'brown',

    'black': 'black',
    'white': 'white', 'off white': 'white', 'transparent': 'white',
    'grey': 'grey', 'silver': 'grey', 'metal': 'grey',
    'beige': 'brown', 'brown': 'brown',

    'blue': 'blue',
    'red': 'red',
    'pink': 'pink',
    'orange': 'orange',
    'yellow': 'yellow',
    'green': 'green',
    'purple': 'purple',

    'undefined': 'other',
    'unknown': 'other',
    'other': 'other',
    'multi': 'multi',
}

COLOR_WHEEL = [
    'red',
    'orange',
    'yellow',
    'olive',
    'green',
    'turquoise',
    'blue',
    'purple',
    'pink',
]

def get_color_family_match(name: str) -> str:
    if not isinstance(name, str):
        return 'other'
    name = name.lower()
    for k, v in COLOR_FAMILY_MAP_MATCH.items():
        if k in name:
            return v
    return 'other'

def classify_color(base_row, cand_row):
    m1 = str(base_row.get('perceived_colour_master_name', '')).lower()
    m2 = str(cand_row.get('perceived_colour_master_name', '')).lower()
    g1 = str(base_row.get('colour_group_name', '')).lower()
    g2 = str(cand_row.get('colour_group_name', '')).lower()

    fam1 = get_color_family_match(g1)
    if fam1 in ('other', 'multi'):
        fam1 = get_color_family_match(m1)
    fam2 = get_color_family_match(g2)
    if fam2 in ('other', 'multi'):
        fam2 = get_color_family_match(m2)

    neutrals = ['black', 'white', 'grey', 'brown']
    if fam1 in neutrals or fam2 in neutrals:
        if (fam1 == 'brown' and fam2 == 'grey') or (fam1 == 'grey' and fam2 == 'brown'):
            return "Conditional"
        return "Allowed"

    if fam1 == fam2:
        return "Allowed"

    if fam1 == 'blue' or fam2 == 'blue':
        return "Allowed"

    if fam1 in COLOR_WHEEL and fam2 in COLOR_WHEEL:
        idx1 = COLOR_WHEEL.index(fam1)
        idx2 = COLOR_WHEEL.index(fam2)
        dist = abs(idx1 - idx2)
        dist = min(dist, len(COLOR_WHEEL) - dist)
        if dist <= 1:
            return "Allowed"
        if dist == 2:
            return "Conditional"

    return "Not recommended"

def compute_color_score(base_row, candidate_row) -> float:
    res = classify_color(base_row, candidate_row)
    if res == "Allowed":
        return 5.0
    if res == "Conditional":
        return 2.0
    return -5.0

# ---------------------------------------------------------
# 8. DATENLADEN
# ---------------------------------------------------------
@st.cache_data
def load_copurchase():
    parts_dir = COPURCHASE_PARTS_DIR
    part_files = sorted(parts_dir.glob("copurchase_part_*.csv"))
    if not part_files:
        raise FileNotFoundError(f"Keine Split-Dateien gefunden in {parts_dir}")

    dfs = []
    for f in part_files:
        df = pd.read_csv(f)
        dfs.append(df)

    df_all = pd.concat(dfs, ignore_index=True)
    df_all["article_id_1"] = df_all["article_id_1"].astype(int)
    df_all["article_id_2"] = df_all["article_id_2"].astype(int)
    return df_all

@st.cache_data
def load_articles():
    df = pd.read_csv(ARTICLES_FILE)

    df["article_id"] = df["article_id"].astype(int)
    df["article_id_str"] = df["article_id"].astype(str).str.zfill(10)

    df["macro_category"] = df["product_type_name"].map(PRODUCT_TYPE_TO_MACRO)

    df["gender"] = df["index_name"].apply(assign_gender)
    df["style"] = df.apply(assign_style, axis=1)

    df["colour_group_name"] = df["colour_group_name"].fillna("Unbekannt")
    df["colour_family"] = df["colour_group_name"].apply(get_color_family_ui)

    df["style_category"] = df.apply(get_style_category_v2, axis=1)

    return df

# ---------------------------------------------------------
# 9. HILFSFUNKTIONEN ALLGEMEIN
# ---------------------------------------------------------
def get_image_url(article_id_str: str) -> str:
    folder = article_id_str[:3]
    filename = f"{article_id_str}.jpg"
    return f"{IMAGES_BASE_URL}/{folder}/{filename}"

def get_base_article_row(df_articles, article_id):
    rows = df_articles[df_articles["article_id"] == article_id]
    if rows.empty:
        return None
    return rows.iloc[0]

def get_target_macros_for_base(base_macro):
    if base_macro == "TOP":
        return ["BOTTOM", "SHOES", "OUTERWEAR", "ACCESSORY"]
    elif base_macro == "BOTTOM":
        return ["TOP", "SHOES", "OUTERWEAR", "ACCESSORY"]
    elif base_macro == "SHOES":
        return ["TOP", "BOTTOM", "OUTERWEAR", "ACCESSORY"]
    elif base_macro == "OUTERWEAR":
        return ["TOP", "BOTTOM", "SHOES", "ACCESSORY"]
    elif base_macro == "ACCESSORY":
        return ["TOP", "BOTTOM", "SHOES", "OUTERWEAR"]
    else:
        return ["TOP", "BOTTOM", "SHOES", "OUTERWEAR", "ACCESSORY"]

# ---------------------------------------------------------
# 10. CANDIDATE-GENERIERUNG & HYBRID-SCORING
# ---------------------------------------------------------
def get_copurchase_candidates(base_article_id, df_articles, df_cop):
    mask = (df_cop["article_id_1"] == base_article_id) | (df_cop["article_id_2"] == base_article_id)
    df_pairs = df_cop[mask].copy()
    if df_pairs.empty:
        return pd.DataFrame()

    def _partner(row):
        return row["article_id_2"] if row["article_id_1"] == base_article_id else row["article_id_1"]

    df_pairs["partner_id"] = df_pairs.apply(_partner, axis=1)

    df_agg = (
        df_pairs.groupby("partner_id")["count"]
        .sum()
        .reset_index()
        .rename(columns={"count": "copurchase_count"})
    )

    df_merged = df_agg.merge(
        df_articles,
        left_on="partner_id",
        right_on="article_id",
        how="left",
    )

    if "macro_category" not in df_merged.columns:
        df_merged["macro_category"] = df_merged["product_type_name"].map(PRODUCT_TYPE_TO_MACRO)

    df_merged = df_merged[df_merged["partner_id"] != base_article_id]
    df_merged = df_merged[~df_merged["macro_category"].isna()]
    df_merged = df_merged.sort_values("copurchase_count", ascending=False)

    return df_merged

def compute_hybrid_score(base_row, cand_row):
    c_score = compute_color_score(base_row, cand_row)
    base_style = base_row.get('style_category', get_style_category_v2(base_row))
    cand_style = cand_row.get('style_category', get_style_category_v2(cand_row))
    s_score = compute_style_score(base_style, cand_style)
    f_penalty = compute_functional_penalty(base_row, cand_row)
    final_score = (s_score * 1.5) + c_score + f_penalty
    return final_score

def rerank_hybrid(base_row, df_cat: pd.DataFrame) -> pd.DataFrame:
    if df_cat.empty:
        return df_cat

    df_cat = df_cat.copy()

    def calculate_components(row):
        c = compute_color_score(base_row, row)
        b_style = base_row.get('style_category', 'CASUAL')
        c_style = row.get('style_category', 'CASUAL')
        s = compute_style_score(b_style, c_style)
        p = compute_functional_penalty(base_row, row)
        final = (s * 1.5) + c + p
        return pd.Series([s, c, p, final])

    df_cat[['style_score', 'color_score', 'func_penalty', 'final_score']] = df_cat.apply(
        calculate_components, axis=1
    )

    df_cat = df_cat.sort_values(
        by=["final_score", "copurchase_count"],
        ascending=[False, False],
    ).reset_index(drop=True)

    return df_cat

def get_similar_articles(base_row, df_articles, max_neighbors: int = 30):
    base_article_id = int(base_row["article_id"])
    base_macro = base_row.get("macro_category", None)
    if pd.isna(base_macro):
        return []

    pool = df_articles[
        (df_articles["macro_category"] == base_macro)
        & (df_articles["article_id"] != base_article_id)
    ].copy()
    if pool.empty:
        return []

    base_pt = base_row.get("product_type_name", None)
    if isinstance(base_pt, str) and base_pt:
        same_pt = pool[pool["product_type_name"] == base_pt]
        if len(same_pt) >= 5:
            pool = same_pt

    pool["similarity_score"] = pool.apply(
        lambda r: compute_hybrid_score(base_row, r),
        axis=1,
    )
    pool = pool.sort_values("similarity_score", ascending=False).head(max_neighbors)
    return pool["article_id"].astype(int).tolist()

def get_copurchases_from_similar(similar_article_ids, base_article_id, df_articles, df_cop):
    if not similar_article_ids:
        return pd.DataFrame()

    df_sim = df_cop[
        df_cop["article_id_1"].isin(similar_article_ids)
        | df_cop["article_id_2"].isin(similar_article_ids)
    ].copy()
    if df_sim.empty:
        return pd.DataFrame()

    def _partner_from_sim(row):
        return row["article_id_2"] if row["article_id_1"] in similar_article_ids else row["article_id_1"]

    df_sim["partner_id"] = df_sim.apply(_partner_from_sim, axis=1)

    df_agg = (
        df_sim.groupby("partner_id")["count"]
        .sum()
        .reset_index()
        .rename(columns={"count": "copurchase_count"})
    )

    df_merged = df_agg.merge(
        df_articles,
        left_on="partner_id",
        right_on="article_id",
        how="left",
    )

    if "macro_category" not in df_merged.columns:
        df_merged["macro_category"] = df_merged["product_type_name"].map(PRODUCT_TYPE_TO_MACRO)

    df_merged = df_merged[df_merged["partner_id"] != base_article_id]
    df_merged = df_merged[~df_merged["macro_category"].isna()]
    df_merged = df_merged.sort_values("copurchase_count", ascending=False)

    return df_merged

def get_outfit_recommendations(base_article_id, df_articles, df_cop, n_per_category=3):
    if "macro_category" not in df_articles.columns:
        df_articles = df_articles.copy()
        df_articles["macro_category"] = df_articles["product_type_name"].map(PRODUCT_TYPE_TO_MACRO)

    if "style_category" not in df_articles.columns:
        df_articles["style_category"] = df_articles.apply(get_style_category_v2, axis=1)

    base_row = get_base_article_row(df_articles, base_article_id)
    if base_row is None:
        return {}

    base_index = str(base_row.get('index_name', '')).lower()
    base_macro = base_row.get("macro_category", None)
    target_macros = get_target_macros_for_base(base_macro)

    candidates_direct = get_copurchase_candidates(base_article_id, df_articles, df_cop)
    if candidates_direct is not None and not candidates_direct.empty:
        candidates_direct["source_type"] = "direct"
    else:
        candidates_direct = pd.DataFrame()

    similar_ids = get_similar_articles(base_row, df_articles, max_neighbors=20)
    candidates_similar = get_copurchases_from_similar(similar_ids, base_article_id, df_articles, df_cop)
    if candidates_similar is not None and not candidates_similar.empty:
        candidates_similar["source_type"] = "similar"
    else:
        candidates_similar = pd.DataFrame()

    all_candidates = pd.concat([candidates_direct, candidates_similar], ignore_index=True)

    if not all_candidates.empty:
        meta_cols = [c for c in all_candidates.columns if c not in ['article_id', 'copurchase_count', 'source_type']]
        all_candidates = all_candidates.groupby('article_id').agg({
            'copurchase_count': 'sum',
            **{c: 'first' for c in meta_cols}
        }).reset_index()
    else:
        all_candidates = pd.DataFrame(columns=["article_id", "macro_category", "copurchase_count", "style_category"])

    if "macro_category" not in all_candidates.columns and "product_type_name" in all_candidates.columns:
        all_candidates["macro_category"] = all_candidates["product_type_name"].map(PRODUCT_TYPE_TO_MACRO)

    if "style_category" not in all_candidates.columns and 'article_id' in all_candidates.columns:
        temp_map = df_articles.set_index('article_id')['style_category']
        all_candidates['style_category'] = all_candidates['article_id'].map(temp_map).fillna('CASUAL')

    if "index_name" not in all_candidates.columns and 'article_id' in all_candidates.columns:
        idx_map = df_articles.set_index('article_id')['index_name']
        all_candidates['index_name'] = all_candidates['article_id'].map(idx_map)

    candidate_pools = {}

    for macro in target_macros:
        pool = all_candidates[all_candidates["macro_category"] == macro] if not all_candidates.empty else pd.DataFrame()

        if not pool.empty and base_index and 'index_name' in pool.columns:
            pool = pool[pool['index_name'].str.lower() == base_index]

        if not pool.empty:
            pool = rerank_hybrid(base_row, pool)
            pool = pool[pool['style_score'] >= 3.0]
            pool = pool[pool['color_score'] >= 3.0]
            pool = pool[pool['final_score'] >= 5.0]

        if len(pool) < 10:
            needed = 10 - len(pool)

            fallback_source = df_articles[
                (df_articles["macro_category"] == macro)
                & (df_articles["article_id"] != base_article_id)
            ]

            if base_index:
                fallback_source = fallback_source[fallback_source['index_name'].str.lower() == base_index]

            if not pool.empty:
                fallback_source = fallback_source[~fallback_source['article_id'].isin(set(pool['article_id']))]

            if not fallback_source.empty and needed > 0:
                fallback_source = fallback_source.copy()
                fallback_source['is_safe'] = 0

                safe_colors = ['black', 'white', 'off white', 'grey', 'dark grey', 'light grey',
                               'blue', 'dark blue', 'denim blue']

                fallback_source['is_safe'] = fallback_source['colour_group_name'].str.lower().isin(safe_colors).astype(int)

                top_candidates = fallback_source.sort_values('is_safe', ascending=False).head(50)
                sample = top_candidates.sample(
                    n=min(len(top_candidates), needed * 5),
                    random_state=42
                ).copy()
                sample["copurchase_count"] = 0

                sample = rerank_hybrid(base_row, sample)
                sample = sample[
                    (sample['style_score'] >= 3.0) &
                    (sample['color_score'] >= 3.0) &
                    (sample['final_score'] >= 7.0)
                ]

                pool = pd.concat([pool, sample.head(needed)], ignore_index=True)

        candidate_pools[macro] = pool.head(10).copy() if not pool.empty else pd.DataFrame()

    recommendations = {}
    for macro in target_macros:
        current_pool = candidate_pools.get(macro, pd.DataFrame())
        if current_pool.empty:
            continue

        def calculate_outfit_score(row):
            base_score = row['final_score']
            peer_scores = []
            for other_macro, other_pool in candidate_pools.items():
                if other_macro == macro or other_pool.empty:
                    continue
                top_peers = other_pool.head(3)
                for _, peer_row in top_peers.iterrows():
                    s = compute_hybrid_score(row, peer_row)
                    peer_scores.append(s)
            if not peer_scores:
                return base_score
            avg_peer_score = sum(peer_scores) / len(peer_scores)
            return (base_score * 0.6) + (avg_peer_score * 0.4)

        current_pool = current_pool.copy()
        current_pool['display_score'] = current_pool.apply(calculate_outfit_score, axis=1)
        current_pool = current_pool.sort_values('display_score', ascending=False)
        current_pool['final_score'] = current_pool['display_score']
        recommendations[macro] = current_pool.head(n_per_category)

    return recommendations

# ---------------------------------------------------------
# 11. UI – SELECTION VIEW
# ---------------------------------------------------------
def render_select_view(df_articles: pd.DataFrame):
    scroll_to_top()
    st.title("H&M Outfit Recommender – Hybrid")

    st.markdown(
        "Wähle Zielgruppe, Stil, Kategorie, Artikelart und Farbe. "
        "Klicke anschließend auf ein Basisteil, um ein komplettes Outfit zu erstellen."
    )

    df = df_articles.copy()

    # 1. Gender Buttons
    genders = ["Damen", "Herren", "Kinder"]
    if "sel_gender" not in st.session_state:
        st.session_state["sel_gender"] = "Damen"

    c1, c2, c3 = st.columns(3)
    for i, g in enumerate(genders):
        col = [c1, c2, c3][i]
        btn_type = "primary" if st.session_state["sel_gender"] == g else "secondary"
        with col:
            if st.button(f"👤 {g}", key=f"gender_{g}", type=btn_type, use_container_width=True):
                st.session_state["sel_gender"] = g
                st.session_state["sel_style"] = "Kids" if g == "Kinder" else "Casual"
                st.session_state["sel_macro"] = None
                st.session_state["sel_subcat"] = "Alle"
                st.session_state["sel_colour"] = "Alle"
                st.rerun()

    df_g = df[df["gender"] == st.session_state["sel_gender"]]

    
    
    # 2. Filterleiste
    with st.container(border=True):
        fc1, fc2, fc3, fc4 = st.columns(4)

        # Stil
        with fc1:
            is_kids = st.session_state["sel_gender"] == "Kinder"
            style_opts = ["Kids"] if is_kids else ["Casual", "Business / Chic", "Sport"]
            cur_style = st.session_state.get("sel_style", style_opts[0])
            if cur_style not in style_opts:
                cur_style = style_opts[0]
            sel_style = st.selectbox(
                "1. Stil",
                options=style_opts,
                index=style_opts.index(cur_style),
                key="sb_style",
                disabled=is_kids,
            )
            st.session_state["sel_style"] = sel_style

        df_s = df_g[df_g["style"] == sel_style]

        # Kategorie (macro_category)
        with fc2:
            macros = sorted(df_s["macro_category"].dropna().unique())
            if not macros:
                st.warning("Keine Artikel für diesen Filter gefunden.")
                return
            cur_macro = st.session_state.get("sel_macro")
            if cur_macro not in macros:
                cur_macro = "TOP" if "TOP" in macros else macros[0]
            sel_macro = st.selectbox(
                "2. Kategorie",
                options=macros,
                index=macros.index(cur_macro),
                format_func=lambda x: MACRO_LABEL_DE.get(x, x),
                key="sb_macro",
            )
            st.session_state["sel_macro"] = sel_macro

        df_m = df_s[df_s["macro_category"] == sel_macro]

        # Artikelart
        with fc3:
            subcats = sorted(df_m["product_type_name"].dropna().unique())
            subcat_options = ["Alle"] + subcats
            cur_subcat = st.session_state.get("sel_subcat", "Alle")
            if cur_subcat not in subcat_options:
                cur_subcat = "Alle"
            sel_subcat = st.selectbox(
                "3. Artikelart",
                options=subcat_options,
                index=subcat_options.index(cur_subcat),
                key="sb_subcat",
            )
            st.session_state["sel_subcat"] = sel_subcat

        if sel_subcat != "Alle":
            df_m = df_m[df_m["product_type_name"] == sel_subcat]

        # Farbe (colour_family)
        with fc4:
            colour_values = sorted(df_m["colour_family"].dropna().unique())
            colour_options = ["Alle"] + colour_values
            cur_colour = st.session_state.get("sel_colour", "Alle")
            if cur_colour not in colour_options:
                cur_colour = "Alle"
            sel_colour = st.selectbox(
                "4. Farbe",
                options=colour_options,
                index=colour_options.index(cur_colour),
                key="sb_colour",
            )
            st.session_state["sel_colour"] = sel_colour

        if sel_colour != "Alle":
            df_m = df_m[df_m["colour_family"] == sel_colour]

    # 3. Grid mit Basisteilen
    st.markdown("---")
    if df_m.empty:
        st.warning("Keine Artikel für diese Auswahl gefunden.")
        return

    df_m = df_m.sort_values(["product_type_name", "prod_name"])
    df_show = df_m.head(80)
    st.caption(f"{len(df_m)} Artikel gefunden, zeige bis zu {len(df_show)} im Grid.")

    cols = st.columns(6)
    current_base_id = st.session_state.get("base_article_id")

    for i, row in enumerate(df_show.itertuples()):
        with cols[i % 6]:
            img_url = get_image_url(row.article_id_str)
            if img_url:
                st.image(img_url, use_container_width=True)
            else:
                st.write("Kein Bild")

            clean_name = (row.prod_name or "").strip()
            if len(clean_name) > 16:
                clean_name = clean_name[:14] + ".."
            label = f"{clean_name}\n({row.colour_group_name})"

            # Button-Typ abhängig davon, ob dieses Teil aktuell Basisteil ist
            is_current_base = current_base_id == int(row.article_id)
            btn_type = "primary" if is_current_base else "secondary"

            if st.button(label, key=f"btn_{row.article_id}", type=btn_type):
                st.session_state["base_article_id"] = int(row.article_id)
                st.session_state["view"] = "outfit"
                st.rerun()

# ---------------------------------------------------------
# 12. UI – OUTFIT VIEW
# ---------------------------------------------------------
def render_outfit_view(df_articles: pd.DataFrame, df_cop: pd.DataFrame, base_article_id: int):
    scroll_to_top()
    base_row = get_base_article_row(df_articles, base_article_id)
    if base_row is None:
        st.error("Basisteil nicht mehr in den Daten gefunden.")
        if st.button("Zurück zur Auswahl"):
            st.session_state["view"] = "select"
            st.rerun()
        return

    st.title("Hund wer den Selector nicht benutzt 🐶")

    col_left, col_right = st.columns([1.4, 2.6])

    with col_left:
        st.subheader("Basisteil")

        img_url = get_image_url(base_row["article_id_str"])
        if img_url:
            st.image(img_url, use_container_width=True)
        else:
            st.write("Kein Bild gefunden.")

        st.markdown(f"**ID:** {base_row['article_id_str']}")
        st.markdown(f"**Name:** {base_row.get('prod_name', '')}")

        st.caption(
            "%s · %s · %s"
            % (
                base_row.get("product_type_name", ""),
                base_row.get("product_group_name", ""),
                base_row.get("index_name", ""),
            )
        )
        st.caption(
            "Farbe: %s, %s"
            % (
                base_row.get("colour_group_name", ""),
                base_row.get("perceived_colour_master_name", ""),
            )
        )

        base_style = base_row.get('style_category', 'Unbekannt')
        base_func = get_functional_type(base_row)
        st.info(f"Erkannter Stil: **{base_style}**\n\nFunktions-Typ: **{base_func}**")

        st.markdown("---")
        st.markdown(
            """
**Wie entsteht dieser Outfit-Vorschlag?**

- Ausgangspunkt ist dein gewähltes Basisteil.
- Co-Purchase-Daten zeigen, welche Teile häufig mit ähnlichen Artikeln zusammen gekauft wurden.
- Ein Farb- und Stil-Score filtert harmonische Kombinationen heraus.
- Ein Saison-/Funktions-Check vermeidet unlogische Paarungen (z. B. Wintermantel + Sandalen).
- Ein Cross-Check bewertet zusätzlich, wie gut alle Teile auch untereinander zusammenpassen.
            """
        )


    with col_right:
        st.subheader("Outfit-Vorschlag (von Kopf bis Fuß)")

        if "selected_outfit" not in st.session_state:
            st.session_state["selected_outfit"] = {}
        selected_outfit: Dict[str, int] = st.session_state["selected_outfit"]

        recommendations = get_outfit_recommendations(
            base_article_id=base_article_id,
            df_articles=df_articles,
            df_cop=df_cop,
            n_per_category=3,
        )

        if not recommendations:
            st.info("Keine passenden Empfehlungen gefunden. Möglicherweise zu wenig Transaktionsdaten.")
        else:
            macros_with_recs = []

            for macro in MACRO_DISPLAY_ORDER:
                if macro not in recommendations:
                    continue
                rec_df = recommendations[macro]
                if rec_df.empty:
                    continue

                macros_with_recs.append(macro)

                label = MACRO_LABEL_DE.get(macro, macro)
                st.markdown(f"##### {label}")

                cols = st.columns(len(rec_df))
                for col, (_, row) in zip(cols, rec_df.iterrows()):
                    with col:
                        img_url = get_image_url(row["article_id_str"])
                        if img_url:
                            st.image(img_url, use_container_width=True)
                        else:
                            st.write("Kein Bild")

                        prod_name = row.get("prod_name", "")
                        if len(prod_name) > 25:
                            prod_name = prod_name[:22] + "..."
                        st.write(f"**{prod_name}**")

                        # Score-Visualisierung (aus demo7_np übernommen)
                        if 'style_score' in row and 'color_score' in row:
                            s_score = float(row['style_score'])
                            c_score = float(row['color_score'])
                            f_penalty = float(row.get('func_penalty', 0.0))
                            final_display = float(row.get("final_score", 0.0))
                        else:
                            s_score = 0.0
                            c_score = compute_color_score(base_row, row)
                            f_penalty = 0.0
                            final_display = 0.0

                        style_color = "green" if s_score >= 4 else "orange" if s_score >= 2 else "red"
                        color_color = "green" if c_score >= 4 else "orange" if c_score >= 1 else "red"

                        st.markdown(f"""
                        <div style="
                            font-size: small;
                            line-height: 1.4;
                            background-color: #262730;
                            color: #ffffff;
                            padding: 5px 6px;
                            border-radius: 8px;
                            border: 1px solid #555;
                        ">
                            <b>Score: {final_display:.1f}</b><br>
                            <span style="color:{style_color}">Stil: {s_score:+.1f}</span> • 
                            <span style="color:{color_color}">Farbe: {c_score:+.1f}</span>
                        </div>
                        """, unsafe_allow_html=True)


                        if f_penalty < 0:
                            st.markdown(
                                f"<span style='color:red; font-weight:bold; font-size:small'>⚠️ Penalty: {f_penalty}</span>",
                                unsafe_allow_html=True,
                            )

                        st.caption(f"{row.get('product_type_name', '')}")
                        st.caption(f"Co-Purchases: {int(row.get('copurchase_count', 0))}")

                        
                        art_id = int(row["article_id"])
                        is_selected = selected_outfit.get(macro) == art_id

                        # Button-Typ je nach Auswahl
                        btn_type = "primary" if is_selected else "secondary"

                        if st.button("Auswählen", key=f"choose_{macro}_{art_id}", type=btn_type):
                            selected_outfit[macro] = art_id
                            st.session_state["selected_outfit"] = selected_outfit
                            st.rerun()

                        if is_selected:
                            st.caption("✅ aktuell gewählt")




            if macros_with_recs:
                num_selected = sum(1 for m in macros_with_recs if m in selected_outfit)
                all_selected = all(m in selected_outfit for m in macros_with_recs)

                st.markdown("---")
                st.caption(f"{num_selected}/{len(macros_with_recs)} Kategorien ausgewählt.")

                if all_selected:
                    if st.button("Gewähltes Outfit anzeigen"):
                        st.session_state["view"] = "summary"
                        st.rerun()
                else:
                    st.info("Wähle in jeder Kategorie einen Favoriten, um das Outfit zu finalisieren.")

    st.markdown("---")
    if st.button("Zurück zur Auswahl"):
        st.session_state["view"] = "select"
        st.rerun()

# ---------------------------------------------------------
# 13. UI – SUMMARY VIEW
# ---------------------------------------------------------
def render_summary_view(df_articles: pd.DataFrame):
    """
    Zeigt das vom Nutzer gewählte Outfit (inkl. Basisteil) in einer
    klaren Reihenfolge von Kopf bis Fuß.
    """
    st.title("Dein gewähltes Outfit")

    # Basisteil laden
    base_article_id = st.session_state.get("base_article_id", None)
    base_row = get_base_article_row(df_articles, base_article_id) if base_article_id is not None else None

    selected_outfit: Dict[str, int] = st.session_state.get("selected_outfit", {})

    if base_row is None or not selected_outfit:
        st.info("Noch kein vollständiges Outfit ausgewählt.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Zurück zu den Vorschlägen"):
                st.session_state["view"] = "outfit"
                st.rerun()
        with col2:
            if st.button("Neue Auswahl starten"):
                st.session_state["selected_outfit"] = {}
                st.session_state["base_article_id"] = None
                st.session_state["view"] = "select"
                st.rerun()
        return

    # -------------------------------------------------
    # 1. Basisteil – groß oben
    # -------------------------------------------------
    st.subheader("Basisteil")

    c_img, c_info = st.columns([1, 2])
    with c_img:
        img_url = get_image_url(base_row["article_id_str"])
        if img_url:
            st.image(img_url, use_container_width=True)
        else:
            st.write("Kein Bild")

    with c_info:
        st.markdown(f"**{base_row.get('prod_name', '')}**")
        st.caption(
            f"{base_row.get('product_type_name', '')} · "
            f"{base_row.get('product_group_name', '')} · "
            f"{base_row.get('index_name', '')}"
        )
        st.caption(
            f"ID: {base_row['article_id_str']} · "
            f"{base_row.get('colour_group_name', '')} · "
            f"{base_row.get('perceived_colour_master_name', '')}"
        )

    st.markdown("---")

    # -------------------------------------------------
    # 2. Outfit von Kopf bis Fuß
    # -------------------------------------------------
    st.subheader("Komplettes Outfit (von Kopf bis Fuß)")

    # Reihenfolge Kopf → Oberteil → Jacke → Unterteil → Schuhe
    base_order = ["ACCESSORY", "TOP", "OUTERWEAR", "BOTTOM", "SHOES", "ONE_PIECE"]
    macros_to_show = [
        m for m in base_order if m in selected_outfit
    ] + [
        m for m in selected_outfit.keys() if m not in base_order
    ]

    cols = st.columns(len(macros_to_show)) if macros_to_show else [st]

    for col, macro in zip(cols, macros_to_show):
        art_id = selected_outfit[macro]
        row = get_base_article_row(df_articles, art_id)
        if row is None:
            continue

        with col:
            img_url = get_image_url(row["article_id_str"])
            if img_url:
                st.image(img_url, use_container_width=True)
            else:
                st.write("Kein Bild")

            label = MACRO_LABEL_DE.get(macro, macro)
            st.markdown(f"**{label}**")
            st.caption(row.get("product_type_name", ""))
            st.write(row.get("prod_name", ""))
            st.caption(f"ID: {row['article_id_str']}")
            st.caption(
                f"{row.get('colour_group_name', '')} · "
                f"{row.get('perceived_colour_master_name', '')}"
            )

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Zurück zu den Vorschlägen"):
            st.session_state["view"] = "outfit"
            st.rerun()
    with col2:
        if st.button("Neue Auswahl starten"):
            st.session_state["selected_outfit"] = {}
            st.session_state["base_article_id"] = None
            st.session_state["view"] = "select"
            st.rerun()


# ---------------------------------------------------------
# 14. MAIN
# ---------------------------------------------------------
def main():
    try:
        df_articles = load_articles()
    except FileNotFoundError:
        st.error(f"articles_filtered.csv nicht gefunden. Pfad prüfen: {ARTICLES_FILE}")
        st.stop()
    except Exception as e:
        st.error(f"Fehler beim Laden von articles_filtered.csv: {e}")
        st.stop()

    try:
        df_cop = load_copurchase()
    except FileNotFoundError:
        st.error("Split-Dateien nicht gefunden. Prüfe Ordner: data_processed/copurchase_parts_5/")
        st.stop()
    except Exception as e:
        st.error(f"Fehler beim Laden der Co-Purchase-Daten: {e}")
        st.stop()

    if "view" not in st.session_state:
        st.session_state["view"] = "select"
    if "base_article_id" not in st.session_state:
        st.session_state["base_article_id"] = None

    if st.session_state["view"] == "select":
        render_select_view(df_articles)
    elif st.session_state["view"] == "outfit":
        base_article_id = st.session_state.get("base_article_id")
        if base_article_id is None:
            st.session_state["view"] = "select"
            st.rerun()
        render_outfit_view(df_articles, df_cop, base_article_id)
    elif st.session_state["view"] == "summary":
        render_summary_view(df_articles)

if __name__ == "__main__":
    main()
