import streamlit as st
import simplekml
import tempfile
from shapely.geometry import Polygon, LineString
from streamlit_folium import st_folium
import folium

# --- 1. Default boundary (lat, lon) ---

default_field_boundary = [
    (43.699047, 27.840622),
    (43.699011, 27.841512),
    (43.699956, 27.841568),
    (43.699999, 27.840693),
    (43.699047, 27.840622),  # close polygon
]

# Input boundary as editable text area
field_boundary_str = st.text_area(
    "Field boundary coordinates as list of (lat, lon) tuples:",
    value=str(default_field_boundary),
    height=120,
)

import ast

try:
    boundary_coords = ast.literal_eval(field_boundary_str)
except Exception as e:
    st.error(f"Invalid input! Using default coordinates. Error: {e}")
    boundary_coords = default_field_boundary

# --- 2. Input mower width and task ---

mower_width = st.number_input("Operating width of mower (meters)", min_value=0.1, value=1.0, step=0.1)

task = st.selectbox("Select task:", ["Grass Cutting", "Lawn Striping", "Pitch Marking"])

# --- 3. Simplified waypoint generation ---

def generate_waypoints(boundary, width, task):
    """
    Simplified waypoints generation:
    - Grass Cutting: generate parallel lines inside polygon spaced by mower width
    - Lawn Striping: similar to grass cutting but offset by half width for stripes
    - Pitch Marking: draw the polygon vertices as waypoints (simplified)
    """
    polygon = Polygon([(lon, lat) for lat, lon in boundary])  # shapely uses (x,y) = (lon,lat)

    minx, miny, maxx, maxy = polygon.bounds

    waypoints = []

    if task in ["Grass Cutting", "Lawn Striping"]:
        # Generate parallel lines spaced by mower width in lat/lon projection (approximate)
        # We'll do lines parallel to the longer side of polygon bounding box for simplicity
        length_x = maxx - minx
        length_y = maxy - miny

        # Decide direction: if width > height, lines along x (constant lat), else lines along y (constant lon)
        if length_x > length_y:
            # Lines parallel to x axis (varying lat)
            start = miny
            end = maxy
            current = start
            while current <= end:
                line = LineString([(minx, current), (maxx, current)])
                # Clip line with polygon to get actual mowing segment
                clipped = line.intersection(polygon)
                if not clipped.is_empty:
                    if clipped.geom_type == 'MultiLineString':
                        for geom in clipped.geoms:
                            waypoints.append(list(geom.coords))
                    elif clipped.geom_type == 'LineString':
                        waypoints.append(list(clipped.coords))
                current += width * 0.0000089  # rough conversion meters to degrees latitude
        else:
            # Lines parallel to y axis (varying lon)
            start = minx
            end = maxx
            current = start
            while current <= end:
                line = LineString([(current, miny), (current, maxy)])
                clipped = line.intersection(polygon)
                if not clipped.is_empty:
                    if clipped.geom_type == 'MultiLineString':
                        for geom in clipped.geoms:
                            waypoints.append(list(geom.coords))
                    elif clipped.geom_type == 'LineString':
                        waypoints.append(list(clipped.coords))
                current += width * 0.0000113  # rough conversion meters to degrees longitude at this latitude

        # If Lawn Striping, offset lines by half width to create stripes
        if task == "Lawn Striping":
            # Add offset lines in between (very simplified)
            offset = width / 2
            offset_waypoints = []
            if length_x > length_y:
                current = start + offset * 0.0000089
                while current <= end:
                    line = LineString([(minx, current), (maxx, current)])
                    clipped = line.intersection(polygon)
                    if not clipped.is_empty:
                        if clipped.geom_type == 'MultiLineString':
                            for geom in clipped.geoms:
                                offset_waypoints.append(list(geom.coords))
                        elif clipped.geom_type == 'LineString':
                            offset_waypoints.append(list(clipped.coords))
                    current += width * 0.0000089
            else:
                current = start + offset * 0.0000113
                while current <= end:
                    line = LineString([(current, miny), (current, maxy)])
                    clipped = line.intersection(polygon)
                    if not clipped.is_empty:
                        if clipped.geom_type == 'MultiLineString':
                            for geom in clipped.geoms:
                                offset_waypoints.append(list(geom.coords))
                        elif clipped.geom_type == 'LineString':
                            offset_waypoints.append(list(clipped.coords))
                    current += width * 0.0000113
            waypoints.extend(offset_waypoints)

    else:
        # Pitch Marking: just polygon vertices as waypoints + simple shapes (simplified)
        waypoints.append([(lon, lat) for lat, lon in boundary])

    return waypoints

waypoints = generate_waypoints(boundary_coords, mower_width, task)

# --- 4. Map display with Folium ---

# Center map roughly
avg_lat = sum([lat for lat, lon in boundary_coords]) / len(boundary_coords)
avg_lon = sum([lon for lat, lon in boundary_coords]) / len(boundary_coords)

m = folium.Map(location=[avg_lat, avg_lon], zoom_start=18)

# Draw boundary polygon
folium.Polygon(locations=boundary_coords, color='green', fill=True, fill_opacity=0.2, popup="Field Boundary").add_to(m)

# Draw waypoints lines
for line in waypoints:
    # Each line is list of (lon, lat), convert back to (lat, lon) for folium
    line_latlon = [(lat, lon) for lon, lat in line]
    folium.PolyLine(locations=line_latlon, color="blue").add_to(m)

st_folium(m, width=700, height=500)

# --- 5. Export waypoints as KML ---

def waypoints_to_kml(wps):
    kml = simplekml.Kml()
    for idx, line in enumerate(wps):
        coords = [(lon, lat) for lon, lat in line]
        kml.newlinestring(name=f"Track {idx+1}", coords=coords)
    return kml

kml_obj = waypoints_to_kml(waypoints)

with tempfile.NamedTemporaryFile(delete=False, suffix=".kml") as tmpfile:
    kml_obj.save(tmpfile.name)
    kml_path = tmpfile.name

with open(kml_path, "rb") as f:
    st.download_button(
        label="Download Waypoints as KML",
        data=f,
        file_name="waypoints.kml",
        mime="application/vnd.google-earth.kml+xml",
    )
