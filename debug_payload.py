import json
from app import connect_redis
r = connect_redis()
val = r.get("AICOV_596:PARENTCONV_1")
chat = json.loads(val)
for i, m in enumerate(chat):
    print(f"Message {i}: role={m.get('role')} timestamp={m.get('timestamp')}")
