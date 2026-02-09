"""Curve processing pipeline: read -> resample -> impute -> validate.

High-level API:
- process_curve(file_or_df) : end-to-end pipeline
- read_curve(file_or_df) : read + format detection
- impute_by_week_shift(df) : weekly-shift imputation

Reuses existing services.curve_standardizer for resampling and validation.
"""

from .io import read_curve
from .imputer import impute_by_week_shift
from .integration import process_curve

__all__ = ["read_curve", "impute_by_week_shift", "process_curve"]
