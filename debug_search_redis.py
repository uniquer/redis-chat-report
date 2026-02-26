import json
from app import connect_redis
r = connect_redis()
if r:
    keys = r.keys("AICOV_*:PARENTCONV_*")
    found_older = 0
    for k in keys:
        val = r.get(k)
        if "2026-02-04" in val:
            found_older += 1
            print(f"FOUND 2026-02-04 IN KEY: {k}")
    print(f"Total keys checked: {len(keys)}")
    print(f"Total containing '2026-02-04': {found_older}")
    
