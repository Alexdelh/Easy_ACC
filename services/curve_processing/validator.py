"""Validate time series curves for temporal continuity and anomalies."""

import pandas as pd
from typing import Dict

from .utils import check_continuity


def validate_curve(df: pd.DataFrame) -> Dict:
    """Validate a curve DataFrame for common issues.

    Checks: duplicates, NaN values, monotonic index, future dates, temporal gaps > 2h,
    negative values.

    Returns:
        dict with 'is_valid', 'errors', 'warnings'.
    """
    report = {"is_valid": True, "errors": [], "warnings": []}

    if df is None or len(df) == 0:
        report["is_valid"] = False
        report["errors"].append("DataFrame is empty")
        return report

    if df.index.duplicated().any():
        dup_count = int(df.index.duplicated().sum())
        report["warnings"].append(f"Found {dup_count} duplicate timestamps")

    nan_count = int(df.isna().sum().sum())
    if nan_count > 0:
        report["warnings"].append(f"Found {nan_count} NaN values")

    if not df.index.is_monotonic_increasing:
        report["is_valid"] = False
        report["errors"].append("Timestamps are not monotonically increasing")

    now = pd.Timestamp.now()
    if df.index.tz is not None:
        now = now.tz_localize(df.index.tz) if now.tz is None else now.tz_convert(df.index.tz)
    if (df.index > now).any():
        report["warnings"].append(f"Found {int((df.index > now).sum())} future timestamps")

    is_continuous, gaps = check_continuity(df.index, max_gap_hours=2)
    if not is_continuous:
        report["warnings"].append(f"Found {len(gaps)} temporal gaps > 2h")
        for gap_start, gap_end, gap_hours in gaps:
            report["warnings"].append(f"  {gap_start} → {gap_end} ({gap_hours:.1f}h)")

    if "value" in df.columns:
        negative_count = int((df["value"] < 0).sum())
        if negative_count > 0:
            report["warnings"].append(f"Found {negative_count} negative values")

    return report
