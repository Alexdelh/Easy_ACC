"""Format production curves for export in 3 standard formats."""

import pandas as pd
from datetime import datetime
from typing import Dict


def to_sge_tiers_format(
    df: pd.DataFrame,
    metadata: Dict = None,
    prm_id: str = "ACCKB_XXXX"
) -> pd.DataFrame:
    """
    Convert to SGE Tiers format (9-column standard).
    
    SGE Tiers format:
    - Identifiant PRM (Meter ID)
    - Date début (Start date)
    - Date fin (End date)
    - Grandeur physique (Physical quantity: energy, power, etc.)
    - Grandeur métier (Business quantity)
    - Étape métier (Business step)
    - Unité (Unit: kW, kWh, etc.)
    - Horodate (Timestamp YYYY-MM-DD HH:MM:SS)
    - Valeur (Value)
    - Pas (Timestep: PT15M, PT30M, PT60M)
    
    Args:
        df: DataFrame with DatetimeIndex and 'value' column
        metadata: Dict with source info (unit, etc.)
        prm_id: Meter identifier (e.g., "ACCKB_0001")
    
    Returns:
        DataFrame in SGE Tiers format
    """
    
    if df is None or len(df) == 0:
        return pd.DataFrame()
    
    metadata = metadata or {}
    
    # Detect timestep from index
    if len(df) > 1:
        freq = pd.infer_freq(df.index)
        timestep_map = {
            '15min': 'PT15M',
            '30min': 'PT30M',
            '60min': 'PT60M',
            'h': 'PT60M',
        }
        timestep = timestep_map.get(str(freq), 'PT60M')
    else:
        timestep = 'PT60M'
    
    unit = metadata.get('unit', 'kW')
    
    # Create SGE Tiers DataFrame
    sge_df = pd.DataFrame({
        'Identifiant PRM': prm_id,
        'Date début': df.index[0].strftime('%Y-%m-%d'),
        'Date fin': df.index[-1].strftime('%Y-%m-%d'),
        'Grandeur physique': 'Énergie' if unit in ['kWh', 'Wh'] else 'Puissance',
        'Grandeur métier': 'Production',
        'Étape métier': 'Mesuré',
        'Unité': unit,
        'Horodate': df.index.strftime('%Y-%m-%d %H:%M:%S'),
        'Valeur': df['value'].values,
        'Pas': timestep,
    })
    
    return sge_df


def to_archelios_format(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert to Archelios format (datetime + value).
    
    Archelios format:
    - DateTime (format: M/D/YY H:MM)
    - Valeur (Value in kW)
    
    Args:
        df: DataFrame with DatetimeIndex and 'value' column
    
    Returns:
        DataFrame in Archelios format
    """
    
    if df is None or len(df) == 0:
        return pd.DataFrame()
    
    # Archelios format: M/D/YY H:MM
    archelios_df = pd.DataFrame({
        'DateTime': df.index.strftime('%-m/%-d/%y %H:%M'),  # Linux/Mac format
        'Valeur': df['value'].values,
    })
    
    return archelios_df


def to_simple_datetime_format(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert to simple datetime + value format (compatible with various tools).
    
    Simple format:
    - DateTime (format: M/D/YY H:MM) - US format without leading zeros
    - Valeur (Value in kW)
    
    This format is similar to some producer data files but more generic.
    
    Args:
        df: DataFrame with DatetimeIndex and 'value' column
    
    Returns:
        DataFrame in simple datetime format
    """
    
    if df is None or len(df) == 0:
        return pd.DataFrame()
    
    # Format datetime without leading zeros: 1/1/24 0:00 instead of 01/01/24 00:00
    # Use strftime with conditional formatting for Windows compatibility
    datetime_strings = []
    for timestamp in df.index:
        # Manual formatting to avoid platform-specific issues with %-m
        dt_str = f"{timestamp.month}/{timestamp.day}/{timestamp.strftime('%y %H:%M')}"
        datetime_strings.append(dt_str)
    
    simple_df = pd.DataFrame({
        'DateTime': datetime_strings,
        'Valeur': df['value'].values,
    })
    
    return simple_df


def to_pvgis_format(df: pd.DataFrame) -> str:
    """
    Convert to PVGIS compact format.
    
    PVGIS format: YYYYMMDD:HHMM;value
    One timestamp:value per line
    
    Example:
    20240101:0000;0.0
    20240101:0015;0.5
    20240101:0030;1.2
    
    Args:
        df: DataFrame with DatetimeIndex and 'value' column
    
    Returns:
        String with PVGIS format data
    """
    
    if df is None or len(df) == 0:
        return ""
    
    lines = []
    for timestamp, row in df.iterrows():
        # Format: YYYYMMDD:HHMM;value
        time_str = timestamp.strftime('%Y%m%d:%H%M')
        value = row['value']
        line = f"{time_str};{value:.2f}"
        lines.append(line)
    
    return '\n'.join(lines)


def to_pvgis_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert to PVGIS format as DataFrame.
    
    Returns:
        DataFrame with ['time', 'value'] columns in PVGIS format
    """
    
    if df is None or len(df) == 0:
        return pd.DataFrame()
    
    pvgis_df = pd.DataFrame({
        'time': df.index.strftime('%Y%m%d:%H%M'),
        'value': df['value'].values,
    })
    
    return pvgis_df
