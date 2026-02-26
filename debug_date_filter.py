import pandas as pd
from app import connect_redis, fetch_chat_data
from datetime import date

r = connect_redis()
if r:
    df = fetch_chat_data(r)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    min_d = df['Timestamp'].min().date()
    max_d = df['Timestamp'].max().date()
    
    start_date = date(2026, 2, 26)
    end_date = date(2026, 2, 26)
    
    mask = (df['Timestamp'].dt.date >= start_date) & (df['Timestamp'].dt.date <= end_date)
    print(f"Total rows: {len(df)}, Filtered rows: {mask.sum()}, Dates: {min_d} to {max_d}")
