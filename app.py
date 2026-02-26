import streamlit as st
import redis
import json
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv
import io
import plotly.graph_objects as go

# Load environment variables
load_dotenv()

def connect_redis(env="Dev"):
    env_suffix = f"_{env.upper()}"
    redis_url = os.getenv(f"REDIS_URL{env_suffix}", None)
    redis_host = os.getenv(f"REDIS_HOST{env_suffix}", "localhost")
    redis_port = int(os.getenv(f"REDIS_PORT{env_suffix}", 6379))
    redis_username = os.getenv(f"REDIS_USERNAME{env_suffix}", "default")
    redis_password = os.getenv(f"REDIS_PASSWORD{env_suffix}", None)
    redis_ssl = os.getenv(f"REDIS_SSL{env_suffix}", "False").lower() == "true"
    
    try:
        if redis_url:
            r = redis.Redis.from_url(redis_url, decode_responses=True)
        else:
            r = redis.Redis(
                host=redis_host,
                port=redis_port,
                username=redis_username,
                password=redis_password,
                ssl=redis_ssl,
                decode_responses=True
            )
        r.ping()
        return r
    except Exception as e:
        st.error(f"Failed to connect to Redis {env}: {e}")
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
                    # Extract relatedQuestion and feedback from assistant message
                    related_q = msg.get("relatedQuestion")
                    if isinstance(related_q, dict):
                        rq_str = "\n".join([str(v) for v in related_q.values() if v])
                    else:
                        rq_str = str(related_q) if related_q else None
                        
                    feedback = msg.get("feedback") or {}
                    if isinstance(feedback, dict):
                        f_action = feedback.get("action")
                        f_remark = feedback.get("remark")
                        f_comment = feedback.get("comment")
                    else:
                        f_action = None
                        f_remark = None
                        f_comment = None

                    # Found a pair
                    all_data.append({
                        "User ID": user_id,
                        "Conversation ID": conv_id,
                        "Timestamp": current_user_msg["timestamp"],
                        "Query (User)": current_user_msg["query"],
                        "Response (AI)": content,
                        "Related Questions": rq_str,
                        "Action": f_action,
                        "Remark": f_remark,
                        "Comment": f_comment,
                        "Key": key
                    })
                    current_user_msg = None # Reset for next pair
                    
        except Exception as e:
            st.warning(f"Error processing key {key}: {e}")
            
    return pd.DataFrame(all_data)

@st.cache_data(ttl=60) # Cache the raw fetched data for 60 seconds to avoid unnecessary Redis calls
def get_cached_chat_data(env="Dev"):
    r = connect_redis(env)
    if not r:
        return pd.DataFrame()
    return fetch_chat_data(r)

def main():
    st.set_page_config(page_title="Redis Chat Report", layout="wide")
    st.title("📊 Redis Chat Report Exporter")
    
    # Sidebar for Refresh and Info
    with st.sidebar:
        default_env = os.getenv("REDIS_ENV", "Dev")
        env_index = 0 if default_env.lower() == "dev" else 1
        
        selected_env = st.selectbox("Environment", ["Dev", "Prod"], index=env_index)
        st.info(f"Status: Connected to {selected_env}")
        
        if st.button("🔄 Force Refresh Data"):
            get_cached_chat_data.clear() # Clear cache on explicit refresh
            st.rerun()

    with st.spinner(f"Fetching data from {selected_env} Redis..."):
        df = get_cached_chat_data(selected_env)

    if df.empty:
        st.warning("No chat data found in Redis.")
        return

    # Convert timestamp to datetime for filtering and charting
    # Handling both timezone-aware (Z) and timezone-naive strings seamlessly
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='ISO8601', utc=True, errors='coerce')
    df = df.sort_values(by='Timestamp', ascending=False)
    
    # Initialize session state for filters if not present
    if 'filter_start_date' not in st.session_state:
        st.session_state.filter_start_date = df['Timestamp'].min().date()
    if 'filter_end_date' not in st.session_state:
        st.session_state.filter_end_date = df['Timestamp'].max().date()
    if 'filter_actions' not in st.session_state:
        st.session_state.filter_actions = []

    s_date = st.session_state.filter_start_date
    e_date = st.session_state.filter_end_date
    acts = st.session_state.filter_actions

    # 1. Base filtered dataframe (Applies to both Dashboard and Table)
    mask = (df['Timestamp'].dt.date >= s_date) & (df['Timestamp'].dt.date <= e_date)
    if acts and 'Action' in df.columns:
        mask &= df['Action'].isin(acts)
        
    filtered_df = df.loc[mask].copy()

    # 2. Prepare Dashboard Data from filtered_df
    dash_df = filtered_df.copy()
    # Explicitly convert to standard YYYY-MM-DD string to prevent continuous/timezone axis bugs
    dash_df['Date'] = dash_df['Timestamp'].dt.strftime('%Y-%m-%d')
    grouped = dash_df.groupby('Date').agg(
        Queries=('Key', 'count'),
        Likes=('Action', lambda x: (x == 'like').sum()),
        Dislikes=('Action', lambda x: (x == 'dislike').sum())
    ).reset_index()

    st.subheader("Dashboard Overview")
    
    fig = go.Figure()
    # 0 = Bar (Queries)
    fig.add_trace(go.Bar(x=grouped['Date'], y=grouped['Queries'], name='Total Queries', marker_color='#3b82f6'))
    # 1 = Scatter (Likes)
    fig.add_trace(go.Scatter(x=grouped['Date'], y=grouped['Likes'], mode='markers', name='Likes', marker=dict(size=12, color='#22c55e')))
    # 2 = Scatter (Dislikes)
    fig.add_trace(go.Scatter(x=grouped['Date'], y=grouped['Dislikes'], mode='markers', name='Dislikes', marker=dict(size=12, color='#ef4444')))

    fig.update_layout(
        title="Queries, Likes, and Dislikes over Time",
        xaxis_title="Date",
        yaxis_title="Count",
        xaxis=dict(
            type='category',
            tickformat='%d %b %Y'
        ),
        hovermode="x unified",
        margin=dict(l=20, r=20, t=40, b=20),
        height=400,
        clickmode='event+select'
    )

    # Render interactive Plotly chart
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
    
    # 3. Process chart selections
    if event and 'selection' in event and 'points' in event['selection'] and len(event['selection']['points']) > 0:
        point = event['selection']['points'][0]
        selected_chart_date = pd.to_datetime(point['x']).date()
        trace_id = point['curve_number']
        
        # Determine if Like (1) or Dislike (2) was clicked
        if trace_id == 1:
            selected_chart_action = ['like']
        elif trace_id == 2:
            selected_chart_action = ['dislike']
        else:
            selected_chart_action = []

        # Check if a rerun is needed to prevent infinite loops from Streamlit components
        needs_rerun = False
        if st.session_state.filter_start_date != selected_chart_date or st.session_state.filter_end_date != selected_chart_date:
            st.session_state.filter_start_date = selected_chart_date
            st.session_state.filter_end_date = selected_chart_date
            needs_rerun = True
            
        if set(st.session_state.filter_actions) != set(selected_chart_action):
            st.session_state.filter_actions = selected_chart_action
            needs_rerun = True
            
        if needs_rerun:
            st.rerun()

    # 4. Filtering UI (Bound directly to session state, auto updates on change)
    st.subheader("Filters")
    col1, col2, col3, col4 = st.columns([2, 2, 4, 1])
    
    with col1:
        st.date_input("Start Date", key="filter_start_date")
        
    with col2:
        st.date_input("End Date", key="filter_end_date")
        
    with col3:
        unique_actions = sorted(df['Action'].dropna().unique().tolist()) if 'Action' in df.columns else []
        st.multiselect("Filter by Action ('like', 'dislike', etc.)", options=unique_actions, key="filter_actions")

    def reset_filters(min_d, max_d):
        st.session_state.filter_start_date = min_d
        st.session_state.filter_end_date = max_d
        st.session_state.filter_actions = []

    with col4:
        st.write("") # Spacing
        st.write("")
        st.button(
            "Reset Filters", 
            use_container_width=True, 
            on_click=reset_filters, 
            args=(df['Timestamp'].min().date(), df['Timestamp'].max().date())
        )

    # 5. Display Data
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
