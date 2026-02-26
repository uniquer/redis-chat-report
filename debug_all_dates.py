import pandas as pd
from app import connect_redis, fetch_chat_data
r = connect_redis()
if r:
    df = fetch_chat_data(r)
    print(f"Total rows fetched: {len(df)}")
    print("Unique dates:")
    if 'Timestamp' in df.columns:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        print(df['Timestamp'].dt.date.value_counts())
    else:
        print("No Timestamp column")
    
    # Check if there are keys that don't match the pattern
    all_keys = r.keys("*")
    print(f"Total keys in Redis: {len(all_keys)}")
    pattern_keys = r.keys("AICOV_*:PARENTCONV_*")
    print(f"Keys matching pattern: {len(pattern_keys)}")
    
