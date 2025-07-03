import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point

def generate_headland_passes(field_boundary, operating_width, num_passes):
    """
    Generate headland passes around the outer boundary of the field.
    Each pass is offset from the previous one, moving inward.
    """
    headland_passes = []
    
    # Convert the polygon's exterior boundary to a LineString
    boundary_line = field_boundary.exterior
    
    # Start with the field boundary as the first headland pass
    current_boundary = boundary_line
    for i in range(num_passes):
        # Generate the next pass by offsetting the boundary (parallel offset)
        # 'side' can be 'left' or 'right', we can alternate if necessary
        current_pass = current_boundary.parallel_offset(operating_width, side='left', resolution=16)
        headland_passes.append(current_pass)
        
        # Update the boundary for the next pass (move inward)
        # After applying the offset, we want the next pass to be generated inside
        current_boundary = current_pass

    return headland_passes

def generate_tracks(field_polygon, operating_width, driving_direction):
    """
    Generate mowing tracks parallel to the driving direction (long or short side).
    """
    tracks = []
    # Simplified logic for generating tracks: create lines inside the field polygon
    # based on the chosen driving direction.
    if driving_direction == 'long':
        # Create tracks parallel to the long side (touchline direction)
        pass
    elif driving_direction == 'short':
        # Create tracks parallel to the short side (goal line direction)
        pass
    return tracks

def find_intersections(headland_passes, tracks):
    """
    Find intersections of the generated tracks with the headland passes.
    """
    intersections = []
    for track in tracks:
        for pass_ in headland_passes:
            if track.intersects(pass_):
                intersection = track.intersection(pass_)
                if isinstance(intersection, Point):
                    intersections.append(intersection)
    return intersections

def save_to_shapefile(headland_passes, tracks, intersections, output_filename):
    """
    Saves the generated passes, tracks, and intersections into a shapefile.
    This method ensures all geometries are valid before saving.
    """
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

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(geometry=all_geometries)

    # Set CRS to EPSG:4326 (WGS84)
    gdf.set_crs("EPSG:4326", allow_override=True, inplace=True)

    # Save to shapefile
    gdf.to_file(output_filename, driver="ESRI Shapefile")

def main():
    # Example inputs
    field_coords = [(43.555830, 27.826090), (43.555775, 27.826100), (43.555422, 27.826747),
                    (43.555425, 27.826786), (43.556182, 27.827557), (43.556217, 27.827538),
                    (43.556559, 27.826893), (43.556547, 27.826833)]
    field_polygon = Polygon(field_coords)  # Create polygon from coordinates
    operating_width = 2  # Mower operating width in meters
    num_headland_passes = 2  # Number of headland passes
    driving_direction = 'long'  # Direction for generating tracks (can be 'long' or 'short')

    # Step 1: Generate headland passes
    headland_passes = generate_headland_passes(field_polygon, operating_width, num_headland_passes)

    # Step 2: Generate tracks parallel to the driving direction
    tracks = generate_tracks(field_polygon, operating_width, driving_direction)

    # Step 3: Find intersections between tracks and headland passes
    intersections = find_intersections(headland_passes, tracks)

    # Step 4: Save to shapefile
    save_to_shapefile(headland_passes, tracks, intersections, "output_field.shp")

if __name__ == "__main__":
    main()
