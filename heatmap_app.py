import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from matplotlib.widgets import RectangleSelector

# Read in Data
pickup_data = pd.read_csv('6_pickup.csv')
full_refundable_rates_data = pd.read_csv('data-1725876476777.csv')
bookings_forecast_data = pd.read_csv('bookings_forecast.csv')

def create_normalized_heatmap(data, start_date, end_date, value_column='refundable_rate', cmap='rainbow'):
    # Convert 'report_date' and 'stay_date' to datetime and then to date
    data['report_date'] = pd.to_datetime(data['report_date']).dt.date
    data['stay_date'] = pd.to_datetime(data['stay_date']).dt.date
    
    # Convert start_date and end_date to datetime.date objects if they're not already
    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()
    
    # Create a date range for both axes
    all_dates = pd.date_range(start=start_date, end=end_date).date
    
    # Create a pivot table with the full date range
    pivot_data = data.pivot_table(values=value_column, index='stay_date', columns='report_date', aggfunc='sum')
    pivot_data = pivot_data.reindex(index=all_dates, columns=all_dates, fill_value=np.nan)
    
    # Check for any infinities or very large values
    if np.isinf(pivot_data).any().any() or (np.abs(pivot_data) > 1e10).any().any():
        print("Warning: Infinite or very large values detected in the data.")
        pivot_data = pivot_data.replace([np.inf, -np.inf], np.nan)
    
    # Normalize the data to 0-1 range, handling potential division by zero
    pivot_data_min = pivot_data.min().min()
    pivot_data_max = pivot_data.max().max()
    if pivot_data_min == pivot_data_max:
        print("Warning: All values are the same. Cannot normalize.")
        normalized_data = pivot_data
    else:
        normalized_data = (pivot_data - pivot_data_min) / (pivot_data_max - pivot_data_min)
    
    return normalized_data

def plot_heatmap(data, title, value_column, start_date, end_date, cmap='rainbow'):
    # Check if the data is not empty
    if not data.empty:
        # Set up the plot style
        plt.style.use('default')
        
        # Create the figure and axes (increased figure size)
        fig, ax = plt.subplots(figsize=(24, 20))
        
        # Create the heatmap using seaborn
        sns.heatmap(
            data,
            cmap=cmap,
            annot=False,
            fmt='.2f',
            cbar_kws={'label': f'Normalized {value_column}'},
            ax=ax,
            mask=data.isnull()
        )
        
        # Set title and labels
        ax.set_title(f'{title}\nfor Dates from {start_date.strftime("%d/%m/%Y")} to {end_date.strftime("%d/%m/%Y")}',
                     fontsize=24, fontweight='bold', pad=20)
        ax.set_xlabel('Report Date', fontsize=18, labelpad=10)
        ax.set_ylabel('Stay Date', fontsize=18, labelpad=10)
        
        # Calculate tick positions and labels
        num_ticks = 15  # Increased number of ticks
        tick_indices = np.linspace(0, len(data.index) - 1, num_ticks, dtype=int)
        tick_dates = [data.index[i] for i in tick_indices]
        tick_labels = [date.strftime('%d/%m/%Y') for date in tick_dates]
        
        # Set x-axis and y-axis ticks
        ax.set_xticks(tick_indices)
        ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=12)
        ax.set_yticks(tick_indices)
        ax.set_yticklabels(tick_labels, fontsize=12)
        
        # Remove gridlines
        ax.grid(False)
        
        # Adjust layout
        plt.tight_layout()
        
        return fig, ax
    else:
        print(f"No data found for dates from {start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}.")
        return None, None

# Streamlit app
st.title('Heatmap Dashboard')

# Date range selection (with British format display)
start_date = st.date_input("Start Date", value=pd.to_datetime('2023-01-01'), format="DD/MM/YYYY")
end_date = st.date_input("End Date", value=pd.to_datetime('2024-07-10'), format="DD/MM/YYYY")

# Color map selection
cmap = st.selectbox("Select Color Map", options=['rainbow', 'coolwarm', 'viridis', 'plasma', 'inferno', 'magma', 'YlGnBu', 'RdYlBu', 'PuRd'])

# Create normalized data for each dataset
pickup_norm = create_normalized_heatmap(pickup_data, start_date, end_date, 'total_rooms', cmap)
full_refundable_norm = create_normalized_heatmap(full_refundable_rates_data, start_date, end_date, 'refundable_rate', cmap)
bookings_norm = create_normalized_heatmap(bookings_forecast_data, start_date, end_date, 'revenue', cmap)

# Create tabs for each heatmap
tab1, tab2, tab3 = st.tabs(["Pickup Data", "Forecasted Revenue Data", "Full Refundable Rates Data"])

# Function to handle zooming
def zoom_factory(ax, base_scale=1.1):
    def zoom_fun(event):
        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()

        xdata = event.xdata
        ydata = event.ydata

        if event.button == 'up':
            scale_factor = base_scale
        elif event.button == 'down':
            scale_factor = 1/base_scale
        else:
            scale_factor = 1

        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

        relx = (cur_xlim[1] - xdata)/(cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata)/(cur_ylim[1] - cur_ylim[0])

        ax.set_xlim([xdata - new_width * (1-relx), xdata + new_width * (relx)])
        ax.set_ylim([ydata - new_height * (1-rely), ydata + new_height * (rely)])
        ax.figure.canvas.draw()

    fig = ax.get_figure()
    fig.canvas.mpl_connect('scroll_event', zoom_fun)

    return zoom_fun

# Plot heatmaps in tabs
with tab1:
    fig1, ax1 = plot_heatmap(pickup_norm, 'Heatmap of Total Rooms', 'total_rooms', start_date, end_date, cmap)
    if fig1 is not None:
        zoom_factory(ax1)
        st.pyplot(fig1)

with tab2:
    fig2, ax2 = plot_heatmap(bookings_norm, 'Heatmap of Forecasted Revenue', 'revenue', start_date, end_date, cmap)
    if fig2 is not None:
        zoom_factory(ax2)
        st.pyplot(fig2)

with tab3:
    fig3, ax3 = plot_heatmap(full_refundable_norm, 'Heatmap of Refundable Rates', 'refundable_rate', start_date, end_date, cmap)
    if fig3 is not None:
        zoom_factory(ax3)
        st.pyplot(fig3)

st.caption("Use the mouse wheel to zoom in and out on the heatmaps.")