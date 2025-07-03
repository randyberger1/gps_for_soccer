import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Polygon, LineString
import simplekml
from io import BytesIO
import math


# --- Helper Functions ---

def parse_coords(text):
    coords = []
    for line in text.strip().split("\n"):
        try:
            lat, lon = map(float, line.strip().split(","))
            coords.append((lat, lon))
        except Exception:
            st.error(f"Invalid coordinate line: {line}")
            return None
    return coords

def polygon_dimensions(coords):
    """
    Approximate length and width of polygon in meters,
    assuming small area (use Haversine or UTM for precise).
    """
    # Convert lat/lon to meters approx for small distances:
    # 1 degree lat ~ 111 km, 1 degree lon ~ cos(lat)*111 km
    latitudes = [lat for lat, lon in coords]
    longitudes = [lon for lat, lon in coords]

    avg_lat = sum(latitudes) / len(latitudes)
    meters_per_deg_lat = 111320
    meters_per_deg_lon = 40075000 * math.cos(math.radians(avg_lat)) / 360

    xs = [(lon - longitudes[0]) * meters_per_deg_lon for lon in longitudes]
    ys = [(lat - latitudes[0]) * meters_per_deg_lat for lat in latitudes]

    polygon_xy = list(zip(xs, ys))
    poly = Polygon(polygon_xy)

    minx, miny, maxx, maxy = poly.bounds
    length = maxx - minx
    width = maxy - miny
    return length, width

def generate_parallel_waypoints(polygon_coords, mower_width, driving_direction, headland_passes):
    """
    Generate parallel waypoints for grass cutting.

    driving_direction: "Parallel to Longest Side" or "Perpendicular to Longest Side"
    """
    # Convert coords to shapely Polygon (in lat/lon)
    poly = Polygon(polygon_coords)
    if not poly.is_valid:
        poly = poly.buffer(0)

    # Approximate conversion lat/lon to meters (for spacing calculation)
    latitudes = [lat for lat, lon in polygon_coords]
    longitudes = [lon for lat, lon in polygon_coords]
    avg_lat = sum(latitudes) / len(latitudes)
    meters_per_deg_lat = 111320
    meters_per_deg_lon = 40075000 * math.cos(math.radians(avg_lat)) / 360

    # Create polygon in meters XY for easier math
    xs = [(lon - longitudes[0]) * meters_per_deg_lon for lon in longitudes]
    ys = [(lat - latitudes[0]) * meters_per_deg_lat for lat in latitudes]
    poly_xy = Polygon(zip(xs, ys))

    # Determine driving direction vector based on driving_direction
    minx, miny, maxx, maxy = poly_xy.bounds
    length_x = maxx - minx
    length_y = maxy - miny

    if driving_direction == "Parallel to Longest Side":
        if length_x >= length_y:
            # Driving direction along X axis
            direction = (1, 0)
        else:
            # Driving direction along Y axis
            direction = (0, 1)
    else:  # Perpendicular
        if length_x >= length_y:
            direction = (0, 1)
        else:
            direction = (1, 0)

    # Generate headland passes — offset from polygon boundary
    offsets = []
    for i in range(headland_passes):
        offset_distance = mower_width * i
        offset_poly = poly_xy.buffer(-offset_distance)
        if offset_poly.is_empty or not offset_poly.is_valid:
            break
        offsets.append(offset_poly)

    # The innermost polygon after headland passes:
    if offsets:
        working_poly = offsets[-1]
    else:
        working_poly = poly_xy

    # Generate parallel lines inside working_poly spaced by mower_width
    # We'll create lines perpendicular to driving direction spaced mower_width apart.

    waypoints = []

    # bounding box of working_poly
    minx, miny, maxx, maxy = working_poly.bounds

    # Lines will be perpendicular to driving direction vector
    # If direction = (1,0), lines are vertical spaced along x; if (0,1), lines are horizontal spaced along y.

    # Calculate number of lines needed
    if direction == (1, 0):
        # lines along y axis spaced along x
        start = minx
        end = maxx
        num_lines = int((end - start) / mower_width) + 1
        for i in range(num_lines):
            x = start + i * mower_width
            line = LineString([(x, miny), (x, maxy)])
            inter = line.intersection(working_poly)
            if inter.is_empty:
                continue
            if inter.geom_type == 'LineString':
                waypoints.append(list(inter.coords))
            elif inter.geom_type == 'MultiLineString':
                for geom in inter.geoms:
                    waypoints.append(list(geom.coords))
    else:
        # lines along x axis spaced along y
        start = miny
        end = maxy
        num_lines = int((end - start) / mower_width) + 1
        for i in range(num_lines):
            y = start + i * mower_width
            line = LineString([(minx, y), (maxx, y)])
            inter = line.intersection(working_poly)
            if inter.is_empty:
                continue
            if inter.geom_type == 'LineString':
                waypoints.append(list(inter.coords))
            elif inter.geom_type == 'MultiLineString':
                for geom in inter.geoms:
                    waypoints.append(list(geom.coords))

    # Convert back to lat/lon coordinates (from meters)
    final_waypoints = []
    for segment in waypoints:
        segment_latlon = []
        for x, y in segment:
            lat = y / meters_per_deg_lat + latitudes[0]
            lon = x / meters_per_deg_lon + longitudes[0]
            segment_latlon.append((lat, lon))
        final_waypoints.append(segment_latlon)

    return final_waypoints


def create_kml(waypoints):
    kml = simplekml.Kml()
    for idx, segment in enumerate(waypoints):
        ls = kml.newlinestring(name=f"Pass {idx+1}", coords=[(lon, lat) for lat, lon in segment])
        ls.style.linestyle.width = 3
        ls.style.linestyle.color = simplekml.Color.green
    return kml


# --- Streamlit App ---

def main():
    st.title("Football Field Grass Cutting Planner")

    # Default polygon coordinates (8 vertices + close polygon)
    default_coords = [
        (43.555830, 27.826090),
        (43.555775, 27.826100),
        (43.555422, 27.826747),
        (43.555425, 27.826786),
        (43.556182, 27.827557),
        (43.556217, 27.827538),
        (43.556559, 27.826893),
        (43.556547, 27.826833),
        (43.555830, 27.826090),  # close polygon
    ]

    if "field_coords" not in st.session_state:
        st.session_state.field_coords = default_coords

    st.subheader("Input Field Coordinates (lat, lon):")
    coord_text = "\n".join(f"{lat}, {lon}" for lat, lon in st.session_state.field_coords)
    user_input = st.text_area("Edit field coordinates (one pair per line)", coord_text, height=200)

    if st.button("Update Polygon"):
        new_coords = parse_coords(user_input)
        if new_coords:
            if new_coords[0] != new_coords[-1]:
                new_coords.append(new_coords[0])
            st.session_state.field_coords = new_coords
            st.success("Polygon updated!")

    validate = st.checkbox("Validate FIFA Standard Dimensions (105×68 m)")

    if validate:
        length, width = polygon_dimensions(st.session_state.field_coords)
        st.write(f"Estimated Field Length: **{length:.2f} m**")
        st.write(f"Estimated Field Width: **{width:.2f} m**")

        length_ok = 100 <= length <= 110
        width_ok = 63 <= width <= 73

        if length_ok and width_ok:
            st.success("Field dimensions comply with FIFA standards (±5 m tolerance).")
        else:
            st.error("Field dimensions do NOT comply with FIFA standards.")

    st.subheader("Mowing Parameters")

    mower_width = st.number_input("Mower Operating Width (meters)", min_value=0.5, max_value=10.0, value=2.0, step=0.1)

    driving_direction = st.radio(
        "Driving Direction",
        options=["Parallel to Longest Side", "Perpendicular to Longest Side"],
        index=0,
    )

    headland_passes = st.number_input("Number of Headland Passes", min_value=0, max_value=5, value=2, step=1)

    generate = st.button("Generate Waypoints")

    # Map initialization
    m = folium.Map(location=st.session_state.field_coords[0], zoom_start=18)
    folium.Polygon(locations=st.session_state.field_coords, color="green", fill=True, fill_opacity=0.3).add_to(m)

    if generate:
        waypoints = generate_parallel_waypoints(
            st.session_state.field_coords,
            mower_width,
            driving_direction,
            headland_passes,
        )
        # Add lines to map
        for segment in waypoints:
            folium.PolyLine(locations=segment, color="blue", weight=3).add_to(m)

        # Save KML for download
        kml = create_kml(waypoints)
        kml_bytes = BytesIO()
        kml.save(kml_bytes)
        kml_bytes.seek(0)

        st.download_button(
            label="Download Waypoints KML",
            data=kml_bytes,
            file_name="waypoints.kml",
            mime="application/vnd.google-earth.kml+xml"
        )

    st_folium(m, width=700, height=500)


if __name__ == "__main__":
    main()
