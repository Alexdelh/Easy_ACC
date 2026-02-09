"""Imputation utilities for time series curves.

Imputation strategy: for each missing timestamp try weekly shifts in order:
 t-1w, t+1w, t-2w, t+2w, ..., up to max_weeks (default 4).

This module exposes `impute_by_week_shift(df, value_col='value', max_weeks=4)`
which returns (df_imputed, impute_report).
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Tuple, Dict


def impute_by_week_shift(df: pd.DataFrame, value_col: str = "value", max_weeks: int = 4) -> Tuple[pd.DataFrame, Dict]:
    """Impute missing values by searching weekly shifted timestamps.

    Args:
        df: DataFrame indexed by DatetimeIndex (regular or not). Must contain `value_col`.
        value_col: column name holding numeric values.
        max_weeks: maximum number of weeks to try in each direction.

    Returns:
        df_out: DataFrame with imputations applied and two additional columns:
            - `_imputed`: boolean flag True when value was imputed
            - `_impute_source`: integer week offset used (e.g. -1 for t-1w, +2 for t+2w), 0 when original
        report: dict with summary statistics
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if value_col not in df.columns:
        raise KeyError(f"Column '{value_col}' not found in DataFrame")

    # Work on a copy
    df = df.copy()

    # Ensure DatetimeIndex and sorted
    if not isinstance(df.index, pd.DatetimeIndex):
        if "datetime" in df.columns:
            df = df.set_index(pd.to_datetime(df["datetime"]))
        else:
            raise ValueError("DataFrame must have a DatetimeIndex or a 'datetime' column")

    df = df.sort_index()

    # Ensure hourly frequency if possible (not forcing reindex here)
    # Mark original mask
    orig_mask = df[value_col].notna()

    # Prepare imputed columns
    df["_imputed"] = False
    df["_impute_source"] = 0

    total_missing_before = int(df[value_col].isna().sum())

    # If no missing, return early
    if total_missing_before == 0:
        report = {
            "total_points": len(df),
            "missing_before": 0,
            "missing_after": 0,
            "imputed_count": 0,
            "imputed_pct": 0.0,
        }
        return df, report

    # For efficiency create a Series view
    s = df[value_col]

    # We'll attempt weekly shifts up to max_weeks
    # For each week offset in order [-1, +1, -2, +2, ...]
    offsets = []
    for w in range(1, max_weeks + 1):
        offsets.append(-w)
        offsets.append(+w)

    # convert offsets (weeks) to pandas DateOffset (7 days)
    # We'll perform loop filling missing values progressively
    missing_idx = s[s.isna()].index

    for off in offsets:
        if missing_idx.empty:
            break
        # create shifted series
        shift_hours = off * 24 * 7
        shifted = s.shift(shift_hours, freq="H") if isinstance(shift_hours, int) else s.shift(pd.DateOffset(weeks=off))

        # For positions still missing, try to fill from shifted
        for ts in list(missing_idx):
            try:
                val = shifted.get(ts, np.nan)
            except Exception:
                # fallback: compute target ts and lookup
                target_ts = ts + pd.DateOffset(weeks=off)
                val = s.get(target_ts, np.nan)

            if pd.notna(val):
                df.at[ts, value_col] = val
                df.at[ts, "_imputed"] = True
                df.at[ts, "_impute_source"] = off

        # Update missing_idx
        missing_idx = df[df[value_col].isna()].index

    total_missing_after = int(df[value_col].isna().sum())
    imputed_count = int(((~orig_mask) & df["_imputed"]).sum())

    # REJET : Si des NaN restent après imputation (impossible à remplir dans ±4 semaines)
    rejected = total_missing_after > 0

    report = {
        "total_points": len(df),
        "missing_before": total_missing_before,
        "missing_after": total_missing_after,
        "imputed_count": imputed_count,
        "imputed_pct": round(100.0 * imputed_count / (len(df) if len(df) else 1), 2),
        "rejected": rejected,  # ← REJET si NaN irrécupérables
    }

    return df, report
