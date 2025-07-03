import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Polygon, LineString, Point
import math

# Default field polygon (lat, lon)
field_poly_latlon = [
    (43.699047, 27.840622),
    (43.699011, 27.841512),
    (43.699956, 27.841568),
    (43.699999, 27.840693),
    (43.699047, 27.840622),  # close polygon
]

st.title("FIFA Pitch Marking Visualization")

# Convert lat/lon to local meters approximation for small areas (equirectangular approx)
# Approximate meters per degree at given latitude
lat_ref = field_poly_latlon[0][0]
m_per_deg_lat = 111320  # meters per degree latitude approx
m_per_deg_lon = 40075000 * math.cos(math.radians(lat_ref)) / 360  # meters per degree longitude approx

def latlon_to_xy(lat, lon):
    x = (lon - field_poly_latlon[0][1]) * m_per_deg_lon
    y = (lat - field_poly_latlon[0][0]) * m_per_deg_lat
    return (x, y)

def xy_to_latlon(x, y):
    lon = x / m_per_deg_lon + field_poly_latlon[0][1]
    lat = y / m_per_deg_lat + field_poly_latlon[0][0]
    return (lat, lon)

# Convert polygon to local xy
field_poly_xy = [latlon_to_xy(lat, lon) for lat, lon in field_poly_latlon]

# Pitch standard dimensions (meters)
lp = 105.0  # length
wp = 68.0   # width

# We'll draw the pitch aligned with the local XY, starting at (0,0)
pitch_origin = (0, 0)

def make_rect(x, y, length, width):
    return [
        (x, y),
        (x + length, y),
        (x + length, y + width),
        (x, y + width),
        (x, y)
    ]

# Pitch outer boundary
pitch_outer = make_rect(pitch_origin[0], pitch_origin[1], lp, wp)

# Center line - line at half length
center_line = [(lp/2, 0), (lp/2, wp)]

# Center circle - radius 9.15m, center at (lp/2, wp/2)
center_circle_center = (lp/2, wp/2)
center_circle_radius = 9.15

# Penalty areas: two rectangles at ends
penalty_area_length = 40.32
penalty_area_width = 16.5

penalty_area_1 = make_rect(0, (wp - penalty_area_width)/2, penalty_area_length, penalty_area_width)
penalty_area_2 = make_rect(lp - penalty_area_length, (wp - penalty_area_width)/2, penalty_area_length, penalty_area_width)

# Penalty marks: 11m from goal line at center width
penalty_mark_distance = 11
penalty_mark_1 = (penalty_mark_distance, wp/2)
penalty_mark_2 = (lp - penalty_mark_distance, wp/2)

# Penalty arcs radius 9.15m centered at penalty marks (only outside the penalty box)
penalty_arc_radius = 9.15

# Goal areas: two rectangles at ends (smaller than penalty area)
goal_area_length = 18.32
goal_area_width = 5.5
goal_area_1 = make_rect(0, (wp - goal_area_width)/2, goal_area_length, goal_area_width)
goal_area_2 = make_rect(lp - goal_area_length, (wp - goal_area_width)/2, goal_area_length, goal_area_width)

# Corner arcs radius 1m at each corner
corner_arc_radius = 1.0
corners = [
    (0,0),
    (lp,0),
    (lp,wp),
    (0,wp)
]

# Function to convert list of xy coords to latlon
def convert_shape_xy_to_latlon(shape):
    return [xy_to_latlon(x,y) for x,y in shape]

# Create Folium map centered at midpoint
mid_lat = sum([lat for lat, lon in field_poly_latlon]) / len(field_poly_latlon)
mid_lon = sum([lon for lat, lon in field_poly_latlon]) / len(field_poly_latlon)
m = folium.Map(location=[mid_lat, mid_lon], zoom_start=18)

# Draw field boundary polygon (your input)
folium.Polygon(locations=field_poly_latlon, color='green', fill=True, fill_opacity=0.1, popup='Field Boundary').add_to(m)

# Draw pitch outer boundary
folium.PolyLine(locations=convert_shape_xy_to_latlon(pitch_outer), color='white', weight=3).add_to(m)

# Draw center line
folium.PolyLine(locations=convert_shape_xy_to_latlon(center_line), color='white', weight=2).add_to(m)

# Draw center circle as circle
folium.Circle(
    location=xy_to_latlon(*center_circle_center),
    radius=center_circle_radius,
    color='white',
    weight=2,
    fill=False
).add_to(m)

# Draw penalty areas
folium.PolyLine(locations=convert_shape_xy_to_latlon(penalty_area_1), color='white', weight=2).add_to(m)
folium.PolyLine(locations=convert_shape_xy_to_latlon(penalty_area_2), color='white', weight=2).add_to(m)

# Draw goal areas
folium.PolyLine(locations=convert_shape_xy_to_latlon(goal_area_1), color='white', weight=2).add_to(m)
folium.PolyLine(locations=convert_shape_xy_to_latlon(goal_area_2), color='white', weight=2).add_to(m)

# Draw penalty marks as small circles
folium.Circle(location=xy_to_latlon(*penalty_mark_1), radius=0.15, color='white', fill=True).add_to(m)
folium.Circle(location=xy_to_latlon(*penalty_mark_2), radius=0.15, color='white', fill=True).add_to(m)

# Draw penalty arcs
# We'll approximate arcs by drawing many points (only outside the box)

def draw_penalty_arc(center, inside_box_x):
    # Arc from -60 to +60 degrees (120 degrees) centered at penalty mark
    arc_points = []
    center_x, center_y = center
    start_angle = -60
    end_angle = 60
    steps = 30
    for i in range(steps+1):
        angle_deg = start_angle + i * (end_angle - start_angle) / steps
        angle_rad = math.radians(angle_deg)
        x = center_x + penalty_arc_radius * math.cos(angle_rad)
        y = center_y + penalty_arc_radius * math.sin(angle_rad)
        # Only outside penalty box (x > inside_box_x for left box, x < inside_box_x for right box)
        if inside_box_x == 'left' and x < penalty_area_length:
            continue
        if inside_box_x == 'right' and x > lp - penalty_area_length:
            continue
        arc_points.append((x,y))
    return arc_points

arc_left = draw_penalty_arc(penalty_mark_1, 'left')
arc_right = draw_penalty_arc(penalty_mark_2, 'right')

folium.PolyLine(locations=convert_shape_xy_to_latlon(arc_left), color='white', weight=2).add_to(m)
folium.PolyLine(locations=convert_shape_xy_to_latlon(arc_right), color='white', weight=2).add_to(m)

# Draw corner arcs (quarter circles with radius 1m)
def draw_corner_arc(corner, quadrant):
    points = []
    steps = 10
    for i in range(steps+1):
        angle = i * (math.pi / 2) / steps
        if quadrant == 'bl':  # bottom-left corner (0,0)
            x = corner[0] + corner_arc_radius * math.cos(angle)
            y = corner[1] + corner_arc_radius * math.sin(angle)
        elif quadrant == 'br': # bottom-right corner (lp,0)
            x = corner[0] - corner_arc_radius * math.cos(angle)
            y = corner[1] + corner_arc_radius * math.sin(angle)
        elif quadrant == 'tr': # top-right corner (lp,wp)
            x = corner[0] - corner_arc_radius * math.cos(angle)
            y = corner[1] - corner_arc_radius * math.sin(angle)
        elif quadrant == 'tl': # top-left corner (0,wp)
            x = corner[0] + corner_arc_radius * math.cos(angle)
            y = corner[1] - corner_arc_radius * math.sin(angle)
        points.append((x,y))
    return points

# Add arcs
corners_and_quadrants = [
    (corners[0], 'bl'),
    (corners[1], 'br'),
    (corners[2], 'tr'),
    (corners[3], 'tl'),
]

for corner, quad in corners_and_quadrants:
    arc_pts = draw_corner_arc(corner, quad)
    folium.PolyLine(locations=convert_shape_xy_to_latlon(arc_pts), color='white', weight=2).add_to(m)

st_folium(m, width=700, height=500)
