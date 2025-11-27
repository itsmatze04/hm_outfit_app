import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from pathlib import Path
import time
import math
import requests
from PIL import Image
import colorsys
from collections import Counter

# ---------------------------------------------------------
# 1. KONFIGURATION & CSS
# ---------------------------------------------------------
st.set_page_config(
    page_title="H&M Style Guide",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# DEINE FARBE (Marineblau)
PRIMARY_COLOR = "#004080" 

st.markdown(f"""
<style>
    /* --- INTRO PAGE (FIX) --- */
    /* Wir nutzen kein 'fixed' mehr, damit der Button nicht verschwindet */
    
    .intro-container {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        /* Vertikale Zentrierung ohne Scrollen */
        min-height: 80vh; 
        text-align: center;
    }}
    
    .intro-title {{
        /* Rundere, moderne Schrift */
        font-family: "Arial Rounded MT Bold", "Helvetica Rounded", Arial, sans-serif;
        font-size: 90px;
        font-weight: 900; /* Extra Fett */
        letter-spacing: -3px;
        color: #ffffff;
        margin-bottom: 0px;
        line-height: 1.0;
        text-shadow: 0px 0px 20px rgba(0, 64, 128, 0.5); /* Leichter Glow in Marineblau */
    }}
    
    .intro-subtitle {{
        font-family: "Source Sans Pro", sans-serif;
        font-size: 22px;
        font-weight: 300;
        color: #a0c0e0; /* Leichtes Blau-Grau */
        margin-top: 15px;
        margin-bottom: 40px;
    }}
    
    /* Credits ganz klein */
    .intro-credits {{
        font-family: monospace;
        font-size: 10px;
        color: #444;
        margin-top: 60px;
    }}

    /* --- BUTTONS (MARINEBLAU) --- */
    
    /* Primary (Ausgewählt / Wichtig) */
    div[data-testid="stButton"] button[kind="primary"] {{
        background-color: {PRIMARY_COLOR} !important;
        color: white !important;
        border: 1px solid {PRIMARY_COLOR} !important;
        font-weight: bold !important;
        border-radius: 8px !important;
    }}
    div[data-testid="stButton"] button[kind="primary"]:hover {{
        background-color: #003366 !important; /* Dunkleres Blau beim Hover */
        border-color: #003366 !important;
    }}

    /* Secondary (Nicht ausgewählt) - Transparent/Dunkel */
    div[data-testid="stButton"] button[kind="secondary"] {{
        background-color: #1e1e1e !important;
        color: #cccccc !important;
        border: 1px solid transparent !important;
        border-radius: 8px !important;
    }}
    div[data-testid="stButton"] button[kind="secondary"]:hover {{
        background-color: #333333 !important;
        color: white !important;
        border: 1px solid #555 !important;
    }}

    /* --- BILDER (BÜNDIG & RAHMEN) --- */
    div[data-testid="stImage"] img {{
        height: 280px !important;
        object-fit: contain !important;
        background-color: #ffffff;
        border-radius: 8px;
        padding: 5px;
        border: 1px solid #333; /* Dunklerer Rahmen für Darkmode */
    }}
    
    /* --- ALLGEMEINE BUTTON GRÖSSE --- */
    div[data-testid="stButton"] button {{
        height: 50px !important;
        width: 100% !important;
    }}

    /* Spinner Farbe */
    .stSpinner > div {{
        border-top-color: {PRIMARY_COLOR} !important;
    }}
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent
DATA_PROCESSED = BASE_DIR / "data_processed"
IMAGES_BASE_URL = "https://pub-65f13bc76a9245c6b68256fb466fe755.r2.dev"
ARTICLES_FILE = DATA_PROCESSED / "articles_filtered.csv"
COPURCHASE_PARTS_DIR = DATA_PROCESSED / "copurchase_parts_5"

# ---------------------------------------------------------
# 2. HELPER: SCROLL TO TOP
# ---------------------------------------------------------
def scroll_to_top():
    js = f"""
    <script>
        function forceScroll() {{
            window.scrollTo(0, 0);
            var doc = window.parent.document.querySelector('[data-testid="stAppViewContainer"]');
            if (doc) doc.scrollTop = 0;
            setTimeout(function() {{ window.parent.scrollTo(0, 0); if (doc) doc.scrollTop = 0; }}, 100);
            setTimeout(function() {{ window.parent.scrollTo(0, 0); if (doc) doc.scrollTop = 0; }}, 500);
        }}
        forceScroll();
    </script>
    <div style="display:none;">{time.time()}</div>
    """
    components.html(js, height=0)

# ---------------------------------------------------------
# 3. EXTERNE LOGIK (WETTER & BILD)
# ---------------------------------------------------------
def get_weather(city):
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=de&format=json"
        geo_res = requests.get(geo_url).json()
        if not "results" in geo_res: return None
        lat = geo_res["results"][0]["latitude"]
        lon = geo_res["results"][0]["longitude"]
        w_res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true").json()
        temp = w_res["current_weather"]["temperature"]
        wcode = w_res["current_weather"]["weathercode"]
        condition = "Normal"
        if wcode >= 51: condition = "Rain"
        if wcode >= 71: condition = "Snow"
        if temp < 15: condition = "Cold"
        if temp > 25: condition = "Hot"
        return {"temp": temp, "condition": condition}
    except:
        return None

def get_dominant_color_name(image):
    img = image.convert("RGB").resize((50, 50))
    w, h = img.size
    img = img.crop((w*0.2, h*0.2, w*0.8, h*0.8))
    colors = {
        "black": (0, 0, 0), "white": (255, 255, 255), "grey": (128, 128, 128),
        "red": (255, 0, 0), "blue": (0, 0, 255), "navy": (0, 0, 128), "green": (0, 128, 0),
        "yellow": (255, 255, 0), "beige": (245, 245, 220), "brown": (165, 42, 42),
        "pink": (255, 192, 203), "orange": (255, 165, 0), "purple": (128, 0, 128),
        "turquoise": (64, 224, 208)
    }
    scored_colors = []
    for pixel in img.getdata():
        r, g, b = pixel
        h_val, s_val, v_val = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        best_match = "other"
        min_dist = float("inf")
        for name, (cr, cg, cb) in colors.items():
            dist = math.sqrt((r-cr)**2 + (g-cg)**2 + (b-cb)**2)
            if dist < min_dist:
                min_dist = dist
                best_match = name
        weight = 1
        if s_val > 0.1 and v_val > 0.2 and v_val < 0.9: 
            if best_match not in ["white", "grey", "black", "beige"]: weight = 3
        scored_colors.extend([best_match] * weight)
    counts = Counter(scored_colors)
    if "other" in counts: del counts["other"]
    if not counts: return "grey"
    return counts.most_common(1)[0][0]

# ---------------------------------------------------------
# 4. MAPPINGS & KEYWORDS
# ---------------------------------------------------------
PRODUCT_TYPE_TO_MACRO = {
    "Hoodie": "TOP", "Sweater": "TOP", "Top": "TOP", "T-shirt": "TOP", "Shirt": "TOP",
    "Polo shirt": "TOP", "Blouse": "TOP", "Cardigan": "TOP", "Vest top": "TOP",
    "Sweatshirt": "TOP", "Long sleeve top": "TOP", "Longsleeve": "TOP",
    "Trousers": "BOTTOM", "Jeans": "BOTTOM", "Shorts": "BOTTOM", "Skirt": "BOTTOM", "Leggings/Tights": "BOTTOM",
    "Jacket": "OUTERWEAR", "Coat": "OUTERWEAR", "Blazer": "OUTERWEAR",
    "Sneakers": "SHOES", "Boots": "SHOES", "Bootie": "SHOES", "Ballerinas": "SHOES",
    "Moccasins": "SHOES", "Pumps": "SHOES", "Heels": "SHOES", "Heeled sandals": "SHOES",
    "Sandals": "SHOES", "Flat shoe": "SHOES", "Flat shoes": "SHOES", "Flip flop": "SHOES", "Other shoe": "SHOES",
    "Cap": "ACCESSORY", "Beanie": "ACCESSORY", "Headband": "ACCESSORY", "Hat/beanie": "ACCESSORY",
    "Hat/brim": "ACCESSORY", "Straw hat": "ACCESSORY", "Felt hat": "ACCESSORY", "Bucket hat": "ACCESSORY", "Bag": "ACCESSORY",
}

MACRO_LABEL_DE = {
    "TOP": "Oberteil", "BOTTOM": "Unterteil", "OUTERWEAR": "Jacke/Mantel",
    "SHOES": "Schuhe", "ACCESSORY": "Accessoires", "ONE_PIECE": "Kleid/Overall"
}
MACRO_DISPLAY_ORDER = ["ACCESSORY", "TOP", "OUTERWEAR", "BOTTOM", "SHOES"]

COLOR_PALETTES = {
    "beige": ["dark green", "dark blue", "denim blue", "white", "black", "brown", "khaki", "red"],
    "black": ["white", "beige", "grey", "light grey", "silver", "gold", "red", "light blue", "pink", "khaki"],
    "white": ["black", "blue", "dark blue", "beige", "grey", "silver", "denim blue", "khaki", "pink", "red"],
    "off white": ["black", "blue", "dark blue", "beige", "brown", "khaki", "grey"],
    "grey": ["white", "black", "light pink", "pink", "blue", "denim blue", "dark blue", "red", "purple"],
    "dark grey": ["white", "black", "light pink", "yellow", "light blue", "grey"],
    "blue": ["white", "beige", "grey", "black", "yellow", "orange", "silver"],
    "dark blue": ["white", "beige", "grey", "yellow", "gold", "red", "denim blue", "black"], 
    "light blue": ["dark blue", "white", "beige", "pink", "silver", "grey"],
    "red": ["black", "white", "dark blue", "denim blue", "beige", "grey"],
    "dark red": ["black", "beige", "grey", "white", "dark blue"],
    "pink": ["grey", "white", "dark blue", "denim blue", "black", "silver"],
    "green": ["beige", "white", "black", "navy", "denim blue", "yellow"],
    "dark green": ["beige", "gold", "brown", "white", "black", "grey"],
    "khaki": ["white", "black", "orange", "red", "denim blue"],
    "yellow": ["blue", "grey", "white", "black", "navy", "denim blue"],
    "orange": ["blue", "white", "black", "grey", "khaki"],
    "brown": ["beige", "white", "blue", "denim blue", "green", "dark green", "black"],
    "gold": ["black", "white", "dark green", "dark red", "dark blue"],
    "silver": ["black", "white", "blue", "grey", "pink"],
}



# Farb-Familien für die UI (vereinfacht aus demo8)
COLOR_FAMILY_MAP_UI = {
    # Beige / Braun
    "beige": "Beige/Brown",
    "dark beige": "Beige/Brown",
    "light beige": "Beige/Brown",
    "greyish beige": "Beige/Brown",
    "yellowish brown": "Beige/Brown",
    "brown": "Beige/Brown",
    "dark brown": "Beige/Brown",
    "light brown": "Beige/Brown",
    "khaki": "Beige/Brown",

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
    "navy": "Blue",
    "denim blue": "Blue",

    # Rot / Pink
    "red": "Red",
    "dark red": "Red",
    "light red": "Red",
    "other red": "Red",
    "pink": "Pink",
    "dark pink": "Pink",
    "light pink": "Pink",
    "other pink": "Pink",

    # Grün
    "green": "Green",
    "dark green": "Green",
    "light green": "Green",
    "other green": "Green",
    "lime": "Green",
    "olive": "Green",

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

    # Lila
    "purple": "Purple",
    "dark purple": "Purple",
    "light purple": "Purple",
    "lilac": "Purple",

    # Metallic / Spezial
    "gold": "Metallic",
    "silver": "Metallic",
    "metallic": "Metallic",

    # Bunt / Sonstiges
    "multi": "Multicolour",
    "multicolour": "Multicolour",
    "multi coloured": "Multicolour",
    "other": "Other/Unknown",
    "unknown": "Other/Unknown",
}

def get_color_family_ui(name: str) -> str:
    """
    Liefert die 'schönen' Farbfamilien wie in demo8 für die UI.
    Input kann z.B. 'dark blue' oder 'beige' sein.
    """
    name = (name or "").strip().lower()
    if not name:
        return "Other/Unknown"
    if name in COLOR_FAMILY_MAP_UI:
        return COLOR_FAMILY_MAP_UI[name]
    # Fallback: Einfach lesbar machen
    return name.title()



BUSINESS_TYPES = ['Blazer', 'Shirt', 'Blouse', 'Trousers', 'Skirt', 'Coat', 'Pumps', 'Heels', 'Loafers', 'Boots', 'Polo shirt']
ANTI_BUSINESS_KEYWORDS = ['jogger', 'sweat', 'runner', 'loose', 'relaxed', 'cargo', 'denim', 'jeans']
SPORT_KEYWORDS = ['sport', 'running', 'training', 'gym', 'racer', 'seamless', 'leggings', 'bra', 'technical', 'yoga']
PARTY_KEYWORDS = ['sequin', 'glitter', 'sparkle', 'metallic', 'satin', 'velvet', 'tuxedo', 'suit', 'dressy', 'party', 'rhinestone']
LOUNGE_KEYWORDS = ['pyjama', 'robe', 'sleep', 'night', 'fleece', 'soft', 'home', 'slipper', 'jogger', 'hoodie']

def get_color_family(name: str) -> str:
    name = (name or "").lower().strip()
    if not name or name == "nan": return "other"
    for k in COLOR_PALETTES.keys():
        if k in name: return k
    return name

# ---------------------------------------------------------
# 5. CORE LOGIK
# ---------------------------------------------------------
def get_image_url(article_id_str: str) -> str:
    return f"{IMAGES_BASE_URL}/{article_id_str[:3]}/{article_id_str}.jpg"

def assign_gender(idx_name):
    idx = str(idx_name)
    if 'Menswear' in idx: return 'Herren'
    if 'Baby' in idx or 'Children' in idx: return 'Kinder'
    return 'Damen' 


def fix_outerwear_mislabels(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    # 1) Konkrete bekannte Fehlklassifikation korrigieren
    jacket_ids = [176209023]  # Mr Harrington w/hood
    df.loc[df["article_id"].isin(jacket_ids), "macro_category"] = "OUTERWEAR"
    df.loc[df["article_id"].isin(jacket_ids), "product_type_name"] = "Jacket"

    # 2) Generische Regel: Texte enthalten "jacket"/"coat"/"parka" etc.
    jacket_keywords = ["jacket", "coat", "parka", "anorak", "puffer"]
    mask_text = (
        df["detail_desc"].str.lower().fillna("").str.contains("|".join(jacket_keywords))
        | df["prod_name"].str.lower().fillna("").str.contains("|".join(jacket_keywords))
    )
    # Nur Oberkörper-Gruppen umlabeln, die bisher kein OUTERWEAR sind
    mask_group = df["product_group_name"].str.contains("Garment Upper body", na=False)
    mask = mask_text & mask_group & (df["macro_category"] != "OUTERWEAR")

    df.loc[mask, "macro_category"] = "OUTERWEAR"
    # product_type_name kannst du optional lassen oder pauschal auf "Jacket" setzen
    # df.loc[mask, "product_type_name"] = "Jacket"

    return df



def get_functional_type(row):
    idx = str(row['index_name'])
    pt = str(row['product_type_name'])
    name = str(row['prod_name']).lower()
    if 'Baby' in idx or 'Children' in idx: return 'Kids'
    if 'Sport' in idx or pt in ('Sneakers', 'Leggings/Tights') or any(k in name for k in SPORT_KEYWORDS): return 'Sport'
    if any(k in name for k in LOUNGE_KEYWORDS): return 'Lounge'
    if any(k in name for k in PARTY_KEYWORDS) or ('gold' in str(row['colour_group_name']).lower()): return 'Party'
    if pt in BUSINESS_TYPES:
        if 'Divided' in idx or any(k in name for k in ANTI_BUSINESS_KEYWORDS): return 'Casual'
        return 'Business'
    return 'Casual'

# ---------------------------------------------------------
# 6. STATE MANAGEMENT
# ---------------------------------------------------------
def init_session_state():
    defaults = {
        "intro_done": False,
        "view": "select",
        "sel_gender": None,
        "sel_style": "Casual",
        "sel_macro": "TOP",
        "base_article_id": None,
        "final_selection": {},
        "blocked_ids": [],
        "weather_data": None,
        "use_weather_logic": False, 
        "uploaded_base_item": None,
        "uploaded_image_object": None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
            
    for m in MACRO_DISPLAY_ORDER:
        if f"idx_{m}" not in st.session_state:
            st.session_state[f"idx_{m}"] = 0

def set_base_article(art_id):
    st.session_state["base_article_id"] = int(art_id)
    if int(art_id) != 999999:
        st.session_state["uploaded_base_item"] = None
        st.session_state["uploaded_image_object"] = None
    st.session_state["view"] = "outfit"
    for m in MACRO_DISPLAY_ORDER: st.session_state[f"idx_{m}"] = 0

def block_item(macro, art_id):
    st.session_state["blocked_ids"].append(art_id)

def next_item(macro, max_len):
    st.session_state[f"idx_{macro}"] = (st.session_state[f"idx_{macro}"] + 1) % max_len

def prev_item(macro, max_len):
    st.session_state[f"idx_{macro}"] = (st.session_state[f"idx_{macro}"] - 1) % max_len

def finish_intro():
    st.session_state["intro_done"] = True
    st.rerun()

# ---------------------------------------------------------
# 7. DATEN LADEN
# ---------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(ARTICLES_FILE)
    df["article_id"] = df["article_id"].astype(int)
    df["article_id_str"] = df["article_id"].astype(str).str.zfill(10)

    # 1) Grund-Mapping
    df["macro_category"] = df["product_type_name"].map(PRODUCT_TYPE_TO_MACRO)

    # 2) 🔹 Fehlklassifizierte Outerwear (Jacken/Mäntel) korrigieren
    df = fix_outerwear_mislabels(df)

    # 3) Restliche Features berechnen
    df["gender"] = df["index_name"].apply(assign_gender)
    df["colour_family"] = df["colour_group_name"].apply(get_color_family)
    df["colour_family_ui"] = df["colour_family"].apply(get_color_family_ui)
    df["style"] = df.apply(get_functional_type, axis=1)

    return df


@st.cache_data
def load_copurchase():
    parts_dir = COPURCHASE_PARTS_DIR
    part_files = sorted(parts_dir.glob("copurchase_part_*.csv"))
    dfs = [pd.read_csv(f) for f in part_files]
    df_all = pd.concat(dfs, ignore_index=True)
    df_all["article_id_1"] = df_all["article_id_1"].astype(int)
    df_all["article_id_2"] = df_all["article_id_2"].astype(int)
    return df_all

def get_base_article_row(df_articles, article_id):
    if st.session_state["uploaded_base_item"] is not None:
        if int(article_id) == 999999:
            return st.session_state["uploaded_base_item"]
    rows = df_articles[df_articles["article_id"] == article_id]
    if rows.empty: return None
    return rows.iloc[0]



# sehr robuste Erkennung für Jacken/Mäntel
def is_outerwear_like(row):
    macro = str(row.get("macro_category", "") or "")
    if macro == "OUTERWEAR":
        return True

    pt = str(row.get("product_type_name", "") or "").lower()
    name = str(row.get("prod_name", "") or "").lower()

    keywords = [
        "jacket", "coat", "parka", "anorak", "blazer",
        "outerwear", "puffer", "down jacket", "windbreaker"
    ]

    if any(k in pt for k in keywords):
        return True
    if any(k in name for k in keywords):
        return True

    return False






# ---------------------------------------------------------
# 8. RECOMMENDATION ENGINE
# ---------------------------------------------------------
def calculate_complex_score(base, cand):
    score = 0.0
    log = []
    
    # 1. STIL
    if base['style'] == cand['style']:
        score += 4.0
        log.append("✅ Stil: Perfekt (+4)")
    elif (base['style'] == 'Casual' and cand['style'] == 'Sport'):
        score += 2.0
        log.append("🆗 Stil: Okay (+2)")
    elif (base['style'] == 'Business' and cand['style'] == 'Sport'):
        score -= 10.0
        log.append("❌ No-Go: Business + Sport (-10)")
    else:
        score -= 2.0
        log.append("⚠️ Stil-Mix (-2)")

    # 2. FARBE
    b_col = base['colour_family']
    c_col = cand['colour_family']
    palette = COLOR_PALETTES.get(b_col, [])
    
    if b_col == c_col:
        score += 3.0
        log.append("🎨 Monochrom (+3)")
    elif c_col in palette:
        score += 4.0
        log.append(f"🎨 Harmonisch (+4)")
    elif b_col in ["black", "white", "grey"]:
        score += 2.0
        log.append("🛡️ Neutral (+2)")
    else:
        score -= 1.0
        log.append("🎨 Riskant (-1)")

    # 3. WETTER
    weather = st.session_state.get("weather_data")
    use_w = st.session_state.get("use_weather_logic", False)
    if weather and use_w:
        pt = cand['product_type_name']
        if weather["condition"] in ["Cold", "Rain", "Snow"]:
            if pt in ["Jacket", "Coat", "Hoodie", "Sweater", "Boots"]:
                score += 3.0
                log.append("🌤️ Wetter: Warm (+3)")
            if pt in ["Shorts", "Sandals", "Vest top"]:
                score -= 5.0
                log.append("🥶 Wetter: Zu kalt (-5)")
        elif weather["condition"] == "Hot":
            if pt in ["Shorts", "Sandals", "Vest top", "T-shirt", "Skirt"]:
                score += 3.0
                log.append("☀️ Wetter: Luftig (+3)")
            if pt in ["Coat", "Sweater", "Hoodie"]:
                score -= 5.0
                log.append("🥵 Wetter: Zu heiß (-5)")

    # 4. BONUS
    if cand.get('is_copurchase', False):
        score += 2.0
        log.append("🔥 Popularity Bonus (+2)")

    final_percent = int(max(0, min(100, score * 10 + 20)))
    return final_percent, "\n".join(log)


def get_smart_recommendations(base_id, df, df_cop, n=20, selected_macros=None):
    base_row = get_base_article_row(df, base_id)
    if base_row is None:
        return {}

    base_macro = base_row["macro_category"]
    base_gender = base_row["gender"]

    # Basisteil jacken-/mantelartig?
    base_is_outerwear_like = is_outerwear_like(base_row)

    # -------------------------
    # Co-Purchase-Kandidaten
    # -------------------------
    candidates = pd.DataFrame()
    if base_id != 999999:
        mask = (df_cop["article_id_1"] == base_id) | (df_cop["article_id_2"] == base_id)
        df_pairs = df_cop[mask].copy()
        if not df_pairs.empty:
            df_pairs["partner_id"] = df_pairs.apply(
                lambda r: r["article_id_2"] if r["article_id_1"] == base_id else r["article_id_1"],
                axis=1,
            )
            candidates = df_pairs.merge(df, left_on="partner_id", right_on="article_id")

    outfit = {}

    # -------------------------
    # Ziel-Makros bestimmen
    # -------------------------
    def build_target_macros(selected_macros_local):
        result = []
        for m in MACRO_DISPLAY_ORDER:
            # UI-Auswahl respektieren, falls gesetzt
            if selected_macros_local is not None and m not in selected_macros_local:
                continue
            # niemals Makrokategorie des Basisteils doppeln
            if m == base_macro:
                continue
            # wenn Basisteil Jacke/Mantel → keine OUTERWEAR-Makros mehr
            if base_is_outerwear_like and m == "OUTERWEAR":
                continue
            result.append(m)
        return result

    target_macros = build_target_macros(selected_macros)

    # Fallback, falls alles rausgefiltert wurde
    if not target_macros:
        target_macros = build_target_macros(None)

    # -------------------------
    # Empfehlungen pro Makro
    # -------------------------
        # -------------------------
    # Empfehlungen pro Makro
    # -------------------------
    for target in target_macros:
        pool = df[
            (df["macro_category"] == target)
            & (df["gender"] == base_gender)
            & (df["article_id"] != base_id)
        ]

        # Basis-Filter auf dem "normalen" Pool
        if base_is_outerwear_like:
            pool = pool[~pool.apply(is_outerwear_like, axis=1)]

        cp_matches = pd.DataFrame()
        if not candidates.empty:
            cp_matches = candidates[candidates["macro_category"] == target].copy()
            cp_matches["is_copurchase"] = True

        pool_sample = pool.head(200).copy()
        pool_sample["is_copurchase"] = False

        combined = pd.concat([cp_matches, pool_sample]).drop_duplicates(subset="article_id")

        # 🔴 WICHTIG: Jetzt auch Co-Purchase-Jacken rauswerfen
        if base_is_outerwear_like:
            combined = combined[~combined.apply(is_outerwear_like, axis=1)]

        combined = combined[~combined["article_id"].isin(st.session_state["blocked_ids"])]

        if combined.empty:
            continue

        results = []
        for _, row in combined.iterrows():
            sc, tt = calculate_complex_score(base_row, row)
            row["match_score"] = sc
            row["tooltip"] = tt
            results.append(row)

        if not results:
            continue

        final_df = pd.DataFrame(results)
        top_picks = (
            final_df.sort_values("match_score", ascending=False)
            .head(10)
            .reset_index(drop=True)
        )

        if not top_picks.empty:
            outfit[target] = top_picks


        if combined.empty:
            continue

        results = []
        for _, row in combined.iterrows():
            sc, tt = calculate_complex_score(base_row, row)
            row["match_score"] = sc
            row["tooltip"] = tt
            results.append(row)

        if not results:
            continue

        final_df = pd.DataFrame(results)
        top_picks = (
            final_df.sort_values("match_score", ascending=False)
            .head(10)
            .reset_index(drop=True)
        )

        if not top_picks.empty:
            outfit[target] = top_picks

    return outfit

# ---------------------------------------------------------
# 9. UI: INTRO PAGE
# ---------------------------------------------------------
def render_intro_page():
    st.markdown("""
    <div class="intro-container">
        <div class="intro-title">H&M Style Guide</div>
        <div class="intro-subtitle">Discover your perfect look.</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Ghost Button Zentriert
    c1, c2, c3 = st.columns([1, 1, 1])
    if c2.button("Start Experience >", type="primary", use_container_width=True):
        finish_intro()
        
    st.markdown('<div class="intro-credits">by Matze, Finn & Nicolas</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 10. UI: LANDING PAGE
# ---------------------------------------------------------
def render_landing_page(df):
    scroll_to_top()
    st.title("H&M Style Guide")
    
    # ----------------- GENDER + ÜBERRASCH MICH -----------------
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1.5])
    genders = ["Damen", "Herren", "Kinder"]
    
    for i, g in enumerate(genders):
        isActive = st.session_state.sel_gender == g
        if [c1, c2, c3][i].button(
            f"👤 {g}",
            key=f"g_{g}",
            type="primary" if isActive else "secondary",
            use_container_width=True,
        ):
            st.session_state.sel_gender = g
            st.session_state.sel_style = "Kids" if g == "Kinder" else "Casual"
            st.rerun()

    disabled_surprise = st.session_state.sel_gender is None
    if c4.button("🎲 Überrasch mich!", disabled=disabled_surprise, type="secondary", use_container_width=True):
        subset = df[(df["gender"] == st.session_state.sel_gender) & (df["macro_category"] == "TOP")]
        if not subset.empty:
            rnd = subset.sample(1).iloc[0]
            set_base_article(rnd.article_id)
            st.rerun()

    if st.session_state.sel_gender is None:
        st.info("👆 Bitte wähle zuerst eine Abteilung aus.")
        return

    # ----------------- WETTER -----------------
    with st.expander("🌤️ Wetter-Check", expanded=False):
        city = st.text_input("Stadtname:", placeholder="z.B. Berlin")
        use_w = st.checkbox("Wetter berücksichtigen", value=False)
        st.session_state["use_weather_logic"] = use_w
        
        if city:
            wdata = get_weather(city)
            if wdata:
                st.session_state["weather_data"] = wdata
                cond_map = {
                    "Cold": "❄️ Kalt",
                    "Hot": "☀️ Heiß",
                    "Rain": "🌧️ Regen",
                    "Snow": "🌨️ Schnee",
                    "Normal": "🌤️ Normal",
                }
                st.success(f"Aktuell in {city}: {wdata['temp']}°C ({cond_map.get(wdata['condition'], 'Normal')})")
            else:
                st.toast("Stadt nicht gefunden 🚫", icon="⚠️")
        
    # ----------------- MATCH MY CLOSET -----------------
    with st.expander("📸 Match my Closet", expanded=False):
        uploaded_file = st.file_uploader("Lade ein Foto deines Teils hoch", type=["jpg", "png"])
        if uploaded_file:
            img = Image.open(uploaded_file)
            col_name = get_dominant_color_name(img)
            st.image(img, width=100, caption=f"Erkannte Farbe: {col_name.title()}")
            
            col_families = sorted(list(COLOR_PALETTES.keys()))
            def_idx = 0
            if col_name in col_families:
                def_idx = col_families.index(col_name)
            final_col = st.selectbox("Farbe bestätigen/korrigieren:", col_families, index=def_idx)
            
            friendly_macros = list(MACRO_LABEL_DE.values())
            selected_friendly = st.selectbox("Was ist das?", friendly_macros)
            reverse_map = {v: k for k, v in MACRO_LABEL_DE.items()}
            internal_macro = reverse_map[selected_friendly]
            
            style_manual = st.selectbox("Welcher Stil?", ["Casual", "Business", "Party", "Sport", "Lounge"])
            
            if st.button("Outfit dazu suchen", type="primary"):
                fake_id = 999999
                fake_row = pd.Series({
                    "article_id": fake_id,
                    "article_id_str": "0000000000",
                    "prod_name": "Dein Upload",
                    "product_type_name": "Upload",
                    "macro_category": internal_macro,
                    "colour_group_name": final_col,
                    "colour_family": final_col,
                    "style": style_manual,
                    "gender": st.session_state.sel_gender,
                    "index_name": "Upload",
                })
                st.session_state["uploaded_base_item"] = fake_row
                st.session_state["uploaded_image_object"] = img
                set_base_article(fake_id)
                st.rerun()

    # ----------------- FILTER: STIL / KATEGORIE / ART / FARBE -----------------
    df_g = df[df["gender"] == st.session_state.sel_gender]
    with st.container(border=True):
        fc1, fc2, fc3, fc4 = st.columns(4)

        # 1. Stil
        with fc1:
            is_kids = st.session_state.sel_gender == "Kinder"
            style_opts = ["Kids"] if is_kids else ["Casual", "Business", "Party", "Lounge", "Sport"]
            if st.session_state.sel_style not in style_opts:
                st.session_state.sel_style = style_opts[0]
            st.session_state.sel_style = st.selectbox(
                "1. Stil",
                style_opts,
                key="sb_style",
                disabled=is_kids,
            )
        df_s = df_g[df_g["style"] == st.session_state.sel_style]

        # 2. Makrokategorie
        with fc2:
            macros = sorted(df_s["macro_category"].dropna().unique())
            if not macros:
                st.warning("Keine Artikel")
                return
            if st.session_state.sel_macro not in macros:
                st.session_state.sel_macro = "TOP" if "TOP" in macros else macros[0]
            st.session_state.sel_macro = st.selectbox(
                "2. Kategorie",
                macros,
                index=macros.index(st.session_state.sel_macro),
                format_func=lambda x: MACRO_LABEL_DE.get(x, x),
                key="sb_macro",
            )
        df_m = df_s[df_s["macro_category"] == st.session_state.sel_macro]

        # 3. Artikelart
        with fc3:
            subcats = ["Alle"] + sorted(df_m["product_type_name"].unique())
            st.session_state.sel_subcat = st.selectbox("3. Artikelart", subcats, key="sb_sub")
        if st.session_state.sel_subcat != "Alle":
            df_m = df_m[df_m["product_type_name"] == st.session_state.sel_subcat]

        # 4. Farbe (UI-Farbfamilie wie in demo8)
        with fc4:
            colour_values = sorted(df_m["colour_family_ui"].dropna().unique())
            color_options = ["Alle"] + colour_values

            cur_colour = st.session_state.get("sel_colour", "Alle")
            if cur_colour not in color_options:
                cur_colour = "Alle"

            st.session_state.sel_colour = st.selectbox(
                "4. Farbe",
                options=color_options,
                index=color_options.index(cur_colour),
                key="sb_col",
            )

        if st.session_state.sel_colour != "Alle":
            df_m = df_m[df_m["colour_family_ui"] == st.session_state.sel_colour]

    # ----------------- OUTFIT-KATEGORIEN-AUSWAHL -----------------
    with st.expander("Welche Teile sollen im Outfit vorkommen?", expanded=False):
        available_macros = [m for m in MACRO_DISPLAY_ORDER if m in MACRO_LABEL_DE]

        label_map = {m: MACRO_LABEL_DE[m] for m in available_macros}
        reverse_map = {v: k for k, v in label_map.items()}

        prev_selection = st.session_state.get("outfit_macros", available_macros)
        prev_labels = [label_map[m] for m in prev_selection if m in label_map]

        selected_labels = st.multiselect(
            "Kategorien für das Outfit:",
            options=list(label_map.values()),
            default=prev_labels,
            help="Diese Teile versucht die App im Outfit zu ergänzen (z.B. Oberteil, Unterteil, Schuhe, Jacke).",
        )

        selected_macros = [reverse_map[l] for l in selected_labels]
        if selected_macros:
            st.session_state["outfit_macros"] = selected_macros
        else:
            st.session_state["outfit_macros"] = available_macros

    st.markdown("---")
    if df_m.empty:
        st.warning("Keine Artikel gefunden.")
        return


    # ----------------- ARTIKELGRID MIT "MEHR ANZEIGEN" -----------------

    # 1) Filter-Signatur bauen, um bei Filterwechsel den Pool zurückzusetzen
    filter_signature = "|".join([
        str(st.session_state.get("sel_gender")),
        str(st.session_state.get("sel_style")),
        str(st.session_state.get("sel_macro")),
        str(st.session_state.get("sel_subcat")),
        str(st.session_state.get("sel_colour")),
    ])

    # 2) Falls Filter neu → Pool neu aufbauen + Limit zurücksetzen
    if (
        "base_filter_sig" not in st.session_state
        or st.session_state.base_filter_sig != filter_signature
    ):
        st.session_state.base_filter_sig = filter_signature

        # zufällige Reihenfolge der Artikel für diese Filterkombination
        st.session_state.base_pool_ids = (
            df_m["article_id"]
            .sample(frac=1.0, replace=False, random_state=None)
            .tolist()
        )

        # Start-Limit (z. B. 24 oder 48)
        st.session_state.base_visible = min(len(st.session_state.base_pool_ids), 24)

    pool_ids = st.session_state.base_pool_ids
    visible = st.session_state.base_visible

    if not pool_ids:
        st.warning("Keine Artikel gefunden.")
        return

    # 3) Aktuell sichtbare IDs auswählen
    ids_to_show = pool_ids[:visible]
    df_show = df_m[df_m["article_id"].isin(ids_to_show)]

    # 4) Grid rendern
    cols = st.columns(6)
    for i, row in enumerate(df_show.itertuples()):
        with cols[i % 6]:
            st.image(get_image_url(row.article_id_str), use_container_width=True)
            clean_name = row.prod_name.strip()
            if len(clean_name) > 16:
                clean_name = clean_name[:14] + ".."
            label = f"{clean_name}\n({row.colour_group_name})"
            st.button(
                label,
                key=f"btn_{row.article_id}",
                on_click=set_base_article,
                args=(row.article_id,),
                use_container_width=True,
            )

    # 5) "Mehr anzeigen"-Button, wenn noch Artikel übrig sind
    if visible < len(pool_ids):
        more_cols = st.columns([1, 1, 4])
        with more_cols[0]:
            if st.button("Mehr anzeigen", key="btn_load_more"):
                # z. B. jeweils 24 zusätzliche Artikel laden
                st.session_state.base_visible = min(
                    visible + 24,
                    len(pool_ids),
                )
                st.rerun()


# ---------------------------------------------------------
# 11. UI: OUTFIT PAGE
# ---------------------------------------------------------
def render_outfit_view(df, df_cop, base_id):
    scroll_to_top()
    if st.button("⬅️ Zurück zur Auswahl"):
        st.session_state["view"] = "select"
        st.rerun()

    base_row = get_base_article_row(df, base_id)
    if base_row is None:
        st.error("Datenfehler")
        return

    # Outfit-Kategorien aus der Landing-Page übernehmen (falls gesetzt)
    selected_macros = st.session_state.get("outfit_macros")

    recommendations = get_smart_recommendations(
        base_id,
        df,
        df_cop,
        n=10,
        selected_macros=selected_macros,
    )


    col_left, col_right = st.columns([1.4, 2.6])

    with col_left:
        st.subheader("Basisteil")
        if base_id == 999999:
             st.info("📸 Dein Foto")
             if st.session_state.get("uploaded_image_object"):
                 st.image(st.session_state["uploaded_image_object"], use_container_width=True)
        else:
            st.image(get_image_url(base_row["article_id_str"]), use_container_width=True)
        
        st.markdown(f"**{base_row['prod_name']}**")
        st.caption(f"Stil: {base_row['style']} | Farbe: {base_row['colour_group_name']}")
        
        w = st.session_state.get("weather_data")
        use_w = st.session_state.get("use_weather_logic", False)
        if w and use_w:
            st.info(f"Wetter berücksichtigt: {w['temp']}°C")

    with col_right:
        st.subheader("Stell deinen Look zusammen")
        current_outfit = {}

        for macro in MACRO_DISPLAY_ORDER:
            if macro in recommendations and not recommendations[macro].empty:
                rec_df = recommendations[macro]
                label = MACRO_LABEL_DE.get(macro, macro)
                st.markdown(f"##### {label}")
                
                idx_key = f"idx_{macro}"
                idx = st.session_state[idx_key]
                if idx >= len(rec_df): idx = 0
                
                item = rec_df.iloc[idx]
                current_outfit[macro] = item["article_id"]
                
                c_p, c_i, c_n = st.columns([1, 5, 1])
                
                with c_p:
                    st.markdown('<div class="nav-btn">', unsafe_allow_html=True)
                    if st.button("◀", key=f"p_{macro}"):
                        prev_item(macro, len(rec_df))
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                with c_i:
                    st.image(get_image_url(item["article_id_str"]), use_container_width=True)
                    st.caption(f"{item['prod_name']}")
                    
                    sc = int(item["match_score"])
                    col = "green" if sc > 80 else "orange" if sc > 50 else "red"
                    tt = item["tooltip"].replace('\n', '&#10;')
                    
                    st.markdown(
                        f"""
                        <div title="{tt}" style="background:transparent; border: 1px solid #333; padding:5px; border-radius:5px; text-align:center; cursor:help;">
                            <span style="color:{col}; font-weight:bold;">Match: {sc}%</span> ℹ️
                        </div>
                        """, unsafe_allow_html=True
                    )
                    
                    st.markdown('<div class="block-btn">', unsafe_allow_html=True)
                    if st.button("🚫 Blockieren", key=f"blk_{item['article_id']}"):
                        block_item(macro, item["article_id"])
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                with c_n:
                    st.markdown('<div class="nav-btn">', unsafe_allow_html=True)
                    if st.button("▶", key=f"n_{macro}"):
                        next_item(macro, len(rec_df))
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown("---")

        st.write("")
        if st.button("Outfit fertigstellen & anzeigen", type="primary", use_container_width=True):
            st.session_state["final_selection"] = current_outfit
            st.session_state["view"] = "final"
            st.rerun()

# ---------------------------------------------------------
# 12. UI: FINAL PAGE
# ---------------------------------------------------------
def render_final_page(df):
    scroll_to_top()
    st.balloons()
    st.toast("Outfit erfolgreich gespeichert!", icon="✅")
    
    if st.button("⬅️ Zurück zum Bearbeiten"):
        st.session_state["view"] = "outfit"
        st.rerun()
        
    st.title("Dein fertiger Look:")
    
    base_id = st.session_state["base_article_id"]
    base_row = get_base_article_row(df, base_id)
    final_ids = st.session_state["final_selection"]
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("### Dein Basisteil")
        if base_id == 999999:
             st.info("📸 Dein Foto")
             if st.session_state.get("uploaded_image_object"):
                 st.image(st.session_state["uploaded_image_object"], use_container_width=True)
        else:
            st.image(get_image_url(base_row["article_id_str"]), use_container_width=True)
        
        st.markdown(f"**{base_row['prod_name']}**")
        st.markdown("---")
        
        st.markdown("### Dazu hast du gewählt:")
        for macro in MACRO_DISPLAY_ORDER:
            if macro in final_ids:
                art_id = final_ids[macro]
                row = get_base_article_row(df, art_id)
                if row is not None:
                    st.caption(MACRO_LABEL_DE.get(macro, macro))
                    st.image(get_image_url(row["article_id_str"]), use_container_width=True)
                    st.markdown(f"**{row['prod_name']}**")
                    st.markdown("---")
    
    if st.button("Neues Outfit starten", type="primary", use_container_width=True):
        st.session_state["view"] = "select"
        st.session_state["uploaded_base_item"] = None
        st.session_state["base_article_id"] = None
        st.rerun()

# ---------------------------------------------------------
# 13. MAIN ROUTING
# ---------------------------------------------------------
def main():
    init_session_state()
    
    if not st.session_state["intro_done"]:
        render_intro_page()
    else:
        try:
            with st.spinner("Lade Daten..."):
                df = load_data()
                df_cop = load_copurchase()
        except Exception as e:
            st.error(f"Fehler: {e}"); st.stop()

        if st.session_state["view"] == "select":
            render_landing_page(df)
        elif st.session_state["view"] == "outfit":
            if st.session_state["base_article_id"] is None:
                st.session_state["view"] = "select"; st.rerun()
            render_outfit_view(df, df_cop, st.session_state["base_article_id"])
        elif st.session_state["view"] == "final":
            render_final_page(df)

if __name__ == "__main__":

    main()
