import fiona

gpkg_path = "input_data/urban_ctm12_anonymized.gpkg"

layers = fiona.listlayers(gpkg_path)

urban_ctm12_layers = [
    layer for layer in layers
    if layer.startswith("U_") and layer.endswith("_CTM12")
]

print("Urban CTM12 Layers Found:")
for layer in urban_ctm12_layers:
    print("-", layer)

print("\nTotal:", len(urban_ctm12_layers))