"""
generate_sample_gpkg.py
-----------------------
Generates a lightweight sample GeoPackage (sample_errors.gpkg) from the
full output_errors.gpkg for Streamlit Cloud deployment.

Strategy:
  - Geometry layers    : all features (few, lightweight)
  - Duplicate layers   : all features (few, lightweight)
  - Overlap layers     : sample of MAX_SAMPLE features
  - Hierarchy layers   : sample of MAX_SAMPLE features
  - Attribute layers   : sample of MAX_SAMPLE features
  - Referential layers : sample of MAX_SAMPLE features

Target size: ~5-15 MB (suitable for GitHub and fast map loading)

Usage:
    python generate_sample_gpkg.py
"""

import geopandas as gpd
import fiona
import os

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

INPUT_GPKG  = "outputs/output_errors.gpkg"
OUTPUT_GPKG = "outputs/sample_errors.gpkg"
MAX_SAMPLE  = 500   # max features per large layer

# Layers to keep in full (small layers)
FULL_LAYERS = [
    "geom",   # geometry errors — always few features
    "dup",    # duplicate errors — always few features
]

# ---------------------------------------------------
# MAIN
# ---------------------------------------------------

def should_keep_full(layer_name: str) -> bool:
    return any(layer_name.startswith(prefix) for prefix in FULL_LAYERS)


def main():
    if not os.path.exists(INPUT_GPKG):
        print(f"ERROR: {INPUT_GPKG} not found. Run main.py first.")
        return

    layers = fiona.listlayers(INPUT_GPKG)
    print(f"Found {len(layers)} layers in {INPUT_GPKG}\n")

    # Remove existing output
    if os.path.exists(OUTPUT_GPKG):
        os.remove(OUTPUT_GPKG)

    total_in  = 0
    total_out = 0

    for layer in layers:
        try:
            gdf = gpd.read_file(INPUT_GPKG, layer=layer)

            if gdf.empty:
                print(f"  SKIP  {layer:<50} (empty)")
                continue

            n_in = len(gdf)

            if should_keep_full(layer):
                sample = gdf
                label = "full"
            else:
                sample = gdf.sample(
                    n=min(MAX_SAMPLE, len(gdf)),
                    random_state=42
                )
                label = f"sample {len(sample)}/{n_in}"

            sample.to_file(OUTPUT_GPKG, layer=layer, driver="GPKG")

            total_in  += n_in
            total_out += len(sample)

            print(f"  OK    {layer:<50} {label}")

        except Exception as e:
            print(f"  ERROR {layer:<50} {e}")

    # Report output size
    size_mb = os.path.getsize(OUTPUT_GPKG) / (1024 * 1024)

    print(f"\n{'─'*60}")
    print(f"  Input features  : {total_in:,}")
    print(f"  Output features : {total_out:,}")
    print(f"  Output file     : {OUTPUT_GPKG}")
    print(f"  Output size     : {size_mb:.1f} MB")
    print(f"{'─'*60}")

    if size_mb > 95:
        print("\n  WARNING: File exceeds 95 MB — reduce MAX_SAMPLE before pushing to GitHub.")
    elif size_mb > 50:
        print("\n  NOTE: File is over 50 MB — GitHub will warn but allow it.")
    else:
        print("\n  Ready to push to GitHub.")


if __name__ == "__main__":
    main()
