import redis
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", None)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_USERNAME = os.getenv("REDIS_USERNAME", "default")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_SSL = os.getenv("REDIS_SSL", "False").lower() == "true"

def seed():
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
    
    sample_data = [
        {
            "key": "AICOV_596:PARENTCONV_1",
            "messages": [
                {"role": "user", "content": "How to help FPOs?", "timestamp": (datetime.now() - timedelta(days=2)).isoformat()},
                {"role": "assistant", "content": "FPOs can be helped by providing credit access.", "timestamp": (datetime.now() - timedelta(days=1)).isoformat()}
            ]
        },
        {
            "key": "AICOV_596:PARENTCONV_2",
            "messages": [
                {"role": "user", "content": "मोठ्या खरेदीदारांना कसे विकावे?", "timestamp": datetime.now().isoformat()},
                {"role": "assistant", "content": "मोठ्या खरेदीदारांना विक्रीसाठी स्पष्ट रणनीती असावी लागते.", "timestamp": datetime.now().isoformat()}
            ]
        }
    ]
    
    for item in sample_data:
        r.set(item["key"], json.dumps(item["messages"]))
        print(f"Seeded {item['key']}")

if __name__ == "__main__":
    seed()
