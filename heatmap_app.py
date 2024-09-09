import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Read in Data
pickup_data = pd.read_csv('6_pickup.csv')
mismatched_rates_data = pd.read_csv('rates_6_refundables.csv')
full_refundable_rates_data = pd.read_csv('data-1725876476777.csv')

def create_normalized_heatmap(data, start_date, end_date, value_column='refundable_rate', cmap='coolwarm'):
    # Convert 'report_date' and 'stay_date' to datetime and then to date
    data['report_date'] = pd.to_datetime(data['report_date']).dt.date
    data['stay_date'] = pd.to_datetime(data['stay_date']).dt.date
    
    # Create a pivot table
    pivot_data = data.pivot_table(values=value_column, index='report_date', columns='stay_date', aggfunc='sum')
    
    # Sort the index (report_date) and columns (stay_date)
    pivot_data = pivot_data.sort_index()
    pivot_data = pivot_data.reindex(columns=sorted(pivot_data.columns))
    
    # Convert start_date and end_date to datetime.date objects if they're not already
    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()
    
    # Select the date range
    date_range = pd.date_range(start=start_date, end=end_date).date
    filtered_data = pivot_data.loc[:, pivot_data.columns.isin(date_range)]
    
    # Normalize the data to 0-1 range
    normalized_data = (filtered_data - filtered_data.min().min()) / (filtered_data.max().max() - filtered_data.min().min())
    
    # Check if the filtered data is not empty
    if not normalized_data.empty:
        # Set up the plot style
        plt.style.use('default')
        
        # Create the figure and axes
        fig, ax = plt.subplots(figsize=(20, 16))
        
        # Reverse the order of the stay dates (y-axis)
        stay_dates = normalized_data.columns[::-1]
        
        # Create the heatmap using seaborn
        sns.heatmap(
            normalized_data.T.loc[stay_dates],
            cmap=cmap,
            annot=False,
            fmt='.2f',
            cbar_kws={'label': f'Normalized {value_column}'},
            yticklabels=30,  # Show every 30th label
            xticklabels=30,  # Show every 30th label
            ax=ax
        )
        
        # Set title and labels
        ax.set_title(f'Normalized Heatmap of {value_column}\nfor Stay Dates from {start_date} to {end_date}',
                     fontsize=20, fontweight='bold', pad=20)
        ax.set_xlabel('Report Date', fontsize=14, labelpad=10)
        ax.set_ylabel('Stay Date', fontsize=14, labelpad=10)
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right', fontsize=10)
        plt.yticks(fontsize=10)
        
        # Remove gridlines
        ax.grid(False)
        
        # Adjust layout
        plt.tight_layout()
        return fig
    else:
        return None

# Streamlit app
st.title('Normalized Heatmap Generator')

# Dataset selection
dataset_option = st.selectbox(
    "Choose a dataset",
    ("Pickup Data", "Mismatched Rates Data", "Full Refundable Rates Data")
)

if dataset_option == "Pickup Data":
    data = pickup_data
elif dataset_option == "Mismatched Rates Data":
    data = mismatched_rates_data
else:
    data = full_refundable_rates_data

# Date range selection
start_date = st.date_input("Start Date", value=pd.to_datetime('2023-01-01'))
end_date = st.date_input("End Date", value=pd.to_datetime('2024-07-10'))

# Column selection
value_column = st.selectbox("Select Value Column", options=data.columns)

# Color map selection
cmap = st.selectbox("Select Color Map", options=['coolwarm', 'viridis', 'plasma', 'inferno', 'magma', 'YlGnBu', 'RdYlBu', 'PuRd'])

# Generate button
if st.button("Generate Heatmap"):
    fig = create_normalized_heatmap(data, start_date, end_date, value_column, cmap)
    if fig:
        st.pyplot(fig)
    else:
        st.write(f"No data found for stay dates from {start_date} to {end_date}.")