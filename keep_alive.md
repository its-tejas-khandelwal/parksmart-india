# Fix Render Free Tier Timeout (App goes to sleep)

Render free tier sleeps after 15 minutes of no traffic.
Fix it with UptimeRobot (free):

1. Go to https://uptimerobot.com → Sign up free
2. Click "Add New Monitor"
3. Monitor Type: HTTP(s)
4. Friendly Name: ParkSmart
5. URL: https://parksmart-india.onrender.com/health
6. Monitoring Interval: Every 14 minutes
7. Click "Create Monitor"

That's it — your app stays awake 24/7 for free.
