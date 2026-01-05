"""Resample and standardize production curves to target timesteps."""

import pandas as pd
import numpy as np
from typing import Literal, Tuple
from .utils import detect_timestep


def resample_curve(
    df: pd.DataFrame,
    target_timestep: Literal['PT15M', 'PT30M', 'PT60M'] = 'PT60M',
    method: Literal['auto', 'aggregate', 'interpolate'] = 'auto'
) -> Tuple[pd.DataFrame, str]:
    """
    Resample a production curve to target timestep.
    
    Args:
        df: DataFrame with DatetimeIndex and 'value' column
        target_timestep: 'PT15M' (15min), 'PT30M' (30min), or 'PT60M' (60min)
        method: 'auto' = aggregate if coarser, interpolate if finer
               'aggregate' = sum values (for energy) or mean (for power)
               'interpolate' = linear interpolation
    
    Returns:
        Tuple of (resampled_df, method_used)
    """
    
    # Map timestep to frequency string
    freq_map = {
        'PT15M': '15min',
        'PT30M': '30min',
        'PT60M': '60min',
        'PT1H': '60min',  # Alias
    }
    target_freq = freq_map.get(target_timestep, '60min')
    
    # Detect source timestep
    source_timestep = detect_timestep(df, df.index)
    
    # If already at target, return as-is
    if source_timestep == target_timestep:
        return df.copy(), f"No change (already {target_timestep})"
    
    # Determine method if 'auto'
    if method == 'auto':
        # Convert to minutes for comparison
        freq_minutes = {
            'PT15M': 15,
            'PT30M': 30,
            'PT60M': 60,
            'PT1H': 60,
            'h': 60,
            '15min': 15,
            '30min': 30,
            '60min': 60,
            '1h': 60,
        }
        
        source_min = freq_minutes.get(source_timestep, 60)
        target_min = freq_minutes.get(target_freq, 60)
        
        method = 'aggregate' if target_min >= source_min else 'interpolate'
    
    # Apply resampling
    if method == 'aggregate':
        # Use sum for energy (Wh, kWh), mean for power (W, kW)
        # Assume column is 'value'
        resampled = df.resample(target_freq).agg({
            'value': 'sum'  # Default to sum (energy context)
        })
        # If original was at coarser timestep, convert sum to mean power
        # This is a simplification; ideally we'd know the unit context
        if 'PT15M' in source_timestep or '15min' in str(source_timestep):
            # 15min → 60min: sum 4 values to get total energy
            pass  # Keep as sum
    else:  # interpolate
        # Linear interpolation for finer timestep
        resampled = df.resample(target_freq)['value'].interpolate(method='linear')
        resampled = resampled.to_frame()
    
    # Handle NaN values from resampling (e.g., at edges)
    resampled = resampled.fillna(0)
    
    return resampled, f"Resampled {source_timestep} → {target_timestep} ({method})"


def aggregate_curve(df: pd.DataFrame, freq: str = '60min') -> pd.DataFrame:
    """
    Aggregate curve to coarser frequency (sum values).
    
    Useful for converting high-frequency data to hourly or 30-min.
    """
    return df.resample(freq).agg({'value': 'sum'})


def interpolate_curve(df: pd.DataFrame, freq: str = '15min') -> pd.DataFrame:
    """
    Interpolate curve to finer frequency (linear).
    
    Useful for converting hourly data to 15-min or 30-min.
    """
    resampled = df.resample(freq)['value'].interpolate(method='linear')
    return resampled.to_frame().fillna(0)
