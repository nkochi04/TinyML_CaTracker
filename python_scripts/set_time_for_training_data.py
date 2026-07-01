import pandas as pd
from pathlib import Path
labels = ("eat", "groom", "play", "walk", "chill")
for l in labels:
    INPUT_DIR = Path(l)   # folder with your raw CSVs
    OUTPUT_DIR = Path(l + "_impulse")
    SAMPLE_RATE_HZ = 50
    MS_PER_SAMPLE = 1000 // SAMPLE_RATE_HZ  # 20 ms

    OUTPUT_DIR.mkdir(exist_ok=True)

    csv_files = list(INPUT_DIR.glob("*.csv"))
    if not csv_files:
        print("No CSV files found in", INPUT_DIR.resolve())
    else:
        for csv_path in sorted(csv_files):
            try:
                df = pd.read_csv(csv_path)
            except pd.errors.EmptyDataError:
                print(f"⚠  Skipped (empty): {csv_path.name}")
                continue

            if df.empty or not {"ax", "ay", "az", "gx", "gy", "gz"}.issubset(df.columns):
                print(f"⚠  Skipped (missing columns): {csv_path.name}")
                continue

            df_out = pd.DataFrame()
            df_out["timestamp"] = range(0, len(df) * MS_PER_SAMPLE, MS_PER_SAMPLE)
            df_out["accX"] = df["ax"]
            df_out["accY"] = df["ay"]
            df_out["accZ"] = df["az"]
            df_out["gyrX"] = df["gx"]
            df_out["gyrY"] = df["gy"]
            df_out["gyrZ"] = df["gz"]

            out_path = OUTPUT_DIR / csv_path.name
            df_out.to_csv(out_path, index=False)
            print(f"✓ {csv_path.name}  ({len(df_out)} rows)  →  {out_path}")

        print(f"\nDone. {len(csv_files)} file(s) written to '{OUTPUT_DIR}/'")
