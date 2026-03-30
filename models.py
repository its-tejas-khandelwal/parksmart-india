# ParkSmart India — Complete Deployment Guide ($0)
## Time needed: ~30 minutes

---

## PART 1 — Fix Supabase Connection (Most Important)

Your current Supabase URL might be the wrong format. Here's how to get the correct one:

1. Go to **supabase.com** → your project
2. Click **Project Settings** (gear icon) → **Database**
3. Scroll to **Connection string** → click the **URI** tab
4. Copy the full string — it looks like:
   ```
   postgresql://postgres:YOUR_PASSWORD@db.ABCDEFGH.supabase.co:5432/postgres
   ```
5. **IMPORTANT:** Replace `[YOUR-PASSWORD]` with your actual Supabase password

> ⚠️ Do NOT use the "Connection pooling" URL — use the direct URI tab.

---

## PART 2 — Fix Supabase Network Settings

Supabase sometimes blocks Render's servers. Fix this:

1. Go to **Supabase → Project Settings → Database → Network Restrictions**
2. If you see "Restrict to project's own IP range" — **disable it**
3. Set it to **Allow all connections** (safe for a student project)

---

## PART 3 — Set Environment Variables in Render

Go to **render.com → your service → Environment → Add/Edit variables:**

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Your Supabase URI from Part 1 |
| `SECRET_KEY` | Any 32 random characters, e.g. `x7k2mP9qL4nR8jW1vZ5bY3cA` |
| `ADMIN_EMAIL` | `admin@parksmart.in` |
| `ADMIN_PASSWORD` | `Admin@1234` |
| `PYTHON_VERSION` | `3.11.9` |

Click **Save Changes**.

---

## PART 4 — Push Code & Deploy

In terminal inside your project folder:

```bash
git add .
git commit -m "fix: complete rebuild v4"
git push
```

Render auto-deploys on push. Watch the **Logs** tab in Render.

**Success looks like:**
```
[DB] Using PostgreSQL
[DB] Admin created: admin@parksmart.in
```

**Error looks like:**
```
could not connect to server
```
→ Go back and check Part 1 & 2.

---

## PART 5 — Verify Everything

**1. Check DB is working:**
```
https://your-app.onrender.com/health
```
Should return: `"db": "connected (postgresql)"`

**2. Test all 3 roles:**

| Role | Login | Password |
|------|-------|----------|
| Admin | admin@parksmart.in | Admin@1234 |
| Vendor | Register a new vendor account | — |
| Customer | Register a new customer account | — |

**3. Full flow test:**
- Admin logs in → approves vendor account
- Vendor logs in → Add Lot → fill form
- Admin → approves the lot
- Customer → Find Parking → Book Slot → View Digital Pass → WhatsApp share
- Vendor → Live Grid → see slot turn red
- Customer → Checkout → see bill calculated

---

## PART 6 — Keep Free Tier Alive

Render free tier sleeps after 15 minutes of inactivity.

1. Go to **uptimerobot.com** → Sign up free
2. Add Monitor → HTTP(s)
3. URL: `https://your-app.onrender.com/health`
4. Check every **14 minutes**

Your app now stays awake 24/7 for free. ✅

---

## Local Development (Without Render/Supabase)

```bash
# 1. Extract ZIP, open terminal in folder
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 2. Install packages
pip install -r requirements.txt

# 3. Run (uses SQLite automatically — no DB setup needed)
python app.py

# 4. Open browser
# http://localhost:5000
```

Admin is auto-created: `admin@parksmart.in` / `Admin@1234`

---

## How to Check Database Entries

**Option 1 — In-app (easiest):**
Login as Admin → Dashboard → click "🗄️ View DB" button

**Option 2 — Supabase Dashboard:**
Go to supabase.com → your project → Table Editor

**Option 3 — Health endpoint:**
Visit `/health` — shows live record counts

---

## IoT Hardware (Future Upgrade)

| # | Component | Function | Price (India) | Buy From |
|---|-----------|----------|---------------|----------|
| 1 | Raspberry Pi 4B | Main controller at gate | ₹4,500–6,000 | robu.in, evelta.com |
| 2 | ESP32 | Per-slot WiFi sensor node | ₹350–500 each | robu.in |
| 3 | HC-SR04 Ultrasonic | Car detection per slot | ₹60–100 each | robu.in |
| 4 | QR Scanner Module | Scan customer pass at gate | ₹800–1,200 | amazon.in |
| 5 | Servo + Boom Barrier | Physical gate | ₹500–1,500 | amazon.in |
| 6 | 16×2 LCD Display | Show slot count at gate | ₹150–250 | robu.in |
| 7 | RGB LED per slot | Green/Red light above slot | ₹10–20 each | robu.in |
| 8 | Weatherproof Enclosure | Protect outdoor electronics | ₹400–800 | amazon.in |

**Estimated cost for one 30-slot lot: ₹25,000–40,000**

**How IoT connects to your existing code:**
The ESP32 sends a POST to `/vendor/slot/<id>/toggle` when a car arrives or leaves — the same API your web UI already uses. Zero backend changes needed.
