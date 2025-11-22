import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict
import re

# ---------------------------------------------------------
# Streamlit Grundkonfiguration
# ---------------------------------------------------------
st.set_page_config(
    page_title="H&M Outfit Recommender (Demo)",
    layout="wide"
)

# ---------------------------------------------------------
# Pfade / Basis-URLs
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

DATA_PROCESSED = BASE_DIR / "data_processed"
IMAGES_BASE_URL = "https://pub-65f13bc76a9245c6b68256fb466fe755.r2.dev"

ARTICLES_FILE = DATA_PROCESSED / "articles_filtered.csv"
COPURCHASE_PARTS_DIR = DATA_PROCESSED / "copurchase_parts_5"


# ---------------------------------------------------------
# Mapping: product_type_name -> Makrokategorie
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

    # ACCESSORIES (Kopfbedeckung / Bags)
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

COLOR_FAMILY_MAP = {
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
    "gray": "Grey",  # falls irgendwo so vorkommt
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


def get_color_family(name: str) -> str:
    """
    Mappt colour_group_name auf eine gröbere Farbfamilie für die Filter-UI.
    Unbekannte Werte werden 'wie sie sind' (Titlecase) angezeigt.
    """
    name = (name or "").strip().lower()
    if not name:
        return "Other/Unknown"
    if name in COLOR_FAMILY_MAP:
        return COLOR_FAMILY_MAP[name]
    return name.title()


def get_color_family(name: str) -> str:
    """
    Mappt colour_group_name auf eine gröbere Farbfamilie für die Filter-UI.
    Unbekannte Werte werden 'wie sie sind' (Titlecase) angezeigt.
    """
    name = (name or "").strip().lower()
    if not name:
        return "Unbekannt"
    if name in COLOR_FAMILY_MAP:
        return COLOR_FAMILY_MAP[name]
    return name.title()



MACRO_LABEL_DE = {
    "ACCESSORY": "Kopf / Accessoires",
    "TOP": "Oberteil",
    "OUTERWEAR": "Jacke / Mantel",
    "BOTTOM": "Unterteil",
    "SHOES": "Schuhe",
    "ONE_PIECE": "Kleid / Overall",   # NEU
}

MACRO_DISPLAY_ORDER = ["ACCESSORY", "TOP", "OUTERWEAR", "BOTTOM", "SHOES"]

NEUTRAL_KEYWORDS = {
    "black", "white", "off white", "grey", "gray", "light grey", "dark grey",
    "silver", "transparent", "unknown", "navy", "beige", "cream"
}

SYNONYMS: Dict[str, list[str]] = {
    "pulli": ["hoodie", "sweater", "pullover", "sweatshirt"],
    "hoodie": ["sweater", "pullover", "sweatshirt"],
    "hose": ["trousers", "jeans", "shorts", "leggings", "skirt"],
    "jeans": ["trousers", "denim"],
    "schuhe": ["sneakers", "boots", "heels", "sandals"],
    "sneaker": ["sneakers", "trainers"],
    "jacke": ["jacket", "coat", "blazer"],
    "mantel": ["coat"],
    "top": ["t-shirt", "vest top", "blouse", "shirt"],
    "mütze": ["cap", "beanie", "hat"],
}


def filter_articles_in_subcategory(df_sub: pd.DataFrame, query: str) -> pd.DataFrame:
    """
    Textsuche (inkl. Synonyme) innerhalb einer bereits gefilterten Unterkategorie.
    df_sub: z.B. alle Artikel mit product_type_name == current_subcat
    """
    query = (query or "").strip().lower()
    if not query:
        return df_sub

    # Query um Synonyme erweitern (wie in demo6_np)
    query_terms = [query]
    for key, syns in SYNONYMS.items():
        if key in query:
            query_terms.extend(syns)

    # Regex-Pattern (alle Begriffe mit OR verknüpft)
    pattern = "|".join(re.escape(t) for t in query_terms)

    # Auf mehreren Textspalten suchen
    mask = pd.Series(False, index=df_sub.index)

    for col in [
        "article_id_str",
        "prod_name",
        "product_type_name",
        "product_group_name",
        "index_name",
    ]:
        if col in df_sub.columns:
            mask |= df_sub[col].fillna("").str.contains(pattern, case=False, regex=True)

    if "detail_desc" in df_sub.columns:
        mask |= df_sub["detail_desc"].fillna("").str.contains(pattern, case=False, regex=True)

    return df_sub[mask]


# ---------------------------------------------------------
# Datenladen (mit Caching)
# ---------------------------------------------------------
@st.cache_data
def load_copurchase():
    """Lädt automatisch alle Teil-Dateien in data_processed/copurchase_parts_5/."""
    parts_dir = COPURCHASE_PARTS_DIR

    part_files = sorted(parts_dir.glob("copurchase_part_*.csv"))
    if not part_files:
        raise FileNotFoundError("Keine Split-Dateien gefunden in %s" % parts_dir)

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

    # Sicherstellen, dass article_id und article_id_str existieren
    df["article_id"] = df["article_id"].astype(int)
    df["article_id_str"] = df["article_id"].astype(str).str.zfill(10)

    # macro_category IMMER neu aus product_type_name berechnen
    df["macro_category"] = df["product_type_name"].map(PRODUCT_TYPE_TO_MACRO)

    return df


# ---------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------
def get_image_url(article_id_str: str) -> str:
    """
    Build Cloudflare-R2-URL:
    <BASE>/<erste3>/<article_id_str>.jpg
    """
    folder = article_id_str[:3]
    filename = f"{article_id_str}.jpg"
    return f"{IMAGES_BASE_URL}/{folder}/{filename}"


def get_base_article_row(df_articles, article_id):
    rows = df_articles[df_articles["article_id"] == article_id]
    if rows.empty:
        return None
    return rows.iloc[0]

# ---------------------------------------------------------
# Auswahl-Flow für Basisteil (Landing-Page-Version)
# ---------------------------------------------------------

BASE_MACRO_OPTIONS = [
    ("TOP", "Oberteil"),
    ("BOTTOM", "Unterteil"),
    ("ONE_PIECE", "Kleid / Overall"),
    ("OUTERWEAR", "Jacke / Mantel"),
]


def select_base_macro() -> str:
    """
    Schritt 1: Makrokategorie wählen (Buttons).
    Merkt Auswahl in st.session_state["base_macro"].
    """
    st.markdown("### 1. Schritt: Makrokategorie wählen")

    # Default: TOP
    if "base_macro" not in st.session_state:
        st.session_state["base_macro"] = "TOP"

    current = st.session_state["base_macro"]

    cols = st.columns(4)
    clicked_macro = None

    for idx, (macro, label) in enumerate(BASE_MACRO_OPTIONS):
        col = cols[idx % 4]
        with col:
            if st.button(
                label,
                key=f"macro_{macro}",
                type="primary" if macro == current else "secondary",
            ):
                clicked_macro = macro

    if clicked_macro is not None:
        st.session_state["base_macro"] = clicked_macro
        current = clicked_macro

    return current


def select_base_article(df_articles: pd.DataFrame, base_macro: str):
    """
    Schritt 2 & 3:
    - Unterkategorie (product_type_name) innerhalb der Makrokategorie wählen (Buttons)
    - Farbe innerhalb dieser Unterkategorie wählen (Dropdown)
    - Alle passenden Artikel als Karten (kleines Bild + Button)

    Gibt (selected_article_id, base_row) zurück.
    """
    # ---------------------------------------------
    # Schritt 2: Unterkategorie wählen
    # ---------------------------------------------
    st.markdown("### 2. Schritt: Unterkategorie wählen")

    df_macro = df_articles[df_articles["macro_category"] == base_macro].copy()
    if df_macro.empty:
        st.warning("Für diese Kategorie sind im Demo-Datenausschnitt keine Artikel vorhanden.")
        return None, None

    subcats = (
        df_macro["product_type_name"]
        .dropna()
        .sort_values()
        .unique()
        .tolist()
    )
    if not subcats:
        st.warning("Keine Unterkategorien für diese Basiskategorie vorhanden.")
        return None, None

    # aktuelle Unterkategorie aus Session holen oder Default setzen
    if "base_subcat" not in st.session_state or st.session_state["base_subcat"] not in subcats:
        st.session_state["base_subcat"] = subcats[0]

    current_subcat = st.session_state["base_subcat"]

    # Buttons für Unterkategorien (max. 4 pro Reihe)
    cols = st.columns(min(4, len(subcats)))
    clicked_subcat = None
    for idx, subcat in enumerate(subcats):
        col = cols[idx % len(cols)]
        with col:
            if st.button(
                subcat,
                key=f"subcat_{subcat}",
                type="primary" if subcat == current_subcat else "secondary",
            ):
                clicked_subcat = subcat

    if clicked_subcat is not None:
        current_subcat = clicked_subcat
        st.session_state["base_subcat"] = current_subcat

        # ---------------------------------------------
    # Schritt 3: Farbe & Basisteil wählen (mit Farb-Familien)
    # ---------------------------------------------
    st.markdown("### 3. Schritt: Farbe & Basisteil wählen")

    df_base = df_macro[df_macro["product_type_name"] == current_subcat].copy()
    if df_base.empty:
        st.warning("Für diese Unterkategorie sind im Demo-Datenausschnitt keine Artikel vorhanden.")
        return None, None

    # Original-Farbe bereinigen
    df_base["colour_group_name"] = df_base["colour_group_name"].fillna("Unbekannt")

    # NEU: Farbfamilie berechnen (z. B. Yellow statt Light Yellow / Other Yellow)
    df_base["colour_family"] = df_base["colour_group_name"].apply(get_color_family)

    colour_values = sorted(df_base["colour_family"].unique().tolist())
    colour_options = ["Alle Farben"] + colour_values

    # aktuelle Farbe aus Session holen oder Default setzen
    if (
        "base_colour" not in st.session_state
        or st.session_state["base_colour"] not in colour_options
    ):
        st.session_state["base_colour"] = "Alle Farben"

    selected_colour = st.selectbox(
        "Farbe innerhalb dieser Unterkategorie",
        options=colour_options,
        index=colour_options.index(st.session_state["base_colour"]),
        key="base_colour_select",
    )
    st.session_state["base_colour"] = selected_colour

    # Filter auf gewählte Farbfamilie anwenden (außer "Alle Farben")
    if selected_colour != "Alle Farben":
        df_base = df_base[df_base["colour_family"] == selected_colour]

    if df_base.empty:
        st.warning("Für diese Farbauswahl sind im Demo-Datenausschnitt keine Artikel vorhanden.")
        return None, None

    df_base = df_base.sort_values("prod_name")

    selected_article_id = st.session_state.get("base_article_id", None)

    max_items = 60
    df_show = df_base.head(max_items)

    st.caption(f"{len(df_base)} Artikel in dieser Auswahl gefunden.")

    cols = st.columns(3)
    for idx, (_, row) in enumerate(df_show.iterrows()):
        col = cols[idx % 3]
        with col:
            img_url = get_image_url(row["article_id_str"])
            if img_url:
                st.image(img_url, width=120)
            else:
                st.write("Kein Bild")

            # Anzeige: detaillierte Farbe behalten, nicht nur die „grobe“ Familie
            st.caption(row.get("prod_name", "")[:40])
            st.caption(
                f"{row.get('product_type_name', '')} · "
                f"{row.get('colour_group_name', '')} "
                f"({row.get('colour_family', '')})"
            )

            art_id = int(row["article_id"])
            if st.button("Als Basisteil wählen", key=f"base_{art_id}"):
                selected_article_id = art_id
                st.session_state["base_article_id"] = art_id

            if selected_article_id == art_id:
                st.caption("✅ aktuell ausgewählt")

    if selected_article_id is None:
        return None, None

    base_row = get_base_article_row(df_articles, selected_article_id)
    if base_row is None:
        return None, None

    return selected_article_id, base_row


# ---------------------------------------------------------
# Views: Auswahl-Ansicht & Outfit-Ansicht
# ---------------------------------------------------------

def render_select_view(df_articles: pd.DataFrame):
    """
    Landing Page: Basisteil auswählen.
    Gibt (selected_article_id, base_row, base_macro) zurück.
    """
    st.title("Das ist alles 80/20")

    st.markdown(
        "Wähle zuerst eine Kategorie und Unterkategorie aus (du Opfer). "
        "Dann wählst du ein konkretes Basisteil, um das Outfit zu bauen."
    )

    base_macro = select_base_macro()
    st.markdown("---")

    selected_article_id, base_row = select_base_article(df_articles, base_macro)

    # Vorschau des aktuell gewählten Basisteils
    if base_row is not None:
        st.markdown("---")
        st.markdown("### Ausgewähltes Basisteil (Vorschau)")

        col_img, col_txt = st.columns([1, 2])
        with col_img:
            img_url = get_image_url(base_row["article_id_str"])
            if img_url:
                st.image(img_url, use_container_width=True)
            else:
                st.write("Kein Bild gefunden.")

        with col_txt:
            pretty_macro = MACRO_LABEL_DE.get(base_macro, base_macro)
            st.caption(f"Makrokategorie: {pretty_macro}")
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

    return selected_article_id, base_row, base_macro


def render_outfit_view(df_articles: pd.DataFrame, df_cop: pd.DataFrame, base_article_id: int):
    """
    Outfit-Ansicht: zeigt Basisteil links und Outfit-Vorschlag rechts.
    """
    base_row = get_base_article_row(df_articles, base_article_id)
    if base_row is None:
        st.error("Basisteil nicht mehr in den Daten gefunden.")
        if st.button("Zurück zur Auswahl"):
            st.session_state["view"] = "select"
            st.rerun()
        return

    st.title("Das ist alles 80/20, du opfer")

    col_left, col_right = st.columns([1.4, 2.6])

    # Linke Spalte: Basisteil groß
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

        st.markdown("---")
        st.markdown(
            "Logik: Zuerst werden aus Transaktionsdaten gemeinsam gekaufte Artikel bestimmt "
            "(Co-Purchase). Danach werden diese nach Farbübereinstimmung mit dem Basisteil "
            "neu sortiert, um optisch passende Outfits zu erhalten. "
            "Falls es für Artikel keine gemeinsamen Transaktionsdaten gibt, werden "
            "ähnliche Artikel gesucht und deren Co-Purchase-Daten verwendet."
        )

    # Rechte Spalte: Outfit-Vorschlag
    with col_right:
        st.subheader("Outfit-Vorschlag (von Kopf bis Fuß)")

        recommendations = get_outfit_recommendations(
            base_article_id=base_article_id,
            df_articles=df_articles,
            df_cop=df_cop,
            n_per_category=3,
        )

        if not recommendations:
            st.info("Keine passenden Empfehlungen gefunden. Möglicherweise zu wenig Transaktionsdaten.")
        else:
            for macro in MACRO_DISPLAY_ORDER:
                if macro not in recommendations:
                    continue
                rec_df = recommendations[macro]
                if rec_df.empty:
                    continue

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

                        st.caption(row.get("product_type_name", ""))
                        st.write(row.get("prod_name", ""))
                        st.caption(f"ID: {row['article_id_str']}")

                        cps = int(row.get("copurchase_count", 0))
                        cs = float(row.get("color_score", 0.0))
                        st.caption(f"Co-Purchase Count: {cps} · Color-Score: {cs:.1f}")

    st.markdown("---")
    if st.button("Zurück zur Auswahl"):
        st.session_state["view"] = "select"
        st.rerun()




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


def get_copurchase_candidates(base_article_id, df_articles, df_cop):
    # alle Paare, in denen der Basisartikel vorkommt
    mask = (df_cop["article_id_1"] == base_article_id) | (df_cop["article_id_2"] == base_article_id)
    df_pairs = df_cop[mask].copy()
    if df_pairs.empty:
        return pd.DataFrame()

    # jeweils den "anderen" Artikel im Paar bestimmen
    def _partner(row):
        if row["article_id_1"] == base_article_id:
            return row["article_id_2"]
        else:
            return row["article_id_1"]

    df_pairs["partner_id"] = df_pairs.apply(_partner, axis=1)

    # Counts je Partner aufaddieren
    df_agg = (
        df_pairs.groupby("partner_id")["count"]
        .sum()
        .reset_index()
        .rename(columns={"count": "copurchase_count"})
    )

    # mit Artikeldaten mergen
    df_merged = df_agg.merge(
        df_articles,
        left_on="partner_id",
        right_on="article_id",
        how="left"
    )

    # Falls aus irgendeinem Grund macro_category nicht mitgekommen ist: nachziehen
    if "macro_category" not in df_merged.columns:
        df_merged["macro_category"] = df_merged["product_type_name"].map(PRODUCT_TYPE_TO_MACRO)

    # Basisartikel selbst entfernen und nur gültige Makrokategorien behalten
    df_merged = df_merged[df_merged["partner_id"] != base_article_id]
    df_merged = df_merged[~df_merged["macro_category"].isna()]

    # nach Co-Purchase-Count sortieren
    df_merged = df_merged.sort_values("copurchase_count", ascending=False)

    return df_merged

def get_similar_articles(base_row, df_articles, max_neighbors: int = 30):
    """
    Sucht Artikel, die dem Basisteil ähnlich sind:
    - gleiche Makrokategorie
    - bevorzugt gleiche product_type_name
    - nach Farblogik sortiert
    Gibt eine Liste von article_ids zurück.
    """
    base_article_id = int(base_row["article_id"])
    base_macro = base_row.get("macro_category", None)

    if pd.isna(base_macro):
        return []

    # Pool: gleiche Makrokategorie, nicht der Basisartikel selbst
    pool = df_articles[
        (df_articles["macro_category"] == base_macro)
        & (df_articles["article_id"] != base_article_id)
    ].copy()
    if pool.empty:
        return []

    # Wenn möglich, auf gleichen product_type_name einschränken
    base_pt = base_row.get("product_type_name", None)
    if isinstance(base_pt, str) and base_pt:
        same_pt = pool[pool["product_type_name"] == base_pt]
        if not same_pt.empty:
            pool = same_pt

    # Farblogik anwenden, um die "ähnlichsten" zu finden
    pool = pool.copy()
    pool["color_score_tmp"] = pool.apply(
        lambda r: compute_color_score(base_row, r),
        axis=1,
    )
    pool = pool.sort_values("color_score_tmp", ascending=False).head(max_neighbors)

    return pool["article_id"].astype(int).tolist()

def get_copurchases_from_similar(
    similar_article_ids,
    base_article_id,
    df_articles,
    df_cop,
):
    """
    Nutzt die Co-Purchase-Historie der ähnlichen Artikel:
    - sammelt alle Paare, in denen einer der ähnlichen Artikel vorkommt
    - aggregiert die Counts je partner_id
    - mergt Artikeldaten inkl. macro_category
    """
    if not similar_article_ids:
        return pd.DataFrame()

    df_sim = df_cop[
        df_cop["article_id_1"].isin(similar_article_ids)
        | df_cop["article_id_2"].isin(similar_article_ids)
    ].copy()
    if df_sim.empty:
        return pd.DataFrame()

    def _partner_from_sim(row):
        if row["article_id_1"] in similar_article_ids:
            return row["article_id_2"]
        else:
            return row["article_id_1"]

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

    # macro_category nachziehen, falls nötig
    if "macro_category" not in df_merged.columns:
        df_merged["macro_category"] = df_merged["product_type_name"].map(PRODUCT_TYPE_TO_MACRO)

    # Basisartikel selbst raus und nur gültige Makrokategorien behalten
    df_merged = df_merged[df_merged["partner_id"] != base_article_id]
    df_merged = df_merged[~df_merged["macro_category"].isna()]

    df_merged = df_merged.sort_values("copurchase_count", ascending=False)

    return df_merged



# ---------------------------------------------------------
# Farblogik (aus demo5 übernommen)
# ---------------------------------------------------------

# 1. Definition von "No-Go" Paaren (Clashes)
# Diese Kombinationen bekommen massive Punktabzüge.
# Format: (Set A, Set B) -> Wenn Farbe 1 in A und Farbe 2 in B (oder umgekehrt), dann Clash.
CLASH_PAIRS = [
    # Klassiker: Navy & Schwarz beißt sich oft
    ({"black"}, {"dark blue", "navy"}),

    # Braun & Schwarz wirkt oft "schmutzig" zusammen
    ({"black"}, {"brown", "dark beige", "yellowish brown"}),

    # Warm (Beige/Gold) & Kalt (Grau/Silber) mischen
    ({"grey", "dark grey", "light grey", "silver"}, {"beige", "brown", "gold", "yellowish brown", "mustard"}),

    # Rot & Pink/Lila (kann cool sein, ist aber risky für Algorithmen)
    ({"red", "dark red"}, {"pink", "light pink", "dark pink", "purple", "lilac purple"}),

    # Rot & Orange
    ({"red", "dark red"}, {"orange", "dark orange"}),
]

# 2. Konservative "Safe Bet" Paletten
COLOR_PALETTES = {
    "beige":        ["dark green", "dark blue", "denim blue", "white", "black", "brown", "khaki"],
    "black":        ["white", "beige", "grey", "light grey", "silver", "gold", "red", "light blue"],
    "white":        ["black", "blue", "dark blue", "beige", "grey", "silver", "denim blue", "khaki", "pink"],
    "off white":    ["black", "blue", "dark blue", "beige", "brown", "khaki", "grey"],
    "grey":         ["white", "black", "light pink", "pink", "blue", "denim blue", "dark blue", "red", "purple"],
    "dark grey":    ["white", "black", "light pink", "yellow", "light blue"],  # Kein Beige!
    "blue":         ["white", "beige", "grey", "black", "yellow", "orange", "silver"],
    "dark blue":    ["white", "beige", "grey", "yellow", "gold", "red", "denim blue"],  # Kein Schwarz!
    "light blue":   ["dark blue", "white", "beige", "pink", "silver", "grey"],
    "red":          ["black", "white", "dark blue", "denim blue", "beige", "grey"],
    "dark red":     ["black", "beige", "grey", "white", "dark blue"],
    "pink":         ["grey", "white", "dark blue", "denim blue", "black", "silver"],
    "green":        ["beige", "white", "black", "navy", "denim blue", "yellow"],
    "dark green":   ["beige", "gold", "brown", "white", "black", "grey"],
    "khaki":        ["white", "black", "orange", "red", "denim blue", "white"],
    "yellow":       ["blue", "grey", "white", "black", "navy", "denim blue"],
    "orange":       ["blue", "white", "black", "grey", "khaki"],
    "brown":        ["beige", "white", "blue", "denim blue", "green", "dark green"],  # Kein Schwarz/Grau
}


def _is_neutral(name: str) -> bool:
    """Prüft, ob eine Farbe als neutral gilt."""
    name = (name or "").lower().strip()
    return name in NEUTRAL_KEYWORDS or any(k in name for k in NEUTRAL_KEYWORDS)


def _check_clash(col1: str, col2: str) -> bool:
    """Prüft gegen die CLASH_PAIRS Liste."""
    for set_a, set_b in CLASH_PAIRS:
        # Prüfen ob (col1 in A und col2 in B) ODER (col1 in B und col2 in A)
        if (col1 in set_a and col2 in set_b) or (col1 in set_b and col2 in set_a):
            return True
    return False


def compute_color_score(base_row, candidate_row) -> float:
    # Start-Score
    score = 0.0

    # Werte extrahieren & normalisieren
    base_group = str(base_row.get("colour_group_name", "") or "").lower()
    cand_group = str(candidate_row.get("colour_group_name", "") or "").lower()

    base_master = str(base_row.get("perceived_colour_master_name", "") or "").lower()
    cand_master = str(candidate_row.get("perceived_colour_master_name", "") or "").lower()

    base_value = str(base_row.get("perceived_colour_value_name", "") or "").lower()
    cand_value = str(candidate_row.get("perceived_colour_value_name", "") or "").lower()

    # --- LOGIK 0: CLASH CHECK (Todesurteil) ---
    # Wenn die Farben sich beißen, ziehen wir massiv Punkte ab.
    if _check_clash(base_group, cand_group) or _check_clash(base_master, cand_master):
        return -10.0  # Sofortiger "Rauswurf" aus den Top-Rängen

    base_is_neutral = _is_neutral(base_group)
    cand_is_neutral = _is_neutral(cand_group)

    # --- LOGIK 1: PALETTEN-MATCH (Der "Gold Standard") ---
    palette_matches = COLOR_PALETTES.get(base_group, []) + COLOR_PALETTES.get(base_master, [])
    if cand_group in palette_matches or cand_master in palette_matches:
        score += 5.0

    # --- LOGIK 2: KONTRAST (Neutral + Farbe) ---
    if base_is_neutral != cand_is_neutral:
        score += 2.0

    # --- LOGIK 3: MONOCHROM / TON-IN-TON ---
    if base_master == cand_master:
        # Gleiche Farbe ist okay, aber nicht so gut wie ein perfekter Match
        if base_is_neutral:
            score += 1.0  # Schwarz auf Schwarz ist okay
        else:
            score += 1.5  # Rot auf Rot ist ein Statement

    # --- LOGIK 4: HELLIGKEITSKONTRAST ---
    # Wir belohnen "Dunkel + Hell" (z.B. Dunkelblau + Weiß)
    if base_value and cand_value and base_value != cand_value:
        is_dark_base = "dark" in base_value
        is_light_base = "light" in base_value or "dusty light" in base_value

        is_dark_cand = "dark" in cand_value
        is_light_cand = "light" in cand_value or "dusty light" in cand_value

        if (is_dark_base and is_light_cand) or (is_light_base and is_dark_cand):
            score += 1.0

    return score


def rerank_by_color(base_row, df_cat: pd.DataFrame) -> pd.DataFrame:
    if df_cat.empty:
        return df_cat

    df_cat = df_cat.copy()
    df_cat["color_score"] = df_cat.apply(
        lambda r: compute_color_score(base_row, r),
        axis=1,
    )

    if "copurchase_count" not in df_cat.columns:
        df_cat["copurchase_count"] = 0

    # Sortierung: Zuerst Score, dann Kaufhäufigkeit.
    # Durch den negativen Score bei Clashes landen diese ganz hinten.
    df_cat = df_cat.sort_values(
        by=["color_score", "copurchase_count"],
        ascending=[False, False],
    ).reset_index(drop=True)

    return df_cat


# ---------------------------------------------------------
# Outfit-Empfehlungen
# ---------------------------------------------------------
def get_outfit_recommendations(base_article_id, df_articles, df_cop, n_per_category=3):
    # Sicherheitsnetz: falls df_articles ohne macro_category reinkommt
    if "macro_category" not in df_articles.columns:
        df_articles = df_articles.copy()
        df_articles["macro_category"] = df_articles["product_type_name"].map(PRODUCT_TYPE_TO_MACRO)

    base_row = get_base_article_row(df_articles, base_article_id)
    if base_row is None:
        return {}

    base_macro = base_row.get("macro_category", None)
    target_macros = get_target_macros_for_base(base_macro)

    # 1) Co-Purchase-Kandidaten direkt für den Basisartikel
    candidates = get_copurchase_candidates(base_article_id, df_articles, df_cop)

    # 2) Fallback: wenn es KEINE Co-Purchase-Daten gibt,
    #    nutze Co-Purchases von ähnlichen Artikeln
    if candidates is None or candidates.empty:
        similar_ids = get_similar_articles(base_row, df_articles, max_neighbors=30)
        similar_candidates = get_copurchases_from_similar(
            similar_article_ids=similar_ids,
            base_article_id=base_article_id,
            df_articles=df_articles,
            df_cop=df_cop,
        )
        candidates = similar_candidates

    # 3) Wenn immer noch nichts da ist: leeres DF mit minimalen Spalten,
    #    damit der Rest der Logik nicht crasht.
    if candidates is None or candidates.empty:
        candidates = pd.DataFrame(columns=["article_id", "macro_category", "copurchase_count"])

    # Falls macro_category noch fehlt (zusätzliche Absicherung)
    if "macro_category" not in candidates.columns and "product_type_name" in candidates.columns:
        candidates["macro_category"] = candidates["product_type_name"].map(PRODUCT_TYPE_TO_MACRO)

    recommendations = {}

    for macro in target_macros:
        # Co-Purchase-Kandidaten für diese Makrokategorie
        cat_df = candidates[candidates["macro_category"] == macro] if "macro_category" in candidates.columns else pd.DataFrame()

        # Fallback-Pool: alle Artikel dieser Makrokategorie
        fallback_pool = df_articles[
            (df_articles["macro_category"] == macro)
            & (df_articles["article_id"] != base_article_id)
        ]

        if not cat_df.empty:
            cat_df = rerank_by_color(base_row, cat_df)
            cat_top = cat_df.head(n_per_category)
        else:
            cat_top = pd.DataFrame(columns=fallback_pool.columns)

        # Falls zu wenig Kandidaten: mit Fallback auffüllen
        if len(cat_top) < n_per_category and not fallback_pool.empty:
            needed = n_per_category - len(cat_top)
            already_ids = set(cat_top["article_id"].tolist()) if not cat_top.empty else set()
            fallback_pool2 = fallback_pool[~fallback_pool["article_id"].isin(already_ids)]

            if not fallback_pool2.empty and needed > 0:
                fallback_sample = fallback_pool2.sample(
                    n=min(needed, len(fallback_pool2)),
                    random_state=42,
                )
                fallback_sample = fallback_sample.copy()
                fallback_sample["copurchase_count"] = 0

                combined = pd.concat([cat_top, fallback_sample], ignore_index=True)
                combined = rerank_by_color(base_row, combined)
                cat_top = combined.head(n_per_category)

        if not cat_top.empty:
            recommendations[macro] = cat_top

    return recommendations



# ---------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------
def main():
    # Titel etc. kommen aus den View-Funktionen
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

    # View-State initialisieren
    if "view" not in st.session_state:
        st.session_state["view"] = "select"
    if "base_article_id" not in st.session_state:
        st.session_state["base_article_id"] = None

    # Routing: Auswahl-Screen vs Outfit-Screen
    if st.session_state["view"] == "select":
        selected_article_id, base_row, base_macro = render_select_view(df_articles)

        if selected_article_id is not None:
            st.markdown("---")
            if st.button("Outfit anzeigen"):
                st.session_state["base_article_id"] = selected_article_id
                st.session_state["view"] = "outfit"
                st.rerun()

    elif st.session_state["view"] == "outfit":
        base_article_id = st.session_state.get("base_article_id")
        if base_article_id is None:
            st.session_state["view"] = "select"
            st.rerun()

        render_outfit_view(df_articles, df_cop, base_article_id)


if __name__ == "__main__":
    main()
