"""
attribute_validator.py
----------------------
Attribute validation for urban cadastral layers under the LADM-COL / CTM12 standard.
Validates: mandatory fields, field length constraints, code format rules,
referential integrity between layers, and domain value checks.

Based on schema extracted from urban_ctm12_anonymized.gpkg (CRS: EPSG:3116)
"""

import geopandas as gpd
import pandas as pd


# ---------------------------------------------------------------------------
# SCHEMA DEFINITION — CTM12 mandatory fields and constraints
# ---------------------------------------------------------------------------

# Fields that must not be null or empty per layer
# Mandatory fields per layer following the LADM-COL / CTM12 standard (IGAC).
# High null counts in the current dataset are expected — this GeoPackage
# is a provisional migration from the previous cadastral model.
# The final dataset will contain all required values.
# These validations are intentionally kept strict to identify
# pending fields before final delivery to IGAC.
MANDATORY_FIELDS = {
    "U_MANZANA_CTM12": [
        "CODIGO", "CODIGO_MUNICIPIO"
    ],
    "U_SECTOR_CTM12": [
        "CODIGO", "CODIGO_MUNICIPIO"
    ],
    "U_TERRENO_CTM12": [
        "CODIGO", "MANZANA_CODIGO", "CODIGO_MUNICIPIO"
    ],
    "U_CONSTRUCCION_CTM12": [
        "CODIGO", "TERRENO_CODIGO", "TIPO_CONSTRUCCION",
        "NUMERO_PISOS", "CODIGO_MUNICIPIO"
    ],
    "U_UNIDAD_CTM12": [
        "CODIGO", "TERRENO_CODIGO", "CONSTRUCCION_CODIGO",
        "PLANTA", "TIPO_CONSTRUCCION", "CODIGO_MUNICIPIO"
    ],
}

# Expected string field lengths (max characters) per layer
FIELD_LENGTH_RULES = {
    "U_MANZANA_CTM12": {
        "CODIGO": 17,
        "BARRIO_CODIGO": 13,
        "CODIGO_MUNICIPIO": 5,
    },
    "U_SECTOR_CTM12": {
        "CODIGO": 9,
        "CODIGO_MUNICIPIO": 5,
    },
    "U_TERRENO_CTM12": {
        "CODIGO": 30,
        "MANZANA_CODIGO": 17,
        "CODIGO_MUNICIPIO": 5,
    },
    "U_CONSTRUCCION_CTM12": {
        "CODIGO": 30,
        "TERRENO_CODIGO": 30,
        "CODIGO_MUNICIPIO": 5,
    },
    "U_UNIDAD_CTM12": {
        "CODIGO": 30,
        "TERRENO_CODIGO": 30,
        "CONSTRUCCION_CODIGO": 30,
        "PLANTA": 5,
        "CODIGO_MUNICIPIO": 5,
    },
}

# Valid domain values per field
# Valid domain values per field.
# PLANTA uses text descriptors — validated by prefix pattern, not exact match.
DOMAIN_VALUES = {
    "U_CONSTRUCCION_CTM12": {
        "TIPO_CONSTRUCCION": ["Convencional", "No Convencional"],
    },
    "U_UNIDAD_CTM12": {
        "TIPO_CONSTRUCCION": ["Convencional", "No Convencional"],
    },
}

# Valid PLANTA prefixes — values use coded format after GDB→GeoPackage migration:
#   PS-XX  → Piso (e.g. PS-01, PS-02)
#   ST-XX  → Sótano (e.g. ST-01)
#   SS-XX  → Semisótano (e.g. SS-01)
#   SB-XX  → Sótano Bajo (e.g. SB-01)
#   MZ-XX  → Mezanine (e.g. MZ-01)
# Invalid examples found in dataset: "01", "1", "A" → flagged as errors
PLANTA_VALID_PREFIXES = ["PS-", "ST-", "SS-", "SB-", "MZ-"]

# Numeric field constraints
NUMERIC_RULES = {
    # NUMERO_PISOS min=1 — a construction must have at least 1 floor.
    # Values of 0 indicate incomplete migration from the previous cadastral model.
    # These will be errors in the final LADM-COL dataset.
    "U_CONSTRUCCION_CTM12": {
        "NUMERO_PISOS": {"min": 1, "max": 163},
        "NUMERO_SOTANOS": {"min": 0, "max": 50},
        "NUMERO_MEZANINES": {"min": 0, "max": 50},
        "NUMERO_SEMISOTANOS": {"min": 0, "max": 50},
    }
}


# ---------------------------------------------------------------------------
# VALIDATORS
# ---------------------------------------------------------------------------

def validate_null_fields(gdf: gpd.GeoDataFrame, layer_name: str) -> gpd.GeoDataFrame:
    """
    Detect features with null or empty values in mandatory fields.
    Returns one row per (feature x field) combination found with errors.

    Parameters
    ----------
    gdf : GeoDataFrame
        Layer to validate.
    layer_name : str
        CTM12 layer name.

    Returns
    -------
    GeoDataFrame with one row per error found,
    including 'error_field' and 'error_type' columns.
    """
    mandatory = MANDATORY_FIELDS.get(layer_name, [])
    if not mandatory:
        return gpd.GeoDataFrame(columns=["geometry", "error_field", "error_type"])

    errors = []

    for field in mandatory:
        if field not in gdf.columns:
            continue

        null_mask = (
            gdf[field].isna() |
            (gdf[field].astype(str).str.strip() == "") |
            (gdf[field].astype(str).str.strip() == "nan") |
            (gdf[field].astype(str).str.strip().str.upper() == "NONE") |
            (gdf[field].astype(str).str.strip().str.upper() == "NULL")
        )

        # Only keep geometry + error columns to avoid duplication
        null_features = gdf.loc[null_mask, ["geometry"]].copy()

        if not null_features.empty:
            null_features["error_field"] = field
            null_features["error_type"] = "null_mandatory_field"
            errors.append(null_features)

    if errors:
        return gpd.GeoDataFrame(
            pd.concat(errors, ignore_index=True),
            crs=gdf.crs
        )

    return gpd.GeoDataFrame(
        columns=["geometry", "error_field", "error_type"],
        crs=gdf.crs
    )


def validate_field_lengths(gdf: gpd.GeoDataFrame, layer_name: str) -> gpd.GeoDataFrame:
    """
    Detect features where string fields exceed the maximum allowed length.

    Parameters
    ----------
    gdf : GeoDataFrame
        Layer to validate.
    layer_name : str
        CTM12 layer name.

    Returns
    -------
    GeoDataFrame with error features, including 'error_field', 'error_type',
    'field_value', and 'max_length' columns.
    """
    length_rules = FIELD_LENGTH_RULES.get(layer_name, {})
    if not length_rules:
        return gpd.GeoDataFrame(columns=["geometry", "error_field", "error_type"])

    errors = []

    for field, max_len in length_rules.items():
        if field not in gdf.columns:
            continue

        mask = gdf[field].dropna().astype(str).str.len() > max_len
        invalid = gdf.loc[mask[mask].index].copy()

        if not invalid.empty:
            invalid["error_field"] = field
            invalid["error_type"] = "field_length_exceeded"
            invalid["field_value"] = invalid[field].astype(str)
            invalid["max_length"] = max_len
            errors.append(invalid)

    if errors:
        return gpd.GeoDataFrame(pd.concat(errors, ignore_index=True), crs=gdf.crs)

    return gpd.GeoDataFrame(columns=gdf.columns.tolist() + ["error_field", "error_type"])


def validate_domain_values(gdf: gpd.GeoDataFrame, layer_name: str) -> gpd.GeoDataFrame:
    """
    Detect features with values outside the allowed domain for controlled fields.

    Parameters
    ----------
    gdf : GeoDataFrame
        Layer to validate.
    layer_name : str
        CTM12 layer name.

    Returns
    -------
    GeoDataFrame with error features, including 'error_field', 'error_type',
    'field_value', and 'allowed_values' columns.
    """
    domain_rules = DOMAIN_VALUES.get(layer_name, {})
    if not domain_rules:
        return gpd.GeoDataFrame(columns=["geometry", "error_field", "error_type"])

    errors = []

    for field, allowed in domain_rules.items():
        if field not in gdf.columns:
            continue

        # Exclude whitespace-only values (handled by null validator)
        non_null = gdf[
            gdf[field].notna() &
            (gdf[field].astype(str).str.strip() != "") &
            (gdf[field].astype(str).str.strip() != "nan")
        ].copy()
        invalid = non_null[~non_null[field].str.strip().isin(allowed)].copy()

        if not invalid.empty:
            invalid["error_field"] = field
            invalid["error_type"] = "invalid_domain_value"
            invalid["field_value"] = invalid[field].astype(str)
            invalid["allowed_values"] = str(allowed)
            errors.append(invalid)

    if errors:
        return gpd.GeoDataFrame(pd.concat(errors, ignore_index=True), crs=gdf.crs)

    return gpd.GeoDataFrame(columns=gdf.columns.tolist() + ["error_field", "error_type"])


def validate_numeric_ranges(gdf: gpd.GeoDataFrame, layer_name: str) -> gpd.GeoDataFrame:
    """
    Detect features with numeric field values outside the allowed range.

    Parameters
    ----------
    gdf : GeoDataFrame
        Layer to validate.
    layer_name : str
        CTM12 layer name.

    Returns
    -------
    GeoDataFrame with error features, including 'error_field', 'error_type',
    'field_value', 'min_allowed', and 'max_allowed' columns.
    """
    numeric_rules = NUMERIC_RULES.get(layer_name, {})
    if not numeric_rules:
        return gpd.GeoDataFrame(columns=["geometry", "error_field", "error_type"])

    errors = []

    for field, bounds in numeric_rules.items():
        if field not in gdf.columns:
            continue

        # Exclude null, whitespace-only, and non-numeric values
        non_null = gdf[
            gdf[field].notna() &
            (gdf[field].astype(str).str.strip() != "") &
            (gdf[field].astype(str).str.strip() != "nan")
        ].copy()

        # Coerce to numeric safely — non-numeric become NaN and are excluded
        numeric_values = pd.to_numeric(non_null[field], errors="coerce")
        non_null = non_null[numeric_values.notna()].copy()
        numeric_values = numeric_values[numeric_values.notna()]

        invalid = non_null[
            (numeric_values < bounds["min"]) | (numeric_values > bounds["max"])
        ].copy()

        if not invalid.empty:
            invalid["error_field"] = field
            invalid["error_type"] = "numeric_out_of_range"
            invalid["field_value"] = invalid[field].astype(str)
            invalid["min_allowed"] = bounds["min"]
            invalid["max_allowed"] = bounds["max"]
            errors.append(invalid)

    if errors:
        return gpd.GeoDataFrame(pd.concat(errors, ignore_index=True), crs=gdf.crs)

    return gpd.GeoDataFrame(columns=gdf.columns.tolist() + ["error_field", "error_type"])


def validate_referential_integrity(
    child_gdf: gpd.GeoDataFrame,
    parent_gdf: gpd.GeoDataFrame,
    child_field: str,
    parent_field: str,
    child_layer: str,
    parent_layer: str,
) -> gpd.GeoDataFrame:
    """
    Detect features in the child layer whose reference code does not exist
    in the parent layer — orphaned records.

    Example: U_CONSTRUCCION.TERRENO_CODIGO must exist in U_TERRENO.CODIGO

    Parameters
    ----------
    child_gdf : GeoDataFrame
        Child layer (e.g. U_CONSTRUCCION_CTM12).
    parent_gdf : GeoDataFrame
        Parent layer (e.g. U_TERRENO_CTM12).
    child_field : str
        Foreign key field in the child layer.
    parent_field : str
        Primary key field in the parent layer.
    child_layer : str
        Child layer name (for reporting).
    parent_layer : str
        Parent layer name (for reporting).

    Returns
    -------
    GeoDataFrame with orphaned features, including 'error_field',
    'error_type', 'missing_reference', 'child_layer', and 'parent_layer' columns.
    """
    if child_field not in child_gdf.columns or parent_field not in parent_gdf.columns:
        return gpd.GeoDataFrame(columns=["geometry", "error_field", "error_type"])

    valid_codes = set(parent_gdf[parent_field].dropna().astype(str).unique())
    child_codes = child_gdf[child_field].astype(str)

    orphaned = child_gdf[~child_codes.isin(valid_codes)].copy()

    if not orphaned.empty:
        orphaned["error_field"] = child_field
        orphaned["error_type"] = "referential_integrity_error"
        orphaned["missing_reference"] = orphaned[child_field].astype(str)
        orphaned["child_layer"] = child_layer
        orphaned["parent_layer"] = parent_layer
        return gpd.GeoDataFrame(orphaned, crs=child_gdf.crs)

    return gpd.GeoDataFrame(
        columns=child_gdf.columns.tolist() + [
            "error_field", "error_type",
            "missing_reference", "child_layer", "parent_layer"
        ]
    )


# ---------------------------------------------------------------------------
# PLANTA — format and null validation (U_UNIDAD_CTM12 only)
# ---------------------------------------------------------------------------

def validate_planta(gdf: gpd.GeoDataFrame, layer_name: str) -> dict:
    """
    Validate the PLANTA field in U_UNIDAD_CTM12.
    Checks for:
      - Null / empty / whitespace-only values
      - Values that do not start with a valid prefix
        (Piso, Mezanine, Sotano, Semisotano)

    Parameters
    ----------
    gdf : GeoDataFrame
        Layer to validate.
    layer_name : str
        CTM12 layer name.

    Returns
    -------
    dict with keys:
        null_count   : int           — features with null/empty PLANTA
        null_records : GeoDataFrame  — features with null/empty PLANTA
        invalid_count   : int           — features with invalid PLANTA format
        invalid_records : GeoDataFrame  — features with invalid PLANTA format
    """
    empty_result = {
        "null_count": 0,
        "null_records": gpd.GeoDataFrame(),
        "invalid_count": 0,
        "invalid_records": gpd.GeoDataFrame(),
    }

    if layer_name != "U_UNIDAD_CTM12" or "PLANTA" not in gdf.columns:
        return empty_result

    # Null / whitespace check
    null_mask = (
        gdf["PLANTA"].isna() |
        (gdf["PLANTA"].astype(str).str.strip() == "") |
        (gdf["PLANTA"].astype(str).str.strip() == "nan") |
        (gdf["PLANTA"].astype(str).str.strip().str.upper() == "NULL")
    )
    null_records = gdf[null_mask][["geometry"]].copy()
    null_records["error_field"] = "PLANTA"
    null_records["error_type"] = "null_planta"

    # Format check — only on non-null values
    non_null = gdf[~null_mask].copy()
    invalid_format_mask = ~non_null["PLANTA"].astype(str).str.strip().apply(
        lambda v: any(v.startswith(prefix) for prefix in PLANTA_VALID_PREFIXES)
    )
    invalid_records = non_null[invalid_format_mask][["geometry"]].copy()
    invalid_records["error_field"] = "PLANTA"
    invalid_records["error_type"] = "invalid_planta_format"
    invalid_records["field_value"] = non_null.loc[invalid_format_mask, "PLANTA"].values

    return {
        "null_count": len(null_records),
        "null_records": gpd.GeoDataFrame(null_records, crs=gdf.crs),
        "invalid_count": len(invalid_records),
        "invalid_records": gpd.GeoDataFrame(invalid_records, crs=gdf.crs),
    }


# ---------------------------------------------------------------------------
# TIPO_CONSTRUCCION — null / empty check
# ---------------------------------------------------------------------------

def validate_tipo_construccion_nulls(
    gdf: gpd.GeoDataFrame,
    layer_name: str,
) -> dict:
    """
    Detect null, empty, or whitespace-only values in TIPO_CONSTRUCCION.
    Only applies to U_CONSTRUCCION_CTM12 and U_UNIDAD_CTM12.

    Parameters
    ----------
    gdf : GeoDataFrame
        Layer to validate.
    layer_name : str
        CTM12 layer name.

    Returns
    -------
    dict with keys:
        count   : int           — number of features with null/empty TIPO_CONSTRUCCION
        records : GeoDataFrame  — features with the error, including 'error_type' column
    """
    applicable_layers = ["U_CONSTRUCCION_CTM12", "U_UNIDAD_CTM12"]

    if layer_name not in applicable_layers or "TIPO_CONSTRUCCION" not in gdf.columns:
        return {"count": 0, "records": gpd.GeoDataFrame()}

    null_mask = (
        gdf["TIPO_CONSTRUCCION"].isna() |
        (gdf["TIPO_CONSTRUCCION"].astype(str).str.strip() == "") |
        (gdf["TIPO_CONSTRUCCION"].astype(str).str.strip().str.upper() == "NONE") |
        (gdf["TIPO_CONSTRUCCION"].astype(str).str.strip().str.upper() == "NULL")
    )

    null_records = gdf[null_mask].copy()
    null_records["error_field"] = "TIPO_CONSTRUCCION"
    null_records["error_type"] = "null_tipo_construccion"

    return {
        "count": len(null_records),
        "records": gpd.GeoDataFrame(null_records, crs=gdf.crs),
    }


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT — run all attribute validations for a layer
# ---------------------------------------------------------------------------

def validate_attributes(
    gdf: gpd.GeoDataFrame,
    layer_name: str,
) -> dict:
    """
    Run all attribute validations for a given CTM12 layer.

    Parameters
    ----------
    gdf : GeoDataFrame
        Layer to validate.
    layer_name : str
        CTM12 layer name.

    Returns
    -------
    dict with keys:
        null_fields        : GeoDataFrame — null/empty mandatory fields
        field_lengths      : GeoDataFrame — fields exceeding max length
        domain_values      : GeoDataFrame — values outside allowed domain
        numeric_ranges     : GeoDataFrame — numeric values out of range
    """
    planta = validate_planta(gdf, layer_name)
    return {
        "null_fields": validate_null_fields(gdf, layer_name),
        "field_lengths": validate_field_lengths(gdf, layer_name),
        "domain_values": validate_domain_values(gdf, layer_name),
        "numeric_ranges": validate_numeric_ranges(gdf, layer_name),
        "tipo_construccion_nulls": validate_tipo_construccion_nulls(gdf, layer_name)["records"],
        "planta_nulls": planta["null_records"],
        "planta_invalid_format": planta["invalid_records"],
    }