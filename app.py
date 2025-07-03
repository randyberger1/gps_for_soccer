import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Polygon, LineString
from shapely.affinity import rotate, translate
from pyproj import Proj, transform
import numpy as np
from io import BytesIO

# Default 8-vertex boundary coordinates (lat, lon)
DEFAULT_BOUNDARY_LATLON = [
    (43.555830, 27.826090),
    (43.555775, 27.826100),
    (43.555422, 27.826747),
    (43.555425, 27.826786),
    (43.556182, 27.827557),
    (43.556217, 27.827538),
    (43.556559, 27.826893),
    (43.556500, 27.826500),  # Example 8th vertex
]

# Projection setup: WGS84 to UTM (zone 35N for this lat/lon range)
proj_wgs84 = Proj("epsg:4326")
proj_utm = Proj("epsg:32635")  # Adjust zone as needed

def latlon_to_utm(latlon_points):
    utm_points = []
    for lat, lon in latlon_points:
        x, y = transform(proj_wgs84, proj_utm, lon, lat)
        utm_points.append((x, y))
    return utm_points

def utm_to_latlon(utm_points):
    latlon_points = []
    for x, y in utm_points:
        lon, lat = transform(proj_utm, proj_wgs84, x, y)
        latlon_points.append((lat, lon))
    return latlon_points

def generate_driving_lines(polygon_utm, mower_width, driving_direction_vector, headland_passes=2):
    # Rotate polygon so driving direction aligns with x-axis
    angle = np.degrees(np.arctan2(driving_direction_vector[1], driving_direction_vector[0]))
    polygon_rot = rotate(polygon_utm, -angle, origin='centroid', use_radians=False)
    minx, miny, maxx, maxy = polygon_rot.bounds

    # Headland passes zones at edges
    headland_width = mower_width * headland_passes
    # Lines for headland passes
    headland_lines = []
    for i in range(headland_passes):
        y1 = miny + i * mower_width
        y2 = maxy - i * mower_width
        line1 = LineString([(minx, y1), (maxx, y1)])
        line2 = LineString([(minx, y2), (maxx, y2)])
        headland_lines.extend([line1, line2])

    # Inner field area excluding headlands
    inner_min_y = miny + headland_width
    inner_max_y = maxy - headland_width

    # Generate parallel driving lines in inner area
    driving_lines = []
    y = inner_min_y
    toggle = False  # for back and forth path
    while y <= inner_max_y:
        line = LineString([(minx, y), (maxx, y)])
        driving_lines.append(line if not toggle else LineString([(maxx, y), (minx, y)]))
        y += mower_width
        toggle = not toggle

    # Combine all lines
    all_lines = headland_lines + driving_lines

    # Rotate lines back to original orientation
    all_lines_rot_back = [rotate(line, angle, origin=polygon_utm.centroid, use_radians=False) for line in all_lines]

    return all_lines_rot_back

def lines_to_latlon_points(lines):
    # Convert each LineString's coords from UTM back to lat/lon
    all_points = []
    for line in lines:
        points_utm = list(line.coords)
        points_latlon = utm_to_latlon(points_utm)
        all_points.append(points_latlon)
    return all_points

def create_kml(lines_latlon):
    from simplekml import Kml
    kml = Kml()
    for points in lines_latlon:
        kml.newlinestring(coords=[(lon, lat) for lat, lon in points], altitudemode='clampToGround')
    return kml.kml()

def main():
    st.title("Football Grass Field Waypoints Generator")

    st.markdown("### Field Boundary (8 vertices)")

    # Show vertices with indices and coordinates
    for i, (lat, lon) in enumerate(DEFAULT_BOUNDARY_LATLON):
        st.write(f"Vertex {i}: Lat {lat:.6f}, Lon {lon:.6f}")

    # UI to select driving direction by vertex indices
    st.markdown("### Select Driving Direction")
    start_vertex = st.selectbox("Start Vertex", options=range(len(DEFAULT_BOUNDARY_LATLON)), index=0)
    end_vertex = st.selectbox("End Vertex", options=[i for i in range(len(DEFAULT_BOUNDARY_LATLON)) if i != start_vertex], index=1)

    mower_width = st.number_input("Mower Operating Width (meters)", min_value=0.5, max_value=10.0, value=2.0, step=0.1)
    headland_passes = st.number_input("Number of Headland Passes", min_value=0, max_value=5, value=2, step=1)

    if st.button("Generate Driving Course"):
        # Convert boundary to UTM
        polygon_utm_coords = latlon_to_utm(DEFAULT_BOUNDARY_LATLON)
        polygon_utm = Polygon(polygon_utm_coords)

        # Calculate driving direction vector from selected vertices (in UTM coords)
        start_pt = polygon_utm_coords[start_vertex]
        end_pt = polygon_utm_coords[end_vertex]
        direction_vec = (end_pt[0] - start_pt[0], end_pt[1] - start_pt[1])

        # Generate driving lines
        driving_lines_utm = generate_driving_lines(polygon_utm, mower_width, direction_vec, headland_passes)

        # Convert driving lines back to lat/lon for display
        driving_lines_latlon = lines_to_latlon_points(driving_lines_utm)

        # Prepare folium map centered on polygon centroid
        centroid_latlon = (np.mean([p[0] for p in DEFAULT_BOUNDARY_LATLON]), np.mean([p[1] for p in DEFAULT_BOUNDARY_LATLON]))
        m = folium.Map(location=centroid_latlon, zoom_start=18)

        # Add polygon (field boundary)
        folium.PolyLine(DEFAULT_BOUNDARY_LATLON + [DEFAULT_BOUNDARY_LATLON[0]], color="green", weight=3, opacity=0.7).add_to(m)

        # Add vertex markers with popup indices
        for i, (lat, lon) in enumerate(DEFAULT_BOUNDARY_LATLON):
            folium.Marker(
                location=(lat, lon),
                popup=f"Vertex {i}",
                icon=folium.DivIcon(html=f"""<div style="font-size: 12pt; color: blue;">{i}</div>""")
            ).add_to(m)

        # Add driving lines
        for line_points in driving_lines_latlon:
            folium.PolyLine(line_points, color="blue", weight=2).add_to(m)

        # Display map
        st_folium(m, width=700, height=500)

        # Export KML file
        kml_content = create_kml(driving_lines_latlon)
        kml_bytes = BytesIO(kml_content.encode('utf-8'))

        st.download_button(
            label="Download Driving Course KML",
            data=kml_bytes,
            file_name="driving_course.kml",
            mime="application/vnd.google-earth.kml+xml"
        )

if __name__ == "__main__":
    main()
