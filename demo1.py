import streamlit as st
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_PROCESSED = BASE_DIR / "data_processed"
IMAGES_DIR = BASE_DIR / "images_sample"


@st.cache_data
def load_articles():
    df = pd.read_csv(DATA_PROCESSED / "articles_top.csv")
    df["article_id_str"] = df["article_id"].astype(str).str.zfill(10)

    def make_label(row):
        parts = [
            row["article_id_str"],
            str(row.get("product_type_name", "")),
            str(row.get("product_group_name", "")),
        ]
        return " | ".join([p for p in parts if p])
    df["label"] = df.apply(make_label, axis=1)

    return df


@st.cache_data
def load_copurchase():
    path = DATA_PROCESSED / "copurchase_top.csv"
    if not path.exists():
        return pd.DataFrame(columns=["article_id_1", "article_id_2", "count"])
    df = pd.read_csv(path)
    return df


def get_image_path(article_id: int) -> Path | None:
    aid = str(article_id).zfill(10)
    subdir = aid[:3]
    path = IMAGES_DIR / subdir / f"{aid}.jpg"
    return path if path.exists() else None


def get_recommendations(
    article_id: int,
    articles: pd.DataFrame,
    cop: pd.DataFrame,
    top_n: int = 6,
) -> pd.DataFrame:
    if cop.empty:
        return pd.DataFrame()

    # Paare finden, in denen der Artikel vorkommt
    mask = (cop["article_id_1"] == article_id) | (cop["article_id_2"] == article_id)
    df = cop.loc[mask].copy()
    if df.empty:
        return pd.DataFrame()

    # Partner-Artikel bestimmen
    df["partner_id"] = df.apply(
        lambda row: row["article_id_2"]
        if row["article_id_1"] == article_id
        else row["article_id_1"],
        axis=1,
    )

    # Nach Häufigkeit sortieren, Duplikate entfernen
    df = df.sort_values("count", ascending=False).drop_duplicates("partner_id")

    # Mit Artikeltabelle joinen
    recs = df.merge(
        articles,
        left_on="partner_id",
        right_on="article_id",
        how="left",
        suffixes=("", "_article"),
    )

    # Nur die wichtigsten Spalten behalten
    cols = [
        "partner_id",
        "count",
        "article_id",
        "article_id_str",
        "prod_name",
        "product_type_name",
        "product_group_name",
        "index_name",
        "colour_group_name",
    ]
    recs = recs[[c for c in cols if c in recs.columns]]

    return recs.head(top_n)

def get_fallback_recommendations(
    selected: pd.Series,
    articles: pd.DataFrame,
    top_n: int = 6,
) -> pd.DataFrame:
    """Fallback: ähnliche Artikel aus derselben Produktgruppe, ohne Co-Purchase."""
    base = articles[articles["article_id"] != selected["article_id"]].copy()

    # Gleiche Produktgruppe bevorzugen
    if "product_group_name" in articles.columns:
        same_group = base[base["product_group_name"] == selected.get("product_group_name")]
        if len(same_group) >= 1:
            base = same_group

    # Zur Sicherheit mischen und begrenzen
    if len(base) > top_n:
        base = base.sample(n=top_n, random_state=42)

    # Einheitliches Schema: so tun, als käme das Feld 'partner_id'
    base = base.copy()
    base["partner_id"] = base["article_id"]
    base["count"] = 0  # keine Co-Purchase-Counts

    return base



def main():
    st.title("Nicos, Finns und Matzes Geilo Outfit Recommender 👕👖👟")
    st.write(
        "Wähle einen Artikel aus und sieh dir Bild, Basisinformationen und einfache Outfit-Vorschläge "
        "auf Basis von Co-Purchase-Daten an (ich grüße meine Oma)."
    )

    articles = load_articles()
    copurchase = load_copurchase()

    if articles.empty:
        st.error("Keine Artikel in data_processed/articles_top.csv gefunden.")
        return

    selected_label = st.selectbox(
        "Artikel wählen",
        options=articles["label"].tolist(),
    )

    selected = articles.loc[articles["label"] == selected_label].iloc[0]
    selected_id = int(selected["article_id"])

    main_cols = st.columns([1, 2])

    with main_cols[0]:
        img_path = get_image_path(selected_id)
        if img_path is not None:
            st.image(str(img_path), use_container_width=True)
        else:
            st.info("Kein Bild im Sample für diesen Artikel gefunden.")

    with main_cols[1]:
        st.subheader("Artikelinformationen")
        st.markdown(f"**Article ID:** {selected_id}")
        if "prod_name" in selected:
            st.markdown(f"**Name:** {selected['prod_name']}")
        if "product_type_name" in selected:
            st.markdown(f"**Product type:** {selected['product_type_name']}")
        if "product_group_name" in selected:
            st.markdown(f"**Product group:** {selected['product_group_name']}")
        if "index_name" in selected:
            st.markdown(f"**Index:** {selected['index_name']}")
        if "colour_group_name" in selected:
            st.markdown(f"**Colour:** {selected['colour_group_name']}")

    st.markdown("---")
    st.subheader("Outfit-Vorschläge (Co-Purchase)")

    recs = get_recommendations(selected_id, articles, copurchase, top_n=6)

    if recs.empty:
        st.info(
            "Für diesen Artikel wurden im Sample keine Co-Purchase-Vorschläge gefunden.\n"
            "Es werden stattdessen ähnliche Artikel angezeigt."
        )
        recs = get_fallback_recommendations(selected, articles, top_n=6)

    cols = st.columns(3)

    for idx, (_, row) in enumerate(recs.iterrows()):
        col = cols[idx % 3]
        with col:
            rec_img_path = get_image_path(int(row["partner_id"]))
            if rec_img_path is not None:
                st.image(str(rec_img_path), use_container_width=True)
            else:
                st.text("(kein Bild)")
            st.markdown(f"**{str(int(row['partner_id'])).zfill(10)}**")
            if "prod_name" in row:
                st.caption(str(row["prod_name"]))
            if "product_group_name" in row:
                st.text(str(row["product_group_name"]))
            st.text(f"Gemeinsame Käufe: {int(row['count'])}")


if __name__ == "__main__":
    main()
