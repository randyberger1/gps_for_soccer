def main():
    st.title("Football Field Boundary and Validation")

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
            # Close polygon if not closed
            if new_coords[0] != new_coords[-1]:
                new_coords.append(new_coords[0])
            st.session_state.field_coords = new_coords
            st.success("Polygon updated!")

    # Validate FIFA dimension checkbox
    validate = st.checkbox("Validate FIFA Standard Dimensions (105×68 m)")

    if validate:
        length, width = polygon_dimensions(st.session_state.field_coords)
        st.write(f"Estimated Field Length: **{length:.2f} m**")
        st.write(f"Estimated Field Width: **{width:.2f} m**")

        length_ok = 100 <= length <= 110  # ±5 meters tolerance
        width_ok = 63 <= width <= 73

        if length_ok and width_ok:
            st.success("Field dimensions comply with FIFA standards (±5 m tolerance).")
        else:
            st.error("Field dimensions do NOT comply with FIFA standards.")

    # --- New Inputs for mower width, direction, and headland passes ---

    st.subheader("Mowing Parameters")

    mower_width = st.number_input("Mower Operating Width (meters)", min_value=0.5, max_value=10.0, value=2.0, step=0.1)

    driving_direction = st.radio(
        "Driving Direction",
        options=["Parallel to Longest Side", "Perpendicular to Longest Side"],
        index=0,
    )

    headland_passes = st.number_input("Number of Headland Passes", min_value=0, max_value=5, value=2, step=1)

    # Show map with polygon
    m = folium.Map(location=st.session_state.field_coords[0], zoom_start=18)
    folium.Polygon(locations=st.session_state.field_coords, color="green", fill=True, fill_opacity=0.3).add_to(m)
    st_folium(m, width=700, height=500)
