import sys
import os
# Add project root to path (2 levels up from this file)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pandas as pd
from services.curve_standardizer.standardizer import CurveStandardizer

# Fichier de test
TEST_FILE = "ACC_data/producers/14505643960682.csv"

if __name__ == "__main__":
    std = CurveStandardizer()
    result = std.process(TEST_FILE)
    print("Result:", result)
    preview_df = std.get_preview_dataframe()
    print("Preview DataFrame:")
    print(preview_df.head())
    if preview_df is None or preview_df.empty:
        print("⚠️ Courbe non exploitable pour l'affichage. Vérifiez le format (datetime + colonnes numériques).")
    else:
        print("✅ Courbe exploitable pour l'affichage.")
