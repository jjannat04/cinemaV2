import httpx

# Check gateway debug from app container
try:
    debug = httpx.get('http://gateway:9000/debug/deliveries', timeout=5).json()
    print(f'Gateway deliveries: {debug.get("count", 0)}')
    if debug.get('count', 0) > 0:
        latest = debug['deliveries'][-1]
        print(f'Latest: {latest}')
except Exception as e:
    print(f'Gateway debug error: {e}')