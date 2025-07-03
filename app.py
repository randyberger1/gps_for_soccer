import streamlit as st
import folium
import math
from streamlit_folium import st_folium

# FIFA field constants
lp = 105  # playing field length (m)
wp = 68   # playing field width (m)

penalty_area_length = 16.5
penalty_area_width = 40.32
goal_area_length = 5.5
goal_area_width = 18.32
center_circle_radius = 9.15
penalty_arc_radius = 9.15
corner_arc_radius = 1.0

def add_polyline(points, m, color="white", weight=2):
    # Convert (x,y) in meters to lat/lon - here we fake conversion for demo, replace with real conversion
    locations = [(p[1] + base_lat, p[0] + base_lon) for p in points]  
    folium.PolyLine(locations=locations, color=color, weight=weight).add_to(m)

def draw_penalty_arc(center, side):
    arc_points = []
    cx, cy = center
    start_angle = -60
    end_angle = 60
    steps = 30
    for i in range(steps + 1):
        angle_deg = start_angle + i * (end_angle - start_angle) / steps
        angle_rad = math.radians(angle_deg)
        x = cx + penalty_arc_radius * math.cos(angle_rad)
        y = cy + penalty_arc_radius * math.sin(angle_rad)
        # Fixed logic:
        if side == 'left' and x <= penalty_area_length:
            continue
        if side == 'right' and x >= lp - penalty_area_length:
            continue
        arc_points.append((x, y))
    return arc_points

def main():
    global base_lat, base_lon
    st.title("FIFA Pitch Marking Visualization")

    # Base GPS coordinate for demo (replace with your field's GPS)
    base_lat, base_lon = 43.699047, 27.840622

    # Create Folium map centered at base coordinates
    m = folium.Map(location=[base_lat, base_lon], zoom_start=18, tiles="OpenStreetMap")

    # Draw outer field rectangle (approximate with simple rectangle)
    field_corners = [
        (0, 0),
        (lp, 0),
        (lp, wp),
        (0, wp),
        (0, 0)
    ]
    add_polyline(field_corners, m, color="white", weight=3)

    # Draw center line
    center_line = [(lp/2, 0), (lp/2, wp)]
    add_polyline(center_line, m, color="white")

    # Draw center circle
    center = (lp/2, wp/2)
    center_circle = []
    steps = 100
    for i in range(steps+1):
        angle = 2 * math.pi * i / steps
        x = center[0] + center_circle_radius * math.cos(angle)
        y = center[1] + center_circle_radius * math.sin(angle)
        center_circle.append((x, y))
    add_polyline(center_circle, m, color="white")

    # Draw penalty areas
    # Left penalty box corners
    left_penalty_box = [
        (0, (wp - penalty_area_width) / 2),
        (penalty_area_length, (wp - penalty_area_width) / 2),
        (penalty_area_length, (wp + penalty_area_width) / 2),
        (0, (wp + penalty_area_width) / 2),
        (0, (wp - penalty_area_width) / 2)
    ]
    add_polyline(left_penalty_box, m, color="white")

    # Right penalty box corners
    right_penalty_box = [
        (lp, (wp - penalty_area_width) / 2),
        (lp - penalty_area_length, (wp - penalty_area_width) / 2),
        (lp - penalty_area_length, (wp + penalty_area_width) / 2),
        (lp, (wp + penalty_area_width) / 2),
        (lp, (wp - penalty_area_width) / 2)
    ]
    add_polyline(right_penalty_box, m, color="white")

    # Draw penalty arcs
    arc_left = draw_penalty_arc(center=(penalty_area_length, wp/2), side='left')
    arc_right = draw_penalty_arc(center=(lp - penalty_area_length, wp/2), side='right')
    add_polyline(arc_left, m, color="white")
    add_polyline(arc_right, m, color="white")

    # Draw corner arcs (4 corners)
    def draw_corner_arc(cx, cy, start_angle_deg):
        arc_points = []
        steps = 20
        for i in range(steps + 1):
            angle = math.radians(start_angle_deg + i * 90 / steps)
            x = cx + corner_arc_radius * math.cos(angle)
            y = cy + corner_arc_radius * math.sin(angle)
            arc_points.append((x, y))
        return arc_points

    corners = [
        (0, 0, 0),            # Bottom-left corner start at 0 deg
        (lp, 0, 90),          # Bottom-right corner start at 90 deg
        (lp, wp, 180),        # Top-right corner start at 180 deg
        (0, wp, 270)          # Top-left corner start at 270 deg
    ]
    for cx, cy, start_angle in corners:
        arc = draw_corner_arc(cx, cy, start_angle)
        add_polyline(arc, m, color="white")

    # Show map in Streamlit
    st_folium(m, width=700, height=500)

if __name__ == "__main__":
    main()
