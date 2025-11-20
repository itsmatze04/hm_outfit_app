Kontext / Projektstand (Fortsetzung H&M Outfit-App):

- Ziel: Interaktive Streamlit-Web-App „Complete the Look“ auf Basis des Kaggle-Datensatzes „H&M Personalized Fashion Recommendations“ (articles + transactions + Bilder). App soll in der Präsentation live gezeigt werden (Streamlit Community Cloud).
- Relevante Kategorien wurden bereits definiert (Tops, Bottoms, Shoes, Outerwear, Accessoires wie Caps/Hats/Bags). „Unnötige“ Kategorien (Dog Wear, Slippers, Pre-walkers, etc.) sind rausgefiltert.
- Es existiert:
  - `data_raw/articles.csv`
  - `data_raw/transactions_train.csv`
  - Original-Bilder unter `data_raw/images/...`
  - Gefilterte Artikeldaten: `data_processed/articles_filtered.csv`
  - Bildsample für diese Artikel: `images_sample/<erste3>/<article_id>.jpg` (lokal weiterhin vorhanden, v. a. für Tests/Backups)
  - Co-Purchase-Skript `scripts/build_copurchase_filtered.py`, das auf Basis von `articles_filtered.csv` und `transactions_train.csv` eine Co-Purchase-Datei baut:
    - Output: `data_processed/copurchase_filtered.csv` mit Spalten `article_id_1`, `article_id_2`, `count`
- Bild-Hosting / Schnittstelle:
  - Die relevanten H&M-Bilder (aktuell ca. 60.000 / ~27 GB) wurden aus dem lokalen Ordner auf **Cloudflare R2** migriert.
  - Die Bilder liegen in einem R2-Bucket (z. B. `hm-images`) und sind öffentlich per HTTPS-URL abrufbar.
  - Die App greift **nicht mehr direkt auf lokale Bildpfade** zu, sondern holt Bilder über eine einfache Schnittstelle/Funktion, die aus der `article_id` die passende URL ableitet:
    - Beispiel (Prinzip):
      - `BASE_URL = "https://<accountid>.r2.cloudflarestorage.com/hm-images"` oder eine eigene CDN-Domain (z. B. `https://cdn.deine-domain.de`)
      - `get_image_url(article_id) -> f"{BASE_URL}/{article_id}.jpg"` bzw. mit Prefix-Ordnern `f"{BASE_URL}/{article_id[:3]}/{article_id}.jpg"`
    - In der Streamlit-App werden Bilder über `st.image(get_image_url(article_id))` geladen.
  - Vorteil:
    - GitHub-Repo bleibt leichtgewichtig (keine Gigabyte an Bildern im Repo).
    - Streamlit Community Cloud muss keine lokalen Bilddateien ausliefern, sondern nur externe URLs rendern.
    - Das Setup ist skalierbar, da Cloudflare R2 Storage und Traffic effizient übernimmt.
  - Lokale `images_sample/`-Struktur kann weiterhin für Offline-Tests genutzt werden, ist für das Deployment aber nicht mehr zwingend notwendig.

- Die aktuelle `app.py`:
  - Lädt `articles_filtered.csv` und `copurchase_filtered.csv`.
  - Mappt `product_type_name` auf Makrokategorien: `TOP`, `BOTTOM`, `OUTERWEAR`, `SHOES`, `ACCESSORY`.
  - Basisteil-Auswahl aktuell über Selectbox (`article_id_str | prod_name | product_type_name`).
  - Zeigt das Basisteil links (Bild + Grundinfos).
  - Rechts: Outfit-Vorschlag „von Kopf bis Fuß“ in fester Reihenfolge:
    - `ACCESSORY` (Kopf/Accessoires)
    - `TOP`
    - `OUTERWEAR`
    - `BOTTOM`
    - `SHOES`
  - Empfehlungslogik:
    1) Co-Purchase-Kandidaten für das Basisteil (Warenkorb: gleicher Kunde + gleiches Datum).
    2) Pro Ziel-Makrokategorie werden Top-N Kandidaten gewählt.
    3) Farblogik:
       - Einfache Heuristik über `colour_group_name`, `perceived_colour_value_name`, `perceived_colour_master_name`
       - neutrale Farben (black, white, grey, beige, cream, navy) werden „kombinationsfreundlich“ behandelt
       - Kandidaten werden nach `color_score` und dann `copurchase_count` sortiert (Reranking).
    4) Fallback: Fehlen Co-Purchase-Kandidaten oder sind es zu wenige, werden ähnliche Artikel aus derselben Makrokategorie random gesampelt und ebenfalls mit der Farblogik gerankt.
  - Layout ist Desktop-first, kompakt, Bilder werden mit `use_container_width=True` angezeigt.
  - Streamlit läuft lokal; Deprecation-Warnungen zu `use_column_width` wurden bereits behoben.

Zusätzliche Ziele / Feature-Ideen für die nächsten Iterationen:
- Browser zur Basisteil-Auswahl:
  - Statt nur einer Selectbox soll es eine Art „Katalog-/Browser-Ansicht“ geben, in der der Nutzer visuell durch Basisteile scrollen kann (z. B. Grid mit Bildern der Tops).
- Filter durch Kategorie-Auswahl:
  - Möglichkeit, die sichtbaren Basisteile nach Makrokategorie oder Produktgruppe zu filtern (z. B. nur Tops, nur Schuhe, nur Jacken).
- Vorschau der Teile:
  - Optionale Vorschau-Komponente, z. B. Hover-Preview oder eine kompakte Overlay-Ansicht, bevor ein Basisteil „aktiv“ gewählt wird.
- Color-Score weniger streng machen:
  - Die aktuelle Farbheuristik ist eher konservativ. Ziel ist, die Gewichtung zu entschärfen (z. B. neutrale Farben stärker zulassen, weniger harte Bestrafung bei unterschiedlichen Farbfamilien), damit mehr Kombinationen als „okay“ durchgehen.
- Auf den Bildvorschlägen einen Button zum weiter"swipen", wo dann das nächste Produkt dieser Kategorie erscheint.
    

Wichtig: Co-Purchase-Berechnung kann länger laufen; im Skript gibt es eine Fortschrittsanzeige im Terminal. Für die Präsentation ist mindestens eine stabile, gut getestete Demo-App geplant (ggf. später zusätzliche Varianten mit alternativen UI-Konzepten wie „Tinder-Swipen“).

Bitte dort weitermachen, wo wir aufgehört haben, und zwar mit folgenden nächsten Schritten:

1. Kurzcheck der aktuellen App:
   - Prüfen, ob `copurchase_filtered.csv` erfolgreich erstellt wurde (Dateigröße, Anzahl Zeilen).
   - In der App 3–5 konkrete Demo-Artikel durchklicken (sportlich, business, winter) und schauen, ob:
     - pro Makrokategorie sinnvolle Vorschläge kommen,
     - die von-Kopf-bis-Fuß-Reihenfolge gut aussieht,
     - die Farblogik grob plausible Kombinationen erzeugt.
   - Erste Einschätzung, ob der Color-Score „zu streng“ ist und wo wir lockern sollten (z. B. stärkere Gewichtung neutraler Farben, niedrigere Scores für exakte Übereinstimmungen).

2. Präsentationsvorbereitung:
   - Gemeinsame Erarbeitung von 2–3 idealen Demo-Szenarien:
     - z. B. Sport-Look, Business-Look, Winter-Look mit konkreten `article_id`s.
   - Ausformulierte Bulletpoints für 1–2 Folien:
     - Datensatz / Setup
     - Logik (Co-Purchase + Farb-Reranking + Kategorien)
     - Business-Nutzen (Cross-Selling, Warenkorbwert, Personalisierung)
   - Vorschlag für Folie mit App-URL + QR-Code und Demo-Flow (welche Artikel klicke ich in welcher Reihenfolge).

3. UI-/Feature-Weiterentwicklung:
   - Entwurf für einen einfachen „Basisteil-Browser“ mit Kategorie-Filter (z. B. Tabs oder Selectbox nach Makrokategorie + Grid mit Bildern).
   - Grobes Konzept, wie eine „Tinder“-artige Swipe-/Click-Navigation für Outfits in Streamlit aussehen könnte (z. B. ein zentrales Bild + Buttons „Next Outfit“ / „Gefällt mir“).

4. Deployment-Vorbereitung:
   - Überprüfung/Erstellung von `requirements.txt` (mindestens: `streamlit`, `pandas`, `numpy`; optional `scipy`/`scikit-learn` falls benötigt).
   - Kurzer Check, ob Daten- und Bildumfang für Streamlit Community Cloud im Rahmen bleibt (Daten im Repo klein halten, Bilder ausgelagert nach Cloudflare R2).
   - Schritt-für-Schritt-Plan für Deployment auf Streamlit Cloud (Repo-Struktur, Pfade, typische Fehlerquellen).

5. Optional (falls zeitlich drin):
   - Feintuning der Farblogik (Gewichtungen anpassen, ggf. alternative Scoring-Variante).
   - UX-Verbesserungen in der App (Tooltips, kurze erklärende Texte pro Kategorie, Hinweis „Demo-Datenausschnitt“).
