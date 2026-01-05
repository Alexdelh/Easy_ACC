import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pandas as pd
from services.curve_standardizer.utils import clean_numeric_string

# Fichier de test
TEST_FILE = "ACC_data/producers/14505643960682.csv"

# Charger le CSV brut
raw_df = pd.read_csv(TEST_FILE, sep=None, engine='python', header=None, encoding='utf-8-sig')
raw_df.columns = ['datetime', 'value']

print("=== RAW DATA ===")
print(f"Shape: {raw_df.shape}")
print(f"First 15 rows:")
print(raw_df.head(15))
print(f"\nData types:")
print(raw_df.dtypes)

print("\n=== DATETIME PARSING ===")
dt_series = pd.to_datetime(raw_df['datetime'], errors='coerce')
print(f"Parsed datetime count: {dt_series.notna().sum()} / {len(dt_series)}")
print(f"NaT count: {dt_series.isna().sum()}")
print(f"First 10 parsed dates:")
print(dt_series.head(10))

print("\n=== VALUE CLEANING ===")
print("First 15 raw values:")
print(raw_df['value'].head(15))

cleaned_values = raw_df['value'].apply(clean_numeric_string)
print("\nFirst 15 cleaned values:")
print(cleaned_values.head(15))

numeric_values = pd.to_numeric(cleaned_values, errors='coerce')
print(f"\nConverted numeric count: {numeric_values.notna().sum()} / {len(numeric_values)}")
print(f"NaN count: {numeric_values.isna().sum()}")
print(f"First 15 numeric values:")
print(numeric_values.head(15))

print("\n=== COMBINED ===")
combined_df = pd.DataFrame({
    'value': numeric_values
}, index=dt_series)
print(f"Combined shape: {combined_df.shape}")
print(f"Non-null rows: {combined_df.notna().all(axis=1).sum()}")
print(f"First 15 rows:")
print(combined_df.head(15))

combined_df_clean = combined_df.dropna()
print(f"\nAfter dropna: {combined_df_clean.shape}")
print(f"First 10 rows:")
print(combined_df_clean.head(10))
