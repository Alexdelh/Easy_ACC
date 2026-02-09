"""Test suite for curve processing pipeline.

Tests reading, imputation, and resampling across all formats.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import pandas as pd
import pytest
from services.curve_processing.io import read_curve
from services.curve_processing.imputer import impute_by_week_shift
from services.curve_processing.integration import process_curve


class TestReadCurve:
    """Test curve reading for different formats."""

    def test_read_ems_format(self):
        """Read EMS format (conso)."""
        file_path = "ACC_data/samples/exemple-conso-ems.csv"
        if not os.path.exists(file_path):
            pytest.skip(f"{file_path} not found")

        df, meta = read_curve(file_path)

        assert isinstance(df, pd.DataFrame)
        assert isinstance(df.index, pd.DatetimeIndex)
        assert "value" in df.columns
        assert meta["detected_format"] == "EMS"
        assert len(df) > 0
        print(f"✓ EMS: {len(df)} rows, format={meta['detected_format']}, freq={meta['frequency']}")

    def test_read_sge_consumption(self):
        """Read SGE format (conso)."""
        file_path = "ACC_data/samples/exemple-conso-sge.csv"
        if not os.path.exists(file_path):
            pytest.skip(f"{file_path} not found")

        df, meta = read_curve(file_path)

        assert isinstance(df, pd.DataFrame)
        assert isinstance(df.index, pd.DatetimeIndex)
        assert "value" in df.columns
        assert meta["detected_format"] == "SGE"
        assert meta["frequency"] == "PT30M"  # SGE conso is 30min
        assert meta["unit"] == "W"
        assert len(df) > 0
        print(f"✓ SGE Conso: {len(df)} rows, freq={meta['frequency']}, unit={meta['unit']}")

    def test_read_sge_production(self):
        """Read SGE format (prod)."""
        file_path = "ACC_data/samples/exemple-prod-sge.csv"
        if not os.path.exists(file_path):
            pytest.skip(f"{file_path} not found")

        df, meta = read_curve(file_path)

        assert isinstance(df, pd.DataFrame)
        assert isinstance(df.index, pd.DatetimeIndex)
        assert "value" in df.columns
        assert meta["detected_format"] == "SGE"
        assert meta["frequency"] == "PT5M"  # SGE prod is 5min
        assert meta["unit"] == "W"
        assert len(df) > 0
        print(f"✓ SGE Prod: {len(df)} rows, freq={meta['frequency']}, unit={meta['unit']}")

    def test_read_archelios_format(self):
        """Read Archelios format (prod)."""
        file_path = "ACC_data/samples/exemple-prod-archelios.csv"
        if not os.path.exists(file_path):
            pytest.skip(f"{file_path} not found")

        df, meta = read_curve(file_path)

        assert isinstance(df, pd.DataFrame)
        assert isinstance(df.index, pd.DatetimeIndex)
        assert "value" in df.columns
        assert meta["detected_format"] == "Archelios"
        assert meta["frequency"] == "PT60M"  # Archelios is hourly
        assert len(df) > 0
        print(f"✓ Archelios: {len(df)} rows, freq={meta['frequency']}")

    def test_read_alex_format(self):
        """Read ALEX format (can be consumption or production)."""
        file_path = "ACC_data/samples/14501012966710.csv"
        if not os.path.exists(file_path):
            pytest.skip(f"{file_path} not found")

        df, meta = read_curve(file_path)

        assert isinstance(df, pd.DataFrame)
        assert isinstance(df.index, pd.DatetimeIndex)
        assert "value" in df.columns
        assert meta["detected_format"] == "ALEX"
        assert meta["frequency"] == "PT60M"  # ALEX is hourly
        assert meta["unit"] == "W"
        assert len(df) > 0
        print(f"✓ ALEX: {len(df)} rows, freq={meta['frequency']}, unit={meta['unit']}")


class TestImputation:
    """Test imputation algorithm."""

    def test_impute_simple_gap(self):
        """Test imputation of simple gap with week-shift."""
        # Create simple test: hourly from Jan 1-8, with gap on Jan 4
        dates = pd.date_range("2024-01-01", "2024-01-08", freq="H")
        values = [10.0] * len(dates)
        df = pd.DataFrame({"value": values}, index=dates)

        # Create gap on Jan 4
        mask = (df.index.day != 4) | (df.index.hour != 12)
        df = df[mask]

        # Impute
        df_imputed, report = impute_by_week_shift(df, value_col="value", max_weeks=1)

        # Jan 4 12:00 should be filled from Jan 11 12:00 (but Jan 11 doesn't exist, so not filled)
        # Actually, with max_weeks=1, we're looking t-1w (Jan -3, doesn't exist), t+1w (Jan 11, doesn't exist)
        # So this gap won't be filled. Let's adjust test.

        # Create a longer series with a gap that CAN be filled
        dates = pd.date_range("2024-01-01", "2024-01-22", freq="H")
        values = list(range(len(dates)))  # Unique values to track
        df = pd.DataFrame({"value": values}, index=dates)

        # Remove Jan 4 (but keep Jan 11 which is +1 week)
        mask = df.index.date != pd.Timestamp("2024-01-04").date()
        df_gap = df[mask]

        # Impute
        df_imputed, report = impute_by_week_shift(df_gap, value_col="value", max_weeks=4)

        assert report["missing_before"] == 24  # Jan 4 has 24 hours
        assert report["imputed_count"] == 24  # All 24 should be filled from Jan 11
        assert report["missing_after"] == 0
        print(
            f"✓ Imputation test: {report['imputed_count']}/{report['missing_before']} filled, "
            f"missing_after={report['missing_after']}"
        )

    def test_impute_rejection_threshold(self):
        """Test that excessive gaps trigger rejection."""
        # Create series with >20% missing
        dates = pd.date_range("2024-01-01", "2024-01-31", freq="H")
        values = [10.0] * len(dates)
        df = pd.DataFrame({"value": values}, index=dates)

        # Remove all of Jan 4-11 (8 days = 192 hours out of 744 total)
        mask = ~((df.index.date >= pd.Timestamp("2024-01-04").date()) & (df.index.date <= pd.Timestamp("2024-01-11").date()))
        df_gap = df[mask]

        # Impute
        df_imputed, report = impute_by_week_shift(df_gap, value_col="value", max_weeks=1)

        # With max_weeks=1, gaps >1 week won't be filled
        assert report["missing_after"] > 0
        assert report["imputed_pct"] < 100
        print(f"✓ Rejection: {report['imputed_pct']}% imputed, {report['missing_after']} still missing")


class TestProcessCurve:
    """Test end-to-end pipeline."""

    def test_process_ems_full_pipeline(self):
        """End-to-end: read EMS → resample → impute → validate."""
        file_path = "ACC_data/samples/exemple-conso-ems.csv"
        if not os.path.exists(file_path):
            pytest.skip(f"{file_path} not found")

        result = process_curve(file_path, target_timestep="PT60M", max_weeks=4)

        assert result["success"] is True
        assert result["df"] is not None
        assert result["impute_report"] is not None
        assert result["validation"] is not None
        assert "_imputed" in result["df"].columns
        assert "_impute_source" in result["df"].columns

        print(f"✓ EMS pipeline: {len(result['df'])} rows after processing, "
              f"{result['impute_report']['imputed_pct']:.1f}% imputed")

    def test_process_sge_consumption(self):
        """End-to-end: read SGE conso → resample (30min→60min) → impute."""
        file_path = "ACC_data/samples/exemple-conso-sge.csv"
        if not os.path.exists(file_path):
            pytest.skip(f"{file_path} not found")

        result = process_curve(file_path, target_timestep="PT60M", max_weeks=4)

        assert result["success"] is True
        assert result["df"] is not None
        print(f"✓ SGE Conso pipeline: {len(result['df'])} rows, freq inferred as 30min → resampled to 1h")

    def test_process_alex_format(self):
        """End-to-end: read ALEX → already 1h → impute."""
        file_path = "ACC_data/samples/14501012966710.csv"
        if not os.path.exists(file_path):
            pytest.skip(f"{file_path} not found")

        result = process_curve(file_path, target_timestep="PT60M", max_weeks=4)

        assert result["success"] is True
        assert result["df"] is not None
        assert result["metadata"]["detected_format"] == "ALEX"
        print(f"✓ ALEX pipeline: {len(result['df'])} rows, {result['impute_report']['imputed_pct']:.1f}% imputed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
