import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point
import pyproj
import simplekml
from io import BytesIO

# Helper functions

def latlon_to_utm(lat, lon):
    """Convert lat/lon to UTM (returns easting, northing, zone number, zone letter)."""
    proj_utm = pyproj.Proj(proj='utm', zone=33, ellps='WGS84')  # You might want to dynamically select zone
    easting, northing = proj_utm(lon, lat)
    return easting, northing

def utm_to_latlon(easting, northing):
    proj_utm = pyproj.Proj(proj='utm', zone=33, ellps='WGS84')
    lon, lat = proj_utm(easting, northing, inverse=True)
    return lat, lon

def generate_grass_cutting_waypoints(boundary_utm, operating_width, driving_direction=0):
    """
    Simplified grass cutting waypoint generator.
    boundary_utm: Polygon in UTM coords
    operating_width: mower width (m)
    driving_direction: angle in degrees to driving direction line (0 = along X axis)
    Returns: list of LineStrings representing tracks
    """
    minx, miny, maxx, maxy = boundary_utm.bounds
    
    # rotate polygon to align driving direction with X axis
    from shapely.affinity import rotate, translate
    
    rotated_poly = rotate(boundary_utm, -driving_direction, origin='centroid', use_radians=False)
    bounds = rotated_poly.bounds
    
    # Generate parallel lines inside polygon spaced by operating width
    tracks = []
    y = bounds[1]
    while y < bounds[3]:
        line = LineString([(bounds[0], y), (bounds[2], y)])
        intersect = line.intersection(rotated_poly)
        if not intersect.is_empty:
            # Keep only line or multiline segments inside polygon
            if intersect.geom_type == 'LineString':
                tracks.append(intersect)
            elif intersect.geom_type == 'MultiLineString':
                tracks.extend(list(intersect))
        y += operating_width
    
    # Rotate back the tracks
    tracks = [rotate(track, driving_direction, origin='centroid', use_radians=False) for track in tracks]
    return tracks

def create_kml_from_tracks(tracks, zone=33):
    kml = simplekml.Kml()
    for idx, track in enumerate(tracks):
        coords = []
        for x, y in list(track.coords):
            # convert UTM back to lat/lon
            lat, lon = utm_to_latlon(x, y)
            coords.append((lon, lat))
        ls = kml.newlinestring(name=f'Track {idx+1}', coords=coords)
        ls.style.linestyle.width = 2
        ls.style.linestyle.color = simplekml.Color.blue
    return kml.kml()

# Streamlit app

st.title("Football Field Robotics: Waypoint Generator")

st.markdown("""
Enter the **boundary coordinates** of the grass field (lat, lon) as CSV or paste below.
Example for a rectangle (lat, lon per line, comma separated):
