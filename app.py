import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Polygon, LineString, Point
import math
import simplekml
from io import BytesIO

# Default field polygon (lat, lon)
field_poly_latlon = [
    (43.699047, 27.840622),
    (43.699011, 27.841512),
    (43.699956, 27.841568),
    (43.699999, 27.840693),
    (43.699047, 27.840622),  # close polygon
]

st.title("FIFA Pitch Marking with KML Export")

# Convert lat/lon to local meters approx
lat_ref = field_poly_latlon[0][0]
m_per_deg_lat = 111320
m_per_deg_lon = 40075000 * math.cos(math.radians(lat_ref)) / 360

def latlon_to_xy(lat, lon):
    x = (lon - field_poly_latlon[0][1]) * m_per_deg_lon
    y = (lat - field_poly_latlon[0][0]) * m_per_deg_lat
    return (x, y)

def xy_to_latlon(x, y):
    lon = x / m_per_deg_lon + field_poly_latlon[0][1]
    lat = y / m_per_deg_lat + field_poly_latlon[0][0]
    return (lat, lon)

def make_rect(x, y, length, width):
    return [
        (x, y),
        (x + length, y),
        (x + length, y + width),
        (x, y + width),
        (x, y)
    ]

# Pitch standard dimensions
lp = 105.0
wp = 68.0

pitch_outer = make_rect(0, 0, lp, wp)
center_line = [(lp/2, 0), (lp/2, wp)]
center_circle_center = (lp/2, wp/2)
center_circle_radius = 9.15

penalty_area_length = 40.32
penalty_area_width = 16.5
penalty_area_1 = make_rect(0, (wp - penalty_area_width)/2, penalty_area_length, penalty_area_width)
penalty_area_2 = make_rect(lp - penalty_area_length, (wp - penalty_area_width)/2, penalty_area_length, penalty_area_width)

penalty_mark_distance = 11
penalty_mark_1 = (penalty_mark_distance, wp/2)
penalty_mark_2 = (lp - penalty_mark_distance, wp/2)
penalty_arc_radius = 9.15

goal_area_length = 18.32
goal_area_width = 5.5
goal_area_1 = make_rect(0, (wp - goal_area_width)/2, goal_area_length, goal_area_width)
goal_area_2 = make_rect(lp - goal_area_length, (wp - goal_area_width)/2, goal_area_length, goal_area_width)

corner_arc_radius = 1.0
corners = [
    (0,0),
    (lp,0),
    (lp,wp),
    (0,wp)
]

def convert_shape_xy_to_latlon(shape):
    return [xy_to_latlon(x,y) for x,y in shape]

def draw_penalty_arc(center, side):
    arc_points = []
    cx, cy = center
    start_angle = -60
    end_angle = 60
    steps = 30
    for i in range(steps+1):
        angle_deg = start_angle + i * (end_angle - start_angle) / steps
        angle_rad = math.radians(angle_deg)
        x = cx + penalty_arc_radius * math.cos(angle_rad)
        y = cy + penalty_arc_radius * math.sin(angle_rad)
        if side == 'left' and x < penalty_area_length:
            continue
        if side == 'right' and x > lp - penalty_area_length:
            continue
        arc_points.append((x,y))
    return arc_points

def draw_corner_arc(corner, quadrant):
    points = []
    steps = 10
    for i in range(steps+1):
        angle = i * (math.pi / 2) / steps
        if quadrant == 'bl':
            x = corner[0] + corner_arc_radius * math.cos(angle)
            y = corner[1] + corner_arc_radius * math.sin(angle)
        elif quadrant == 'br':
            x = corner[0] - corner_arc_radius * math.cos(angle)
            y = corner[1] + corner_arc_radius * math.sin(angle)
        elif quadrant == 'tr':
            x = corner[0] - corner_arc_radius * math.cos(angle)
            y = corner[1] - corner_arc_radius * math.sin(angle)
        elif quadrant == 'tl':
            x = corner[0] + corner_arc_radius * math.cos(angle)
            y = corner[1] - corner_arc_radius * math.sin(angle)
        points.append((x,y))
    return points

# Create map
mid_lat = sum([lat for lat, lon in field_poly_latlon]) / len(field_poly_latlon)
mid_lon = sum([lon for lat, lon in field_poly_latlon]) / len(field_poly_latlon)
m = folium.Map(location=[mid_lat, mid_lon], zoom_start=18, tiles='cartodbpositron')

# Draw original field polygon
folium.Polygon(locations=field_poly_latlon, color='green', fill=True, fill_opacity=0.1, popup='Field Boundary').add_to(m)

# Draw pitch markings
def add_polyline(shape_xy, color='white', weight=2):
    folium.PolyLine(locations=convert_shape_xy_to_latlon(shape_xy), color=color, weight=weight).add_to(m)

# Pitch outer boundary
add_polyline(pitch_outer, weight=3)

# Center line
add_polyline(center_line)

# Center circle
folium.Circle(
    location=xy_to_latlon(*center_circle_center),
    radius=center_circle_radius,
    color='white',
    weight=2,
    fill=False
).add_to(m)

# Penalty areas
add_polyline(penalty_area_1)
add_polyline(penalty_area_2)

# Goal areas
add_polyline(goal_area_1)
add_polyline(goal_area_2)

# Penalty marks
folium.Circle(location=xy_to_latlon(*penalty_mark_1), radius=0.15, color='white', fill=True).add_to(m)
folium.Circle(location=xy_to_latlon(*penalty_mark_2), radius=0.15, color='white', fill=True).add_to(m)

# Penalty arcs
arc_left = draw_penalty_arc(penalty_mark_1, 'left')
arc_right = draw_penalty_arc(penalty_mark_2, 'right')
add_polyline(arc_left)
add_polyline(arc_right)

# Corner arcs
corners_and_quadrants = [
    (corners[0], 'bl'),
    (corners[1], 'br'),
    (corners[2], 'tr'),
    (corners[3], 'tl'),
]

for corner, quad in corners_and_quadrants:
    arc_pts = draw_corner_arc(corner, quad)
    add_polyline(arc_pts)

st_folium(m, width=700, height=500)

# === KML EXPORT ===

def add_kml_line(kml_obj, coords, name):
    ls = kml_obj.newlinestring(name=name)
    ls.coords = [(lon, lat) for lat, lon in coords]
    ls.style.linestyle.color = simplekml.Color.white
    ls.style.linestyle.width = 2

if st.button("Export Pitch Markings as KML"):

    kml = simplekml.Kml()

    # Add all lines and arcs
    add_kml_line(kml, convert_shape_xy_to_latlon(pitch_outer), "Pitch Outer Boundary")
    add_kml_line(kml, convert_shape_xy_to_latlon(center_line), "Center Line")
    kml.newpoint(name="Center Circle Center", coords=[(center_circle_center[1], center_circle_center[0])])  # just a point

    # Approximate center circle by many points
    center_circle_coords = []
    for angle in range(0, 361, 5):
        rad = math.radians(angle)
        x = center_circle_center[0] + center_circle_radius * math.cos(rad)
        y = center_circle_center[1] + center_circle_radius * math.sin(rad)
        center_circle_coords.append(xy_to_latlon(x, y))
    add_kml_line(kml, center_circle_coords, "Center Circle")

    add_kml_line(kml, convert_shape_xy_to_latlon(penalty_area_1), "Penalty Area Left")
    add_kml_line(kml, convert_shape_xy_to_latlon(penalty_area_2), "Penalty Area Right")

    add_kml_line(kml, convert_shape_xy_to_latlon(goal_area_1), "Goal Area Left")
    add_kml_line(kml, convert_shape_xy_to_latlon(goal_area_2), "Goal Area Right")

    # Penalty marks as points
    kml.newpoint(name="Penalty Mark Left", coords=[(penalty_mark_1[1], penalty_mark_1[0])])
    kml.newpoint(name="Penalty Mark Right", coords=[(penalty_mark_2[1], penalty_mark_2[0])])

    # Penalty arcs
    add_kml_line(kml, arc_left, "Penalty Arc Left")
    add_kml_line(kml, arc_right, "Penalty Arc Right")

    # Corner arcs
    for idx, (corner, quad) in enumerate(corners_and_quadrants):
        arc_pts = draw_corner_arc(corner, quad)
        add_kml_line(kml, arc_pts, f"Corner Arc {idx+1}")

    # Export KML to bytes and download
    kml_bytes = kml.kml().encode('utf-8')
    st.download_button(
        label="Download KML",
        data=kml_bytes,
        file_name="fifa_pitch_markings.kml",
        mime="application/vnd.google-earth.kml+xml"
    )
