import geopandas as gpd
import pandas as pd

# Load data
gdf = gpd.read_file("../data/cadastral_sample.geojson")

results = []

# 1. Check missing owner
gdf["missing_owner"] = gdf["owner"] == ""

# 2. Check minimum area (threshold = 300 m2)
gdf["area_below_threshold"] = gdf["area_m2"] < 300

# 3. Check invalid geometries
gdf["invalid_geometry"] = ~gdf.is_valid

# 4. Check overlapping parcels
gdf["overlaps"] = False

for i in range(len(gdf)):
    for j in range(len(gdf)):
        if i != j:
            if gdf.geometry[i].intersects(gdf.geometry[j]):
                gdf.at[i, "overlaps"] = True

# Export report
report = gdf[[
    "parcel_id",
    "missing_owner",
    "area_below_threshold",
    "invalid_geometry",
    "overlaps"
]]

report.to_csv("../outputs/validation_report.csv", index=False)

print("Validation completed. Report generated.")
