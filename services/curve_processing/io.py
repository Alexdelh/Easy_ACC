"""Flexible curve reading module for multiple formats.

Handles: EMS, SGE (consumption/production), Archelios formats.
Auto-detects delimiter, datetime format, value column.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
import io
from typing import Tuple, Dict, Any, Optional


def read_curve(file_or_df: Any) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Read and normalize curve from various formats.

    Args:
        file_or_df: file path (str), BytesIO, or DataFrame

    Returns:
        (df_normalized, metadata) where df_normalized has:
        - DatetimeIndex (UTC naive)
        - column 'value' (numeric, in kW or W depending on source)
        - clean column names

    Metadata contains: source_file, detected_format, frequency, unit
    """
    metadata: Dict[str, Any] = {
        "source_file": None,
        "detected_format": None,
        "frequency": None,
        "unit": None,
        "total_rows": None,
    }

    # Load raw data
    if isinstance(file_or_df, str):
        # File path
        if file_or_df.lower().endswith(".xlsx") or file_or_df.lower().endswith(".xls"):
            raw_df = pd.read_excel(file_or_df)
        else:
            # Try auto-detect delimiter
            raw_df = pd.read_csv(file_or_df, sep=None, engine="python", dtype=str)
        metadata["source_file"] = file_or_df
    elif isinstance(file_or_df, (io.BytesIO, io.StringIO)):
        # File-like object (Streamlit uploader)
        try:
            raw_df = pd.read_excel(file_or_df)
        except Exception:
            file_or_df.seek(0)
            raw_df = pd.read_csv(file_or_df, sep=None, engine="python", dtype=str)
        metadata["source_file"] = "uploaded_file"
    elif isinstance(file_or_df, pd.DataFrame):
        raw_df = file_or_df.copy()
        metadata["source_file"] = "dataframe"
    else:
        raise TypeError(f"Expected str, file-like, or DataFrame; got {type(file_or_df)}")

    # Clean column names
    raw_df.columns = [str(c).strip() for c in raw_df.columns]

    metadata["total_rows"] = len(raw_df)

    # Detect format and extract datetime + value columns
    dt_col, val_col, fmt = _detect_format(raw_df)

    if dt_col is None or val_col is None:
        raise ValueError(f"Could not detect datetime and value columns in {raw_df.columns.tolist()}")

    metadata["detected_format"] = fmt

    # Extract and normalize
    df = raw_df[[dt_col, val_col]].copy()
    df.columns = ["datetime", "value"]

    # Parse datetime
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce", utc=True)
    df = df[df["datetime"].notna()]

    # Convert to naive UTC
    if df["datetime"].dt.tz is not None:
        df["datetime"] = df["datetime"].dt.tz_localize(None)

    # Parse value as numeric (handle comma decimal)
    df["value"] = df["value"].astype(str).str.replace(",", ".").apply(pd.to_numeric, errors="coerce")
    df = df[df["value"].notna()]

    # Infer unit (heuristic) BEFORE normalization
    unit = _infer_unit(fmt, val_col)
    metadata["unit"] = unit

    # **NORMALIZE TO kW**
    if unit == "W":
        df["value"] = df["value"] / 1000.0  # W → kW
    elif unit == "Wh":
        df["value"] = df["value"] / 1000.0  # Wh → kWh

    # Update metadata to reflect normalized unit
    if unit == "W":
        metadata["unit"] = "kW"
    elif unit == "Wh":
        metadata["unit"] = "kWh"

    # Set index
    df = df.set_index("datetime").sort_index()

    # Infer frequency
    freq = _infer_frequency(df.index)
    metadata["frequency"] = freq

    return df[["value"]], metadata


def _detect_format(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], str]:
    """Detect format and return (datetime_col, value_col, format_name)."""
    cols = df.columns.tolist()
    cols_lower = [c.lower() for c in cols]

    # ALEX Format (simple: datetime + W columns with comma delimiter)
    if len(cols) == 2 and "datetime" in cols_lower and "w" in cols_lower:
        dt_idx = cols_lower.index("datetime")
        w_idx = cols_lower.index("w")
        return cols[dt_idx], cols[w_idx], "ALEX"

    # SGE Format (consumption or production)
    if "horodate" in cols_lower and "valeur" in cols_lower:
        return "Horodate", "Valeur", "SGE"

    # EMS Format (consumption)
    if "date" in cols_lower and "valeur" in cols_lower:
        return "date", "valeur", "EMS"

    # Archelios Format (no header, try first two columns)
    if len(cols) >= 2:
        # Check if first col looks like datetime and second like numeric
        try:
            pd.to_datetime(df.iloc[:5, 0], errors="coerce")
            # At least 3 of 5 are parseable
            if pd.to_datetime(df.iloc[:5, 0], errors="coerce").notna().sum() >= 3:
                return cols[0], cols[1], "Archelios"
        except Exception:
            pass

    # Fallback: find any datetime-like and numeric columns
    dt_col = None
    val_col = None

    for col in cols_lower:
        if any(x in col for x in ["date", "time", "horodate", "datetime"]):
            dt_col = cols[cols_lower.index(col)]
            break

    if dt_col is None and len(cols) >= 1:
        dt_col = cols[0]

    for col in cols_lower:
        if any(x in col for x in ["valeur", "value", "val", "power", "w", "kw"]):
            val_col = cols[cols_lower.index(col)]
            break

    if val_col is None and len(cols) >= 2:
        val_col = cols[1]

    return dt_col, val_col, "Unknown"


def _infer_frequency(index: pd.DatetimeIndex) -> str:
    """Infer timestep from DatetimeIndex."""
    if len(index) < 2:
        return "Unknown"

    deltas = index[1:] - index[:-1]
    most_common_delta = deltas.value_counts().idxmax()

    total_seconds = most_common_delta.total_seconds()

    if total_seconds <= 60:
        return "PT1M"
    elif total_seconds <= 300:
        return "PT5M"
    elif total_seconds <= 900:
        return "PT15M"
    elif total_seconds <= 1800:
        return "PT30M"
    elif total_seconds <= 3600:
        return "PT60M"
    else:
        return f"PT{int(total_seconds/60)}M"


def _infer_unit(fmt: str, val_col: str) -> str:
    """Infer unit (W, kW, Wh, kWh) from format and column name."""
    col_lower = val_col.lower()

    # ALEX format is always in W
    if fmt == "ALEX":
        return "W"

    # SGE is always in W
    if fmt == "SGE":
        return "W"

    # Check column name
    if "kw" in col_lower:
        return "kW"
    if "w" in col_lower:
        return "W"
    if "kwh" in col_lower:
        return "kWh"
    if "wh" in col_lower:
        return "Wh"

    # Default
    return "Unknown"
