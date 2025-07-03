import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon, LineString, Point

def generate_headland_passes(field_boundary, operating_width, num_headland_passes):
    """
    Generates headland passes around the outer boundary of the field.
    These will be parallel to the field's boundary and will be offset by the mower's width.
    """
    headland_passes = []
    for i in range(num_headland_passes):
        offset_distance = operating_width * i  # Offset distance for each pass
        headland_pass = field_boundary.parallel_offset(offset_distance, side='left')
        headland_passes.append(headland_pass)
    return headland_passes

def generate_tracks(field_boundary, driving_direction, operating_width):
    """
    Generates tracks that are parallel to the driving direction inside the field.
    """
    tracks = []
    field_bounds = field_boundary.bounds  # Get the bounds of the field
    min_x, min_y, max_x, max_y = field_bounds
    
    # Depending on the driving direction, generate tracks (parallel to the long axis or short axis)
    if driving_direction == 'long':  # Parallel to the long axis (touchline)
        y_start = min_y
        y_end = max_y
        while y_start < y_end:
            track = LineString([(min_x, y_start), (max_x, y_start)])
            tracks.append(track)
            y_start += operating_width  # Increment by the mower width
    else:  # Parallel to the short axis (goal line)
        x_start = min_x
        x_end = max_x
        while x_start < x_end:
            track = LineString([(x_start, min_y), (x_start, max_y)])
            tracks.append(track)
            x_start += operating_width  # Increment by the mower width
    return tracks

def find_intersections(headland_passes, tracks):
    """
    Find intersections between headland passes and the generated tracks.
    """
    intersections = []
    for track in tracks:
        for pass_ in headland_passes:
            if track.intersects(pass_):
                intersection_point = track.intersection(pass_)
                intersections.append(intersection_point)
    return intersections

def save_to_shapefile(headland_passes, tracks, intersections, output_filename):
    """
    Saves the generated passes, tracks, and intersections into a shapefile.
    """
    all_geometries = headland_passes + tracks + intersections
    gdf = gpd.GeoDataFrame(geometry=all_geometries)
    gdf.to_file(output_filename)

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
