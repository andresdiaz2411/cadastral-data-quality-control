import fiona

gpkg_path = "input_data/urban_ctm12_anonymized.gpkg"

layers = fiona.listlayers(gpkg_path)

print("Number of layers:", len(layers))
print("\nLayers found:")

for layer in layers:
    print("-", layer)

with fiona.open("input_data/urban_ctm12_anonymized.gpkg", layer="U_TERRENO_CTM12") as src:
    print("Geometry type:", src.schema["geometry"])
    print("Fields:", src.schema["properties"])