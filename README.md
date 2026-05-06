# ParkSmart India 🇮🇳
### A Real-Time Web-Based Smart Parking System

> **B.Tech Final Year Project** — No IoT hardware required.  
> 100% web-based. Deployable for **$0/month**.

---

## 🚀 Demo Accounts (after first run)

| Role | Email | Password |
|------|-------|----------|
| Super Admin | admin@parksmart.in | Admin@123 |
| Vendor | vendor@parksmart.in | Vendor@123 |
| Customer | customer@parksmart.in | Customer@123 |

---

## 📁 Project Structure

```
parksmart_final/
├── app.py                  ← Main Flask application (all routes)
├── models.py               ← Database models (SQLAlchemy)
├── requirements.txt        ← Python dependencies
├── Procfile                ← For Render deployment
├── runtime.txt             ← Python version for Render
├── .env.example            ← Environment variables template
├── .gitignore
└── templates/
    ├── base.html           ← Master layout + dark/light theme engine
    ├── index.html          ← Landing page
    ├── login.html          ← Login page
    ├── register.html       ← Registration page
    ├── dashboard_customer.html
    ├── dashboard_vendor.html   ← Live slot grid with 3s polling
    ├── dashboard_admin.html    ← Platform overview
    ├── lots_list.html          ← Leaflet.js map + lot cards
    ├── book_slot.html          ← Slot selection + booking form
    ├── digital_pass.html       ← QR pass + WhatsApp share + Hindi/EN toggle
    ├── my_bookings.html
    ├── add_lot.html
    ├── lot_grid.html           ← Vendor slot management
    └── scan_result.html        ← QR scanner result page
```

---

## ⚡ Run Locally (5 minutes)

```bash
# 1. Clone / extract the project
cd parksmart_final

# 2. Create virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy env file
cp .env.example .env
# Edit .env with your values (leave DATABASE_URL blank for SQLite)

# 5. Run the app
python app.py

# Open: http://localhost:5000
```

The app will automatically:
- Create all database tables
- Seed demo accounts (Admin, Vendor, Customer)
- Create a sample parking lot with slots

---

## 🌐 Deploy Live for FREE

See the full step-by-step guide in this README below.

---

## Tech Stack

- **Backend:** Python Flask + Flask-SQLAlchemy + Flask-Login
- **Database:** PostgreSQL on Supabase (free) / SQLite for local dev
- **Frontend:** Tailwind CSS CDN + custom CSS variables
- **Maps:** Leaflet.js + OpenStreetMap (free, no API key)
- **Icons:** Lucide Icons
- **Fonts:** Plus Jakarta Sans + DM Sans + JetBrains Mono
- **Hosting:** Render.com (free tier)
- **Auth:** Flask-Login + Flask-Bcrypt (session-based)
