"""Data aggregation module for building consolidated consumption and production DataFrames.

Aggregates multiple PDL (Points De Livraison) time series into two main DataFrames:
- consumers_df : columns=PDL names, rows=hourly datetimes, values=consumption (W or kW)
- producers_df : columns=PDL names, rows=hourly datetimes, values=production (W or kW)

Structure:
                PDL_001   PDL_002   PDL_003  ...
2024-01-01 00:00:00  100      150      200
2024-01-01 01:00:00  120      160      210
...
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional, Any


def build_dataframes(
    points_consumers: List[Dict[str, Any]],
    points_producers: List[Dict[str, Any]],
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Dict[str, Any]]:
    """Build consolidated consumption and production DataFrames from points.

    EXPECTED INPUT STRUCTURE (points_consumers/points_producers):
    Each point dict should contain:
    - 'nom' or 'pdl': PDL identifier (string) [REQUIRED for naming]
    - 'courbe_consommation' (consumers) or 'courbe_production' (producers): curve data
      * Can be None (skipped with warning)
      * Can be DataFrame with DatetimeIndex and 'value' column (in kW after read_curve())
      * OR Dict with 'df', 'metadata', 'impute_report' keys (from process_curve())
    - All other fields: ignored but preserved

    REJECTION LOGIC:
    - If impute_report['rejected']==True: skip PDL (not included in consolidated output)
    - If no curve data at all: skip PDL with error message

    Args:
        points_consumers: List of consumer points
        points_producers: List of producer points
        start_date: Start date for alignment (optional)
        end_date: End date for alignment (optional)

    Returns:
        (consumers_df, producers_df, summary_dict) where:
        - consumers_df: DataFrame with PDL names as columns, hourly index, values in kW
        - producers_df: DataFrame with PDL names as columns, hourly index, values in kW
        - summary_dict: {
            'consumers_count': int (total provided, including rejected),
            'producers_count': int (total provided, including rejected),
            'consumers_with_data': int (successfully included, not rejected),
            'producers_with_data': int (successfully included, not rejected),
            'time_range': (min_dt, max_dt) or None,
            'alignment_status': 'OK' or 'Partial' or 'ERROR',
            'errors': list of rejection/error messages
          }
    """
    summary = {
        "consumers_count": len(points_consumers),
        "producers_count": len(points_producers),
        "consumers_with_data": 0,
        "producers_with_data": 0,
        "time_range": None,
        "alignment_status": "OK",
        "errors": [],
    }

    # Collect time series from consumers
    consumers_ts = {}
    for point in points_consumers:
        pdl_name = point.get("nom") or point.get("pdl") or f"Consumer_{len(consumers_ts)}"
        curve = point.get("courbe_consommation") or point.get("curve_data")

        if curve is None:
            summary["errors"].append(f"Consumer '{pdl_name}': no curve data")
            continue

        # Handle dict result from process_curve() with imputation report
        if isinstance(curve, dict) and "df" in curve:
            impute_report = curve.get("impute_report", {})
            if impute_report.get("rejected", False):
                summary["errors"].append(
                    f"Consumer '{pdl_name}': REJECTED (no imputable values after ±4 weeks)"
                )
                continue
            curve = curve["df"]

        # Now curve should be a DataFrame
        if isinstance(curve, pd.DataFrame) and len(curve) > 0:
            normalized_curve = _normalize_curve(curve, pdl_name)
            if normalized_curve is not None:
                consumers_ts[pdl_name] = normalized_curve
                summary["consumers_with_data"] += 1
            else:
                summary["errors"].append(f"Consumer '{pdl_name}': could not normalize curve")
        else:
            summary["errors"].append(f"Consumer '{pdl_name}': no valid curve data")

    # Collect time series from producers
    producers_ts = {}
    for point in points_producers:
        pdl_name = point.get("nom") or point.get("pdl") or f"Producer_{len(producers_ts)}"
        curve = point.get("courbe_production") or point.get("curve_data")

        if curve is None:
            summary["errors"].append(f"Producer '{pdl_name}': no curve data")
            continue

        # Handle dict result from process_curve() with imputation report
        if isinstance(curve, dict) and "df" in curve:
            impute_report = curve.get("impute_report", {})
            if impute_report.get("rejected", False):
                summary["errors"].append(
                    f"Producer '{pdl_name}': REJECTED (no imputable values after ±4 weeks)"
                )
                continue
            curve = curve["df"]

        # Now curve should be a DataFrame
        if isinstance(curve, pd.DataFrame) and len(curve) > 0:
            normalized_curve = _normalize_curve(curve, pdl_name)
            if normalized_curve is not None:
                producers_ts[pdl_name] = normalized_curve
                summary["producers_with_data"] += 1
            else:
                summary["errors"].append(f"Producer '{pdl_name}': could not normalize curve")
        else:
            summary["errors"].append(f"Producer '{pdl_name}': no valid curve data")

    # Build consolidated DataFrames
    consumers_df = None
    producers_df = None

    if consumers_ts:
        consumers_df = _build_consolidated_dataframe(consumers_ts, start_date, end_date, "consumers")
    else:
        summary["errors"].append("No consumer data to aggregate")

    if producers_ts:
        producers_df = _build_consolidated_dataframe(producers_ts, start_date, end_date, "producers")
    else:
        summary["errors"].append("No producer data to aggregate")

    # Align time ranges if both exist
    if consumers_df is not None and producers_df is not None:
        min_time = max(consumers_df.index.min(), producers_df.index.min())
        max_time = min(consumers_df.index.max(), producers_df.index.max())

        if min_time > max_time:
            summary["alignment_status"] = "ERROR: no temporal overlap"
            summary["errors"].append("Consumer and producer time ranges do not overlap")
        else:
            consumers_df = consumers_df.loc[min_time : max_time]
            producers_df = producers_df.loc[min_time : max_time]
            summary["time_range"] = (min_time, max_time)
            summary["alignment_status"] = "Aligned"
    elif consumers_df is not None:
        summary["time_range"] = (consumers_df.index.min(), consumers_df.index.max())
    elif producers_df is not None:
        summary["time_range"] = (producers_df.index.min(), producers_df.index.max())

    return consumers_df, producers_df, summary


def _normalize_curve(df: pd.DataFrame, name: str = "curve") -> Optional[pd.Series]:
    """Normalize a curve DataFrame to a Series with DatetimeIndex and numeric values.

    Args:
        df: DataFrame (may or may not have DatetimeIndex)
        name: name for logging

    Returns:
        Series with DatetimeIndex and numeric values, or None if could not normalize
    """
    try:
        df = df.copy()

        # Ensure DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            if "datetime" in df.columns:
                df.index = pd.to_datetime(df["datetime"], errors="coerce")
                df = df.drop(columns=["datetime"])
            elif len(df.columns) > 0 and df.columns[0].lower() in ["date", "horodate", "time", "timestamp"]:
                df.index = pd.to_datetime(df.iloc[:, 0], errors="coerce")
                df = df.drop(columns=[df.columns[0]])
            else:
                # Try to parse first column as datetime
                try:
                    df.index = pd.to_datetime(df.iloc[:, 0], errors="coerce")
                    df = df.drop(columns=[df.columns[0]])
                except Exception:
                    return None

        # Remove rows with NaT index
        df = df[df.index.notna()]

        # Extract numeric column (prefer 'value', fallback to first numeric column)
        if "value" in df.columns:
            series = df["value"]
        elif "P_ac_kW" in df.columns:
            series = df["P_ac_kW"]
        elif "_imputed" in df.columns:
            # Filter out _imputed and _impute_source columns
            numeric_cols = df.select_dtypes(include=["number"]).columns
            numeric_cols = [c for c in numeric_cols if c not in ["_imputed", "_impute_source"]]
            if len(numeric_cols) > 0:
                series = df[numeric_cols[0]]
            else:
                return None
        else:
            numeric_cols = df.select_dtypes(include=["number"]).columns
            if len(numeric_cols) > 0:
                series = df[numeric_cols[0]]
            else:
                return None

        # Convert to numeric, drop NaN
        series = pd.to_numeric(series, errors="coerce")
        series = series[series.notna()]

        if len(series) == 0:
            return None

        series.index = pd.to_datetime(series.index, errors="coerce")
        return series

    except Exception as e:
        return None


def _build_consolidated_dataframe(
    ts_dict: Dict[str, pd.Series],
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
    data_type: str = "data",
) -> Optional[pd.DataFrame]:
    """Build a consolidated DataFrame from a dict of time series.

    Merges all time series into a single DataFrame with PDL names as columns,
    ensuring consistent hourly frequency.

    WHY RESAMPLE (conditional):
    - Resample: Aligns all time series to exact hourly grid if not already hourly
      (defensive: handles edge case where uploaded files have non-standard frequency)
    - Only resamples if frequency != 1H (no unnecessary processing)
    - Uses mean() for aggregation in case timestamps are slightly offset

    NaN HANDLING:
    - NO forward/backward fill applied here
    - Relies on week-shift imputation at curve processing stage
    - Remaining NaN values preserved for analysis (indicate true data gaps)

    Args:
        ts_dict: {PDL_name: Series with DatetimeIndex and numeric values}
        start_date: optional start date for filtering
        end_date: optional end date for filtering
        data_type: "consumers" or "producers" (for logging)

    Returns:
        Consolidated DataFrame (PDL columns × hourly rows) or None if no data
    """
    if not ts_dict:
        return None

    # Combine all series
    df = pd.DataFrame(ts_dict)

    # Resample to hourly frequency ONLY if needed
    if df.index.freq != pd.offsets.Hour():
        df = df.resample("1H").mean()
    # Otherwise already hourly, no need to resample

    # Filter by date range if provided
    if start_date is not None:
        start_date = pd.to_datetime(start_date)
        df = df[df.index >= start_date]

    if end_date is not None:
        end_date = pd.to_datetime(end_date)
        df = df[df.index <= end_date]

    return df if len(df) > 0 else None
