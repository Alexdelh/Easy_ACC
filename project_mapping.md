# Project Easy_ACC Detailed Function Mapping

This document maps every function and method across the precalibrage and bilan phases, including services and navigation.

## Core Application
### File: `app.py`
**Type:** Python Module


---

## Module: Pages
### File: `pages/precalibrage/projects_list.py`
**Type:** Python Module

#### Function: `render`
- **Parameters:** ``
- **Returns:** `None explicitly annotated`
- **What it does:** Render the Projects List within the Precalibrage phase.

### File: `pages/precalibrage/consommation.py`
**Type:** Python Module

#### Function: `show_map_with_radius`
- **Parameters:** `points, radius_km, zoom`
- **Returns:** `None explicitly annotated`
- **What it does:** Crée une carte avec cercle de rayon et centroïde optimisé.

Cherche le centroïde qui maximise le nombre de points à l'intérieur du rayon.
Si plusieurs centroïdes donnent le même nombre de points inside,
choisit celui minimisant la somme totale des distances.

Args:
    points: list of dicts {'name', 'lat', 'lon'}
    radius_km: rayon du cercle en km
    zoom: niveau de zoom folium

Retourne : (folium.Map, (center_lat, center_lon), inside_list, outside_list)
    - inside_list / outside_list: list of tuples (name, distance_km)

#### Function: `cercle`
- **Parameters:** `coords, map_object, radius_km, color, fill_opacity`
- **Returns:** `None`
- **What it does:** Ajoute un cercle sur une carte Folium.

Args:
    coords: dict avec keys 'lat' et 'lng'
    map_object: objet folium.Map
    radius_km: rayon du cercle en kilomètres
    color: couleur du cercle
    fill_opacity: opacité du remplissage
    **kwargs: arguments supplémentaires pour folium.Circle

#### Function: `extract_distance_km`
- **Parameters:** `distance_str`
- **Returns:** `float`
- **What it does:** Extract numeric distance value from strings like '2 km', '2km', '2.5', or return float inputs.

#### Function: `render`
- **Parameters:** ``
- **Returns:** `None explicitly annotated`
- **What it does:** Render the Points de soutirage page with two-tab structure.

#### Function: `_lon`
- **Parameters:** `p`
- **Returns:** `None explicitly annotated`
- **What it does:** No docstring provided.

#### Function: `compute_lists`
- **Parameters:** `center_lat, center_lon`
- **Returns:** `None explicitly annotated`
- **What it does:** No docstring provided.

#### Function: `total_distance`
- **Parameters:** `center_lat, center_lon`
- **Returns:** `None explicitly annotated`
- **What it does:** No docstring provided.

### File: `pages/precalibrage/parametres.py`
**Type:** Python Module

#### Function: `safe_rerun`
- **Parameters:** ``
- **Returns:** `None explicitly annotated`
- **What it does:** Try to trigger a Streamlit rerun in a version-compatible way.

#### Function: `render`
- **Parameters:** ``
- **Returns:** `None explicitly annotated`
- **What it does:** Render the Paramètres page.

### File: `pages/precalibrage/production.py`
**Type:** Python Module

#### Function: `show_map_with_radius`
- **Parameters:** `points, radius_km, zoom`
- **Returns:** `None explicitly annotated`
- **What it does:** Crée une carte avec cercle de rayon et centroïde optimisé.

Cherche le centroïde qui maximise le nombre de points à l'intérieur du rayon.
Si plusieurs centroïdes donnent le même nombre de points inside,
choisit celui minimisant la somme totale des distances.

Args:
    points: list of dicts {'name', 'lat', 'lon'}
    radius_km: rayon du cercle en km
    zoom: niveau de zoom folium

Retourne : (folium.Map, (center_lat, center_lon), inside_list, outside_list)
    - inside_list / outside_list: list of tuples (name, distance_km)

#### Function: `cercle`
- **Parameters:** `coords, map_object, radius_km, color, fill_opacity`
- **Returns:** `None`
- **What it does:** Ajoute un cercle sur une carte Folium.

Args:
    coords: dict avec keys 'lat' et 'lng'
    map_object: objet folium.Map
    radius_km: rayon du cercle en kilomètres
    color: couleur du cercle
    fill_opacity: opacité du remplissage
    **kwargs: arguments supplémentaires pour folium.Circle

#### Function: `extract_distance_km`
- **Parameters:** `distance_str`
- **Returns:** `float`
- **What it does:** Extract numeric distance value from strings like '2 km', '2km', '2.5', or return float inputs.

#### Function: `normalize_curve_df`
- **Parameters:** `df`
- **Returns:** `pd.DataFrame | None`
- **What it does:** Normalize an uploaded or modeled curve DataFrame for plotting.

- Tries to set a datetime index if a suitable column exists
- Selects numeric columns and drops all-null columns
- Sorts by datetime index when present
Returns a numeric DataFrame or None if unusable.

#### Function: `render`
- **Parameters:** ``
- **Returns:** `None explicitly annotated`
- **What it does:** Render the Points d'injection page with two-tab structure.

#### Function: `_lon`
- **Parameters:** `p`
- **Returns:** `None explicitly annotated`
- **What it does:** No docstring provided.

#### Function: `compute_lists`
- **Parameters:** `center_lat, center_lon`
- **Returns:** `None explicitly annotated`
- **What it does:** No docstring provided.

#### Function: `total_distance`
- **Parameters:** `center_lat, center_lon`
- **Returns:** `None explicitly annotated`
- **What it does:** No docstring provided.

### File: `pages/precalibrage/general.py`
**Type:** Python Module

#### Function: `render`
- **Parameters:** ``
- **Returns:** `None explicitly annotated`
- **What it does:** Render the Infos Générales page.

### File: `pages/bilan/energie.py`
**Type:** Python Module

#### Function: `render`
- **Parameters:** ``
- **Returns:** `None explicitly annotated`
- **What it does:** Render the Bilan Énergétique page.

#### Function: `colorblind_palette`
- **Parameters:** `n`
- **Returns:** `None explicitly annotated`
- **What it does:** No docstring provided.

#### Function: `donut_total_kwh`
- **Parameters:** `values, labels`
- **Returns:** `None explicitly annotated`
- **What it does:** No docstring provided.

#### Function: `display_legend`
- **Parameters:** `labels, values, colors`
- **Returns:** `None explicitly annotated`
- **What it does:** No docstring provided.


---

## Module: Navigation
### File: `navigation/sidebar_bilan.py`
**Type:** Python Module

#### Function: `render_sidebar_bilan`
- **Parameters:** ``
- **Returns:** `None explicitly annotated`
- **What it does:** Sidebar for bilan phase - navigation only.

### File: `navigation/sidebar_precalibrage.py`
**Type:** Python Module

#### Function: `render_sidebar_precalibrage`
- **Parameters:** ``
- **Returns:** `None explicitly annotated`
- **What it does:** Sidebar for precalibrage phase - navigation only.


---

## Module: Services
### File: `services/geolocation.py`
**Type:** Python Module

#### Function: `extract_postal_code`
- **Parameters:** `address`
- **Returns:** `str`
- **What it does:** Extract French postal code from address string.
French postal codes are 5 digits.

Args:
    address: Address string that may contain a postal code

Returns:
    Postal code string (5 digits) or empty string if not found

#### Function: `get_coordinates_from_address`
- **Parameters:** `address`
- **Returns:** `Dict[str, float]`
- **What it does:** Retrieve coordinates from address using Nominatim API (OpenStreetMap).
First tries the mock database for known cities, then falls back to live API.
Results cached for 1 hour to minimize API calls.

### File: `services/models.py`
**Type:** Python Module

#### Class: `Base`
- **What it does:** No docstring provided.

#### Class: `Project`
- **What it does:** No docstring provided.

#### Class: `Dataset`
- **What it does:** No docstring provided.

### File: `services/database.py`
**Type:** Python Module

#### Class: `UnsupportedFileTypeError`
- **What it does:** No docstring provided.

#### Function: `init_db`
- **Parameters:** ``
- **Returns:** `None explicitly annotated`
- **What it does:** Initialize the SQLite database and create tables.

#### Function: `get_db`
- **Parameters:** ``
- **Returns:** `None explicitly annotated`
- **What it does:** Dependency for session management.

#### Function: `save_project`
- **Parameters:** `name, current_phase, state_dict, project_id`
- **Returns:** `int`
- **What it does:** Save or update a project atomically.
Returns the project ID.

#### Function: `load_project`
- **Parameters:** `project_id`
- **Returns:** `None explicitly annotated`
- **What it does:** Load a project by ID.

#### Function: `list_projects`
- **Parameters:** ``
- **Returns:** `None explicitly annotated`
- **What it does:** List all projects.

#### Function: `delete_project`
- **Parameters:** `project_id`
- **Returns:** `None explicitly annotated`
- **What it does:** Delete a project and its datasets (Cascade).

#### Function: `validate_file_type`
- **Parameters:** `filename_or_type`
- **Returns:** `None explicitly annotated`
- **What it does:** Gatekeeper: Restrict to .csv, .txt, .xlsx or known internal types.
If 'type' is passed (like 'production_curve'), we check usage context or assume it's valid if internal.
The user requirement was specific to 'uploads'.

#### Function: `save_dataset`
- **Parameters:** `project_id, name, type, data, metadata, file_type`
- **Returns:** `None explicitly annotated`
- **What it does:** Save a dataset linked to a project using an Atomic Transaction.
Updates the project's 'updated_at' timestamp automatically via relationship touch or explicit update.

#### Function: `list_datasets`
- **Parameters:** `project_id, dataset_type`
- **Returns:** `None explicitly annotated`
- **What it does:** List datasets for a specific project.

#### Function: `load_dataset`
- **Parameters:** `dataset_id`
- **Returns:** `None explicitly annotated`
- **What it does:** Load a dataset by ID.

#### Function: `delete_dataset`
- **Parameters:** `dataset_id`
- **Returns:** `None explicitly annotated`
- **What it does:** Delete a dataset.

#### Function: `get_storage_usage`
- **Parameters:** ``
- **Returns:** `None explicitly annotated`
- **What it does:** Calculate total storage used by datasets.

### File: `services/pvgis.py`
**Type:** Python Module

#### Function: `fetch_tmy`
- **Parameters:** `lat, lon, usehorizon`
- **Returns:** `Tuple[pd.DataFrame, dict]`
- **What it does:** Fetch PVGIS Typical Meteorological Year (TMY) data for a location.

Returns a tuple of (weather_df, metadata).

#### Function: `compute_pv_curve`
- **Parameters:** `lat, lon, peakpower_kw, tilt_deg, azimuth_deg, losses_pct, start_date, end_date`
- **Returns:** `Optional[pd.DataFrame]`
- **What it does:** Compute hourly AC power curve using PVWatts with PVGIS TMY weather.

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

### File: `services/state_serializer.py`
**Type:** Python Module

#### Function: `serialize_state`
- **Parameters:** `state`
- **Returns:** `None explicitly annotated`
- **What it does:** Recursively serialize a dictionary (state) into a JSON-compatible format.
Handles pandas DataFrames by converting them to dictionaries with metadata.

#### Function: `deserialize_state`
- **Parameters:** `state`
- **Returns:** `None explicitly annotated`
- **What it does:** Recursively deserialize a JSON-compatible structure back into original objects.
Reconstructs pandas DataFrames from the custom dictionary format.

### File: `services/curve_standardizer/validator.py`
**Type:** Python Module

#### Function: `validate_curve`
- **Parameters:** `df`
- **Returns:** `Dict[str, any]`
- **What it does:** Validate a parsed production curve for issues.

Checks:
- Temporal continuity (gaps > 2 hours)
- Duplicates
- NaN values
- Monotonic increasing timestamps
- Future dates

Returns:
    validation_report dict with 'is_valid', 'errors', 'warnings'

### File: `services/curve_standardizer/formatters.py`
**Type:** Python Module

#### Function: `to_sge_tiers_format`
- **Parameters:** `df, metadata, prm_id`
- **Returns:** `pd.DataFrame`
- **What it does:** Convert to SGE Tiers format (9-column standard).

SGE Tiers format:
- Identifiant PRM (Meter ID)
- Date début (Start date)
- Date fin (End date)
- Grandeur physique (Physical quantity: energy, power, etc.)
- Grandeur métier (Business quantity)
- Étape métier (Business step)
- Unité (Unit: kW, kWh, etc.)
- Horodate (Timestamp YYYY-MM-DD HH:MM:SS)
- Valeur (Value)
- Pas (Timestep: PT15M, PT30M, PT60M)

Args:
    df: DataFrame with DatetimeIndex and 'value' column
    metadata: Dict with source info (unit, etc.)
    prm_id: Meter identifier (e.g., "ACCKB_0001")

Returns:
    DataFrame in SGE Tiers format

#### Function: `to_archelios_format`
- **Parameters:** `df`
- **Returns:** `pd.DataFrame`
- **What it does:** Convert to Archelios format (datetime + value).

Archelios format:
- DateTime (format: M/D/YY H:MM)
- Valeur (Value in kW)

Args:
    df: DataFrame with DatetimeIndex and 'value' column

Returns:
    DataFrame in Archelios format

#### Function: `to_simple_datetime_format`
- **Parameters:** `df`
- **Returns:** `pd.DataFrame`
- **What it does:** Convert to simple datetime + value format (compatible with various tools).

Simple format:
- DateTime (format: M/D/YY H:MM) - US format without leading zeros
- Valeur (Value in kW)

This format is similar to some producer data files but more generic.

Args:
    df: DataFrame with DatetimeIndex and 'value' column

Returns:
    DataFrame in simple datetime format

#### Function: `to_pvgis_format`
- **Parameters:** `df`
- **Returns:** `str`
- **What it does:** Convert to PVGIS compact format.

PVGIS format: YYYYMMDD:HHMM;value
One timestamp:value per line

Example:
20240101:0000;0.0
20240101:0015;0.5
20240101:0030;1.2

Args:
    df: DataFrame with DatetimeIndex and 'value' column

Returns:
    String with PVGIS format data

#### Function: `to_pvgis_dataframe`
- **Parameters:** `df`
- **Returns:** `pd.DataFrame`
- **What it does:** Convert to PVGIS format as DataFrame.

Returns:
    DataFrame with ['time', 'value'] columns in PVGIS format

### File: `services/curve_standardizer/parser.py`
**Type:** Python Module

#### Function: `parse_curve`
- **Parameters:** `file_or_df`
- **Returns:** `Tuple[pd.DataFrame, Dict[str, Any]]`
- **What it does:** Parse a production curve from file or DataFrame.

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

#### Function: `_detect_source_format`
- **Parameters:** `datetime_col, value_col`
- **Returns:** `str`
- **What it does:** Detect source format based on column names.

### File: `services/curve_standardizer/standardizer.py`
**Type:** Python Module

#### Class: `CurveStandardizer`
- **What it does:** Main orchestrator for production curve standardization.

Workflow:
1. Parse input file (CSV, Excel, or DataFrame)
2. Validate temporal continuity
3. Resample to 3 target timesteps (PT15M, PT30M, PT60M)
4. Format to 3 output formats (SGE Tiers, Archelios, PVGIS)
5. Return 9 export variants or multi-file export

##### Method: `CurveStandardizer.__init__`
- **Parameters:** `self, prm_id`
- **Returns:** `None explicitly annotated`
- **What it does:** Initialize standardizer.

Args:
    prm_id: Meter/Point d'injection identifier (for SGE format)

##### Method: `CurveStandardizer.process`
- **Parameters:** `self, file_or_df`
- **Returns:** `Dict`
- **What it does:** Full processing pipeline: parse -> validate -> resample -> format.

Args:
    file_or_df: File path, BytesIO, or DataFrame

Returns:
    Dict with 'success', 'parsed', 'validation', 'exports'

##### Method: `CurveStandardizer.get_preview_dataframe`
- **Parameters:** `self`
- **Returns:** `Optional[pd.DataFrame]`
- **What it does:** Get a simplified DataFrame for preview/plotting.

Returns:
    DataFrame with datetime index and numeric production columns,
    or None if not yet parsed

##### Method: `CurveStandardizer.get_export`
- **Parameters:** `self, format_type, timestep`
- **Returns:** `Optional[pd.DataFrame]`
- **What it does:** Get export in specific format and timestep.

Args:
    format_type: 'sge_tiers', 'archelios', 'pvgis', or 'simple_datetime'
    timestep: 'PT15M', 'PT30M', or 'PT60M'
    
Returns:
    DataFrame in requested format, or None if not available

##### Method: `CurveStandardizer.get_all_exports`
- **Parameters:** `self`
- **Returns:** `Dict[Tuple[str, str], any]`
- **What it does:** Retrieve all 9 export variants.

Returns:
    Dict mapping (format, timestep) -> data

##### Method: `CurveStandardizer.export_to_files`
- **Parameters:** `self, output_dir`
- **Returns:** `List[str]`
- **What it does:** Export all variants to individual files.

Args:
    output_dir: Output directory path

Returns:
    List of created file paths

##### Method: `CurveStandardizer._format_curve`
- **Parameters:** `self, df, format_type`
- **Returns:** `pd.DataFrame`
- **What it does:** Format curve to specific export format.

#### Function: `__init__`
- **Parameters:** `self, prm_id`
- **Returns:** `None explicitly annotated`
- **What it does:** Initialize standardizer.

Args:
    prm_id: Meter/Point d'injection identifier (for SGE format)

#### Function: `process`
- **Parameters:** `self, file_or_df`
- **Returns:** `Dict`
- **What it does:** Full processing pipeline: parse -> validate -> resample -> format.

Args:
    file_or_df: File path, BytesIO, or DataFrame

Returns:
    Dict with 'success', 'parsed', 'validation', 'exports'

#### Function: `get_preview_dataframe`
- **Parameters:** `self`
- **Returns:** `Optional[pd.DataFrame]`
- **What it does:** Get a simplified DataFrame for preview/plotting.

Returns:
    DataFrame with datetime index and numeric production columns,
    or None if not yet parsed

#### Function: `get_export`
- **Parameters:** `self, format_type, timestep`
- **Returns:** `Optional[pd.DataFrame]`
- **What it does:** Get export in specific format and timestep.

Args:
    format_type: 'sge_tiers', 'archelios', 'pvgis', or 'simple_datetime'
    timestep: 'PT15M', 'PT30M', or 'PT60M'
    
Returns:
    DataFrame in requested format, or None if not available

#### Function: `get_all_exports`
- **Parameters:** `self`
- **Returns:** `Dict[Tuple[str, str], any]`
- **What it does:** Retrieve all 9 export variants.

Returns:
    Dict mapping (format, timestep) -> data

#### Function: `export_to_files`
- **Parameters:** `self, output_dir`
- **Returns:** `List[str]`
- **What it does:** Export all variants to individual files.

Args:
    output_dir: Output directory path

Returns:
    List of created file paths

#### Function: `_format_curve`
- **Parameters:** `self, df, format_type`
- **Returns:** `pd.DataFrame`
- **What it does:** Format curve to specific export format.

### File: `services/curve_standardizer/utils.py`
**Type:** Python Module

#### Function: `clean_numeric_string`
- **Parameters:** `value`
- **Returns:** `None explicitly annotated`
- **What it does:** Clean a numeric string value to handle various formats.

Handles:
- European format (comma as decimal separator): "0,147" -> "0.147"
- Quoted values: '"0,147"' -> "0.147"
- Spaces: "1 234,56" -> "1234.56"

Returns cleaned string or original value if not a string.

#### Function: `detect_datetime_column`
- **Parameters:** `df`
- **Returns:** `Optional[str]`
- **What it does:** Detect which column contains datetime information.

Looks for common patterns: date, time, horodate, datetime, timestamp, etc.
Returns column name or None if not found.
Special case: Returns '__index__' if DataFrame already has a DatetimeIndex.

#### Function: `detect_value_column`
- **Parameters:** `df, exclude_cols`
- **Returns:** `Optional[str]`
- **What it does:** Detect which column contains the numeric values (production).

Prioritizes columns with production-related keywords, then falls back to numeric columns.
Returns first valid numeric column that's not in exclude_cols.

#### Function: `try_parse_datetime`
- **Parameters:** `series`
- **Returns:** `Optional[pd.DatetimeIndex]`
- **What it does:** Attempt to parse a series as datetime.

Returns DatetimeIndex if successful, None otherwise.

#### Function: `detect_timestep`
- **Parameters:** `df, datetime_index`
- **Returns:** `Optional[str]`
- **What it does:** Detect the frequency/timestep of the time series.

Returns inferred frequency string (e.g., 'h', '30min', '15min') or None.

#### Function: `normalize_unit`
- **Parameters:** `value, from_unit, to_unit`
- **Returns:** `float`
- **What it does:** Normalize power units.

Supports: W, kW, MW, GW, Wh, kWh, MWh, GWh

#### Function: `check_continuity`
- **Parameters:** `datetime_index, max_gap_hours`
- **Returns:** `Tuple[bool, list]`
- **What it does:** Check for temporal continuity and detect gaps > max_gap_hours.

Returns (is_continuous, gaps_list)
where gaps_list is a list of (gap_start, gap_end, gap_duration_hours) tuples.

### File: `services/curve_standardizer/resampler.py`
**Type:** Python Module

#### Function: `resample_curve`
- **Parameters:** `df, target_timestep, method`
- **Returns:** `Tuple[pd.DataFrame, str]`
- **What it does:** Resample a production curve to target timestep.

Args:
    df: DataFrame with DatetimeIndex and 'value' column
    target_timestep: 'PT15M' (15min), 'PT30M' (30min), or 'PT60M' (60min)
    method: 'auto' = aggregate if coarser, interpolate if finer
           'aggregate' = sum values (for energy) or mean (for power)
           'interpolate' = linear interpolation

Returns:
    Tuple of (resampled_df, method_used)

#### Function: `aggregate_curve`
- **Parameters:** `df, freq`
- **Returns:** `pd.DataFrame`
- **What it does:** Aggregate curve to coarser frequency (sum values).

Useful for converting high-frequency data to hourly or 30-min.

#### Function: `interpolate_curve`
- **Parameters:** `df, freq`
- **Returns:** `pd.DataFrame`
- **What it does:** Interpolate curve to finer frequency (linear).

Useful for converting hourly data to 15-min or 30-min.

### File: `services/curve_standardizer/test_debug_parser.py`
**Type:** Python Module

### File: `services/curve_standardizer/test_curve_import.py`
**Type:** Python Module


---

## Module: Utils
### File: `utils/helpers.py`
**Type:** Python Module

#### Function: `get_coordinates_from_address`
- **Parameters:** `commune`
- **Returns:** `dict`
- **What it does:** Retrieve coordinates from mock geographic database.

#### Function: `get_coordinates_from_postal_code`
- **Parameters:** `postal_code`
- **Returns:** `dict`
- **What it does:** Retrieve coordinates from postal code using Nominatim API (OpenStreetMap).
Results are cached for 1 hour to minimize API calls.

Args:
    postal_code: French postal code (5 digits)

Returns:
    dict with keys: lat, lng, city, epci

#### Function: `render_banner_with_navigation`
- **Parameters:** `current_page, banner_content`
- **Returns:** `None explicitly annotated`
- **What it does:** Render left banner (1/4) with navigation structure, buttons, and project info.

#### Function: `render_page_header_with_banner`
- **Parameters:** `title, banner_content`
- **Returns:** `None explicitly annotated`
- **What it does:** Render page with expandable banner (1/4) and title + content area (3/4).

#### Function: `init_session_state`
- **Parameters:** ``
- **Returns:** `None explicitly annotated`
- **What it does:** No docstring provided.

#### Function: `render_navigation_footer`
- **Parameters:** `current_page`
- **Returns:** `None explicitly annotated`
- **What it does:** Render Previous/Next navigation buttons at page bottom.

#### Function: `process_actors_file`
- **Parameters:** `uploaded_file, actor_type`
- **Returns:** `None explicitly annotated`
- **What it does:** No docstring provided.

#### Function: `_save_bytes_to_path`
- **Parameters:** `b, path`
- **Returns:** `None explicitly annotated`
- **What it does:** No docstring provided.

#### Function: `process_curves_files`
- **Parameters:** `uploaded_files, actor_type, subdir`
- **Returns:** `None explicitly annotated`
- **What it does:** No docstring provided.

#### Function: `render_actor_list`
- **Parameters:** `df, actor_type, curves_dir`
- **Returns:** `None explicitly annotated`
- **What it does:** No docstring provided.

#### Function: `render_actor_block`
- **Parameters:** `block_title, actor_type, curves_subdir`
- **Returns:** `None explicitly annotated`
- **What it does:** Reusable actor block: upload actors and curves, show list.


---

## Module: State
### File: `state/init_state.py`
**Type:** Python Module

#### Function: `init_session_state`
- **Parameters:** ``
- **Returns:** `None explicitly annotated`
- **What it does:** Initialize Streamlit session_state with standard keys and defaults.


---
