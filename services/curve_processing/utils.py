"""Utility functions for curve processing."""

import pandas as pd
from typing import Optional, Tuple


def detect_timestep(df: pd.DataFrame, datetime_index: pd.DatetimeIndex) -> Optional[str]:
    """Detect the frequency/timestep of the time series.

    Returns inferred frequency string (e.g., 'h', '30min', '15min') or None.
    """
    try:
        return pd.infer_freq(datetime_index)
    except Exception:
        return None


def check_continuity(datetime_index: pd.DatetimeIndex, max_gap_hours: int = 2) -> Tuple[bool, list]:
    """Check for temporal continuity and detect gaps > max_gap_hours.

    Returns (is_continuous, gaps_list)
    where gaps_list is a list of (gap_start, gap_end, gap_duration_hours) tuples.
    """
    if len(datetime_index) < 2:
        return True, []

    diffs = datetime_index.to_series().diff()
    max_diff = pd.Timedelta(hours=max_gap_hours)

    gaps = []
    for i, (idx, diff) in enumerate(diffs[1:].items(), start=1):
        if diff > max_diff:
            gap_hours = diff.total_seconds() / 3600
            gaps.append((datetime_index[i - 1], datetime_index[i], gap_hours))

    return len(gaps) == 0, gaps
