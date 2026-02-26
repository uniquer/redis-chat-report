import json
from app import connect_redis

r = connect_redis()
key = "AICOV_596:PARENTCONV_1"
val = r.get(key)
chat_payload = json.loads(val)

print(f"Total messages in payload: {len(chat_payload)}")

current_user_msg = None
all_data = []

for msg in chat_payload:
    role = msg.get("role")
    content = msg.get("content")
    timestamp = msg.get("timestamp")
    
    if role == "user":
        current_user_msg = {"query": content, "timestamp": timestamp}
        print(f"Processing user msg: {timestamp}")
    elif role == "assistant" and current_user_msg:
        print(f"Found assistant pair for: {current_user_msg['timestamp']}")
        # Found a pair
        all_data.append({
            "Timestamp": current_user_msg["timestamp"],
        })
        current_user_msg = None # Reset for next pair

print(f"Data appended: {all_data}")
        
