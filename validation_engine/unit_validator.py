"""
unit_validator.py
-----------------
Overlap validation for U_UNIDAD_CTM12 following the LADM-COL / CTM12 model.

Business rule:
    Units (U_UNIDAD) within the same construction (CONSTRUCCION_CODIGO) CAN
    share the same spatial footprint — this is expected when different units
    occupy different floors of the same building.

    An overlap IS an error only when two units share BOTH:
      - The same CONSTRUCCION_CODIGO
      - The same PLANTA (floor)

    Units on different floors sharing a footprint are valid and must NOT
    be flagged as errors.
"""

import geopandas as gpd
import pandas as pd


def validate_unit_overlaps_by_construction(
    units_gdf: gpd.GeoDataFrame,
    min_area: float = 0.1,
) -> gpd.GeoDataFrame:
    """
    Detect overlapping U_UNIDAD features that share the same construction
    AND the same floor (PLANTA).

    Units on different floors sharing a spatial footprint are valid in
    the LADM-COL model and are excluded from results.

    Parameters
    ----------
    units_gdf : GeoDataFrame
        U_UNIDAD_CTM12 layer.
    min_area : float
        Minimum overlap area in m² to report (default: 0.1 m²).

    Returns
    -------
    GeoDataFrame with overlap geometries and context columns:
        - CONSTRUCCION_CODIGO : construction the units belong to
        - PLANTA              : shared floor where the overlap occurs
        - UNIDAD_1            : CODIGO of first unit
        - UNIDAD_2            : CODIGO of second unit
        - overlap_area        : area of the intersection in m²
        - error_type          : "same_floor_overlap"
    """
    error_list = []

    # Remove null geometries
    units_gdf = units_gdf[~units_gdf.geometry.isna()].copy()

    # Group by CONSTRUCCION_CODIGO and PLANTA — only same floor units compete
    grouped = units_gdf.groupby(["CONSTRUCCION_CODIGO", "PLANTA"])

    for (construccion_id, planta), group in grouped:

        if len(group) < 2:
            continue

        group = group.reset_index(drop=True)
        sindex = group.sindex

        for idx, row in group.iterrows():
            possible_matches_index = list(
                sindex.intersection(row.geometry.bounds)
            )

            for match_idx in possible_matches_index:

                if idx >= match_idx:
                    continue

                other_geom = group.loc[match_idx, "geometry"]

                if row.geometry.intersects(other_geom):
                    intersection = row.geometry.intersection(other_geom)

                    if intersection.area > min_area:
                        error_list.append({
                            "CONSTRUCCION_CODIGO": construccion_id,
                            "PLANTA": planta,
                            "UNIDAD_1": row["CODIGO"],
                            "UNIDAD_2": group.loc[match_idx, "CODIGO"],
                            "overlap_area": round(intersection.area, 4),
                            "error_type": "same_floor_overlap",
                            "geometry": intersection,
                        })

    if not error_list:
        return gpd.GeoDataFrame(
            columns=["CONSTRUCCION_CODIGO", "PLANTA", "UNIDAD_1",
                     "UNIDAD_2", "overlap_area", "error_type", "geometry"],
            geometry="geometry",
            crs=units_gdf.crs
        )

    return gpd.GeoDataFrame(
        error_list,
        geometry="geometry",
        crs=units_gdf.crs
    )