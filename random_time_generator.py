import random
from datetime import datetime, timedelta

# Function to generate random time intervals
# Takes the number of intervals and duration of each interval in seconds

def generate_random_intervals(num_intervals=3, duration_seconds=86400):  # Changed to 86400 (24 hours)
    intervals = []
    current_time = datetime.utcnow()
    for _ in range(num_intervals):
        # Random time within the past 30 days (30 * 86400 seconds)
        end_time = current_time - timedelta(seconds=random.randint(0, 30 * 86400))
        start_time = end_time - timedelta(seconds=duration_seconds)
        # Format dates in the format that DBeaver expects: 'YYYY-MM-DD HH:MM:SS'
        formatted_start = start_time.strftime('%Y-%m-%d %H:%M:%S')
        formatted_end = end_time.strftime('%Y-%m-%d %H:%M:%S')
        intervals.append((formatted_start, formatted_end))
    return intervals

# Example usage
intervals = generate_random_intervals()
for start, end in intervals:
    print(f"Start: {start}, End: {end}")
