"""Integration wrapper to provide a simple `process_curve` API compatible with existing pages.

This wrapper:
1. Calls io.read_curve() for flexible format detection (EMS, SGE, Archelios, etc)
2. Uses resample_curve() for 1h standardization
3. Applies impute_by_week_shift() for missing value imputation
4. Validates with validate_curve()

Returns consistent output: { success, df, metadata, validation, impute_report, errors }

The output df has DatetimeIndex (UTC naive, hourly) and columns:
- 'value' : numeric values in kW
- '_imputed' : bool, True if value was imputed
- '_impute_source' : int, week offset used for imputation (0 = original)
"""
from __future__ import annotations

from typing import Any, Dict
import pandas as pd

from .io import read_curve
from .resampler import resample_curve
from .validator import validate_curve
from .imputer import impute_by_week_shift


def process_curve(file_or_df: Any, value_col: str = "value", target_timestep: str = "PT60M", max_weeks: int = 4) -> Dict[str, Any]:
    """High-level processing: parse -> resample (1h) -> impute -> validate

    Returns dict with keys: 'success', 'df', 'metadata', 'validation', 'impute_report', 'errors'
    """
    result: Dict[str, Any] = {
        "success": False,
        "df": None,
        "metadata": None,
        "validation": None,
        "impute_report": None,
        "errors": [],
    }

    try:
        # Parse using flexible reader
        parsed_df, metadata = read_curve(file_or_df)
        result["metadata"] = metadata

        # Normalize column name for value
        if "value" not in parsed_df.columns:
            # try common names
            for candidate in ["W", "kW", "P_ac_kW", "value"]:
                if candidate in parsed_df.columns:
                    parsed_df = parsed_df.rename(columns={candidate: "value"})
                    break

        # Resample to target (use existing resample_curve which returns (df, message))
        resampled_df, _msg = resample_curve(parsed_df, target_timestep)

        # Ensure hourly index if target_timestep is PT60M
        # Our imputer expects DatetimeIndex
        if not isinstance(resampled_df.index, pd.DatetimeIndex):
            if "datetime" in resampled_df.columns:
                resampled_df = resampled_df.set_index(pd.to_datetime(resampled_df["datetime"]))

        # If multiple numeric columns, take first numeric as value
        if "value" not in resampled_df.columns:
            num_cols = resampled_df.select_dtypes(include=["number"]).columns
            if len(num_cols) >= 1:
                resampled_df = resampled_df.rename(columns={num_cols[0]: "value"})

        # Impute missing using week-shift strategy
        df_imputed, impute_report = impute_by_week_shift(resampled_df, value_col="value", max_weeks=max_weeks)
        result["impute_report"] = impute_report

        # Validate
        validation = validate_curve(df_imputed)
        result["validation"] = validation

        result["df"] = df_imputed
        result["success"] = True

    except Exception as e:
        result["errors"].append(str(e))

    return result
