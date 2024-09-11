from datetime import datetime, timedelta

def convert_to_previous_year_same_weekday(date):
    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d')
    
    # Go back 52 weeks (364 days)
    prev_year_date = date - timedelta(days=364)
    
    # Adjust if necessary to get the same weekday
    while prev_year_date.weekday() != date.weekday():
        prev_year_date -= timedelta(days=1)
    
    return prev_year_date

# Example usage
start_date = datetime(2023, 9, 11)  # A Monday
result = convert_to_previous_year_same_weekday(start_date)

print(f"Original date: {start_date.strftime('%Y-%m-%d')} ({start_date.strftime('%A')})")
print(f"Previous year same weekday: {result.strftime('%Y-%m-%d')} ({result.strftime('%A')})")