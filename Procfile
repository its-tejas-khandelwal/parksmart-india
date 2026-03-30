# SpotEasy Keep-Alive Worker
# Runs as a separate background process on Render
# Pings the site every 10 minutes

import time, requests, os
from datetime import datetime

URL = os.environ.get('RENDER_EXTERNAL_URL', 'https://parksmart-india.onrender.com')

def ping():
    try:
        r = requests.get(f"{URL}/health", timeout=15)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Ping ✅ {r.status_code}", flush=True)
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Ping ❌ {e}", flush=True)

if __name__ == '__main__':
    print(f"Keep-alive started for {URL}", flush=True)
    while True:
        ping()
        time.sleep(10 * 60)  # ping every 10 minutes
