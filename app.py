import streamlit as st
import redis
import json
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv
import io

# Load environment variables
load_dotenv()

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", None)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_USERNAME = os.getenv("REDIS_USERNAME", "default")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_SSL = os.getenv("REDIS_SSL", "False").lower() == "true"

def connect_redis():
    try:
        if REDIS_URL:
            r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        else:
            r = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                username=REDIS_USERNAME,
                password=REDIS_PASSWORD,
                ssl=REDIS_SSL,
                decode_responses=True
            )
        r.ping()
        return r
    except Exception as e:
        st.error(f"Failed to connect to Redis: {e}")
        return None

def fetch_chat_data(r):
    all_data = []
    # Adjust pattern if needed
    keys = r.keys("AICOV_*:PARENTCONV_*")
    
    for key in keys:
        try:
            # Parse User ID and Conversation ID from key
            # Example key: AICOV_596:PARENTCONV_1
            try:
                parts = key.split(":")
                user_id = parts[0].replace("AICOV_", "")
                conv_id = parts[1].replace("PARENTCONV_", "")
            except Exception:
                user_id = "N/A"
                conv_id = "N/A"

            val = r.get(key)
            if not val:
                continue
            
            chat_payload = json.loads(val)
            
            # The payload is expected to be a list of messages
            # We want to pair User and Assistant messages
            current_user_msg = None
            
            for msg in chat_payload:
                role = msg.get("role")
                content = msg.get("content")
                timestamp = msg.get("timestamp")
                
                if role == "user":
                    current_user_msg = {"query": content, "timestamp": timestamp}
                elif role == "assistant" and current_user_msg:
                    # Found a pair
                    all_data.append({
                        "User ID": user_id,
                        "Conversation ID": conv_id,
                        "Timestamp": current_user_msg["timestamp"],
                        "Query (User)": current_user_msg["query"],
                        "Response (AI)": content,
                        "Key": key
                    })
                    current_user_msg = None # Reset for next pair
                    
        except Exception as e:
            st.warning(f"Error processing key {key}: {e}")
            
    return pd.DataFrame(all_data)

def main():
    st.set_page_config(page_title="Redis Chat Report", layout="wide")
    st.title("📊 Redis Chat Report Exporter")
    
    # Sidebar for Refresh and Info
    with st.sidebar:
        st.info(f"Connected to: {REDIS_HOST}:{REDIS_PORT}")
        if st.button("🔄 Refresh Data"):
            st.rerun()

    r = connect_redis()
    if not r:
        st.stop()

    with st.spinner("Fetching data from Redis..."):
        df = fetch_chat_data(r)

    if df.empty:
        st.warning("No chat data found in Redis.")
        return

    # Convert timestamp to datetime for filtering
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    df = df.sort_values(by='Timestamp', ascending=False)

    # Filtering UI
    st.subheader("Filters")
    col1, col2 = st.columns(2)
    
    with col1:
        min_date = df['Timestamp'].min().date()
        max_date = df['Timestamp'].max().date()
        start_date = st.date_input("Start Date", min_date)
        
    with col2:
        end_date = st.date_input("End Date", max_date)

    # Apply filters
    mask = (df['Timestamp'].dt.date >= start_date) & (df['Timestamp'].dt.date <= end_date)
    filtered_df = df.loc[mask].copy()

    # Display Data
    st.subheader(f"Results ({len(filtered_df)} chats)")
    
    # Format timestamp for display
    display_df = filtered_df.copy()
    display_df['Timestamp'] = display_df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    st.dataframe(display_df, use_container_width=True)

    # Export to Excel
    if not filtered_df.empty:
        towrite = io.BytesIO()
        # Use XlsxWriter engine which supports UTF-8 well
        with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
            # Excel does not support timezone-aware datetimes
            excel_df = filtered_df.copy()
            if not excel_df.empty and pd.api.types.is_datetime64_any_dtype(excel_df['Timestamp']):
                excel_df['Timestamp'] = excel_df['Timestamp'].dt.tz_localize(None)
            
            excel_df.to_excel(writer, index=False, sheet_name='Chat Report')
            # Optional: Adjust column widths
            worksheet = writer.sheets['Chat Report']
            for i, col in enumerate(filtered_df.columns):
                column_len = filtered_df[col].astype(str).str.len().max()
                column_len = max(column_len, len(col)) + 2
                worksheet.set_column(i, i, min(column_len, 50))
        
        towrite.seek(0)
        
        st.download_button(
            label="📥 Download Excel Report",
            data=towrite,
            file_name=f"redis_chat_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()
