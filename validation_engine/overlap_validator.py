import geopandas as gpd

def validate_overlaps(gdf, layer_name, min_area=0.10):

    gdf = gdf.reset_index(drop=True)

    sindex = gdf.sindex
    overlap_geoms = []

    for idx, geom in enumerate(gdf.geometry):

        possible_matches_index = list(sindex.intersection(geom.bounds))
        possible_matches = gdf.iloc[possible_matches_index]

        for match_idx, match_geom in possible_matches.geometry.items():

            if idx >= match_idx:
                continue

            if geom.intersects(match_geom):
                intersection = geom.intersection(match_geom)

                if not intersection.is_empty and intersection.area > min_area:
                    overlap_geoms.append(intersection)

    
    if overlap_geoms:
        return gpd.GeoDataFrame(geometry=overlap_geoms, crs=gdf.crs)
    else:
        return gpd.GeoDataFrame(columns=["geometry"], crs=gdf.crs)