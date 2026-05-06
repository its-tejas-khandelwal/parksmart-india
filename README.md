# SpotEasy India 🅿️
### Real-Time Web-Based Smart Parking System

> **Updated build** with: map z-index fix · UPI checkout (txn ID) · vendor + admin lot editing (with admin approval workflow) · admin can add lots · AJAX auto-refresh every 4s · browser + email notifications · always-on geolocation · all lots show as map pins · refresh-on-back.

---

## 🚀 Default admin (auto-seeded on first run)

| Role | Email | Password |
|------|-------|----------|
| Super Admin | `admin@spoteasy.in` | `Admin@1234` |

Override via `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`.

---

## 🆕 What's new in this build

| # | Feature | Where |
|---|---------|-------|
| 1 | **Map z-index fixed** — content always sits above the map; map is properly constrained to its container | `lots_list.html`, `base.html` (`.map-wrap`, `.leaflet-container` rules) |
| 2 | **UPI checkout flow** — vendor enters UPI ID + uploads QR; customer sees QR + ID, pays via any UPI app, then enters transaction ID. No real gateway, no deployment page. | `book_slot.html` → `digital_pass.html` checkout panel · `app.py:checkout` |
| 3 | **Vendor + Admin can edit lots** | `edit_lot.html` · `app.py:edit_lot` |
| 4 | **Admin approval for vendor edits** — *the lot stays LIVE with old values until admin approves* | `app.py:edit_lot`, `approve_lot_edit`, `reject_lot_edit` · model `ParkingLot.pending_edit` |
| 5 | **Admin can add lots** — admin-created lots are instantly live | route `add_lot` is shared by `/vendor/add_lot` and `/admin/add_lot` |
| 6 | **AJAX auto-refresh every 4s** on every page (no flicker) | `base.html` exposes `window.SE_AUTOREFRESH` hook; pages opt-in |
| 7 | **Refresh on browser back/forward** | `pageshow` listener in `base.html` |
| 8 | **Browser & email notifications for every event** — booking · checkout · vendor approval · lot approval · edit approval/rejection · admin alerts | `app.py:push_notification` + `Notification` model + `/api/notifications` polling |
| 9 | **Geolocation prompt on every page** — re-asks every 60s if previously denied | `base.html:SE_LOC` block |
| 10 | **All parking lots shown as pins on map** | `lots_list.html:placeMarkers` |

---

## 🏃 Run locally

```bash
pip install -r requirements.txt
cp .env.example .env       # edit values
python app.py
```

App runs at <http://localhost:5000>

---

## 🌐 Deploy

### Render
1. Push to GitHub
2. New Web Service → connect repo
3. Build cmd: `pip install -r requirements.txt`
4. Start cmd: `gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT --timeout 120`
5. Add env vars from `.env.example` (use Render Postgres for `DATABASE_URL`)

### Railway
Auto-detects via `railway.json`.

The app **automatically migrates** existing databases (adds new columns) — your old data is preserved.

---

## 📁 Project Structure

```
spoteasy/
├── app.py                  # All Flask routes + APIs + migration
├── models.py               # SQLAlchemy models (User, Lot, Slot, Reservation, Notification)
├── requirements.txt
├── runtime.txt
├── Procfile
├── railway.json
├── .env.example
├── .gitignore
├── README.md
├── templates/
│   ├── base.html           # Master layout (auto-refresh hook, notifications, geo prompt)
│   ├── index.html          # Landing page
│   ├── login.html · register.html
│   ├── lots_list.html      # Find Parking (FIXED z-index, AJAX refresh, all pins on map)
│   ├── book_slot.html      # Slot picker (live availability)
│   ├── digital_pass.html   # QR pass + UPI/cash checkout (txn ID input)
│   ├── add_lot.html        # Add lot (vendor or admin) — UPI ID + QR upload
│   ├── edit_lot.html       # Edit lot (vendor → pending; admin → instant)
│   ├── lot_grid.html       # Vendor slot manager (live)
│   ├── dashboard_customer.html
│   ├── dashboard_vendor.html
│   ├── dashboard_admin.html  # Pending vendors / lots / lot edits queue
│   ├── my_bookings.html
│   ├── account.html        # Profile + notification prefs + password
│   ├── notifications.html  # Full notification history
│   ├── admin_notify.html   # Send broadcast notifications
│   ├── db_view.html        # DB diagnostics + CSV export
│   ├── terms.html · 404.html · 500.html · offline.html
└── static/
    ├── manifest.json
    ├── sw.js
    ├── uploads/qr/         # Vendor UPI QR uploads land here
    └── icons/              # PWA icons (drop your icon-72/96/128/192/512.png here)
```

---

## 🔔 Notifications — how they work

The app uses **3 layers** for every event:

1. **In-app bell** in the top-right of the nav — shows unread count, dropdown lists last 15 notifications, real-time poll every 5 s
2. **Browser native notifications** (toast on desktop / OS) — only if the user grants permission. The app asks once on first authenticated page-load.
3. **Email** via SMTP — only if `EMAIL_FROM` and `EMAIL_KEY` env vars are set (Gmail app password recommended). User can disable this from `Account → Notification Preferences`.

Events that fire notifications:
- New booking (notifies customer + lot owner)
- Checkout (notifies customer + lot owner)
- New vendor pending (notifies all admins)
- New lot pending (notifies all admins)
- Vendor approved (notifies vendor)
- Lot approved (notifies vendor)
- Lot edit submitted (notifies admins)
- Lot edit approved/rejected (notifies vendor)
- Admin broadcast (`Admin → Notify users`)

---

## 💳 UPI Payment Flow (free, no gateway)

1. Vendor (or admin) goes to **Edit Lot** and enters their UPI ID + uploads a UPI QR PNG/JPG.
2. Customer books a slot, then on the digital pass page chooses **UPI** at checkout.
3. The QR + UPI ID is shown. Customer pays through any UPI app (GPay/PhonePe/Paytm).
4. Customer pastes the transaction reference (UTR) and submits — the booking is closed and the txn ID is saved.
5. Admin can see all transaction IDs in **Admin → DB View → reservations**.

If a vendor hasn't configured UPI, the admin's UPI (set on Account page) is used as fallback. If neither, the customer is told to pay cash.

---

## 🔁 Auto-refresh

`base.html` exposes a global hook:

```js
window.SE_AUTOREFRESH = function(){ /* pull fresh data via AJAX */ };
```

Pages that need live data (find parking, slot grid, dashboards, book slot) define this function. The base layout calls it every 4 seconds. Plus, browser back/forward triggers a full reload via `pageshow`.

---

## 🗺️ Geolocation

`base.html` requests location on every page-load. If the user denies, it remembers for 60 seconds, then asks again. The Find Parking page sorts cards by distance to the user pin once granted.

