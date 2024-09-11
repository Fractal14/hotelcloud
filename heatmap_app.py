import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import plotly.graph_objects as go
from PIL import Image

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
    
    # Convert to previous year
    prev_start = start_date.replace(year=start_date.year - 1)
    prev_end = end_date.replace(year=end_date.year - 1)
    
    # Adjust for leap years
    if start_date.month == 2 and start_date.day == 29:
        prev_start = prev_start - timedelta(days=1)
    if end_date.month == 2 and end_date.day == 29:
        prev_end = prev_end - timedelta(days=1)
    
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

def plot_heatmap_plotly(data, title, value_column, start_date, end_date):
    fig = go.Figure(data=go.Heatmap(
        z=data.values,
        x=data.columns,
        y=data.index,
        colorscale='Rainbow',
        colorbar=dict(
            title=value_column,
            orientation='h',
            y=-0.15,
            yanchor='top',
            thickness=20,
            len=0.9
        )
    ))
    
    fig.update_layout(
        title=f'{title}<br>for Dates from {start_date.strftime("%d/%m/%Y")} to {end_date.strftime("%d/%m/%Y")}',
        xaxis_title='Report Date',
        yaxis_title='Stay Date',
        height=700,  # Increased height to accommodate the colorbar
        margin=dict(b=150)  # Increased bottom margin for the colorbar
    )
    
    # Reverse the y-axis to have dates increasing downwards
    fig.update_yaxes(autorange="reversed")
    
    return fig

# Streamlit app


col1, col2 = st.columns([1, 3])

# Add the logo to the second (narrower) column
with col1:
    logo = Image.open('hotelcloud_logo.png')
    st.image(logo, width=300) 

# Global date range selection (with British format display)
# User input for date range
start_date = st.date_input("Start Date", value=date(2023, 1, 1), format="DD/MM/YYYY")
end_date = st.date_input("End Date", value=date(2024, 7, 10), format="DD/MM/YYYY")

# Calculate previous year dates
prev_start_date, prev_end_date = convert_to_previous_year(start_date, end_date)

# Precompute normalized data
pickup_norm = create_normalized_heatmap(pickup_data, start_date, end_date, 'total_rooms')
pickup_norm_prev = create_normalized_heatmap(pickup_data, prev_start_date, prev_end_date, 'total_rooms')

full_refundable_norm = create_normalized_heatmap(full_refundable_rates_data, start_date, end_date, 'refundable_rate')
full_refundable_norm_prev = create_normalized_heatmap(full_refundable_rates_data, prev_start_date, prev_end_date, 'refundable_rate')

bookings_norm = create_normalized_heatmap(bookings_forecast_data, start_date, end_date, 'revenue')
bookings_norm_prev = create_normalized_heatmap(bookings_forecast_data, prev_start_date, prev_end_date, 'revenue')

# Create tabs for each heatmap
tab1, tab2, tab3 = st.tabs(["Pickup Data", "Forecasted Revenue Data", "Full Refundable Rates Data"])

# Plot heatmaps in tabs
with tab1:
    year_selection = st.radio("Select Year", ["Current Year", "Previous Year"], key="pickup_year_selection", horizontal=True)
    st.empty()  # Add an empty space to maintain layout
    if year_selection == "Current Year":
        fig = plot_heatmap_plotly(pickup_norm, 'Heatmap of Total Rooms', 'Total Rooms', start_date, end_date)
    else:
        fig = plot_heatmap_plotly(pickup_norm_prev, 'Heatmap of Total Rooms (Previous Year)', 'Total Rooms', prev_start_date, prev_end_date)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    year_selection = st.radio("Select Year", ["Current Year", "Previous Year"], key="bookings_year_selection", horizontal=True)
    st.empty()  # Add an empty space to maintain layout
    if year_selection == "Current Year":
        fig = plot_heatmap_plotly(bookings_norm, 'Heatmap of Forecasted Revenue', 'Revenue', start_date, end_date)
    else:
        fig = plot_heatmap_plotly(bookings_norm_prev, 'Heatmap of Forecasted Revenue (Previous Year)', 'Revenue', prev_start_date, prev_end_date)
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    year_selection = st.radio("Select Year", ["Current Year", "Previous Year"], key="refundable_year_selection", horizontal=True)
    st.empty()  # Add an empty space to maintain layout
    if year_selection == "Current Year":
        fig = plot_heatmap_plotly(full_refundable_norm, 'Heatmap of Refundable Rates', 'Refundable Rate', start_date, end_date)
    else:
        fig = plot_heatmap_plotly(full_refundable_norm_prev, 'Heatmap of Refundable Rates (Previous Year)', 'Refundable Rate', prev_start_date, prev_end_date)
    st.plotly_chart(fig, use_container_width=True)

st.caption("Use the mouse to zoom and pan on the heatmaps.")