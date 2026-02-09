"""Orchestrator for production curve standardization (parse -> validate -> resample -> format)."""

import pandas as pd
from typing import Dict, List, Tuple, Literal, Optional
from io import BytesIO
import sys

from .parser import parse_curve
from .validator import validate_curve
from .resampler import resample_curve
from .formatters import to_sge_tiers_format, to_archelios_format, to_pvgis_format, to_pvgis_dataframe


class CurveStandardizer:
    """
    Main orchestrator for production curve standardization.
    
    Workflow:
    1. Parse input file (CSV, Excel, or DataFrame)
    2. Validate temporal continuity
    3. Resample to 3 target timesteps (PT15M, PT30M, PT60M)
    4. Format to 3 output formats (SGE Tiers, Archelios, PVGIS)
    5. Return 9 export variants or multi-file export
    """
    
    TIMESTEPS = ['PT15M', 'PT30M', 'PT60M']
    FORMATS = ['sge_tiers', 'archelios', 'pvgis']
    
    def __init__(self, prm_id: str = "ACCKB_XXXX"):
        """
        Initialize standardizer.
        
        Args:
            prm_id: Meter/Point d'injection identifier (for SGE format)
        """
        self.prm_id = prm_id
        self.parsed_df = None
        self.metadata = None
        self.validation_report = None
        self.exports = {}  # {(format, timestep): df_or_str}
    
    def process(self, file_or_df) -> Dict:
        """
        Full processing pipeline: parse -> validate -> resample -> format.
        
        Args:
            file_or_df: File path, BytesIO, or DataFrame
        
        Returns:
            Dict with 'success', 'parsed', 'validation', 'exports'
        """
        
        result = {
            'success': False,
            'parsed': None,
            'validation': None,
            'exports': {},
            'errors': [],
        }
        
        try:

            print("[CurveStandardizer] Parsing input...")
            self.parsed_df, metadata = parse_curve(file_or_df)
            self.metadata = metadata
            result['parsed'] = {
                'rows': len(self.parsed_df),
                'metadata': metadata,
            }
            print(f"  [OK] Parsed {len(self.parsed_df)} rows")
            
            # Step 2: Validate
            print("[CurveStandardizer] Validating curve...")
            self.validation_report = validate_curve(self.parsed_df)
            result['validation'] = self.validation_report
            print(f"  [OK] Valid: {self.validation_report['is_valid']}")
            if self.validation_report['warnings']:
                print(f"  [WARN] Warnings: {len(self.validation_report['warnings'])}")
            
            # Step 3 & 4: Resample and Format
            print("[CurveStandardizer] Generating 9 export variants...")
            for fmt in self.FORMATS:
                for timestep in self.TIMESTEPS:
                    try:
                        # Resample
                        resampled_df, resample_msg = resample_curve(
                            self.parsed_df, 
                            target_timestep=timestep
                        )
                        
                        # Format
                        if fmt == 'sge_tiers':
                            export_data = to_sge_tiers_format(resampled_df, self.metadata, self.prm_id)
                        elif fmt == 'archelios':
                            export_data = to_archelios_format(resampled_df)
                        elif fmt == 'pvgis':
                            export_data = to_pvgis_format(resampled_df)
                        
                        key = (fmt, timestep)
                        self.exports[key] = export_data
                        result['exports'][key] = len(export_data) if isinstance(export_data, str) else len(export_data)
                        
                        print(f"  [OK] {fmt} / {timestep}: {result['exports'][key]} rows/chars")
                    
                    except Exception as e:
                        print(f"  [FAIL] {fmt} / {timestep}: {str(e)}", file=sys.stderr)
                        result['errors'].append(f"Failed to generate {fmt}/{timestep}: {str(e)}")
            
            result['success'] = True
            print("[CurveStandardizer] [OK] Processing complete")
            
        except Exception as e:
            print(f"[CurveStandardizer] [FAIL] Error: {str(e)}", file=sys.stderr)
            result['errors'].append(str(e))
        
        return result
    
    def get_preview_dataframe(self) -> Optional[pd.DataFrame]:
        """
        Get a simplified DataFrame for preview/plotting.
        
        Returns:
            DataFrame with datetime index and numeric production columns,
            or None if not yet parsed
        """
        if self.parsed_df is None:
            return None
        
        df = self.parsed_df.copy()
        
        # Ensure datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'datetime' in df.columns:
                df = df.set_index('datetime')
            elif 'timestamp' in df.columns:
                df = df.set_index('timestamp')
        
        # Keep only numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            df = df[numeric_cols]
        
        return df

    def process_preview(self, file_or_df) -> Dict:
        """Lightweight preview pipeline that delegates to `process_curve`.

        This keeps backward compatibility for UIs using `CurveStandardizer` to
        preview curves while reusing the unified multi-format pipeline.

        It sets `self.parsed_df`, `self.metadata` and `self.validation_report`
        from the processed result so existing callers can continue to use
        `standardizer.parsed_df` for plotting.

        Returns a dict similar to `process_curve` with keys:
        'success', 'df', 'metadata', 'validation', 'impute_report', 'errors'
        """
        result = {
            'success': False,
            'df': None,
            'metadata': None,
            'validation': None,
            'impute_report': None,
            'errors': [],
        }

        try:
            # Local import to avoid circular dependency at module import time
            from services.curve_processing import process_curve
            proc = process_curve(file_or_df)
            # copy relevant fields
            result.update(proc)

            if proc.get('success') and proc.get('df') is not None:
                self.parsed_df = proc.get('df')
                self.metadata = proc.get('metadata')
                self.validation_report = proc.get('validation')

        except Exception as e:
            result['errors'].append(str(e))

        return result
    
    def get_export(self, format_type: str, timestep: str = 'PT60M') -> Optional[pd.DataFrame]:
        """
        Get export in specific format and timestep.
        
        Args:
            format_type: 'sge_tiers', 'archelios', 'pvgis', or 'simple_datetime'
            timestep: 'PT15M', 'PT30M', or 'PT60M'
            
        Returns:
            DataFrame in requested format, or None if not available
        """
        
        if self.exports is None:
            return None
        
        key = (format_type, timestep)
        return self.exports.get(key)
    
    def get_all_exports(self) -> Dict[Tuple[str, str], any]:
        """
        Retrieve all 9 export variants.
        
        Returns:
            Dict mapping (format, timestep) -> data
        """
        return self.exports.copy()
    
    def export_to_files(self, output_dir: str) -> List[str]:
        """
        Export all variants to individual files.
        
        Args:
            output_dir: Output directory path
        
        Returns:
            List of created file paths
        """
        import os
        
        created_files = []
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        for (fmt, timestep), data in self.exports.items():
            filename = f"curve_{fmt}_{timestep}.csv"
            filepath = os.path.join(output_dir, filename)
            
            try:
                if isinstance(data, str):  # PVGIS format
                    with open(filepath, 'w') as f:
                        f.write(data)
                else:  # DataFrame
                    data.to_csv(filepath, index=False)
                
                created_files.append(filepath)
                print(f"  [OK] Exported: {filepath}")
            
            except Exception as e:
                print(f"  [FAIL] Failed to export {filepath}: {str(e)}")
        
        return created_files
    
    def _format_curve(self, df: pd.DataFrame, format_type: str) -> pd.DataFrame:
        """Format curve to specific export format."""
        
        if format_type == 'sge_tiers':
            return to_sge_tiers_format(df, self.metadata, self.prm_id)
        elif format_type == 'archelios':
            return to_archelios_format(df)
        elif format_type == 'simple_datetime':
            return to_pvgis_dataframe(df)
        elif format_type == 'pvgis':
            return to_pvgis_format(df)
        else:
            return df
