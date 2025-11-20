from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PROCESSED = BASE_DIR / "data_processed"

path = DATA_PROCESSED / "copurchase_top.csv"
print("Pfad:", path)
if not path.exists():
    print("copurchase_top.csv existiert NICHT.")
else:
    df = pd.read_csv(path)
    print("Form:", df.shape)
    print(df.head())
