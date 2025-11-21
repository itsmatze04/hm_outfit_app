import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict

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

MACRO_LABEL_DE = {
    "ACCESSORY": "Kopf / Accessoires",
    "TOP": "Oberteil",
    "OUTERWEAR": "Jacke / Mantel",
    "BOTTOM": "Unterteil",
    "SHOES": "Schuhe",
}

MACRO_DISPLAY_ORDER = ["ACCESSORY", "TOP", "OUTERWEAR", "BOTTOM", "SHOES"]

NEUTRAL_KEYWORDS = {"black", "white", "grey", "gray", "beige", "cream", "creme", "navy"}


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
# Farblogik
# ---------------------------------------------------------
def _is_neutral(name):
    name = (name or "").lower()
    return any(tok in name for tok in NEUTRAL_KEYWORDS)


def compute_color_score(base_row, candidate_row):
    score = 0.0

    base_group = str(base_row.get("colour_group_name", "") or "").lower()
    cand_group = str(candidate_row.get("colour_group_name", "") or "").lower()

    base_value = str(base_row.get("perceived_colour_value_name", "") or "").lower()
    cand_value = str(candidate_row.get("perceived_colour_value_name", "") or "").lower()

    base_master = str(base_row.get("perceived_colour_master_name", "") or "").lower()
    cand_master = str(candidate_row.get("perceived_colour_master_name", "") or "").lower()

    if base_master and cand_master and base_master == cand_master:
        score += 3.0

    if base_group and cand_group and base_group == cand_group:
        score += 2.0

    if base_value and cand_value and base_value == cand_value:
        score += 1.0

    if _is_neutral(base_group) or _is_neutral(base_master):
        score += 0.5
    if _is_neutral(cand_group) or _is_neutral(cand_master):
        score += 0.5

    return score


def rerank_by_color(base_row, df_cat):
    if df_cat.empty:
        return df_cat

    df_cat = df_cat.copy()
    df_cat["color_score"] = df_cat.apply(
        lambda r: compute_color_score(base_row, r),
        axis=1
    )

    if "copurchase_count" not in df_cat.columns:
        df_cat["copurchase_count"] = 0

    df_cat = df_cat.sort_values(
        by=["color_score", "copurchase_count"],
        ascending=[False, False]
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
    st.title("Bitte gute Note 🙏")

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
        st.error(f"Fehler beim Laden von copurchase-Splits: {e}")
        st.stop()

    df_articles["select_label"] = (
        df_articles["article_id_str"]
        + " | "
        + df_articles["prod_name"].fillna("").str.slice(0, 40)
        + " | "
        + df_articles["product_type_name"].fillna("")
    )

    col_left, col_right = st.columns([1.4, 2.6])

    with col_left:
        st.subheader("Basisteil")
        selected_label = st.selectbox(
            "Artikel auswählen",
            options=df_articles["select_label"].tolist(),
        )
        selected_article_id = int(selected_label.split(" | ")[0])

        base_row = get_base_article_row(df_articles, selected_article_id)
        if base_row is None:
            st.error("Ausgewählter Artikel nicht in den gefilterten Daten gefunden.")
            return

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
            "neu sortiert, um optisch passende Outfits zu erhalten." 
            "Falls es für Artikel keine gemeinsamen Transaktionsdaten gibt, werden " \
            "ähnliche Artikel gesucht und deren Co-Purchase-Daten verwendet."
        )

    with col_right:
        st.subheader("Outfit-Vorschlag (von Kopf bis Fuß)")

        recommendations = get_outfit_recommendations(
            base_article_id=selected_article_id,
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


if __name__ == "__main__":
    main()
