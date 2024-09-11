import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import plotly.graph_objects as go
from PIL import Image
import plotly.colors as pc
import math

st.set_page_config(layout="wide")

# Read in Data
@st.cache_data
def load_data():
    pickup_data = pd.read_csv('6_pickup.csv')
    full_refundable_rates_data = pd.read_csv('full_refundables_rate_data.csv')
    bookings_forecast_data = pd.read_csv('bookings_forecast.csv')
    return pickup_data, full_refundable_rates_data, bookings_forecast_data

pickup_data, full_refundable_rates_data, bookings_forecast_data = load_data()

def convert_to_previous_year(start_date, end_date):
    # Convert input strings to datetime objects if they're not already
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

    # Function to get the same weekday from previous year
    def get_previous_year_same_weekday(date):
        prev_year_date = date - timedelta(days=364)
        while prev_year_date.weekday() != date.weekday():
            prev_year_date -= timedelta(days=1)
        return prev_year_date

    # Convert to previous year maintaining the same weekday
    prev_start = get_previous_year_same_weekday(start_date)
    prev_end = get_previous_year_same_weekday(end_date)

    return prev_start, prev_end

@st.cache_data
def create_normalized_heatmap(data, start_date, end_date, value_column='refundable_rate'):
    # Convert 'report_date' and 'stay_date' to datetime
    data['report_date'] = pd.to_datetime(data['report_date'])
    data['stay_date'] = pd.to_datetime(data['stay_date'])
    
    # Ensure start_date and end_date are datetime objects
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    # Create a date range for both axes
    all_dates = pd.date_range(start=start_date, end=end_date)
    
    # Create a pivot table with the full date range
    pivot_data = data.pivot_table(values=value_column, index='stay_date', columns='report_date', aggfunc='sum')
    pivot_data = pivot_data.reindex(index=all_dates, columns=all_dates, fill_value=np.nan)
    
    # Check for any infinities or very large values
    if np.isinf(pivot_data).any().any() or (np.abs(pivot_data) > 1e10).any().any():
        print("Warning: Infinite or very large values detected in the data.")
        pivot_data = pivot_data.replace([np.inf, -np.inf], np.nan)
    
    return pivot_data

def plot_heatmap_plotly(data, title, value_column, start_date, end_date, colorbar_min=None, colorbar_max=None):
    # Set default values if not provided
    if colorbar_min is None:
        colorbar_min = data.values.min()
    if colorbar_max is None:
        colorbar_max = data.values.max()

    # Create a custom colorscale
    colors = pc.sequential.Rainbow
    colorscale = pc.make_colorscale(['rgb(255,255,255)'] + colors)

    heatmap_args = {
        'z': data.values,
        'x': data.columns,
        'y': data.index,
        'colorscale': colorscale,
        'zmin': colorbar_min,
        'zmax': colorbar_max,
        'colorbar': dict(
            title=value_column,
            orientation='h',
            y=-0.15,
            yanchor='top',
            thickness=20,
            len=0.9
        )
    }

    fig = go.Figure(data=go.Heatmap(**heatmap_args))
    
    layout = dict(
        title=f'{title}<br>for Dates from {start_date.strftime("%d/%m/%Y")} to {end_date.strftime("%d/%m/%Y")}',
        xaxis_title='Report Date',
        yaxis_title='Stay Date',
        height=700,
        margin=dict(b=150)
    )
    
    fig.update_layout(layout)
    fig.update_yaxes(autorange="reversed")
    
    return fig, layout

def calculate_step_size(min_value, max_value):
    range_value = max_value - min_value
    if range_value == 0:
        return 0.1  # Default small step if there's no range
    magnitude = 10 ** math.floor(math.log10(range_value))
    scaled_range = range_value / magnitude
    if scaled_range < 1:
        step_size = magnitude / 10
    elif scaled_range < 5:
        step_size = magnitude / 2
    else:
        step_size = magnitude
    return step_size

# Calculate step sizes for each dataset
pickup_step = calculate_step_size(pickup_data['total_rooms'].min(), pickup_data['total_rooms'].max())
revenue_step = calculate_step_size(bookings_forecast_data['revenue'].min(), bookings_forecast_data['revenue'].max())
rate_step = calculate_step_size(full_refundable_rates_data['refundable_rate'].min(), full_refundable_rates_data['refundable_rate'].max())

# Streamlit app

col1, col2 = st.columns([1, 3])

# Add the logo to the first (narrower) column
with col1:
    logo = Image.open('hotelcloud_logo.png')
    st.image(logo, width=300)

    # Move date inputs to the first column
    start_date = st.date_input("Start Date", value=date(2023, 1, 1), format="DD/MM/YYYY")
    end_date = st.date_input("End Date", value=date(2024, 7, 10), format="DD/MM/YYYY")

    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Add checkbox to enable custom colorbar range
    custom_range = st.checkbox("Use custom colorbar range")
    
    # Add sliders for colorbar range, only shown if custom range is enabled
    colorbar_min = None
    colorbar_max = None
    if custom_range:
        # Calculate global min and max values
        global_min = min(pickup_data['total_rooms'].min(), 
                         bookings_forecast_data['revenue'].min(), 
                         full_refundable_rates_data['refundable_rate'].min())
        global_max = max(pickup_data['total_rooms'].max(), 
                         bookings_forecast_data['revenue'].max(), 
                         full_refundable_rates_data['refundable_rate'].max())
        
        st.write(f"Global range: {global_min:.2f} to {global_max:.2f}")
        
        colorbar_min = st.slider("Colorbar Minimum", 
                                 min_value=float(global_min), 
                                 max_value=float(global_max), 
                                 value=float(global_min), 
                                 step=0.1)
        colorbar_max = st.slider("Colorbar Maximum", 
                                 min_value=float(global_min), 
                                 max_value=float(global_max), 
                                 value=float(global_max), 
                                 step=0.1)

    # Add more vertical space
    st.markdown("<br><br><br>", unsafe_allow_html=True)

# Calculate previous year dates
prev_start_date, prev_end_date = convert_to_previous_year(start_date, end_date)

# Precompute all normalized data and graphs
@st.cache_data
def precompute_graphs(pickup_data, full_refundable_rates_data, bookings_forecast_data, start_date, end_date, prev_start_date, prev_end_date, colorbar_min=None, colorbar_max=None):
    pickup_norm = create_normalized_heatmap(pickup_data, start_date, end_date, 'total_rooms')
    pickup_norm_prev = create_normalized_heatmap(pickup_data, prev_start_date, prev_end_date, 'total_rooms')
    full_refundable_norm = create_normalized_heatmap(full_refundable_rates_data, start_date, end_date, 'refundable_rate')
    full_refundable_norm_prev = create_normalized_heatmap(full_refundable_rates_data, prev_start_date, prev_end_date, 'refundable_rate')
    bookings_norm = create_normalized_heatmap(bookings_forecast_data, start_date, end_date, 'revenue')
    bookings_norm_prev = create_normalized_heatmap(bookings_forecast_data, prev_start_date, prev_end_date, 'revenue')

    pickup_fig, pickup_layout = plot_heatmap_plotly(pickup_norm, 'Heatmap of Total Rooms', 'Total Rooms', start_date, end_date, colorbar_min, colorbar_max)
    pickup_fig_prev, pickup_layout_prev = plot_heatmap_plotly(pickup_norm_prev, 'Heatmap of Total Rooms (Previous Year)', 'Total Rooms', prev_start_date, prev_end_date, colorbar_min, colorbar_max)
    bookings_fig, bookings_layout = plot_heatmap_plotly(bookings_norm, 'Heatmap of Forecasted Revenue', 'Revenue', start_date, end_date, colorbar_min, colorbar_max)
    bookings_fig_prev, bookings_layout_prev = plot_heatmap_plotly(bookings_norm_prev, 'Heatmap of Forecasted Revenue (Previous Year)', 'Revenue', prev_start_date, prev_end_date, colorbar_min, colorbar_max)
    full_refundable_fig, full_refundable_layout = plot_heatmap_plotly(full_refundable_norm, 'Heatmap of Refundable Rates', 'Refundable Rate', start_date, end_date, colorbar_min, colorbar_max)
    full_refundable_fig_prev, full_refundable_layout_prev = plot_heatmap_plotly(full_refundable_norm_prev, 'Heatmap of Refundable Rates (Previous Year)', 'Refundable Rate', prev_start_date, prev_end_date, colorbar_min, colorbar_max)

    return (pickup_fig, pickup_fig_prev, bookings_fig, bookings_fig_prev, full_refundable_fig, full_refundable_fig_prev,
            pickup_layout, pickup_layout_prev, bookings_layout, bookings_layout_prev, full_refundable_layout, full_refundable_layout_prev)

# Unpack the returned values from precompute_graphs
(pickup_fig, pickup_fig_prev, bookings_fig, bookings_fig_prev, full_refundable_fig, full_refundable_fig_prev,
 pickup_layout, pickup_layout_prev, bookings_layout, bookings_layout_prev, full_refundable_layout, full_refundable_layout_prev) = precompute_graphs(
    pickup_data, full_refundable_rates_data, bookings_forecast_data, start_date, end_date, prev_start_date, prev_end_date, colorbar_min, colorbar_max
)

# Function to update layout while preserving zoom
def update_layout_preserve_zoom(fig, layout, zoom_info):
    if zoom_info:
        layout.update(
            xaxis=dict(range=zoom_info['xaxis.range']),
            yaxis=dict(range=zoom_info['yaxis.range'])
        )
    else:
        fig.update_layout(layout)
    return fig

# Use the second (wider) column for the tabs and plots
with col2:
    # Create tabs for each heatmap
    tab1, tab2, tab3 = st.tabs(["Pickup Data", "Forecasted Revenue Data", "Full Refundable Rates Data"])

    # Plot heatmaps in tabs
    with tab1:
        year_selection = st.radio("Select Year", ["Current Year", "Previous Year"], key="pickup_year_selection", horizontal=True)
        
        # Get the zoom info from session state (shared between Current Year and Previous Year)
        zoom_info = st.session_state.get('pickup_zoom_info', None)
        
        if year_selection == "Current Year":
            fig = update_layout_preserve_zoom(pickup_fig, pickup_layout, zoom_info)
        else:
            fig = update_layout_preserve_zoom(pickup_fig_prev, pickup_layout_prev, zoom_info)
        
        # Render the plot and save the current zoom state
        st.plotly_chart(fig, use_container_width=True)
        
        # Save the updated zoom state for future use
        st.session_state.pickup_zoom_info = {
            'xaxis.range': fig.layout.xaxis.range,
            'yaxis.range': fig.layout.yaxis.range
        }

    with tab2:
        year_selection = st.radio("Select Year", ["Current Year", "Previous Year"], key="bookings_year_selection", horizontal=True)
        
        zoom_info = st.session_state.get('bookings_zoom_info', None)
        
        if year_selection == "Current Year":
            fig = update_layout_preserve_zoom(bookings_fig, bookings_layout, zoom_info)
        else:
            fig = update_layout_preserve_zoom(bookings_fig_prev, bookings_layout_prev, zoom_info)
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.session_state.bookings_zoom_info = {
            'xaxis.range': fig.layout.xaxis.range,
            'yaxis.range': fig.layout.yaxis.range
        }

    with tab3:
        year_selection = st.radio("Select Year", ["Current Year", "Previous Year"], key="refundable_year_selection", horizontal=True)
        
        zoom_info = st.session_state.get('refundable_zoom_info', None)
        
        if year_selection == "Current Year":
            fig = update_layout_preserve_zoom(full_refundable_fig, full_refundable_layout, zoom_info)
        else:
            fig = update_layout_preserve_zoom(full_refundable_fig_prev, full_refundable_layout_prev, zoom_info)
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.session_state.refundable_zoom_info = {
            'xaxis.range': fig.layout.xaxis.range,
            'yaxis.range': fig.layout.yaxis.range
        }

    st.caption("Use the mouse to zoom and pan on the heatmaps.")

