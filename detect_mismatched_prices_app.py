import psycopg2
import pandas as pd
from sqlalchemy import create_engine
import csv
import numpy as np
import streamlit as st
import os

host = "hotel-cloud-db-dev.cy9have47g8u.eu-west-2.rds.amazonaws.com"
database = "hotelcloud"
user = "hotelcloudadmin"
password = "aX2X1i7z4CUUQihoSAdasd"
port = "5432"  # default PostgreSQL port

#Read in data from all booking.com channels with rate code FLRA1

SQL_QUERY = """
WITH rate_updates AS (
    SELECT DISTINCT ON (u.hotel_id, u.date_update::date)
        u.hotel_id,
        u.rate_update_id,
        u.date_update::date AS report_date
    FROM rate_update u
    WHERE
        u.hotel_id = 6
        AND u.date_update::date >= '2022-05-01'
        AND u.date_update::date < current_date
    ORDER BY u.hotel_id, u.date_update::date, u.date_update DESC
),

-- Subquery 2: ota_rooms
-- This subquery gathers information about rooms available on Online Travel Agencies (OTAs)
ota_rooms AS (
    SELECT DISTINCT
        o.ota_room_id,
        r."name",
        o.room_id
    FROM ota_room o
    JOIN room r ON r.room_id = o.room_id
    LEFT OUTER JOIN room_category rc ON rc.room_category_id = r.room_category_id
    WHERE o.hotel_id = 6
),

-- Subquery 3: rate_data
-- This subquery collects rate information for rooms, including refundable and non-refundable rates
rate_data AS (
    SELECT
        MIN(CASE WHEN r.refundable THEN r.amount END) AS refundable_rate,
        MIN(CASE WHEN NOT r.refundable THEN r.amount END) AS non_refundable_rate,
        u.hotel_id,
        u.report_date,
        r.stay_date,
        o.name AS room_name,
        r.adultcount
    FROM
        rate_new r
    JOIN
        rate_updates u ON r.rate_update_id = u.rate_update_id
    JOIN
        ota_rooms o ON o.ota_room_id = r.ota_room_id
    GROUP BY
        u.hotel_id,
        u.report_date,
        r.stay_date,
        o.name,
        r.adultcount
),

-- Subquery 4: booking
-- This subquery gathers detailed booking information, including guest details, room information, and financial data
booking AS (
    SELECT
        p.first_name,
        p.last_name,
        b.hotel_id,
        b.room_id,
        b.created_date::date AS created_date,
        b.check_in,
        b.check_out, 
        b.cancel_date::date AS cancel_date,
        b.booking_reference, 
        EXTRACT(DAY FROM (dt."date" - b.created_date::date)) AS lead_in,
        b.booking_channel_name,
        b.booking_status, 
        b.adults,
        b.rate_plan_code,
        b.nights,
        b.room_revenue,
        ROUND(COALESCE(br.total_revenue, b.total_revenue / NULLIF(b.nights, 0)),2) AS total_revenue_x,
        Round(b.total_revenue * 1.2) as exp_rate,
        b.total_revenue_after_tax,
        h."name" AS hotel_name,
        r."name" AS room_name,
        r.code as room_code,
        dt."date" AS stay_date
    FROM
        booking b
    JOIN profile p ON b.profile_id = p.profile_id
    JOIN hotel h ON b.hotel_id = h.hotel_id
    JOIN room r ON b.room_id = r.room_id
    JOIN caldate dt ON b.check_in <= dt."date"
        AND (b.check_out > dt."date" OR (b.check_in = b.check_out AND dt."date" = b.check_in))
    LEFT JOIN booking_rate br ON b.booking_id = br.booking_rate_id
    WHERE
        b.created_date >= '2022-01-01'
        AND b.hotel_id = '6'
        AND b.booking_channel_name IN (
 'booking.com', 'Booking.com', 'Booking.Com', 'Booking.Com ', 'BOOKING.COM',
 'BOOKING.COM ', 'booking.com bv', 'Booking.com B.V.', 'BOOKING.COM BV (EUR NL)',
 'Booking.com Limited', 'BOOKING.COM-NOCOMMINBESTCHEQUE', 'Booking.com (Old)',
 'Booking.comVCC', 'Booking.com VCC', 'booking.com (Virtual card',
 'Import/Booking.com', 'Worldwide Booking.com - Guestlink'
)
        AND b.nights = 1
        AND b.rate_plan_code = 'FLRA1'
)

-- Main Query
-- This part combines the booking data with the rate data and filters for discrepancies between expected and actual rates
SELECT b.*, r.*
FROM booking AS b
JOIN caldate dt ON b.check_in <= dt."date"
    AND (b.check_out > dt."date" OR (b.check_in = b.check_out AND dt."date" = b.check_in))
LEFT JOIN rate_data AS r ON r.adultcount = b.adults 
    AND r.room_name = b.room_name 
    AND b.created_date = r.report_date 
    AND dt.date = r.stay_date
WHERE b.exp_rate <> r.refundable_rate
ORDER BY b.nights ASC;
"""


# Database connection function
def connect_to_db():
    try:
        connection = psycopg2.connect(
            host = "hotel-cloud-db-dev.cy9have47g8u.eu-west-2.rds.amazonaws.com",
            database = "hotelcloud",
            user = "hotelcloudadmin",
            password = "aX2X1i7z4CUUQihoSAdasd",
            port = "5432" 
        )
        return connection
    except (Exception, psycopg2.Error) as error:
        st.error(f"Error while connecting to PostgreSQL: {error}")
        return None

# Function to fetch data and save to CSV
def fetch_and_save_data(connection, sql_query):

    filename = "full_rates_data.csv"

    if os.path.exists(filename):
        st.info(f"File {filename} already exists. Using existing data.")
        return pd.read_csv(filename)
        
    try:
        cursor = connection.cursor()
        cursor.execute(sql_query)
        results = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        
        filename = "full_rates_data.csv"
        with open(filename, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(column_names)
            csvwriter.writerows(results)
        
        st.success(f"Data has been written to {filename}")
        return pd.read_csv(filename)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None
    finally:
        if connection:
            cursor.close()
            connection.close()

# Data processing function
def process_data(df):
    rates_comparison_df = df[['booking_reference', 'room_revenue', 'total_revenue_after_tax', 'refundable_rate']]
    
    rates_comparison_df['total_revenue_after_tax_and_discount'] = rates_comparison_df['room_revenue']*1.2/0.9
    rates_comparison_df['total_revenue_after_tax_and_two_discounts'] = rates_comparison_df['room_revenue']*1.2/0.81
    rates_comparison_df['total_revenue_after_tax_and_discount_g2'] = rates_comparison_df['room_revenue']*1.2/0.85
    rates_comparison_df['total_revenue_after_tax_and_discount_g2_and_app_discount'] = rates_comparison_df['room_revenue']*1.2/0.765
    rates_comparison_df['total_revenue_after_tax_and_discount_g3'] = rates_comparison_df['room_revenue']*1.2/0.80
    rates_comparison_df['total_revenue_after_tax_and_discount_g3_and_app_discount'] = rates_comparison_df['room_revenue']*1.2/0.72
    
    return rates_comparison_df

# Comparison function
def compare_rates(df):
    comparisons = [
        ("Genius Level 1", df['total_revenue_after_tax_and_discount']),
        ("Genius Level 1 + App Discount", df['total_revenue_after_tax_and_two_discounts']),
        ("Genius Level 2", df['total_revenue_after_tax_and_discount_g2']),
        ("Genius Level 2 + App Discount", df['total_revenue_after_tax_and_discount_g2_and_app_discount']),
        ("Genius Level 3", df['total_revenue_after_tax_and_discount_g3']),
        ("Genius Level 3 + App Discount", df['total_revenue_after_tax_and_discount_g3_and_app_discount'])
    ]
    
    for name, column in comparisons:
        match = np.isclose(column, df['refundable_rate'], atol=1)
        num_matches = match.sum()
        num_mismatches = (~match).sum()
        st.write(f"\nComparison of {name} with refundable rate:")
        st.write(f"Number of matches: {num_matches}, Percentage of matches: {num_matches/len(df)*100:.2f}%")
        st.write(f"Number of mismatches: {num_mismatches}")

# Mismatch analysis function
def analyze_mismatches(df):
    comparisons = [
        df['total_revenue_after_tax_and_discount'],
        df['total_revenue_after_tax_and_two_discounts'],
        df['total_revenue_after_tax_and_discount_g2'],
        df['total_revenue_after_tax_and_discount_g2_and_app_discount'],
        df['total_revenue_after_tax_and_discount_g3'],
        df['total_revenue_after_tax_and_discount_g3_and_app_discount']
    ]
    
    all_mismatches = np.all([~np.isclose(comp, df['refundable_rate'], atol=1) for comp in comparisons], axis=0)
    mismatches_df = df[all_mismatches]
    
    st.write(f"\nTotal number of rows: {len(df)}")
    st.write(f"Number of mismatches (not matching single or double discounts): {len(mismatches_df)}")
    
    if not mismatches_df.empty:
        st.write("\nFirst few rows of all mismatches (values rounded to nearest integer):")
        numeric_columns = mismatches_df.select_dtypes(include=[np.number]).columns
        mismatches_df_rounded = mismatches_df.copy()
        mismatches_df_rounded[numeric_columns] = mismatches_df_rounded[numeric_columns].round().astype(int)
        st.dataframe(mismatches_df_rounded.head())

# Upgrade analysis function
def analyze_upgrades(df):
    def ends_with_9(x):
        return np.abs(x % 10 - 9) < 0.1
    
    columns_to_check = [
        'total_revenue_after_tax',
        'total_revenue_after_tax_and_discount',
        'total_revenue_after_tax_and_two_discounts',
        'total_revenue_after_tax_and_discount_g2',
        'total_revenue_after_tax_and_discount_g2_and_app_discount',
        'total_revenue_after_tax_and_discount_g3',
        'total_revenue_after_tax_and_discount_g3_and_app_discount'
    ]
    
    any_ends_with_9 = np.any([ends_with_9(df[col]) for col in columns_to_check], axis=0)
    possible_upgrades_df = df[any_ends_with_9]
    
    st.write(f"\nNumber of possible upgrades (i.e. ending with 9): {len(possible_upgrades_df)}")
    
    if not possible_upgrades_df.empty:
        st.write("\nFirst few rows of possible upgrades (rounded to 2 decimal places):")
        upgrades_display = possible_upgrades_df[['booking_reference', 'total_revenue_after_tax',
        'total_revenue_after_tax_and_discount',
        'total_revenue_after_tax_and_two_discounts']].round(2)
        st.dataframe(upgrades_display.head())

# Main Streamlit app
def main():
    st.title("Hotel Rates Analysis")
    
    if st.button("Fetch Data and Analyze"):
        connection = connect_to_db()
        if connection:
            df = fetch_and_save_data(connection, SQL_QUERY)
            if df is not None:
                rates_comparison_df = process_data(df)
                
                st.header("Rate Comparisons")
                compare_rates(rates_comparison_df)
                
                st.header("Mismatch Analysis")
                analyze_mismatches(rates_comparison_df)
                
                st.header("Upgrade Analysis")
                analyze_upgrades(rates_comparison_df)

if __name__ == "__main__":
    main()