import streamlit as st
import pandas as pd
from typing import Tuple, Optional
import logging  # New import for logging

import pvlib
from pvlib.iotools import get_pvgis_tmy
from pvlib.pvsystem import pvwatts_dc, pvwatts_losses
from pvlib.location import Location
from pvlib.irradiance import get_total_irradiance

# Configure logging
logging.basicConfig(level=logging.INFO)  # Set logging level


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_tmy(lat: float, lon: float, usehorizon: bool = True) -> Tuple[pd.DataFrame, dict]:
    """Fetch PVGIS Typical Meteorological Year (TMY) data for a location.

    Returns a tuple of (weather_df, metadata).
    """
    # Round coordinates to avoid cache misses from tiny differences
    lat = round(float(lat), 4)
    lon = round(float(lon), 4)
    
    # pvlib.iotools.get_pvgis_tmy returns (data, months_selected, inputs, metadata)
    data, _months_selected, _inputs, metadata = get_pvgis_tmy(
        latitude=lat,
        longitude=lon,
        outputformat='json',
        usehorizon=usehorizon,
        map_variables=True,
    )
    # Ensure column names consistent for pvlib ModelChain
    # get_pvgis_tmy returns columns like: ghi, dni, dhi, temp_air, wind_speed, etc.
    return data, metadata


@st.cache_data(ttl=3600, show_spinner=False)
def compute_pv_curve(
    lat: float,
    lon: float,
    peakpower_kw: float,
    tilt_deg: float,
    azimuth_deg: float,
    losses_pct: float = 14.0,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
) -> Optional[pd.DataFrame]:
    """Compute hourly AC power curve using PVWatts with PVGIS TMY weather.

    Args:
        lat, lon: Latitude and longitude
        peakpower_kw: Peak power in kW
        tilt_deg: Panel tilt angle (0-90 degrees)
        azimuth_deg: Panel azimuth (0-360 degrees)
        losses_pct: System losses percentage (default 14%)
        start_date: Start date for the curve (default: 2024-01-01)
        end_date: End date for the curve (default: 2024-12-31)

    Returns:
        A DataFrame indexed by datetime with column 'P_ac_kW'.
    """
    try:
        # Round coordinates to match fetch_tmy cache
        lat = round(float(lat), 4)
        lon = round(float(lon), 4)
        
        weather, meta = fetch_tmy(lat, lon, usehorizon=True)
        
        # Convert peakpower to watts
        peakpower_w = float(peakpower_kw) * 1000.0
        
        # Create Location object for solar position calculations
        location = Location(latitude=lat, longitude=lon)
        
        # Calculate solar position
        solar_position = location.get_solarposition(weather.index)
        
        # Calculate POA (Plane of Array) irradiance based on tilt and azimuth
        # This is the key: we need to transpose GHI/DNI/DHI to the panel's plane
        poa_irradiance = get_total_irradiance(
            surface_tilt=tilt_deg,
            surface_azimuth=azimuth_deg,
            solar_zenith=solar_position['apparent_zenith'],
            solar_azimuth=solar_position['azimuth'],
            dni=weather.get('dni', 0),
            ghi=weather.get('ghi', 0),
            dhi=weather.get('dhi', 0)
        )
        
        # Use POA global irradiance for DC power calculation
        poa_global = poa_irradiance['poa_global']
        
        # Estimate cell temperature: T_cell = T_air + 0.0045 * POA
        # (Standard PVWatts approximation)
        t_cell = weather['temp_air'] + 0.0045 * poa_global
        
        # Compute DC power using pvwatts_dc with POA irradiance
        pdc = pvwatts_dc(
            g_poa_effective=poa_global,  # Now using actual POA irradiance
            temp_cell=t_cell,
            pdc0=peakpower_w,
            gamma_pdc=-0.005  # Standard PVWatts temperature coefficient
        )
        
        # Compute system losses using pvwatts_losses (returns % loss)
        # Using default loss parameters
        loss_pct_system = pvwatts_losses()
        
        # Apply inverter efficiency (~0.96) and system losses to get AC power
        # AC = DC * inverter_efficiency * (1 - system_losses/100)
        inverter_eff = 0.96
        pac = pdc * inverter_eff * (1.0 - loss_pct_system / 100.0)
        
        # Build output DataFrame
        df = pd.DataFrame(index=weather.index)
        df['P_ac_kW'] = pac / 1000.0  # Convert W to kW
        
        # Apply additional system losses (simple scalar)
        if losses_pct and losses_pct > 0:
            df['P_ac_kW'] = df['P_ac_kW'] * (1.0 - losses_pct / 100.0)
        
        # Set default dates if not provided
        if start_date is None:
            start_date = pd.Timestamp('2024-01-01')
        else:
            start_date = pd.Timestamp(start_date)
        
        if end_date is None:
            end_date = pd.Timestamp('2024-12-31')
        else:
            end_date = pd.Timestamp(end_date)
        
        # Calculate required number of hours based on date range
        hours_needed = int((end_date - start_date).total_seconds() / 3600) + 1
        
        # TMY data repeats annually, so we can tile it if needed for multi-year periods
        tmy_hours = len(df)
        if hours_needed > tmy_hours:
            # Multi-year period: tile the TMY data
            num_repeats = (hours_needed // tmy_hours) + 1
            df = pd.concat([df] * num_repeats, ignore_index=True)
            df = df.iloc[:hours_needed]
        elif hours_needed < tmy_hours:
            # Less than a year: take subset
            df = df.iloc[:hours_needed]
        
        # Create clean date range based on selected period
        df.index = pd.date_range(start=start_date, periods=len(df), freq='h')
        
        # Ensure we don't go past end_date
        df = df[df.index <= end_date]
        
        return df
    except Exception as e:
        import traceback
        error_msg = f"PVGIS/PVWatts error: {str(e)}\n{traceback.format_exc()}"
        logging.error(error_msg)  # Use logging instead of print
        try:
            st.error(error_msg)
        except Exception:
            pass
        return None
