import streamlit as st
import pandas as pd
from shapely.geometry import Polygon, LineString, Point
from shapely.affinity import rotate
import pyproj
import simplekml
import folium
from streamlit_folium import st_folium

# --- Coordinate conversion helpers ---
def latlon_to_utm(lat, lon, zone_number=33):
    proj_utm = pyproj.Proj(proj='utm', zone=zone_number, ellps='WGS84')
    easting, northing = proj_utm(lon, lat)
    return easting, northing

def utm_to_latlon(easting, northing, zone_number=33):
    proj_utm = pyproj.Proj(proj='utm', zone=zone_number, ellps='WGS84')
    lon, lat = proj_utm(easting, northing, inverse=True)
    return lat, lon

# --- Waypoint generation ---
def generate_grass_cutting_waypoints(polygon_utm, operating_width, driving_direction):
    minx, miny, maxx, maxy = polygon_utm.bounds

    rotated_poly = rotate(polygon_utm, -driving_direction, origin='centroid', use_radians=False)
    bounds = rotated_poly.bounds

    tracks = []
    y = bounds[1]
    while y < bounds[3]:
        line = LineString([(bounds[0], y), (bounds[2], y)])
        intersect = line.intersection(rotated_poly)
        if not intersect.is_empty:
            if intersect.geom_type == 'LineString':
                tracks.append(intersect)
            elif intersect.geom_type == 'MultiLineString':
                tracks.extend(list(intersect))
        y += operating_width

    tracks = [rotate(track, driving_direction, origin='centroid', use_radians=False) for track in tracks]
    return tracks

def generate_lawn_striping_waypoints(polygon_utm, operating_width, pattern, driving_direction):
    # For simplicity, use same as grass cutting with extra step for checkerboard or diagonal
    tracks = generate_grass_cutting_waypoints(polygon_utm, operating_width, driving_direction)

    if pattern == "Checkerboard":
        # add perpendicular tracks
        perp_direction = (driving_direction + 90) % 360
        perp_tracks = generate_grass_cutting_waypoints(polygon_utm, operating_width, perp_direction)
        tracks.extend(perp_tracks)
    elif pattern == "Diagonal":
        diag_direction1 = (driving_direction + 45) % 360
        diag_direction2 = (driving_direction + 135) % 360
        tracks_diag1 = generate_grass_cutting_waypoints(polygon_utm, operating_width, diag_direction1)
        tracks_diag2 = generate_grass_cutting_waypoints(polygon_utm, operating_width, diag_direction2)
        tracks = tracks_diag1 + tracks_diag2
    return tracks

def generate_pitch_marking_waypoints(polygon_utm):
    # Using FIFA standard pitch size (105x68m), centered inside polygon
    # Find polygon centroid to center pitch
    centroid = polygon_utm.centroid
    cx, cy = centroid.x, centroid.y

    lp, wp = 105, 68  # pitch length and width in meters

    # Pitch corners rectangle centered at centroid
    pitch_corners = [
        (cx - lp/2, cy - wp/2),
        (cx - lp/2, cy + wp/2),
        (cx + lp/2, cy + wp/2),
        (cx + lp/2, cy - wp/2),
        (cx - lp/2, cy - wp/2),  # close polygon
    ]

    pitch_polygon = Polygon(pitch_corners)

    # Lines for pitch marking: outline + center line + center circle + penalty areas etc.

    lines = []

    # Outline
    lines.append(LineString(pitch_corners))

    # Center line
    center_line = LineString([(cx, cy - wp/2), (cx, cy + wp/2)])
    lines.append(center_line)

    # Center circle (approximate with points)
    center_circle_points = []
    radius = 9.15
    for angle in range(0, 361, 10):
        x = cx + radius * np.cos(np.radians(angle))
        y = cy + radius * np.sin(np.radians(angle))
        center_circle_points.append((x,y))
    center_circle = LineString(center_circle_points)
    lines.append(center_circle)

    # More markings can be added here similarly: penalty areas, goal boxes, corner arcs

    return lines

# --- KML export ---
def create_kml_from_lines(lines, zone=33):
    kml = simplekml.Kml()
    for i, line in enumerate(lines):
        coords = []
        for x, y in line.coords:
            lat, lon = utm_to_latlon(x, y, zone)
            coords.append((lon, lat))
        ls = kml.newlinestring(name=f'Line {i+1}', coords=coords)
        ls.style.linestyle.width = 2
        ls.style.linestyle.color = simplekml.Color.red
    return kml.kml()

# --- Streamlit UI ---
st.title("Football Field Robotics Waypoint Generator")

st.markdown("""
Input grass field boundary points (latitude, longitude), mower width, select task and generate waypoints with KML export.
""")

coords_text = st.text_area("Paste grass field boundary coordinates (lat, lon each line):", 
"""31.0,29.9
31.0,30.0
31.1,30.0
31.1,29.9
""")

operating_width = st.number_input("Operating width (meters)", min_value=0.1, value=1.0, step=0.1)

task = st.selectbox("Select task", ["Grass Cutting", "Lawn Striping", "Pitch Marking"])

driving_direction = st.slider("Driving direction (degrees from East)", 0, 360, 0)

striping_pattern = None
if task == "Lawn Striping":
    striping_pattern = st.selectbox("Striping pattern", ["Basic", "Checkerboard", "Diagonal"])

import numpy as np

if st.button("Generate Waypoints"):
    try:
        coords = []
        for line in coords_text.strip().split("\n"):
            lat_str, lon_str = line.strip().split(",")
            coords.append((float(lat_str), float(lon_str)))

        if coords[0] != coords[-1]:
            coords.append(coords[0])

        # Convert to UTM (use fixed zone for demo)
        utm_zone = 33
        polygon_utm_points = [latlon_to_utm(lat, lon, utm_zone) for lat, lon in coords]
        polygon_utm = Polygon([(e, n) for e, n, *_ in polygon_utm_points])

        if task == "Grass Cutting":
            tracks = generate_grass_cutting_waypoints(polygon_utm, operating_width, driving_direction)
        elif task == "Lawn Striping":
            pattern = striping_pattern
            if pattern == "Basic":
                pattern = None
            tracks = generate_lawn_striping_waypoints(polygon_utm, operating_width, pattern, driving_direction)
        else:
            tracks = generate_pitch_marking_waypoints(polygon_utm)

        st.success(f"Generated {len(tracks)} tracks/lines.")

        # Display on map with folium
        center_lat = np.mean([pt[0] for pt in coords])
        center_lon = np.mean([pt[1] for pt in coords])
        m = folium.Map(location=[center_lat, center_lon], zoom_start=16)

        # Draw field boundary
        folium.PolyLine(coords, color="green", weight=3, opacity=0.8).add_to(m)

        # Draw tracks
        for track in tracks:
            track_coords_latlon = []
            for x, y in track.coords:
                lat, lon = utm_to_latlon(x, y, utm_zone)
                track_coords_latlon.append((lat, lon))
            folium.PolyLine(track_coords_latlon, color="red", weight=2, opacity=0.7).add_to(m)

        st_folium(m, width=700, height=500)

        # Export KML button
        kml_data = create_kml_from_lines(tracks, zone=utm_zone)
        st.download_button("Download KML", kml_data.encode("utf-8"), "waypoints.kml", "application/vnd.google-earth.kml+xml")

    except Exception as e:
        st.error(f"Error: {e}")
