import pandas as pd
from app import connect_redis, fetch_chat_data
r = connect_redis()
if r:
    df = fetch_chat_data(r)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    print(df['Timestamp'].dt.date.value_counts())
