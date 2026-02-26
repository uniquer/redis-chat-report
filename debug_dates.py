import pandas as pd
from app import connect_redis, fetch_chat_data
r = connect_redis()
if r:
    df = fetch_chat_data(r)
    print("Raw Timestamps:")
    print(df['Timestamp'].head())
    
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    print("\nParsed Timestamps:")
    print(df['Timestamp'].head())
    print("\nDate extractions:")
    print(df['Timestamp'].dt.date.head())
    
    # Test grouping
    dash_df = df.copy()
    dash_df['Date'] = dash_df['Timestamp'].dt.date
    grouped = dash_df.groupby('Date').agg(Queries=('Key', 'count'))
    print("\nGrouped:")
    print(grouped)
    
