"""Curve processing pipeline: read -> resample -> impute -> validate.

High-level API:
- process_curve(file_or_df) : end-to-end pipeline
- read_curve(file_or_df) : read + format detection
- impute_by_week_shift(df) : weekly-shift imputation
- resample_curve(df) : resample to target timestep
- validate_curve(df) : validate temporal continuity
"""

from .io import read_curve
from .imputer import impute_by_week_shift
from .integration import process_curve
from .resampler import resample_curve
from .validator import validate_curve

__all__ = ["read_curve", "impute_by_week_shift", "process_curve", "resample_curve", "validate_curve"]
