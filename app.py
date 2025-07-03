import streamlit as st
import folium
from streamlit_folium import st_folium
import simplekml
from io import BytesIO

# Your 8-point polygon coordinates (lat, lon)
FIELD_BOUNDARY = [
    (43.555830, 27.826090),
    (43.555775, 27.826100),
    (43.555422, 27.826747),
    (43.555425, 27.826786),
    (43.556182, 27.827557),
    (43.556217, 27.827538),
    (43.556559, 27.826893),
    (43.556547, 27.826833),
    (43.555830, 27.826090)  # Close polygon by repeating first point
]

def generate_dummy_driving_lines(field_coords, passes=5):
    """Generate simple vertical lines across polygon bounding box."""
    lats = [pt[0] for pt in field_coords]
    lons = [pt[1] for pt in field_coords]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    lines = []
    for i in range(passes):
        lon = min_lon + i * (max_lon - min_lon) / (passes - 1)
        lines.append([(min_lat, lon), (max_lat, lon)])
    return lines

def create_kml(lines):
    kml = simplekml.Kml()
    for line in lines:
        # simplekml wants (lon, lat) tuples
        coords = [(pt[1], pt[0]) for pt in line]
        kml.newlinestring(coords=coords)
    return kml.kml()

def main():
    st.title("Football Field Grass Cutting Path Generator")

    passes = st.number_input("Number of passes", min_value=2, max_value=10, value=5, step=1)

    if st.button("Generate Driving Course"):
        lines = generate_dummy_driving_lines(FIELD_BOUNDARY, passes)

        # Show map with polygon and driving lines
        m = folium.Map(location=FIELD_BOUNDARY[0], zoom_start=18)
        folium.Polygon(locations=FIELD_BOUNDARY, color="green", fill=True, fill_opacity=0.3).add_to(m)
        for line in lines:
            folium.PolyLine(locations=line, color="blue", weight=3).add_to(m)

        st_folium(m, width=700, height=500)

        # Create KML file for download
        kml_str = create_kml(lines)
        kml_bytes = BytesIO(kml_str.encode("utf-8"))
        st.download_button("Download Driving Course KML", data=kml_bytes, file_name="driving_course.kml", mime="application/vnd.google-earth.kml+xml")

if __name__ == "__main__":
    main()
