"""
duplicate_validator.py
----------------------
Validates uniqueness of the CODIGO field across CTM12 layers.
In the LADM-COL model, CODIGO must be unique within each layer —
duplicate codes indicate data integrity errors that must be resolved
before final delivery to IGAC.
"""

import geopandas as gpd
import pandas as pd


# Fields that must be unique per layer in the LADM-COL / CTM12 model.
#
# U_CONSTRUCCION_CTM12 and U_UNIDAD_CTM12 are intentionally excluded:
#   - U_CONSTRUCCION: CODIGO is referenced by multiple U_UNIDAD features
#     as a foreign key — duplicate values are expected and valid.
#   - U_UNIDAD: CODIGO is shared across units that belong to the same
#     construction — this is how the LADM-COL model links units to parcels.
#
# For U_UNIDAD, duplicate floor detection is handled separately
# in unit_validator.py (validate_unit_overlaps_by_construction).
UNIQUE_FIELDS = {
    "U_MANZANA_CTM12": ["CODIGO"],
    "U_SECTOR_CTM12":  ["CODIGO"],
    "U_TERRENO_CTM12": ["CODIGO"],
}


def validate_duplicates(
    gdf: gpd.GeoDataFrame,
    layer_name: str,
) -> gpd.GeoDataFrame:
    """
    Detect features with duplicate values in the CODIGO field.

    Parameters
    ----------
    gdf : GeoDataFrame
        Layer to validate.
    layer_name : str
        CTM12 layer name.

    Returns
    -------
    GeoDataFrame with all duplicate features (every occurrence),
    including 'duplicate_field', 'duplicate_value',
    'occurrence_count', and 'error_type' columns.
    """
    unique_fields = UNIQUE_FIELDS.get(layer_name, [])

    if not unique_fields:
        return gpd.GeoDataFrame(
            columns=["geometry", "duplicate_field",
                     "duplicate_value", "occurrence_count", "error_type"]
        )

    errors = []

    for field in unique_fields:
        if field not in gdf.columns:
            continue

        # Exclude null/empty values — handled by attribute validator
        non_null = gdf[
            gdf[field].notna() &
            (gdf[field].astype(str).str.strip() != "") &
            (gdf[field].astype(str).str.strip() != "nan")
        ].copy()

        # Count occurrences per value
        value_counts = non_null[field].value_counts()
        duplicate_values = value_counts[value_counts > 1].index

        if len(duplicate_values) == 0:
            continue

        # Get all features that have a duplicate code
        duplicate_features = non_null[
            non_null[field].isin(duplicate_values)
        ][["geometry", field]].copy()

        duplicate_features["duplicate_field"] = field
        duplicate_features["duplicate_value"] = duplicate_features[field].astype(str)
        duplicate_features["occurrence_count"] = duplicate_features[field].map(value_counts)
        duplicate_features["error_type"] = "duplicate_codigo"
        duplicate_features = duplicate_features.drop(columns=[field])

        errors.append(duplicate_features)

    if errors:
        return gpd.GeoDataFrame(
            pd.concat(errors, ignore_index=True),
            crs=gdf.crs
        )

    return gpd.GeoDataFrame(
        columns=["geometry", "duplicate_field",
                 "duplicate_value", "occurrence_count", "error_type"],
        crs=gdf.crs
    )


def summarize_duplicates(gdf: gpd.GeoDataFrame) -> dict:
    """
    Summarize duplicate validation results.

    Parameters
    ----------
    gdf : GeoDataFrame
        Output from validate_duplicates().

    Returns
    -------
    dict with keys:
        total_duplicate_features : int — total features with duplicate codes
        unique_duplicate_codes   : int — number of distinct duplicated codes
        max_occurrences          : int — highest repetition count found
    """
    if gdf.empty or "duplicate_value" not in gdf.columns:
        return {
            "total_duplicate_features": 0,
            "unique_duplicate_codes": 0,
            "max_occurrences": 0,
        }

    return {
        "total_duplicate_features": len(gdf),
        "unique_duplicate_codes": gdf["duplicate_value"].nunique(),
        "max_occurrences": int(gdf["occurrence_count"].max()),
    }