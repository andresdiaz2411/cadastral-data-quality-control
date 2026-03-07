import geopandas as gpd
import os
import pandas as pd

from validation_engine.geometry_validator import validate_geometry, summarize_geometry_errors
from validation_engine.overlap_validator import validate_overlaps
from validation_engine.hierarchy_validator import validate_hierarchy, validate_within_percentage
from validation_engine.unit_validator import validate_unit_overlaps_by_construction
from validation_engine.attribute_validator import validate_attributes, validate_referential_integrity
from validation_engine.duplicate_validator import validate_duplicates, summarize_duplicates
from validation_engine.report_builder import ReportBuilder

# -----------------------------
# PROJECT CONFIGURATION
# -----------------------------

GPKG_PATH = "input_data/urban_ctm12_anonymized.gpkg"
PROJECT_STAGE = "initial"  # options: initial | preliminary | final

def get_overlap_threshold(stage):
    thresholds = {"initial": 0.10, "preliminary": 0.02, "final": 0.0001}
    return thresholds.get(stage, 0.10)

OVERLAP_THRESHOLD = get_overlap_threshold(PROJECT_STAGE)
OUTPUT_GPKG        = "outputs/output_errors.gpkg"
OUTPUT_CSV         = "outputs/quality_report.csv"
OUTPUT_SUMMARY_CSV = "outputs/quality_summary.csv"

LAYERS_TO_VALIDATE = [
    "U_TERRENO_CTM12",
    "U_CONSTRUCCION_CTM12",
    "U_UNIDAD_CTM12",
    "U_MANZANA_CTM12",
]

print("=" * 55)
print(" CADASTRAL DATA QUALITY CONTROL — CTM12 / LADM-COL")
print("=" * 55)
print(f" Project stage     : {PROJECT_STAGE.upper()}")
print(f" Overlap threshold : {OVERLAP_THRESHOLD} m²")
print("=" * 55)

data = {}
for layer in LAYERS_TO_VALIDATE:
    print(f"Loading {layer}...")
    data[layer] = gpd.read_file(GPKG_PATH, layer=layer)
print("\nAll layers loaded successfully.")

os.makedirs("outputs", exist_ok=True)
if os.path.exists(OUTPUT_GPKG):
    os.remove(OUTPUT_GPKG)

builder = ReportBuilder(project_stage=PROJECT_STAGE, overlap_threshold=OVERLAP_THRESHOLD)

# -----------------------------
# GEOMETRY VALIDATION
# -----------------------------
print("\n" + "─" * 55)
print(" GEOMETRY VALIDATION")
print("─" * 55)

for layer in LAYERS_TO_VALIDATE:
    result = validate_geometry(data[layer], layer)
    summary = summarize_geometry_errors(result)
    print(f"{layer}")
    print(f"  Invalid geometries  : {summary['invalid_geometry']}")
    print(f"  Null geometries     : {summary['null_geometry']}")
    print(f"  Empty geometries    : {summary['empty_geometry']}")
    print(f"  Zero-area polygons  : {summary['zero_area_polygon']}")
    builder.add_geometry(layer, summary)
    if not result.empty:
        result.to_file(OUTPUT_GPKG, layer=f"geom_{layer}", driver="GPKG")

# -----------------------------
# DUPLICATE VALIDATION
# -----------------------------
print("\n" + "─" * 55)
print(" DUPLICATE CODIGO VALIDATION")
print("─" * 55)

for layer in LAYERS_TO_VALIDATE:
    result = validate_duplicates(data[layer], layer)
    summary = summarize_duplicates(result)
    print(f"{layer:<35} Duplicates: {summary['total_duplicate_features']} "
          f"({summary['unique_duplicate_codes']} unique codes)")
    builder.add_duplicates(layer, result)
    if not result.empty:
        result.to_file(OUTPUT_GPKG, layer=f"dup_{layer}", driver="GPKG")

# -----------------------------
# OVERLAP VALIDATION
# -----------------------------
print("\n" + "─" * 55)
print(" OVERLAP VALIDATION")
print("─" * 55)

for layer in LAYERS_TO_VALIDATE:
    if layer == "U_UNIDAD_CTM12":
        overlaps = validate_unit_overlaps_by_construction(data[layer], min_area=OVERLAP_THRESHOLD)
    else:
        overlaps = validate_overlaps(data[layer], layer, min_area=OVERLAP_THRESHOLD)
    print(f"{layer:<35} Overlaps > {OVERLAP_THRESHOLD} m² : {len(overlaps)}")
    builder.add_overlaps(layer, overlaps)
    if not overlaps.empty:
        overlaps.to_file(OUTPUT_GPKG, layer=f"overlap_{layer}", driver="GPKG")

# -----------------------------
# HIERARCHY VALIDATION
# -----------------------------
print("\n" + "─" * 55)
print(" HIERARCHY VALIDATION")
print("─" * 55)

hierarchy_checks = [
    (data["U_UNIDAD_CTM12"], data["U_CONSTRUCCION_CTM12"],
     "CONSTRUCCION_CODIGO", "CODIGO",
     "U_UNIDAD_CTM12", "U_CONSTRUCCION_CTM12", "unidad_fuera_construccion_pct"),
    (data["U_CONSTRUCCION_CTM12"], data["U_TERRENO_CTM12"],
     "TERRENO_CODIGO", "CODIGO",
     "U_CONSTRUCCION_CTM12", "U_TERRENO_CTM12", "construccion_fuera_terreno_pct"),
    (data["U_TERRENO_CTM12"], data["U_MANZANA_CTM12"],
     "MANZANA_CODIGO", "CODIGO",
     "U_TERRENO_CTM12", "U_MANZANA_CTM12", "terreno_fuera_manzana_pct"),
]

for child, parent, child_field, parent_field, child_name, parent_name, output_name in hierarchy_checks:
    result = validate_within_percentage(child, parent, child_field, parent_field, child_name, parent_name)
    low      = len(result[result["severity"] == "low"])      if not result.empty else 0
    moderate = len(result[result["severity"] == "moderate"])  if not result.empty else 0
    critical = len(result[result["severity"] == "critical"])  if not result.empty else 0
    print(f"{output_name:<40} Total: {len(result)} (low: {low} | moderate: {moderate} | critical: {critical})")
    builder.add_hierarchy(output_name, result)
    if not result.empty:
        result.to_file(OUTPUT_GPKG, layer=output_name, driver="GPKG")

# -----------------------------
# ATTRIBUTE VALIDATION
# -----------------------------
print("\n" + "─" * 55)
print(" ATTRIBUTE VALIDATION")
print("─" * 55)

for layer in LAYERS_TO_VALIDATE:
    results = validate_attributes(data[layer], layer)
    print(f"\n{layer}")
    print(f"  Null mandatory fields       : {len(results['null_fields'])}")
    print(f"  Field length exceeded       : {len(results['field_lengths'])}")
    print(f"  Invalid domain values       : {len(results['domain_values'])}")
    print(f"  Numeric out of range        : {len(results['numeric_ranges'])}")
    print(f"  Null TIPO_CONSTRUCCION      : {len(results['tipo_construccion_nulls'])}")
    if layer == "U_UNIDAD_CTM12":
        print(f"  Null PLANTA                 : {len(results['planta_nulls'])}")
        print(f"  Invalid PLANTA format       : {len(results['planta_invalid_format'])}")
    builder.add_attributes(layer, results)
    for error_type, gdf in results.items():
        if not isinstance(gdf, gpd.GeoDataFrame):
            continue
        if not gdf.empty and "geometry" in gdf.columns:
            gdf.to_file(OUTPUT_GPKG, layer=f"attr_{error_type}_{layer}"[:63], driver="GPKG")

# -----------------------------
# REFERENTIAL INTEGRITY
# -----------------------------
print("\n" + "─" * 55)
print(" REFERENTIAL INTEGRITY")
print("─" * 55)

ref_checks = [
    (data["U_CONSTRUCCION_CTM12"], data["U_TERRENO_CTM12"],
     "TERRENO_CODIGO", "CODIGO",
     "U_CONSTRUCCION_CTM12", "U_TERRENO_CTM12", "ref_construccion_sin_terreno"),
    (data["U_UNIDAD_CTM12"], data["U_CONSTRUCCION_CTM12"],
     "CONSTRUCCION_CODIGO", "CODIGO",
     "U_UNIDAD_CTM12", "U_CONSTRUCCION_CTM12", "ref_unidad_sin_construccion"),
    (data["U_UNIDAD_CTM12"], data["U_TERRENO_CTM12"],
     "TERRENO_CODIGO", "CODIGO",
     "U_UNIDAD_CTM12", "U_TERRENO_CTM12", "ref_unidad_sin_terreno"),
    (data["U_TERRENO_CTM12"], data["U_MANZANA_CTM12"],
     "MANZANA_CODIGO", "CODIGO",
     "U_TERRENO_CTM12", "U_MANZANA_CTM12", "ref_terreno_sin_manzana"),
]

for child, parent, child_field, parent_field, child_name, parent_name, output_name in ref_checks:
    result = validate_referential_integrity(child, parent, child_field, parent_field, child_name, parent_name)
    print(f"  {output_name:<40} Orphaned records: {len(result)}")
    builder.add_referential(output_name, result)
    if not result.empty:
        result.to_file(OUTPUT_GPKG, layer=output_name, driver="GPKG")

# -----------------------------
# EXPORT REPORTS
# -----------------------------
print("\n" + "─" * 55)

df_detail, df_summary = builder.build()
global_kpis = builder.global_summary()

df_detail.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
df_summary.to_csv(OUTPUT_SUMMARY_CSV, index=False, encoding="utf-8")

print(f"\n Detail report exported   : {OUTPUT_CSV}")
print(f" Summary report exported  : {OUTPUT_SUMMARY_CSV}")
print(f" Error geometries exported: {OUTPUT_GPKG}")
print(f"\n Total errors found       : {global_kpis.get('total_errors', 0)}")
print(f"   Critical                  : {global_kpis.get('total_critical', 0)}")
print(f"   Moderate               : {global_kpis.get('total_moderate', 0)}")
print(f"   Low                   : {global_kpis.get('total_low', 0)}")
print(f"\n Layers with errors       : {global_kpis.get('layers_with_errors', 0)}")
print("\n Validation process completed successfully.")
print("=" * 55)