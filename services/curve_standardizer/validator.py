"""Validate production curves for temporal continuity and anomalies."""

import pandas as pd
from typing import Dict, List, Tuple
from .utils import check_continuity


def validate_curve(df: pd.DataFrame) -> Dict[str, any]:
    """
    Validate a parsed production curve for issues.
    
    Checks:
    - Temporal continuity (gaps > 2 hours)
    - Duplicates
    - NaN values
    - Monotonic increasing timestamps
    - Future dates
    
    Returns:
        validation_report dict with 'is_valid', 'errors', 'warnings'
    """
    
    report = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
    }
    
    if df is None or len(df) == 0:
        report['is_valid'] = False
        report['errors'].append("DataFrame is empty")
        return report
    
    # Check for duplicates in index
    if df.index.duplicated().any():
        dup_count = df.index.duplicated().sum()
        report['warnings'].append(f"Found {dup_count} duplicate timestamps (will be kept)")
    
    # Check for NaN values
    nan_count = df.isna().sum().sum()
    if nan_count > 0:
        report['warnings'].append(f"Found {nan_count} NaN values in data")
    
    # Check for monotonic increasing timestamps
    if not df.index.is_monotonic_increasing:
        report['is_valid'] = False
        report['errors'].append("Timestamps are not monotonically increasing (out of order)")
    
    # Check for future dates
    now = pd.Timestamp.now()
    if df.index.tz is not None:
        if now.tz is None:
            now = now.tz_localize(df.index.tz)
        else:
            now = now.tz_convert(df.index.tz)
            
    if (df.index > now).any():
        future_count = (df.index > now).sum()
        report['warnings'].append(f"Found {future_count} future timestamps")
    
    # Check temporal continuity
    is_continuous, gaps = check_continuity(df.index, max_gap_hours=2)
    if not is_continuous:
        report['warnings'].append(f"Found {len(gaps)} temporal gaps > 2 hours:")
        for gap_start, gap_end, gap_hours in gaps:
            report['warnings'].append(f"  {gap_start} → {gap_end} ({gap_hours:.1f}h)")
    
    # Check for negative values (unusual for production)
    negative_count = (df['value'] < 0).sum()
    if negative_count > 0:
        report['warnings'].append(f"Found {negative_count} negative values (unusual for production)")
    
    return report
