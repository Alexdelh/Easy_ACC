"""Production curve standardization module.

Standardizes production curves to 3 formats × 3 timesteps:
- Formats: SGE Tiers, Archelios, PVGIS
- Timesteps: PT15M (15min), PT30M (30min), PT60M (60min)

Usage:
    from services.curve_standardizer import CurveStandardizer
    
    standardizer = CurveStandardizer(prm_id="ACCKB_0001")
    result = standardizer.process("path/to/curve.xlsx")
    
    # Access variants
    sge_df = standardizer.get_export('sge_tiers', 'PT60M')
    archelios_df = standardizer.get_export('archelios', 'PT30M')
    pvgis_str = standardizer.get_export('pvgis', 'PT15M')
"""

## from .parser import parse_curve  # Désactivé : plus utilisé dans le flux principal
from .validator import validate_curve
from .resampler import resample_curve
from .formatters import (
    to_sge_tiers_format,
    to_archelios_format,
    to_pvgis_format,
)
from .standardizer import CurveStandardizer
from .utils import (
    detect_datetime_column,
    detect_value_column,
    try_parse_datetime,
    detect_timestep,
    normalize_unit,
    check_continuity,
)

__all__ = [
    # Main orchestrator
    'CurveStandardizer',
    
    # Pipeline functions
    # 'parse_curve',  # Désactivé : plus utilisé dans le flux principal
    'validate_curve',
    'resample_curve',
    
    # Formatters
    'to_sge_tiers_format',
    'to_archelios_format',
    'to_pvgis_format',
    
    # Utilities
    'detect_datetime_column',
    'detect_value_column',
    'try_parse_datetime',
    'detect_timestep',
    'normalize_unit',
    'check_continuity',
]
