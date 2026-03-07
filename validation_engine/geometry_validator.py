"""
geometry_validator.py
---------------------
Geometry validation for urban cadastral layers under the LADM-COL / CTM12 standard.
Detects: invalid geometries, null geometries, empty geometries, and zero-area polygons.
"""

import geopandas as gpd
import pandas as pd


def validate_geometry(gdf: gpd.GeoDataFrame, layer_name: str) -> gpd.GeoDataFrame:
    """
    Run all geometry checks on a CTM12 layer.

    Checks performed:
    - Invalid geometries (self-intersections, malformed rings)
    - Null geometries (missing geometry value)
    - Empty geometries (geometry object exists but has no coordinates)
    - Zero-area polygons (degenerate features)

    Parameters
    ----------
    gdf : GeoDataFrame
        Layer to validate.
    layer_name : str
        CTM12 layer name — used for reporting.

    Returns
    -------
    GeoDataFrame with all detected geometry errors,
    including 'error_type' and 'layer' columns.
    """
    errors = []

    # 1. Null geometries
    null_mask = gdf.geometry.isna()
    if null_mask.any():
        null_geoms = gdf[null_mask].copy()
        null_geoms["error_type"] = "null_geometry"
        null_geoms["layer"] = layer_name
        errors.append(null_geoms)

    # Work only on non-null geometries for remaining checks
    valid_gdf = gdf[~null_mask].copy()

    # 2. Empty geometries
    empty_mask = valid_gdf.geometry.is_empty
    if empty_mask.any():
        empty_geoms = valid_gdf[empty_mask].copy()
        empty_geoms["error_type"] = "empty_geometry"
        empty_geoms["layer"] = layer_name
        errors.append(empty_geoms)

    # Work only on non-empty geometries for remaining checks
    non_empty_gdf = valid_gdf[~empty_mask].copy()

    # 3. Invalid geometries (self-intersections, malformed rings)
    invalid_mask = ~non_empty_gdf.geometry.is_valid
    if invalid_mask.any():
        invalid_geoms = non_empty_gdf[invalid_mask].copy()
        invalid_geoms["error_type"] = "invalid_geometry"
        invalid_geoms["layer"] = layer_name
        errors.append(invalid_geoms)

    # 4. Zero-area polygons (only for polygon layers)
    geom_type = non_empty_gdf.geometry.geom_type.iloc[0] if len(non_empty_gdf) > 0 else ""
    if "Polygon" in geom_type or "polygon" in geom_type:
        zero_area_mask = non_empty_gdf.geometry.area == 0
        if zero_area_mask.any():
            zero_area_geoms = non_empty_gdf[zero_area_mask].copy()
            zero_area_geoms["error_type"] = "zero_area_polygon"
            zero_area_geoms["layer"] = layer_name
            errors.append(zero_area_geoms)

    if errors:
        result = gpd.GeoDataFrame(
            pd.concat(errors, ignore_index=True),
            crs=gdf.crs
        )
        return result

    return gpd.GeoDataFrame(
        columns=["geometry", "error_type", "layer"],
        crs=gdf.crs
    )


def summarize_geometry_errors(gdf: gpd.GeoDataFrame) -> dict:
    """
    Summarize geometry errors by type.

    Parameters
    ----------
    gdf : GeoDataFrame
        Output from validate_geometry().

    Returns
    -------
    dict with error type counts:
        null_geometry     : int
        empty_geometry    : int
        invalid_geometry  : int
        zero_area_polygon : int
        total             : int
    """
    if gdf.empty or "error_type" not in gdf.columns:
        return {
            "null_geometry": 0,
            "empty_geometry": 0,
            "invalid_geometry": 0,
            "zero_area_polygon": 0,
            "total": 0,
        }

    counts = gdf["error_type"].value_counts().to_dict()
    return {
        "null_geometry":     counts.get("null_geometry", 0),
        "empty_geometry":    counts.get("empty_geometry", 0),
        "invalid_geometry":  counts.get("invalid_geometry", 0),
        "zero_area_polygon": counts.get("zero_area_polygon", 0),
        "total":             len(gdf),
    }