import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
import rivers_evaluation
import usgs_water
import weather
import pa_river_functions

# Page configuration
st.set_page_config(
    page_title="Pennsylvania River Paddling Conditions",
    page_icon="🚣",
    layout="wide"
)

st.title("🌊 Pennsylvania River Paddling Conditions")
st.markdown("Real-time water levels and weather conditions for Pennsylvania rivers")

# Load river data from local CSV files
@st.cache_data
def load_river_data():
    """Load river data from CSV files in the current directory."""
    try:
        # Try common CSV file names
        possible_files = [
            'river_specs.csv',      # Your actual file
            'pa_rivers_table.csv',  # Alternative file
            'rivers.csv',
            'river_data.csv',
            'paddling.csv',
            'waterways.csv'
        ]

        for filename in possible_files:
            if os.path.exists(filename):
                try:
                    df = pd.read_csv(filename)
                    # Validate required columns
                    required_cols = ['Name', 'Zipcode', 'Gauge_ID', 'Min_Level', 'Max_Level', 'Whitewater']
                    if all(col in df.columns for col in required_cols):
                        return df, filename
                except Exception as e:
                    continue

        # If no valid files found, try any CSV
        csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
        for filename in csv_files:
            try:
                df = pd.read_csv(filename)
                if 'Name' in df.columns and 'Zipcode' in df.columns:
                    return df, filename
            except:
                continue

        return None, None
    except Exception as e:
        st.error(f"Error loading CSV data: {e}")
        return None, None

# Load the data
df, filename = load_river_data()

# Sidebar for configuration
with st.sidebar:
    st.header("🏠 Settings")

    # Home ZIP code
    home_zip = st.text_input("Your Home ZIP Code", value="15221", help="Used for distance calculations")

    st.divider()

    # Date selection
    st.subheader("📅 Date Selection")
    date_option = st.radio("Check conditions for:", ["Today", "Specific Date", "Weekly Forecast"])

    target_date = None
    if date_option == "Specific Date":
        target_date = st.date_input("Select Date",
                                   value=date.today() + timedelta(days=1),
                                   min_value=date.today(),
                                   max_value=date.today() + timedelta(days=7))

    st.divider()

    # Filters
    st.subheader("🔍 Filters")

    # River class filter using your pa_river_functions
    if df is not None and 'Class' in df.columns:
        st.write("**River Class Filter:**")
        class_filter_type = st.selectbox(
            "Filter by difficulty",
            options=["All Rivers", "Flat Water (A-C)", "Easy (I-II)", "Intermediate (II-III)",
                    "Advanced (III-IV)", "Expert (IV-VI)", "Whitewater Only (III+)", "Custom Range"],
            help="Filter rivers by whitewater difficulty class"
        )

        # Set class ranges based on selection
        class_range = None
        if class_filter_type == "Flat Water (A-C)":
            class_range = (0, 0)
        elif class_filter_type == "Easy (I-II)":
            class_range = (1, 2)
        elif class_filter_type == "Intermediate (II-III)":
            class_range = (2, 3)
        elif class_filter_type == "Advanced (III-IV)":
            class_range = (3, 4)
        elif class_filter_type == "Expert (IV-VI)":
            class_range = (4, 6)
        elif class_filter_type == "Whitewater Only (III+)":
            class_range = (3, 6)
        elif class_filter_type == "Custom Range":
            col1, col2 = st.columns(2)
            with col1:
                min_class = st.selectbox("Min Class", [0, 1, 2, 3, 4, 5, 6],
                                       format_func=lambda x: ["A/B/C", "I", "II", "III", "IV", "V", "VI"][x])
            with col2:
                max_class = st.selectbox("Max Class", [0, 1, 2, 3, 4, 5, 6],
                                       format_func=lambda x: ["A/B/C", "I", "II", "III", "IV", "V", "VI"][x],
                                       index=3)
            class_range = (min_class, max_class)
    else:
        # Fallback to original whitewater filter
        st.write("**Whitewater Level:**")
        whitewater_filter = st.selectbox(
            "Filter by difficulty",
            options=["All Rivers", "Casual Only (≤ Class 2)", "Whitewater Only (≥ Class 3)", "Custom"],
            help="Filter rivers by difficulty level"
        )

        max_whitewater = None
        if whitewater_filter == "Casual Only (≤ Class 2)":
            max_whitewater = 3
        elif whitewater_filter == "Whitewater Only (≥ Class 3)":
            max_whitewater = -3
        elif whitewater_filter == "Custom":
            max_whitewater = st.number_input("Max Whitewater Class", min_value=0, max_value=6, value=3)

    # Distance filter
    st.write("**Distance Filter:**")
    distance_filter = st.checkbox("Limit by Distance")
    max_distance = None
    if distance_filter:
        max_distance = st.slider("Maximum Distance (miles)", 10, 300, 100)

    st.divider()

    # Quick actions
    st.subheader("⚡ Quick Actions")
    if st.button("🏞️ Casual Rivers Today", help="Class I-II rivers within 100 miles"):
        st.session_state.quick_action = "casual"
    if st.button("🌊 Whitewater Today", help="Class III+ rivers"):
        st.session_state.quick_action = "whitewater"

if df is not None:
    # Display basic info about the CSV
    st.success(f"✅ Loaded {len(df)} rivers from `{filename}`")

    # Handle quick actions
    if hasattr(st.session_state, 'quick_action'):
        if st.session_state.quick_action == "casual":
            if 'Class' in df.columns:
                class_range = (1, 2)
            else:
                max_whitewater = 3
            max_distance = 100
        elif st.session_state.quick_action == "whitewater":
            if 'Class' in df.columns:
                class_range = (3, 6)
            else:
                max_whitewater = -3
        # Clear the action
        del st.session_state.quick_action

    # Apply class filtering if using the Class column
    filtered_df = df.copy()
    if 'Class' in df.columns and 'class_range' in locals() and class_range is not None:
        try:
            filtered_df = pa_river_functions.river_class(df, class_range)
            if len(filtered_df) < len(df):
                st.info(f"🔍 Filtered to {len(filtered_df)} rivers matching class criteria")
        except Exception as e:
            st.warning(f"Class filtering error: {e}")
            filtered_df = df

    with st.expander("📊 Preview River Data"):
        st.dataframe(filtered_df.head(10), use_container_width=True)
        if len(filtered_df) > 10:
            st.caption(f"Showing first 10 of {len(filtered_df)} rivers")

    # Main functionality tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎯 River Check", "📊 Weekly Forecast", "💧 Water Levels", "🌤️ Weather Check", "📋 River Database"])

    with tab1:
        st.header("Current River Conditions")

        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("🔍 Evaluate All Rivers", type="primary", use_container_width=True):
                with st.spinner("Checking water levels and weather conditions..."):
                    try:
                        # Convert date to string if needed
                        date_str = target_date.strftime('%Y-%m-%d') if target_date else None

                        # Use appropriate filtering based on available columns
                        if 'Class' in df.columns and 'class_range' in locals() and class_range is not None:
                            # Use filtered dataframe from class filtering
                            eval_df = filtered_df
                            max_whitewater_param = None
                        else:
                            # Use original whitewater filtering
                            eval_df = filtered_df
                            max_whitewater_param = max_whitewater if 'max_whitewater' in locals() else None

                        # Run evaluation
                        results = rivers_evaluation.check_rivers_today(
                            df=eval_df,
                            home_zip=home_zip,
                            target_date=date_str,
                            max_whitewater=max_whitewater_param,
                            max_distance=max_distance
                        )

                        # Display results
                        if results:
                            st.success(f"Found {len(results)} qualifying rivers!")

                            # Best recommendation
                            best = results[0]
                            if best['overall_score'] >= 60:
                                st.success(f"🏆 **Top Recommendation:** {best['name']} ({best['route']}) - {best['recommendation']}")

                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Score", f"{best['overall_score']}/100")
                                with col2:
                                    if best.get('distance_miles'):
                                        st.metric("Distance", f"{best['distance_miles']} mi")
                                with col3:
                                    if best.get('current_conditions'):
                                        st.metric("Wind", f"{best['current_conditions']['wind_speed']:.0f} mph")
                                with col4:
                                    if best.get('water_status') and best['water_status'].get('current_level'):
                                        level = best['water_status']['current_level']
                                        metric = best['water_status'].get('metric', 'ft')
                                        unit = 'CFS' if metric == 'cfs' else 'ft'
                                        st.metric("Water Level", f"{level:.1f} {unit}")
                            else:
                                st.warning(f"🟡 **Best Available:** {best['name']} - {best['recommendation']} (Score: {best['overall_score']}/100)")

                            # Results table
                            st.subheader("All River Results")
                            results_data = []
                            for river in results:
                                row = {
                                    "River": river['name'],
                                    "Route": river['route'],
                                    "Score": river['overall_score'],
                                    "Recommendation": river['recommendation'],
                                    "Whitewater": river['whitewater']
                                }

                                if river.get('distance_miles'):
                                    row["Distance (mi)"] = f"{river['distance_miles']:.1f}"

                                if river.get('water_status'):
                                    level = river['water_status'].get('current_level', 'N/A')
                                    metric = river['water_status'].get('metric', 'ft')
                                    unit = 'CFS' if metric == 'cfs' else 'ft'
                                    row["Water Level"] = f"{level} {unit}" if level != 'N/A' else 'N/A'
                                    row["Water Status"] = river['water_status']['status']

                                if river.get('current_conditions'):
                                    conditions = river['current_conditions']
                                    row["Temp (°F)"] = f"{conditions['temperature']:.0f}"
                                    row["Wind (mph)"] = f"{conditions['wind_speed']:.0f}"

                                if river.get('issues'):
                                    row["Issues"] = ', '.join(river['issues'])

                                results_data.append(row)

                            results_df = pd.DataFrame(results_data)
                            st.dataframe(results_df, use_container_width=True)

                            # Download results
                            csv = results_df.to_csv(index=False)
                            st.download_button(
                                label="📥 Download Results as CSV",
                                data=csv,
                                file_name=f"river_conditions_{date.today().strftime('%Y%m%d')}.csv",
                                mime="text/csv"
                            )
                        else:
                            st.warning("No rivers found matching your criteria.")

                    except Exception as e:
                        st.error(f"Error evaluating rivers: {e}")
                        st.exception(e)

        with col2:
            # Info about evaluation
            st.info("💡 **Evaluation considers:**\n- Current water levels\n- Weather conditions\n- Distance from home\n- Your filters")

    with tab2:
        st.header("7-Day Paddling Forecast")

        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("📅 Generate Weekly Forecast", type="primary", use_container_width=True):
                with st.spinner("Generating 7-day forecast..."):
                    try:
                        # Use appropriate filtering
                        if 'Class' in df.columns and 'class_range' in locals() and class_range is not None:
                            eval_df = filtered_df
                            max_whitewater_param = None
                        else:
                            eval_df = filtered_df
                            max_whitewater_param = max_whitewater if 'max_whitewater' in locals() else None

                        results = rivers_evaluation.get_weekly_river_forecast(
                            df=eval_df,
                            home_zip=home_zip,
                            max_whitewater=max_whitewater_param,
                            max_distance=max_distance
                        )

                        if results:
                            st.success("Weekly forecast generated!")

                            # Display best days
                            for i, day in enumerate(results[:7], 1):
                                if day['day_score'] >= 20:  # Lower threshold for display
                                    with st.container():
                                        score_color = "🟢" if day['day_score'] >= 70 else "🟡" if day['day_score'] >= 40 else "🟠"
                                        st.subheader(f"{score_color} {day['day_name']}, {day['date_str']}")

                                        col1, col2 = st.columns([3, 1])
                                        with col1:
                                            if day['rivers']:
                                                best_river = day['rivers'][0]
                                                st.write(f"**Best River:** {best_river['name']} ({best_river['score']:.1f}/100)")

                                                if best_river.get('day_forecast'):
                                                    forecast = best_river['day_forecast']
                                                    weather_text = f"🌡️ {forecast['temperature']:.0f}°F • 💨 {forecast['wind_speed']:.0f}mph wind • 🌧️ {forecast['precipitation_probability']:.0f}% rain"
                                                    st.caption(weather_text)

                                                    if forecast.get('narrative'):
                                                        st.caption(f"*{forecast['narrative']}*")

                                        with col2:
                                            st.metric("Day Score", f"{day['day_score']:.1f}/100")

                                        st.divider()
                        else:
                            st.warning("No good paddling days found in the next 7 days.")

                    except Exception as e:
                        st.error(f"Error generating forecast: {e}")
                        st.exception(e)

        with col2:
            st.info("📈 **Weekly forecast shows:**\n- Best river each day\n- Real weather predictions\n- Optimal paddling windows")

    with tab3:
        st.header("💧 USGS Water Level Checker")

        # Pre-populate with rivers from CSV
        if len(filtered_df) > 0:
            st.subheader("Quick Check: Rivers from Database")
            selected_river = st.selectbox("Select a river to check",
                                        options=filtered_df['Name'].tolist(),
                                        help="Choose from your filtered river list")

            if selected_river:
                river_row = filtered_df[filtered_df['Name'] == selected_river].iloc[0]

                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**River:** {river_row['Name']}")
                    st.write(f"**Route:** {river_row.get('Route', 'N/A')}")
                    st.write(f"**Gauge ID:** {river_row['Gauge_ID']}")
                with col2:
                    st.write(f"**Min Level:** {river_row['Min_Level']} ft")
                    st.write(f"**Max Level:** {river_row['Max_Level']} ft")
                    if pd.notna(river_row.get('Min_cfs')):
                        st.write(f"**Flow Range:** {river_row['Min_cfs']}-{river_row['Max_cfs']} CFS")

                if st.button("Check This River's Water Level", type="primary"):
                    with st.spinner("Checking water level..."):
                        try:
                            result = usgs_water.check_water_level_range(
                                site_id=str(river_row['Gauge_ID']).zfill(8),
                                min_level=river_row['Min_Level'],
                                max_level=river_row['Max_Level'],
                                min_cfs=river_row.get('Min_cfs') if pd.notna(river_row.get('Min_cfs')) else None,
                                max_cfs=river_row.get('Max_cfs') if pd.notna(river_row.get('Max_cfs')) else None
                            )

                            # Display result with color coding
                            if result['status'] == 'good':
                                st.success(f"✅ **GOOD:** {result['message']}")
                            elif result['status'] == 'too_low':
                                st.warning(f"⬇️ **TOO LOW:** {result['message']}")
                            elif result['status'] == 'too_high':
                                st.error(f"⬆️ **TOO HIGH:** {result['message']}")
                            else:
                                st.error(f"❌ **ERROR:** {result['message']}")

                            # Show details
                            if result.get('current_level'):
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    metric = result.get('metric', 'feet')
                                    unit = 'CFS' if metric == 'cfs' else 'ft'
                                    st.metric("Current Level", f"{result['current_level']:.2f} {unit}")
                                with col2:
                                    if result.get('timestamp'):
                                        st.write(f"**Updated:** {result['timestamp'].strftime('%m/%d %H:%M')}")
                                with col3:
                                    st.write(f"**Site:** {result.get('site_id', 'Unknown')}")

                        except Exception as e:
                            st.error(f"Error checking water level: {e}")

        st.divider()

        # Custom gauge checker
        st.subheader("Custom Gauge Check")
        with st.form("water_level_form"):
            col1, col2 = st.columns(2)
            with col1:
                site_id = st.text_input("USGS Site ID", value="03044000", help="8-digit USGS gauge ID")
                min_level = st.number_input("Minimum Level (ft)", value=3.0, step=0.1)
                min_cfs = st.number_input("Minimum Flow (CFS)", value=None, step=10.0)
            with col2:
                site_name = st.text_input("Site Name (optional)", help="For your reference")
                max_level = st.number_input("Maximum Level (ft)", value=8.0, step=0.1)
                max_cfs = st.number_input("Maximum Flow (CFS)", value=None, step=10.0)

            submit_water = st.form_submit_button("Check Water Level", type="primary")

            if submit_water:
                with st.spinner("Checking water level..."):
                    try:
                        result = usgs_water.check_water_level_range(
                            site_id=site_id,
                            min_level=min_level,
                            max_level=max_level,
                            min_cfs=min_cfs,
                            max_cfs=max_cfs
                        )

                        # Display result
                        if result['status'] == 'good':
                            st.success(f"✅ {result['message']}")
                        elif result['status'] in ['too_low', 'too_high']:
                            st.warning(f"⚠️ {result['message']}")
                        else:
                            st.error(f"❌ {result['message']}")

                        # Show details
                        if result.get('current_level'):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                metric = result.get('metric', 'feet')
                                unit = 'CFS' if metric == 'cfs' else 'ft'
                                st.metric("Current Level", f"{result['current_level']:.2f} {unit}")
                            with col2:
                                if result.get('timestamp'):
                                    st.write(f"**Last Updated:** {result['timestamp'].strftime('%Y-%m-%d %H:%M')}")
                            with col3:
                                if site_name:
                                    st.write(f"**Site:** {site_name}")

                    except Exception as e:
                        st.error(f"Error checking water level: {e}")

    with tab4:
        st.header("🌤️ Weather Checker")

        with st.form("weather_form"):
            col1, col2 = st.columns(2)
            with col1:
                location_type = st.radio("Location Type", ["ZIP Code", "City Name"])
                if location_type == "ZIP Code":
                    location = st.text_input("ZIP Code", value="15221")
                else:
                    location = st.text_input("City Name", value="Pittsburgh, PA")

            with col2:
                forecast_days = st.slider("Forecast Days", 1, 7, 3)
                include_assessment = st.checkbox("Include Paddling Assessment", value=True)

            submit_weather = st.form_submit_button("Get Weather", type="primary")

            if submit_weather:
                with st.spinner("Getting weather data..."):
                    try:
                        if location_type == "ZIP Code":
                            weather_data = weather.get_weather_by_zip(location, forecast_days)
                        else:
                            weather_data = weather.get_weather_by_city(location, forecast_days)

                        if weather_data:
                            # Current conditions
                            current = weather.get_current_conditions(weather_data)

                            # Display current conditions
                            st.subheader(f"Current Conditions - {location}")

                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Temperature", f"{current['temperature']:.0f}°F")
                            with col2:
                                st.metric("Wind Speed", f"{current['wind_speed']:.0f} mph")
                            with col3:
                                st.metric("Wind Direction", current['wind_direction_name'])
                            with col4:
                                st.metric("Humidity", f"{current['humidity']:.0f}%")

                            # Paddling assessment
                            if include_assessment:
                                assessment = weather.assess_paddling_conditions(weather_data)

                                if assessment['status'] == 'good':
                                    st.success(f"✅ **{assessment['message']}**")
                                elif assessment['status'] == 'caution':
                                    st.warning(f"⚠️ **{assessment['message']}**")
                                else:
                                    st.error(f"❌ **{assessment['message']}**")

                            # Multi-day forecast
                            if forecast_days > 1:
                                st.subheader("Extended Forecast")
                                forecast_data = []

                                for day_offset in range(1, min(forecast_days + 1, 8)):
                                    target_forecast_date = date.today() + timedelta(days=day_offset)
                                    day_forecast = weather.get_forecast_for_date(weather_data, target_forecast_date)

                                    if day_forecast:
                                        day_name = target_forecast_date.strftime('%A, %B %d')

                                        forecast_data.append({
                                            'Day': day_name,
                                            'Temperature': f"{day_forecast['temperature']:.0f}°F",
                                            'Wind': f"{day_forecast['wind_speed']:.0f} mph",
                                            'Rain Chance': f"{day_forecast['precipitation_probability']:.0f}%",
                                            'Conditions': day_forecast.get('narrative', '')
                                        })

                                if forecast_data:
                                    st.dataframe(pd.DataFrame(forecast_data), use_container_width=True)
                        else:
                            st.error("Could not retrieve weather data")

                    except Exception as e:
                        st.error(f"Error getting weather: {e}")

    with tab5:
        st.header("📋 River Database Explorer")

        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Rivers", len(df))
        with col2:
            if 'Class' in df.columns:
                st.metric("Available Classes", df['Class'].nunique())
            else:
                st.metric("Max Whitewater", df['Whitewater'].max())
        with col3:
            avg_length = df['Length'].mean() if 'Length' in df.columns else 0
            st.metric("Avg Length", f"{avg_length:.1f} mi")
        with col4:
            unique_gauges = df['Gauge_ID'].nunique()
            st.metric("USGS Gauges", unique_gauges)

        # Search and filter
        st.subheader("Search Rivers")
        search_term = st.text_input("Search by river name:", placeholder="e.g., Youghiogheny")

        # Apply search filter
        display_df = filtered_df.copy()
        if search_term:
            mask = display_df['Name'].str.contains(search_term, case=False, na=False)
            display_df = display_df[mask]

        # Display results
        st.subheader(f"Rivers ({len(display_df)} shown)")

        # Column selection for display
        available_cols = display_df.columns.tolist()
        default_cols = ['Name', 'Route', 'Length', 'Whitewater', 'Min_Level', 'Max_Level']
        if 'Class' in available_cols:
            default_cols = ['Name', 'Route', 'Length', 'Class', 'Min_Level', 'Max_Level']

        display_cols = [col for col in default_cols if col in available_cols]

        # Show the dataframe
        st.dataframe(display_df[display_cols], use_container_width=True)

        # Export functionality
        if len(display_df) > 0:
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Filtered Data as CSV",
                data=csv,
                file_name=f"filtered_rivers_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

else:
    # Instructions when no CSV file is found
    st.error("❌ No valid river data CSV file found")

    with st.expander("📋 Required CSV Files"):
        st.markdown("""
        **Place one of these CSV files in the same directory as this app:**
        - `river_specs.csv` (preferred - matches your uploaded file)
        - `pa_rivers_table.csv` (alternative)
        - `rivers.csv`
        - `river_data.csv`
        - Any `.csv` file with river data

        **Required columns:**
        - **Name**: River name
        - **Route**: Specific section/route (optional)
        - **Length**: Length in miles (optional)
        - **Whitewater** OR **Class**: Difficulty level
        - **Zipcode**: ZIP code for weather
        - **Gauge_ID**: USGS gauge ID (8 digits)
        - **Min_Level**: Minimum paddleable level (feet)
        - **Max_Level**: Maximum safe level (feet)
        - **Min_cfs**, **Max_cfs**: Flow range (optional)
        """)

    with st.expander("🔧 Required Python Libraries"):
        st.code("""
pip install streamlit pandas dataretrieval requests
        """)

# Footer
st.markdown("---")
st.markdown("🚣 **Pennsylvania River Paddling Conditions** • Data from USGS and Open-Meteo APIs • Built with Streamlit")
