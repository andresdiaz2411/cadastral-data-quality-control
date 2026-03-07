"""
inspect_schema.py
-----------------
Exports the complete field schema of all CTM12 layers in a GeoPackage
to a CSV file for documentation and attribute validation planning.

Output: schema_reference/layer_schema.csv
"""

import fiona
import pandas as pd
import os

# ---------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------

GPKG_PATH = "input_data/urban_ctm12_anonymized.gpkg"
OUTPUT_DIR = "schema_reference"
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "layer_schema.csv")

# ---------------------------------------------------
# EXTRACT SCHEMA
# ---------------------------------------------------

os.makedirs(OUTPUT_DIR, exist_ok=True)

layers = fiona.listlayers(GPKG_PATH)
ctm12_layers = [l for l in layers if l.startswith("U_") and l.endswith("_CTM12")]

print(f"CTM12 layers found: {len(ctm12_layers)}\n")

rows = []

for layer_name in ctm12_layers:
    with fiona.open(GPKG_PATH, layer=layer_name) as src:
        geom_type = src.schema["geometry"]
        try:
            crs = src.crs.to_epsg() or str(src.crs)
        except Exception:
            crs = str(src.crs) if src.crs else "Unknown"
        feature_count = len(src)

        print(f"{'─'*50}")
        print(f"Layer     : {layer_name}")
        print(f"Geometry  : {geom_type}")
        print(f"CRS       : {crs}")
        print(f"Features  : {feature_count}")
        print(f"Fields    :")

        for field_name, field_type in src.schema["properties"].items():
            print(f"  - {field_name:<35} {field_type}")

            rows.append({
                "layer": layer_name,
                "geometry_type": geom_type,
                "crs": crs,
                "feature_count": feature_count,
                "field_name": field_name,
                "field_type": field_type,
            })

print(f"\n{'─'*50}")

# ---------------------------------------------------
# EXPORT TO CSV
# ---------------------------------------------------

df = pd.DataFrame(rows)
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

print(f"\nSchema exported to: {OUTPUT_CSV}")
print(f"Total fields documented: {len(df)}")
print(f"Layers documented: {df['layer'].nunique()}")