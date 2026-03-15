"""Flexible curve reading module for multiple formats.
Handles: EMS, SGE (consumption/production), Archelios, ALEX formats.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import io
import re
from typing import Tuple, Dict, Any, Optional

def read_curve(file_or_df: Any) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    metadata: Dict[str, Any] = {
        "source_file": None,
        "detected_format": None,
        "frequency": None,
        "unit": None,
        "total_rows": None,
    }

    # 1. Chargement des données brutes
    if isinstance(file_or_df, str):
        metadata["source_file"] = file_or_df
        # Lecture initiale pour vérifier s'il y a un header
        raw_df = pd.read_csv(file_or_df, sep=None, engine="python", nrows=2, header=None)
        # Si la première ligne du fichier ressemble à une date, on recharge sans header
        has_header = not _is_data_row(raw_df.iloc[0])
        raw_df = pd.read_csv(file_or_df, sep=None, engine="python", dtype=str, header=0 if has_header else None)
    
    elif isinstance(file_or_df, (io.BytesIO, io.StringIO)):
        metadata["source_file"] = "uploaded_file"
        content = file_or_df.read()
        file_or_df.seek(0)
        try:
            raw_df = pd.read_excel(io.BytesIO(content))
        except:
            # Détection de header pour les flux CSV
            sample = pd.read_csv(io.BytesIO(content), sep=None, engine="python", nrows=2, header=None)
            has_header = not _is_data_row(sample.iloc[0])
            file_or_df.seek(0)
            raw_df = pd.read_csv(file_or_df, sep=None, engine="python", dtype=str, header=0 if has_header else None)

    elif isinstance(file_or_df, pd.DataFrame):
        raw_df = file_or_df.copy()
        metadata["source_file"] = "dataframe"
    else:
        raise TypeError(f"Expected str, file-like, or DataFrame; got {type(file_or_df)}")

    # Nettoyage des noms de colonnes
    raw_df.columns = [str(c).strip() for c in raw_df.columns]
    
    # 2. Détection du format et des colonnes
    dt_col, val_col, fmt = _detect_format(raw_df)
    if dt_col is None or val_col is None:
        raise ValueError(f"Impossible de détecter les colonnes date et valeur dans {raw_df.columns.tolist()}")

    metadata["detected_format"] = fmt
    df = raw_df.copy()

    # 3. Nettoyage spécifique par format (SGE)
    if fmt == "SGE":
        # On ne garde que la puissance active (W) pour éviter les doublons avec VAr
        if "Unité" in df.columns:
            df = df[df["Unité"].isin(["W", "kW", "Wh", "kWh"])]
        elif "Grandeur physique" in df.columns:
            df = df[df["Grandeur physique"] == "PA"]

    # 4. Extraction et conversion
    df = df[[dt_col, val_col]].copy()
    df.columns = ["datetime", "value"]

    # Parsing Date : on essaie le format jour en premier (standard FR)
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce", dayfirst=True)
    df = df[df["datetime"].notna()]
    if df["datetime"].dt.tz is not None:
        df["datetime"] = df["datetime"].dt.tz_localize(None)

    # Parsing Valeur : gestion des virgules françaises
    df["value"] = df["value"].astype(str).str.replace(",", ".").apply(pd.to_numeric, errors="coerce")
    df = df[df["value"].notna()]

    # 5. Normalisation en kW
    unit = _infer_unit(fmt, val_col, df)
    if unit in ["W", "Wh"]:
        df["value"] = df["value"] / 1000.0
        metadata["unit"] = "kW" if "W" in unit else "kWh"
    else:
        metadata["unit"] = unit if unit != "Unknown" else "kW"

    # Finalisation
    df = df.set_index("datetime").sort_index()
    metadata["total_rows"] = len(df)
    metadata["frequency"] = _infer_frequency(df.index)

    return df[["value"]], metadata

def _is_data_row(row: pd.Series) -> bool:
    """Vérifie si une ligne ressemble à de la donnée (Date, Chiffre) plutôt qu'à un en-tête."""
    try:
        val_str = str(row.iloc[0])
        # Si le premier élément peut être une date, c'est probablement de la donnée
        is_date = pd.to_datetime(val_str, errors='coerce') is not pd.NaT
        return is_date
    except:
        return False

def _detect_format(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], str]:
        
    cols = df.columns.tolist()
    cols_lower = [str(c).lower() for c in cols]

    # SGE
    if "horodate" in cols_lower and "valeur" in cols_lower:
        return cols[cols_lower.index("horodate")], cols[cols_lower.index("valeur")], "SGE"
    
    # EMS
    if "date" in cols_lower and "valeur" in cols_lower:
        return cols[cols_lower.index("date")], cols[cols_lower.index("valeur")], "EMS"

    # ALEX / Standard
    if "datetime" in cols_lower and any(x in cols_lower for x in ["w", "kw", "value"]):
        val_idx = [i for i, c in enumerate(cols_lower) if c in ["w", "kw", "value"]][0]
        return cols[cols_lower.index("datetime")], cols[val_idx], "ALEX"
    
    # PVGIS
    
    if df.shape[1] == 2:
        first_col = df.iloc[:, 0].astype(str)

        pattern = r"^\d{8}:\d{4}$"

        # on regarde les premières lignes
        sample = first_col.head(10)

        if sample.str.match(pattern).all():
            return cols[0], cols[1], "PVGIS"

    # Fallback / Archelios / Headerless
    dt_col, val_col = None, None
    for i, col in enumerate(cols):
        cl = str(col).lower()
        if any(x in cl for x in ["date", "time", "horodate", "heure"]) or _is_data_row(df[col]):
            if dt_col is None: dt_col = col
        elif any(x in cl for x in ["valeur", "value", "w", "kw"]):
            if val_col is None: val_col = col

    # Si on n'a rien trouvé, on prend col 0 et col 1 (cas typique Archelios sans header)
    if dt_col is None: dt_col = cols[0]
    if val_col is None: val_col = cols[1] if len(cols) > 1 else None
    
    return dt_col, val_col, "Archelios" if "Archelios" not in cols else "Unknown"

def _infer_unit(fmt: str, val_col: str, df: pd.DataFrame) -> str:
    col_lower = str(val_col).lower()
    if fmt in ["SGE", "ALEX"] or " w" in col_lower or col_lower == "w":
        return "W"
    if "kw" in col_lower:
        return "kW"
    # Heuristique pour les fichiers sans unité explicite (comme EMS ou Archelios)
    # Si la moyenne est > 100, c'est probablement des Watts
    if df["value"].mean() > 100:
        return "W"
    return "kW"

def _infer_frequency(index: pd.DatetimeIndex) -> str:
    if len(index) < 2: return "Unknown"
    delta = pd.Series(index[1:] - index[:-1]).value_counts().idxmax()
    return f"PT{int(delta.total_seconds()/60)}M"