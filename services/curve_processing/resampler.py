"""Resample time series curves to a target timestep."""

import pandas as pd
from typing import Literal, Tuple

from .utils import detect_timestep


def resample_curve(
    df: pd.DataFrame,
    target_timestep: Literal["PT15M", "PT30M", "PT60M"] = "PT60M",
    method: Literal["auto", "aggregate", "interpolate"] = "auto",
) -> Tuple[pd.DataFrame, str]:
    """Resample a curve to the target timestep.

    Args:
        df: DataFrame with DatetimeIndex and 'value' column (in kW).
        target_timestep: 'PT15M', 'PT30M', or 'PT60M'.
        method: 'auto' = aggregate if downsampling, interpolate if upsampling.

    Returns:
        (resampled_df, message) where message describes the operation performed.
    """
    freq_map = {
        "PT15M": "15min",
        "PT30M": "30min",
        "PT60M": "60min",
        "PT1H": "60min",
    }
    target_freq = freq_map.get(target_timestep, "60min")

    source_timestep = detect_timestep(df, df.index)

    if source_timestep == target_timestep:
        return df.copy(), f"No change (already {target_timestep})"

    if method == "auto":
        freq_minutes = {
            "PT15M": 15, "PT30M": 30, "PT60M": 60, "PT1H": 60,
            "h": 60, "15min": 15, "30min": 30, "60min": 60, "1h": 60,
        }
        source_min = freq_minutes.get(source_timestep, 60)
        target_min = freq_minutes.get(target_freq, 60)
        method = "aggregate" if target_min >= source_min else "interpolate"

    if method == "aggregate":
        resampled = df.resample(target_freq).agg({"value": "sum"})
    else:
        resampled = df.resample(target_freq)["value"].interpolate(method="linear").to_frame()

    resampled = resampled.fillna(0)
    return resampled, f"Resampled {source_timestep} → {target_timestep} ({method})"
