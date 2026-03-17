"""Flexible curve reading module for multiple formats.
Handles: EMS, SGE (consumption/production), Archelios, ALEX formats.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import io
import re
from typing import Tuple, Dict, Any, Optional
import streamlit as st

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
    try:
        st.info(f"Format détecté : {fmt}")
    except ImportError:
        pass
    if fmt == "Generic":
        try:
            st.warning(f"Format de courbe non reconnu, parsing générique appliqué pour le fichier : {metadata['source_file']}. Vérifiez le résultat.")
        except ImportError:
            pass

    # 3. Nettoyage spécifique par format (SGE)
    if fmt == "SGE":
        # On ne garde que la puissance active (W) pour éviter les doublons avec VAr
        if "Unité" in df.columns:
            df = df[df["Unité"].isin(["W", "kW", "Wh", "kWh"])]
        elif "Grandeur physique" in df.columns:
            df = df[df["Grandeur physique"] == "PA"]

    # 3b. Traitement spécifique PVGIS
    if fmt == "PVGIS":
        df = df[[dt_col, val_col]].copy()
        df.columns = ["datetime", "value"]
        # Parsing datetime au format PVGIS
        df["datetime"] = pd.to_datetime(df["datetime"], format="%Y%m%d:%H%M", errors="coerce")
        df = df[df["datetime"].notna()]
        # Parsing valeur (virgule ou point)
        df["value"] = df["value"].astype(str).str.replace(",", ".").apply(pd.to_numeric, errors="coerce")
        df = df[df["value"].notna()]
        # Normalisation en kW
        df["value"] = df["value"] / 1000.0
        metadata["unit"] = "kW"
        df = df.set_index("datetime").sort_index()
        metadata["total_rows"] = len(df)
        metadata["frequency"] = _infer_frequency(df.index)
        return df[["value"]], metadata

    # 4. Extraction et conversion (autres formats)
    df = df[[dt_col, val_col]].copy()
    df.columns = ["datetime", "value"]

    # Parsing Date : on essaie le format jour en premier (standard FR)
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce", dayfirst=True)
    df = df[df["datetime"].notna()]
    if df["datetime"].dt.tz is not None:
        if fmt in ("ALEX", "EMS"):
            # ALEX et EMS : timestamps UTC (suffixe Z) → conversion en heure locale Paris
            # avant suppression de la timezone pour que ex. 2022-12-31 23:00 UTC
            # devienne 2023-01-01 00:00 (Paris) et reste dans l'année calendaire correcte.
            # Le décalage est +1h en hiver (CET) et +2h en été (CEST) — géré automatiquement.
            df["datetime"] = (
                df["datetime"]
                .dt.tz_convert("Europe/Paris")
                .dt.tz_localize(None)
            )
        else:
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
    if df is None or df.empty or df.shape[1] == 0:
        return None, None, "Unknown"

    # On travaille sur une copie str pour l'analyse de motifs
    sample_df = df.head(20).copy().astype(str)
    num_cols = df.shape[1]
    cols = list(df.columns)

    def match_ratio(series, pattern):
        vals = series.dropna().astype(str).str.strip()
        if len(vals) == 0:
            return 0.0
        return vals.str.match(pattern).mean()

    def numeric_ratio(series):
        vals = (
            series.dropna()
            .astype(str)
            .str.strip()
            .str.replace(",", ".", regex=False)
        )
        if len(vals) == 0:
            return 0.0
        parsed = pd.to_numeric(vals, errors="coerce")
        return parsed.notna().mean()

    def datetime_ratio(series):
        vals = series.dropna().astype(str).str.strip()
        if len(vals) == 0:
            return 0.0
        parsed = pd.to_datetime(vals, errors="coerce", dayfirst=True)
        return parsed.notna().mean()

    # 0) SGE : détection prioritaire par noms de colonnes (avant tout le reste)
    # Les noms Horodate/Valeur sont uniques au format SGE et sans ambiguïté.
    cols_lower = [str(c).lower().strip() for c in cols]
    if "horodate" in cols_lower and "valeur" in cols_lower:
        return cols[cols_lower.index("horodate")], cols[cols_lower.index("valeur")], "SGE"

    # 1) PVGIS : Signature YYYYMMDD:HHMM + 2 colonnes
    if num_cols == 2:
        if (
            match_ratio(sample_df.iloc[:, 0], r"^\d{8}:\d{4}$") >= 0.7
            and numeric_ratio(sample_df.iloc[:, 1]) >= 0.7
        ):
            return cols[0], cols[1], "PVGIS"

    # 2) Archelios : Date avec "/" + 2 colonnes
    arche_pattern = r"^\d{1,2}/\d{1,2}/\d{2,4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?$"
    if num_cols == 2:
        if (
            match_ratio(sample_df.iloc[:, 0], arche_pattern) >= 0.7
            and numeric_ratio(sample_df.iloc[:, 1]) >= 0.7
        ):
            return cols[0], cols[1], "Archelios"

    # 3) ALEX : ISO avec T et Z + exactement 2 colonnes (datetime;valeur)
    iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
    if num_cols == 2:
        if (
            match_ratio(sample_df.iloc[:, 0], iso_pattern) >= 0.7
            and numeric_ratio(sample_df.iloc[:, 1]) >= 0.7
        ):
            return cols[0], cols[1], "ALEX"

    # 4) EMS : ISO avec T et Z + plusieurs colonnes (format: nom;date;ID_variable;valeur)
    # On prend la DERNIÈRE colonne numérique après la date (pas l'ID de variable
    # qui est lui aussi numérique mais grand entier situé avant la vraie valeur).
    for i in range(num_cols):
        if match_ratio(sample_df.iloc[:, i], iso_pattern) >= 0.7:
            # Chercher toutes les colonnes numériques après la colonne date
            numeric_candidates = [
                j for j in range(num_cols)
                if j != i and numeric_ratio(sample_df.iloc[:, j]) >= 0.7
            ]
            if numeric_candidates:
                # Prendre la dernière colonne numérique (la valeur, pas l'ID)
                return cols[i], cols[numeric_candidates[-1]], "EMS"

    # 5) SGE : heuristique si headers absents/renommés
    if num_cols >= 8:
        has_sge_units = sample_df.apply(
            lambda s: s.str.upper().isin(["W", "VAR", "VA"]).any()
        ).any()

        sge_date_pattern = r"^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$"
        dt_idx = None
        for i in range(num_cols):
            if match_ratio(sample_df.iloc[:, i], sge_date_pattern) >= 0.7:
                dt_idx = i
                break

        if dt_idx is not None and has_sge_units:
            candidate_order = []
            if dt_idx + 1 < num_cols:
                candidate_order.append(dt_idx + 1)
            candidate_order += [j for j in range(num_cols) if j != dt_idx and j not in candidate_order]

            for j in candidate_order:
                if numeric_ratio(sample_df.iloc[:, j]) >= 0.7:
                    return cols[dt_idx], cols[j], "SGE"

    # 6) Fallback final
    if num_cols >= 2:
        if (
            datetime_ratio(sample_df.iloc[:, 0]) >= 0.7
            and numeric_ratio(sample_df.iloc[:, 1]) >= 0.7
        ):
            return cols[0], cols[1], "Generic"

    return None, None, "Unknown"
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