import geopandas as gpd

def validate_hierarchy(data):

    results = {}

    unidades_fuera = data["U_UNIDAD_CTM12"][
        ~data["U_UNIDAD_CTM12"].within(
            data["U_CONSTRUCCION_CTM12"].unary_union
        )
    ]

    print(f"U_UNIDAD_CTM12 outside U_CONSTRUCCION_CTM12: {len(unidades_fuera)}")

    results["unidad_fuera_construccion"] = unidades_fuera


    construccion_fuera = data["U_CONSTRUCCION_CTM12"][
        ~data["U_CONSTRUCCION_CTM12"].within(
            data["U_TERRENO_CTM12"].unary_union
        )
    ]

    print(f"U_CONSTRUCCION_CTM12 outside U_TERRENO_CTM12: {len(construccion_fuera)}")

    results["construccion_fuera_terreno"] = construccion_fuera


    terreno_fuera = data["U_TERRENO_CTM12"][
        ~data["U_TERRENO_CTM12"].within(
            data["U_MANZANA_CTM12"].unary_union
        )
    ]

    print(f"U_TERRENO_CTM12 outside U_MANZANA_CTM12: {len(terreno_fuera)}")

    results["terreno_fuera_manzana"] = terreno_fuera

    return results

import geopandas as gpd
import pandas as pd

def validate_within_percentage(child_gdf, parent_gdf,
                               child_code_field,
                               parent_code_field,
                               child_name,
                               parent_name):

    results = []

    # Asegurar que parent tenga códigos únicos
    parent_unique = parent_gdf.drop_duplicates(subset=[parent_code_field])

    merged = child_gdf.merge(
        parent_unique[[parent_code_field, "geometry"]],
        left_on=child_code_field,
        right_on=parent_code_field,
        how="left",
        suffixes=("", "_parent")
    )

    for idx, row in merged.iterrows():

        child_geom = row.geometry
        parent_geom = row.geometry_parent

        if parent_geom is None or pd.isna(parent_geom):
            outside_area = child_geom.area
        else:
            intersection = child_geom.intersection(parent_geom)
            outside_area = child_geom.area - intersection.area

        percentage_outside = (
            (outside_area / child_geom.area) * 100
            if child_geom.area > 0 else 0
        )

        if percentage_outside > 0:

            # 🔥 Clasificación por severidad
            if percentage_outside <= 1:
                severity = "low"
            elif percentage_outside <= 10:
                severity = "moderate"
            else:
                severity = "critical"

            results.append({
                "geometry": child_geom,
                "child_id": idx,
                "child_layer": child_name,
                "parent_layer": parent_name,
                "outside_area": outside_area,
                "percentage_outside": percentage_outside,
                "severity": severity
            })

    result_gdf = gpd.GeoDataFrame(results, crs=child_gdf.crs)
    result_gdf = result_gdf.drop_duplicates(subset=["child_id"])

    return result_gdf