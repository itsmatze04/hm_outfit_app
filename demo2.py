import streamlit as st
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------
# Pfade
# ---------------------------------------------------------
DATA_PROCESSED = Path("data_processed")
IMAGES_ROOT = Path("images_sample")

ARTICLES_FILE = DATA_PROCESSED / "articles_filtered.csv"
COPURCHASE_FILE = DATA_PROCESSED / "copurchase_filtered.csv"

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

# Feste Anzeige-Reihenfolge im Outfit (von oben nach unten „angezogen“)
MACRO_DISPLAY_ORDER = ["ACCESSORY", "TOP", "OUTERWEAR", "BOTTOM", "SHOES"]


# ---------------------------------------------------------
# Datenladen (mit Caching)
# ---------------------------------------------------------
@st.cache_data
def load_articles() -> pd.DataFrame:
    df = pd.read_csv(ARTICLES_FILE)
    df["article_id"] = df["article_id"].astype(int)
    df["article_id_str"] = df["article_id"].astype(str).str.zfill(10)
    df["macro_category"] = df["product_type_name"].map(PRODUCT_TYPE_TO_MACRO)
    return df


@st.cache_data
def load_copurchase() -> pd.DataFrame:
    df = pd.read_csv(COPURCHASE_FILE)
    df["article_id_1"] = df["article_id_1"].astype(int)
    df["article_id_2"] = df["article_id_2"].astype(int)
    return df


# ---------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------
def get_image_path(article_id_str: str) -> Path | None:
    folder = article_id_str[:3]
    filename = f"{article_id_str}.jpg"
    path = IMAGES_ROOT / folder / filename
    if path.exists():
        return path
    return None


def get_base_article_row(df_articles: pd.DataFrame, article_id: int) -> pd.Series | None:
    rows = df_articles[df_articles["article_id"] == article_id]
    if rows.empty:
        return None
    return rows.iloc[0]


def get_target_macros_for_base(base_macro: str) -> list[str]:
    """
    Welche Kategorien sollen zum Basisteil ergänzt werden?
    Logik bleibt flexibel, Anzeige-Reihenfolge wird später über MACRO_DISPLAY_ORDER gesteuert.
    """
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


def get_copurchase_candidates(
    base_article_id: int,
    df_articles: pd.DataFrame,
    df_cop: pd.DataFrame
) -> pd.DataFrame:
    """
    Liefert alle Co-Purchase-Kandidaten für base_article_id:
    - partner_id
    - copurchase_count
    - gemergte Artikeldaten inkl. macro_category
    """
    mask = (df_cop["article_id_1"] == base_article_id) | (df_cop["article_id_2"] == base_article_id)
    df_pairs = df_cop[mask].copy()
    if df_pairs.empty:
        return pd.DataFrame()

    df_pairs["partner_id"] = df_pairs.apply(
        lambda row: row["article_id_2"] if row["article_id_1"] == base_article_id else row["article_id_1"],
        axis=1
    )

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
        how="left"
    )

    df_merged = df_merged[df_merged["partner_id"] != base_article_id]
    df_merged = df_merged[~df_merged["macro_category"].isna()]

    df_merged = df_merged.sort_values("copurchase_count", ascending=False)
    return df_merged


def get_outfit_recommendations(
    base_article_id: int,
    df_articles: pd.DataFrame,
    df_cop: pd.DataFrame,
    n_per_category: int = 3,
) -> dict[str, pd.DataFrame]:
    """
    - Makrokategorie des Basisteils bestimmen
    - Co-Purchase-Kandidaten holen
    - pro Ziel-Makrokategorie Top-N auswählen
    - Fallback: zufällige Artikel aus dieser Makrokategorie
    """
    base_row = get_base_article_row(df_articles, base_article_id)
    if base_row is None:
        return {}

    base_macro = base_row.get("macro_category", None)
    target_macros = get_target_macros_for_base(base_macro)
    candidates = get_copurchase_candidates(base_article_id, df_articles, df_cop)

    recommendations: dict[str, pd.DataFrame] = {}

    for macro in target_macros:
        cat_df = candidates[candidates["macro_category"] == macro]
        cat_top = cat_df.head(n_per_category)

        if len(cat_top) < n_per_category:
            needed = n_per_category - len(cat_top)
            fallback_pool = df_articles[
                (df_articles["macro_category"] == macro)
                & (df_articles["article_id"] != base_article_id)
                & (~df_articles["article_id"].isin(cat_top["article_id"]))
            ]

            if not fallback_pool.empty and needed > 0:
                fallback_sample = fallback_pool.sample(
                    n=min(needed, len(fallback_pool)),
                    random_state=42
                )
                fallback_sample = fallback_sample.copy()
                fallback_sample["copurchase_count"] = 0
                cat_top = pd.concat([cat_top, fallback_sample], ignore_index=True)

        if not cat_top.empty:
            recommendations[macro] = cat_top

    return recommendations


# ---------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------
def main():
    st.set_page_config(
        page_title="H&M Outfit Recommender (Demo)",
        layout="wide"
    )

    st.title("Der beste Outfit selector der jemals von Nico, Finn und Matze gebaut wurde")

    df_articles = load_articles()
    df_cop = load_copurchase()

    # kompakteres Label
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

        img_path = get_image_path(base_row["article_id_str"])
        if img_path is not None:
            st.image(str(img_path), use_container_width=True)
        else:
            st.write("Kein Bild gefunden.")

        st.markdown(f"**ID:** {base_row['article_id_str']}")
        st.markdown(f"**Name:** {base_row.get('prod_name', '')}")
        st.caption(
            f"{base_row.get('product_type_name', '')} · "
            f"{base_row.get('product_group_name', '')} · "
            f"{base_row.get('index_name', '')}"
        )
        st.caption(
            f"Farbe: {base_row.get('colour_group_name', '')}, "
            f"{base_row.get('perceived_colour_master_name', '')}"
        )

        st.markdown("---")
        st.markdown(
            "Diese Demo nutzt Co-Purchase-Daten, um passende Teile zu finden "
            "(vereinfachte Warenkorb-Logik auf H&M-Transaktionen)."
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
            # Nach definierter Outfit-Reihenfolge anzeigen:
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
                        img_path = get_image_path(row["article_id_str"])
                        if img_path is not None:
                            st.image(str(img_path), use_container_width=True)
                        else:
                            st.write("Kein Bild")

                        st.caption(row.get("product_type_name", ""))
                        st.write(row.get("prod_name", ""), unsafe_allow_html=False)
                        st.caption(f"ID: {row['article_id_str']}")
                        if "copurchase_count" in row and row["copurchase_count"] > 0:
                            st.caption(f"Co-Purchase Count: {int(row['copurchase_count'])}")

                        # etwas kompakter, daher keine weiteren Infos

if __name__ == "__main__":
    main()
