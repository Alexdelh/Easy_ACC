"""Parse production curves from various file formats."""

import pandas as pd
import io
from typing import Tuple, Dict, Any, Optional
from .utils import (
    detect_datetime_column, detect_value_column, try_parse_datetime,
    detect_timestep, clean_numeric_string
)


def parse_curve(file_or_df) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Parse a production curve from file or DataFrame.
    
    Automatically detects:
    - Datetime column
    - Value column
    - Timestep/frequency
    - Unit (if present in header)
    
    Args:
        file_or_df: File path (str), file-like object, or pandas DataFrame
    
    Returns:
        (df, metadata) where:
        - df: DataFrame with DatetimeIndex and single 'value' column (in kW)
        - metadata: dict with 'unit', 'timestep', 'source_file', 'rows_count', etc.
    """
    
    # Load file if needed
    if isinstance(file_or_df, str):
        # File path
        if file_or_df.endswith('.csv') or file_or_df.endswith('.txt'):
            # Try reading with header first
            raw_df = pd.read_csv(file_or_df, sep=None, engine='python', encoding='utf-8-sig')
            
            # Clean column names (remove BOM and whitespace)
            raw_df.columns = [str(col).strip().lstrip('\ufeff') for col in raw_df.columns]
            
            # Check if it looks like no header (first row looks like data)
            if len(raw_df.columns) <= 2:
                first_col = raw_df.columns[0]
                # Try parsing first column as datetime
                try:
                    pd.to_datetime(first_col, errors='raise')
                    # Looks like data in header, re-read without header
                    raw_df = pd.read_csv(file_or_df, sep=None, engine='python', header=None, encoding='utf-8-sig')
                    raw_df.columns = ['datetime', 'value'] if len(raw_df.columns) >= 2 else raw_df.columns
                except:
                    pass
        elif file_or_df.endswith('.xlsx') or file_or_df.endswith('.xls'):
            raw_df = pd.read_excel(file_or_df)
        else:
            raise ValueError(f"Unsupported file format: {file_or_df}")
        source_file = file_or_df
    elif isinstance(file_or_df, (io.BytesIO, io.StringIO)):
        # File-like object (from Streamlit uploader)
        try:
            raw_df = pd.read_excel(file_or_df)
        except Exception:
            file_or_df.seek(0)
            raw_df = pd.read_csv(file_or_df, sep=None, engine='python', encoding='utf-8-sig')
            # Clean column names
            raw_df.columns = [str(col).strip().lstrip('\ufeff') for col in raw_df.columns]
        source_file = 'uploaded_file'
    elif isinstance(file_or_df, pd.DataFrame):
        raw_df = file_or_df.copy()
        source_file = 'dataframe'
    else:
        raise TypeError(f"Expected str, file-like or DataFrame, got {type(file_or_df)}")
    
    metadata = {
        'source_file': source_file,
        'source_rows': len(raw_df),
        'source_columns': list(raw_df.columns),
    }
    
    # Detect datetime column
    datetime_col = detect_datetime_column(raw_df)
    if datetime_col is None:
        raise ValueError(f"Could not detect datetime column. Available columns: {list(raw_df.columns)}")
    
    # Parse datetime
    if datetime_col == '__index__':
        # DataFrame already has DatetimeIndex (e.g., from PVGIS)
        dt_series = pd.Series(raw_df.index, index=raw_df.index)
        datetime_col = 'index'  # Update for metadata
    else:
        dt_series = try_parse_datetime(raw_df[datetime_col])
        if dt_series is None:
            raise ValueError(f"Could not parse column '{datetime_col}' as datetime")
    
    # Detect value column
    exclude_cols = [datetime_col] if datetime_col != 'index' else []
    value_col = detect_value_column(raw_df, exclude_cols=exclude_cols)
    if value_col is None:
        raise ValueError(f"Could not detect numeric value column. Available columns: {list(raw_df.columns)}")
    
    # Clean and convert values to numeric
    cleaned_values = raw_df[value_col].apply(clean_numeric_string)
    values = pd.to_numeric(cleaned_values, errors='coerce')
    
    # Filter out rows where datetime or value is invalid (before creating DataFrame)
    valid_mask = dt_series.notna() & values.notna()
    dt_series_clean = dt_series[valid_mask]
    values_clean = values[valid_mask]
    
    # Build standardized DataFrame
    df = pd.DataFrame({
        'value': values_clean.values
    }, index=dt_series_clean)
    df.index.name = 'datetime'
    
    # Detect timestep
    timestep = detect_timestep(df, df.index)
    metadata['detected_timestep'] = timestep
    metadata['parsed_rows'] = len(df)
    metadata['datetime_column'] = datetime_col
    metadata['value_column'] = value_col
    
    # Try to detect unit from column name or header
    unit = 'kW'  # Default
    if any(kw in str(value_col).lower() for kw in ['mw', 'megawatt']):
        unit = 'MW'
    elif any(kw in str(value_col).lower() for kw in ['kw', 'kilowatt']):
        unit = 'kW'
    elif any(kw in str(value_col).lower() for kw in ['w', 'watt']):
        unit = 'W'
    
    metadata['unit'] = unit
    
    return df, metadata

def _detect_source_format(datetime_col: str, value_col: str) -> str:
    """Detect source format based on column names."""
    
    datetime_lower = str(datetime_col).lower()
    value_lower = str(value_col).lower()
    
    # SGE Tiers: "Horodate", "Valeur"
    if 'horodate' in datetime_lower and 'valeur' in value_lower:
        return 'sge_tiers'
    
    # Archelios: "DateTime", "Valeur" with specific capital letters
    if datetime_col == 'DateTime' and value_col == 'Valeur':
        return 'archelios'
    
    # Simple datetime format: generic datetime + value (from producers folder)
    if 'datetime' in datetime_lower and 'valeur' in value_lower:
        return 'simple_datetime'
    
    # PVGIS: often just 2 columns
    if datetime_col == 'datetime' and value_col == 'value':
        return 'pvgis'
    
    return 'unknown'
