import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point

def save_to_shapefile(headland_passes, tracks, intersections, output_filename):
    """
    Saves the generated passes, tracks, and intersections into a shapefile.
    This method ensures all geometries are valid before saving.
    """
    # Combine all geometries into one list
    all_geometries = []

    # Add headland passes (LineStrings)
    for pass_ in headland_passes:
        if isinstance(pass_, LineString):
            all_geometries.append(pass_)

    # Add tracks (LineStrings)
    for track in tracks:
        if isinstance(track, LineString):
            all_geometries.append(track)

    # Add intersections (Points)
    for intersection in intersections:
        if isinstance(intersection, Point):
            all_geometries.append(intersection)

    # Create a GeoDataFrame
    gdf = gpd.GeoDataFrame(geometry=all_geometries)

    # Set the CRS (Coordinate Reference System) to WGS84 (EPSG:4326)
    gdf.set_crs("EPSG:4326", allow_override=True, inplace=True)

    # Save the GeoDataFrame to a shapefile
    gdf.to_file(output_filename, driver="ESRI Shapefile")

def main():
    # Example Inputs:
    field_coords = [(43.555830, 27.826090), (43.555775, 27.826100), (43.555422, 27.826747),
                    (43.555425, 27.826786), (43.556182, 27.827557), (43.556217, 27.827538),
                    (43.556559, 27.826893), (43.556547, 27.826833)]
    field_polygon = Polygon(field_coords)  # Create polygon from coordinates
    operating_width = 2  # Mower operating width in meters
    num_headland_passes = 2  # Example number of headland passes
    driving_direction = 'long'  # 'long' for touchline direction, 'short' for goal line
    
    # Step 1: Load inputs and create field polygon
    # (This is already done above with field_polygon)

    # Step 2: Generate headland passes
    headland_passes = generate_headland_passes(field_polygon, operating_width, num_headland_passes)

    # Step 3: Generate tracks parallel to the driving direction
    tracks = generate_tracks(field_polygon, driving_direction, operating_width)

    # Step 4: Find intersections between tracks and headland passes
    intersections = find_intersections(headland_passes, tracks)

    # Step 5: Save generated waypoints to shapefile
    save_to_shapefile(headland_passes, tracks, intersections, "output_field.shp")

if __name__ == "__main__":
    main()
