"""Utility functions for curve standardization."""

import pandas as pd
import re
from typing import Tuple, Optional


def clean_numeric_string(value):
    """
    Clean a numeric string value to handle various formats.
    
    Handles:
    - European format (comma as decimal separator): "0,147" -> "0.147"
    - Quoted values: '"0,147"' -> "0.147"
    - Spaces: "1 234,56" -> "1234.56"
    
    Returns cleaned string or original value if not a string.
    """
    if not isinstance(value, str):
        return value
    
    # Remove quotes and spaces
    cleaned = value.strip().strip('"').strip("'").replace(' ', '')
    
    # Replace comma with dot (European decimal format)
    cleaned = cleaned.replace(',', '.')
    
    return cleaned


def detect_datetime_column(df: pd.DataFrame) -> Optional[str]:
    """
    Detect which column contains datetime information.
    
    Looks for common patterns: date, time, horodate, datetime, timestamp, etc.
    Returns column name or None if not found.
    Special case: Returns '__index__' if DataFrame already has a DatetimeIndex.
    """
    # Check if DataFrame already has a DatetimeIndex (e.g., from PVGIS)
    if isinstance(df.index, pd.DatetimeIndex):
        return '__index__'
    
    datetime_keywords = ['date', 'time', 'horodate', 'datetime', 'timestamp', 'heure', 'jour']
    
    for col in df.columns:
        col_lower = str(col).lower()
        if any(kw in col_lower for kw in datetime_keywords):
            return col
    
    # If no keyword match, check if first column can be parsed as datetime
    if len(df.columns) > 0:
        first_col = df.columns[0]
        try:
            # Try parsing a sample
            sample = df[first_col].dropna().head(5)
            if len(sample) > 0:
                pd.to_datetime(sample, errors='raise')
                return first_col
        except:
            pass
    
    return None


def detect_value_column(df: pd.DataFrame, exclude_cols: list = None) -> Optional[str]:
    """
    Detect which column contains the numeric values (production).
    
    Prioritizes columns with production-related keywords, then falls back to numeric columns.
    Returns first valid numeric column that's not in exclude_cols.
    """
    if exclude_cols is None:
        exclude_cols = []
    
    # First pass: look for production-related keywords
    production_keywords = ['p_ac', 'pac', 'production', 'puissance', 'power', 'pdc', 'p_dc', 'kw', 'kva', 'output', 'ac_power']
    
    for col in df.columns:
        if col in exclude_cols:
            continue
        col_lower = str(col).lower()
        # Check if column name contains production keywords
        if any(kw in col_lower for kw in production_keywords):
            try:
                # First try directly if already numeric
                if pd.api.types.is_numeric_dtype(df[col]):
                    non_null = df[col].notna().sum()
                    if non_null > 0:
                        return col
                
                # Otherwise, try cleaning and converting
                cleaned_series = df[col].apply(clean_numeric_string)
                numeric_series = pd.to_numeric(cleaned_series, errors='coerce')
                non_null_count = df[col].notna().sum()
                valid_numeric_count = numeric_series.notna().sum()
                if non_null_count > 0 and (valid_numeric_count / non_null_count) >= 0.5:
                    return col
            except (ValueError, TypeError):
                continue
    
    # Second pass: look for any numeric column
    for col in df.columns:
        if col in exclude_cols:
            continue
        try:
            # First try directly if already numeric
            if pd.api.types.is_numeric_dtype(df[col]):
                non_null = df[col].notna().sum()
                if non_null > 0:
                    return col
            
            # Otherwise, try cleaning and converting
            cleaned_series = df[col].apply(clean_numeric_string)
            numeric_series = pd.to_numeric(cleaned_series, errors='coerce')
            non_null_count = df[col].notna().sum()
            valid_numeric_count = numeric_series.notna().sum()
            if non_null_count > 0 and (valid_numeric_count / non_null_count) >= 0.5:
                return col
        except (ValueError, TypeError):
            continue
    
    return None


def try_parse_datetime(series: pd.Series) -> Optional[pd.DatetimeIndex]:
    """
    Attempt to parse a series as datetime.
    
    Returns DatetimeIndex if successful, None otherwise.
    """
    try:
        dt = pd.to_datetime(series, errors='coerce')
        if dt.isna().sum() > len(dt) * 0.5:  # More than 50% NaT → likely not datetime
            return None
        return dt
    except Exception:
        return None


def detect_timestep(df: pd.DataFrame, datetime_index: pd.DatetimeIndex) -> Optional[str]:
    """
    Detect the frequency/timestep of the time series.
    
    Returns inferred frequency string (e.g., 'h', '30min', '15min') or None.
    """
    try:
        freq = pd.infer_freq(datetime_index)
        return freq
    except Exception:
        return None


def normalize_unit(value: float, from_unit: str, to_unit: str = 'kW') -> float:
    """
    Normalize power units.
    
    Supports: W, kW, MW, GW, Wh, kWh, MWh, GWh
    """
    conversion_factors = {
        'W': 0.001,      # W to kW
        'kW': 1.0,       # kW to kW
        'MW': 1000.0,    # MW to kW
        'GW': 1e6,       # GW to kW
        'Wh': 0.001,     # Wh to kWh
        'kWh': 1.0,      # kWh to kWh
        'MWh': 1000.0,   # MWh to kWh
        'GWh': 1e6,      # GWh to kWh
    }
    
    if from_unit not in conversion_factors:
        raise ValueError(f"Unknown unit: {from_unit}")
    
    factor = conversion_factors[from_unit]
    return value * factor


def check_continuity(datetime_index: pd.DatetimeIndex, max_gap_hours: int = 2) -> Tuple[bool, list]:
    """
    Check for temporal continuity and detect gaps > max_gap_hours.
    
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
            gaps.append((datetime_index[i-1], datetime_index[i], gap_hours))
    
    is_continuous = len(gaps) == 0
    return is_continuous, gaps
