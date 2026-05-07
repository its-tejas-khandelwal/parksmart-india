import os, base64, io, threading, time, csv, json, uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from flask import (Flask, render_template, request, redirect, url_for, flash,
                   jsonify, send_from_directory, make_response, abort)
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from werkzeug.utils import secure_filename
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from models import db, User, ParkingLot, ParkingSlot, Reservation, Notification

# ────────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))
ALLOWED_QR_EXT = {'png', 'jpg', 'jpeg', 'webp'}
UPLOAD_DIR = os.path.join('static', 'uploads', 'qr')

def now_ist():
    return datetime.now(IST).replace(tzinfo=None)

def to_ist(dt):
    if dt is None: return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).replace(tzinfo=None)

def get_db_url():
    url = os.environ.get('DATABASE_URL', '').strip()
    if not url:
        return 'sqlite:///spoteasy.db'
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    if 'sslmode' not in url:
        url += ('&' if '?' in url else '?') + 'sslmode=require'
    return url

def get_site_url():
    for k in ('RAILWAY_PUBLIC_DOMAIN', 'RENDER_EXTERNAL_URL', 'SITE_URL'):
        v = os.environ.get(k, '').strip()
        if v:
            return v if v.startswith('http') else 'https://' + v
    return 'http://localhost:5000'

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['SQLALCHEMY_DATABASE_URI']      = get_db_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']= False
app.config['SQLALCHEMY_ENGINE_OPTIONS']    = {'pool_recycle': 280, 'pool_pre_ping': True}
app.config['MAX_CONTENT_LENGTH']           = 4 * 1024 * 1024  # 4 MB upload cap

os.makedirs(UPLOAD_DIR, exist_ok=True)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to continue.'

@login_manager.user_loader
def load_user(uid):
    try: return db.session.get(User, int(uid))
    except Exception:
        db.session.rollback(); return None

# ────────────────────────────────────────────────────────────────────
# DB bootstrap + lightweight migration
# ────────────────────────────────────────────────────────────────────
def _ensure_columns():
    """Add new columns to existing tables if upgrading from older schema."""
    try:
        from sqlalchemy import text, inspect
        insp = inspect(db.engine)
        # users
        if 'users' in insp.get_table_names():
            cols = {c['name'] for c in insp.get_columns('users')}
            with db.engine.begin() as conn:
                for col, ddl in [
                    ('notify_browser', 'BOOLEAN DEFAULT TRUE'),
                    ('notify_email',   'BOOLEAN DEFAULT TRUE'),
                    ('upi_id',         'VARCHAR(120)'),
                    ('upi_qr_path',    'VARCHAR(255)'),
                ]:
                    if col not in cols:
                        try: conn.execute(text(f'ALTER TABLE users ADD COLUMN {col} {ddl}'))
                        except Exception as e: print(f'[migrate users.{col}] {e}')
        if 'parking_lots' in insp.get_table_names():
            cols = {c['name'] for c in insp.get_columns('parking_lots')}
            with db.engine.begin() as conn:
                for col, ddl in [
                    ('upi_id',       'VARCHAR(120)'),
                    ('upi_qr_path',  'VARCHAR(255)'),
                    ('pending_edit', 'TEXT'),
                ]:
                    if col not in cols:
                        try: conn.execute(text(f'ALTER TABLE parking_lots ADD COLUMN {col} {ddl}'))
                        except Exception as e: print(f'[migrate lot.{col}] {e}')
        if 'reservations' in insp.get_table_names():
            cols = {c['name'] for c in insp.get_columns('reservations')}
            with db.engine.begin() as conn:
                for col, ddl in [
                    ('payment_status', "VARCHAR(20) DEFAULT 'pending'"),
                    ('txn_id',         'VARCHAR(120)'),
                ]:
                    if col not in cols:
                        try: conn.execute(text(f'ALTER TABLE reservations ADD COLUMN {col} {ddl}'))
                        except Exception as e: print(f'[migrate res.{col}] {e}')
    except Exception as e:
        print(f'[migrate] {e}')

with app.app_context():
    try:
        db.create_all()
        _ensure_columns()
        # Seed admin
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@spoteasy.in')
        admin_pw    = os.environ.get('ADMIN_PASSWORD', 'Admin@1234')
        if not User.query.filter_by(email=admin_email).first():
            a = User(name='Super Admin', email=admin_email, role='admin', is_approved=True)
            a.set_password(admin_pw)
            db.session.add(a); db.session.commit()
            print(f'[DB] Seeded admin: {admin_email} / {admin_pw}')
        print('[DB] Ready')
    except Exception as e:
        print(f'[DB] WARNING: {e}')

# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────
def _safe_decimal(v, default=0):
    try: return Decimal(str(v).replace(',', '').strip())
    except Exception: return Decimal(str(default))

def calc_bill(entry, exit_t, vt, r2w, r4w):
    mins = (exit_t - entry).total_seconds() / 60
    if mins < 15: return Decimal('0.00')
    hours = Decimal(str((exit_t - entry).total_seconds() / 3600))
    rate  = Decimal(str(r2w if vt == '2w' else r4w))
    return (hours * rate).quantize(Decimal('0.01'))

def gen_qr_b64(token):
    try:
        import qrcode
        from qrcode.image.pure import PyPNGImage
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(token); qr.make(fit=True)
        img = qr.make_image(image_factory=PyPNGImage)
        buf = io.BytesIO(); img.save(buf); buf.seek(0)
        return base64.b64encode(buf.read()).decode()
    except Exception:
        try:
            import qrcode as qr2
            buf = io.BytesIO(); qr2.make(token).save(buf, format='PNG'); buf.seek(0)
            return base64.b64encode(buf.read()).decode()
        except Exception as e:
            print('[QR]', e); return ''

def redirect_by_role():
    if not current_user.is_authenticated: return redirect(url_for('index'))
    if current_user.role == 'admin':  return redirect(url_for('admin_dashboard'))
    if current_user.role == 'vendor': return redirect(url_for('vendor_dashboard'))
    return redirect(url_for('customer_dashboard'))

def send_email(to_email, subject, html):
    try:
        smtp_user = os.environ.get('EMAIL_FROM', '')
        smtp_pass = os.environ.get('EMAIL_KEY', '')
        if not smtp_user or not smtp_pass:
            return False
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f'SpotEasy India <{smtp_user}>'
        msg['To']      = to_email
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, to_email, msg.as_string())
        return True
    except Exception as e:
        print('[Email]', e); return False

def push_notification(user_id, title, body='', icon='🔔', url=''):
    """Create an in-app notification record. Browser push is shown on next poll."""
    try:
        n = Notification(user_id=user_id, title=title, body=body, icon=icon, url=url)
        db.session.add(n); db.session.commit()
        # Email best-effort
        u = db.session.get(User, user_id)
        if u and u.notify_email and u.email:
            html = f'<div style="font-family:Inter,sans-serif;padding:24px;"><h2 style="color:#16a34a;">{icon} {title}</h2><p>{body}</p><p style="color:#9ca3af;font-size:12px;">— SpotEasy India</p></div>'
            
            # --- FIX APPLIED HERE ---
            # Send the email in a background thread so the screen doesn't freeze!
            threading.Thread(target=send_email, args=(u.email, f'SpotEasy: {title}', html)).start()
            
        return n
    except Exception as e:
        db.session.rollback(); print('[Notify]', e)

def notify_admins(title, body='', icon='⚙️', url=''):
    for a in User.query.filter_by(role='admin').all():
        push_notification(a.id, title, body, icon, url)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_QR_EXT

def save_qr_upload(file_storage):
    """Save uploaded UPI QR image. Returns relative path or None."""
    if not file_storage or not file_storage.filename: return None
    if not allowed_file(file_storage.filename): return None
    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    fname = f'qr_{uuid.uuid4().hex}.{ext}'
    path = os.path.join(UPLOAD_DIR, fname)
    file_storage.save(path)
    return f'uploads/qr/{fname}'

@app.context_processor
def inject_globals():
    unread = 0
    if current_user.is_authenticated:
        try:
            unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        except Exception:
            unread = 0
    return {'to_ist': to_ist, 'now_ist': now_ist(), 'unread_count': unread}

# ────────────────────────────────────────────────────────────────────
# Public routes
# ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    try:
        active_lots = ParkingLot.query.filter_by(is_active=True).all()
        stats = {
            'total_lots': len(active_lots),
            'total_slots': sum(l.total_slots for l in active_lots),
            'available_slots': sum(l.available_count for l in active_lots),
            'total_cities': len({l.city for l in active_lots}),
            'active_bookings': Reservation.query.filter_by(status='active').count(),
        }
    except Exception:
        stats = {'total_lots':0,'total_slots':0,'available_slots':0,'total_cities':0,'active_bookings':0}
    return render_template('index.html', **stats)

@app.route('/api/live-stats')
def api_live_stats():
    try:
        active_lots = ParkingLot.query.filter_by(is_active=True).all()
        return jsonify({
            'ok': True,
            'total_lots': len(active_lots),
            'total_slots': sum(l.total_slots for l in active_lots),
            'available_slots': sum(l.available_count for l in active_lots),
            'total_cities': len({l.city for l in active_lots}),
            'active_bookings': Reservation.query.filter_by(status='active').count(),
            'ts': int(time.time()),
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ────────────────────────────────────────────────────────────────────
# Auth
# ────────────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect_by_role()
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        pw    = request.form.get('password', '')
        u = User.query.filter_by(email=email).first()
        if u and u.check_password(pw):
            if u.role == 'vendor' and not u.is_approved:
                flash('Your vendor account is awaiting admin approval.', 'warning')
                return redirect(url_for('login'))
            login_user(u)
            return redirect_by_role()
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name  = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        pw    = request.form.get('password', '')
        role  = request.form.get('role', 'customer')
        phone = request.form.get('phone', '').strip()
        if not name or not email or not pw:
            flash('Name, email and password required.', 'danger')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login.', 'danger')
            return render_template('register.html')
        if role not in ('customer', 'vendor'): role = 'customer'
        u = User(name=name, email=email, role=role, phone=phone,
                 is_approved=(role == 'customer'))
        u.set_password(pw)
        db.session.add(u); db.session.commit()
        if role == 'vendor':
            notify_admins('New vendor pending approval',
                          f'{name} ({email}) just registered as a vendor.',
                          '🆕', url_for('admin_dashboard'))
            flash('Vendor account created! Awaiting admin approval.', 'info')
            return redirect(url_for('login'))
        login_user(u)
        return redirect(url_for('customer_dashboard'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ────────────────────────────────────────────────────────────────────
# Find Parking + Lot map
# ────────────────────────────────────────────────────────────────────
@app.route('/lots')
def lots_list():
    lots = ParkingLot.query.filter_by(is_active=True).all()
    return render_template('lots_list.html', lots=lots,
                           lots_json=[l.to_dict() for l in lots])

@app.route('/api/lots')
def api_lots():
    """Live data for the find-parking page (auto-refresh)."""
    try:
        lots = ParkingLot.query.filter_by(is_active=True).all()
        return jsonify({'ok': True, 'ts': int(time.time()),
                        'lots': [l.to_dict() for l in lots]})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ────────────────────────────────────────────────────────────────────
# Customer
# ────────────────────────────────────────────────────────────────────
@app.route('/customer/dashboard')
@login_required
def customer_dashboard():
    if current_user.role != 'customer': return redirect_by_role()
    reservations = Reservation.query.filter_by(customer_id=current_user.id)\
                                    .order_by(Reservation.created_at.desc()).all()
    active = next((r for r in reservations if r.status == 'active'), None)
    return render_template('dashboard_customer.html',
                           reservations=reservations, active=active)

@app.route('/my_bookings')
@login_required
def my_bookings():
    if current_user.role != 'customer': return redirect_by_role()
    reservations = Reservation.query.filter_by(customer_id=current_user.id)\
                                    .order_by(Reservation.created_at.desc()).all()
    return render_template('my_bookings.html', reservations=reservations)

@app.route('/book/<int:lid>', methods=['GET', 'POST'])
@login_required
def book_slot(lid):
    if current_user.role != 'customer':
        flash('Only customers can book.', 'error')
        return redirect_by_role()
    lot = db.session.get(ParkingLot, lid)
    if not lot or not lot.is_active:
        flash('Parking lot not available.', 'error')
        return redirect(url_for('lots_list'))

    is_json = request.headers.get('Accept') == 'application/json'

    if request.method == 'POST':
        try:
            vt    = (request.form.get('vehicle_type') or '').strip().lower()
            vno   = (request.form.get('vehicle_no') or '').strip().upper()
            sid   = request.form.get('slot_id')
            if vt not in ('2w', '4w'):
                msg = 'Choose a valid vehicle type.'
                return jsonify({'error': msg}), 400 if is_json else (flash(msg,'error') or redirect(url_for('book_slot', lid=lid)))
            if not vno or len(vno) < 4:
                msg = 'Enter a valid vehicle number.'
                return jsonify({'error': msg}), 400 if is_json else (flash(msg,'error') or redirect(url_for('book_slot', lid=lid)))
            if not sid:
                msg = 'Select a slot.'
                return jsonify({'error': msg}), 400 if is_json else (flash(msg,'error') or redirect(url_for('book_slot', lid=lid)))
            slot = db.session.get(ParkingSlot, int(sid))
            if not slot or slot.lot_id != lot.id:
                msg = 'Invalid slot.'
                return jsonify({'error': msg}), 400 if is_json else (flash(msg,'error') or redirect(url_for('book_slot', lid=lid)))
            if slot.slot_type != vt:
                expected = '2-Wheeler' if slot.slot_type == '2w' else '4-Wheeler'
                msg = f'This slot is for {expected} only.'
                return jsonify({'error': msg}), 400 if is_json else (flash(msg,'error') or redirect(url_for('book_slot', lid=lid)))
            if slot.status != 'available':
                msg = 'Slot just got taken. Pick another.'
                return jsonify({'error': msg}), 409 if is_json else (flash(msg,'error') or redirect(url_for('book_slot', lid=lid)))
            existing = Reservation.query.filter_by(customer_id=current_user.id, status='active').first()
            if existing:
                msg = 'You already have an active booking. Check out first.'
                if is_json: return jsonify({'error': msg, 'redirect_url': url_for('digital_pass', rid=existing.id)}), 409
                flash(msg,'error'); return redirect(url_for('digital_pass', rid=existing.id))

            res = Reservation(customer_id=current_user.id, slot_id=slot.id,
                              vehicle_type=vt, vehicle_no=vno,
                              entry_time=datetime.utcnow(), status='active',
                              payment_status='pending')
            slot.status = 'occupied'
            db.session.add(res); db.session.commit()
            push_notification(current_user.id, 'Booking confirmed',
                              f'{lot.name} · Slot {slot.label} · {vno}',
                              '✅', url_for('digital_pass', rid=res.id))
            push_notification(lot.owner_id, 'New booking received',
                              f'{vno} parked at {lot.name} (Slot {slot.label})',
                              '🅿️', url_for('vendor_dashboard'))
            redirect_url = url_for('digital_pass', rid=res.id)
            if is_json: return jsonify({'success': True, 'redirect_url': redirect_url})
            return redirect(redirect_url)
        except Exception as e:
            db.session.rollback(); print('[Book]', e)
            msg = 'Booking failed. Try again.'
            if is_json: return jsonify({'error': msg}), 500
            flash(msg, 'error')
            return redirect(url_for('book_slot', lid=lid))

    slots = [s for s in lot.slots if s.status == 'available']
    return render_template('book_slot.html', lot=lot, slots=slots)

@app.route('/reservation/<int:rid>/pass')
@login_required
def digital_pass(rid):
    res = db.session.get(Reservation, rid)
    if not res or res.customer_id != current_user.id:
        flash('Pass not found.', 'danger')
        return redirect(url_for('customer_dashboard'))
    return render_template('digital_pass.html', res=res,
                           qr_b64=gen_qr_b64(res.qr_token))

@app.route('/checkout/<int:rid>', methods=['POST'])
@login_required
def checkout(rid):
    is_json = request.headers.get('Accept') == 'application/json'
    try:
        res = db.session.get(Reservation, rid)
        if not res or res.customer_id != current_user.id:
            msg = 'Reservation not found.'
            if is_json: return jsonify({'error': msg}), 404
            flash(msg, 'error'); return redirect_by_role()
        if res.status != 'active':
            msg = 'Already checked out.'
            if is_json: return jsonify({'error': msg}), 400
            flash(msg, 'error'); return redirect(url_for('digital_pass', rid=rid))

        pay_method = (request.form.get('payment_method') or 'cash').strip().lower()
        if pay_method not in ('cash', 'upi'): pay_method = 'cash'
        txn_id = (request.form.get('txn_id') or '').strip()

        exit_time = datetime.utcnow()
        lot = res.slot.lot
        amount = calc_bill(res.entry_time, exit_time, res.vehicle_type, lot.rate_2w, lot.rate_4w)

        # UPI requires txn id
        if pay_method == 'upi':
            if not txn_id or len(txn_id) < 4:
                msg = 'Please enter the UPI transaction ID.'
                if is_json: return jsonify({'error': msg}), 400
                flash(msg, 'error'); return redirect(url_for('digital_pass', rid=rid))
            res.txn_id = txn_id
            res.payment_status = 'verified'   # Auto-verified (free demo, no real gateway)
        else:
            res.payment_status = 'verified'

        res.exit_time      = exit_time
        res.amount_paid    = amount
        res.status         = 'completed'
        res.payment_method = pay_method
        if res.slot: res.slot.status = 'available'
        db.session.commit()

        push_notification(current_user.id, 'Checkout complete',
                          f'₹{amount} via {pay_method.upper()} · {lot.name}',
                          '💸', url_for('digital_pass', rid=res.id))
        push_notification(lot.owner_id, 'Slot freed',
                          f'{res.vehicle_no} checked out from {lot.name}',
                          '🚪', url_for('vendor_dashboard'))

        redirect_url = url_for('digital_pass', rid=res.id)
        if is_json:
            return jsonify({'success': True, 'redirect_url': redirect_url,
                            'amount': str(amount), 'payment_method': pay_method,
                            'txn_id': txn_id})
        flash(f'Checkout complete. ₹{amount} via {pay_method.upper()}.', 'success')
        return redirect(redirect_url)
    except Exception as e:
        db.session.rollback(); print('[Checkout]', e)
        msg = 'Checkout failed.'
        if is_json: return jsonify({'error': msg}), 500
        flash(msg, 'error')
        return redirect(url_for('digital_pass', rid=rid))

@app.route('/api/lot/<int:lid>/slots')
@login_required
def api_lot_slots(lid):
    try:
        lot = db.session.get(ParkingLot, lid)
        if not lot: return jsonify({'error': 'Not found'}), 404
        return jsonify({
            'ok': True, 'lot_id': lot.id,
            'slots':     [s.to_dict() for s in lot.slots],
            'available': lot.available_count,
            'occupied':  lot.occupied_count,
            'total':     lot.total_slots,
            'avail_2w':  sum(1 for s in lot.slots if s.slot_type=='2w' and s.status=='available'),
            'avail_4w':  sum(1 for s in lot.slots if s.slot_type=='4w' and s.status=='available'),
            'ts': int(time.time()),
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500

# ────────────────────────────────────────────────────────────────────
# Vendor
# ────────────────────────────────────────────────────────────────────
@app.route('/vendor/dashboard')
@login_required
def vendor_dashboard():
    if current_user.role != 'vendor': return redirect_by_role()
    lots = ParkingLot.query.filter_by(owner_id=current_user.id).all()
    res_list = Reservation.query.join(ParkingSlot).join(ParkingLot)\
        .filter(ParkingLot.owner_id == current_user.id)\
        .order_by(Reservation.created_at.desc()).limit(20).all()
    return render_template('dashboard_vendor.html', lots=lots, reservations=res_list)

@app.route('/vendor/lot/<int:lid>')
@login_required
def vendor_lot_grid(lid):
    if current_user.role not in ('vendor', 'admin'):
        return redirect(url_for('index'))
    lot = db.session.get(ParkingLot, lid)
    if not lot or (current_user.role == 'vendor' and lot.owner_id != current_user.id):
        flash('Lot not found.', 'danger'); return redirect_by_role()
    return render_template('lot_grid.html', lot=lot)

@app.route('/vendor/slot/<int:sid>/toggle', methods=['POST'])
@login_required
def toggle_slot(sid):
    if current_user.role not in ('vendor', 'admin'):
        return jsonify({'error': 'Forbidden'}), 403
    slot = db.session.get(ParkingSlot, sid)
    if not slot: return jsonify({'error': 'Not found'}), 404
    if current_user.role == 'vendor' and slot.lot.owner_id != current_user.id:
        return jsonify({'error': 'Forbidden'}), 403
    slot.status = 'occupied' if slot.status == 'available' else 'available'
    db.session.commit()
    return jsonify({'id': slot.id, 'status': slot.status})

# ────────────────────────────────────────────────────────────────────
# Add lot — VENDOR or ADMIN
# ────────────────────────────────────────────────────────────────────
def _parse_lot_form(form, files):
    """Parses & validates the add/edit lot form. Returns (data_dict, error)."""
    name     = form.get('name', '').strip()
    address  = form.get('address', '').strip()
    city     = form.get('city', '').strip()
    lat_str  = form.get('latitude', '').strip()
    lng_str  = form.get('longitude', '').strip()
    s2w      = form.get('slots_2w', '0').strip() or '0'
    s4w      = form.get('slots_4w', '0').strip() or '0'
    r2w      = form.get('rate_2w', '').strip()
    r4w      = form.get('rate_4w', '').strip()
    upi_id   = form.get('upi_id', '').strip()
    if not all([name, address, city, lat_str, lng_str, r2w, r4w]):
        return None, 'All required fields must be filled.'
    try:
        lat = float(lat_str); lng = float(lng_str)
        n2w = int(s2w); n4w = int(s4w)
    except Exception:
        return None, 'Latitude/longitude/slot counts must be numbers.'
    total = n2w + n4w
    if total < 1: return None, 'Total slots must be at least 1.'
    rate_2w = _safe_decimal(r2w); rate_4w = _safe_decimal(r4w)
    if rate_2w <= 0 or rate_4w <= 0: return None, 'Rates must be greater than zero.'
    qr_path = save_qr_upload(files.get('upi_qr'))
    return {
        'name': name, 'address': address, 'city': city,
        'latitude': lat, 'longitude': lng,
        'n2w': n2w, 'n4w': n4w, 'total': total,
        'rate_2w': rate_2w, 'rate_4w': rate_4w,
        'upi_id': upi_id, 'upi_qr_path': qr_path,
    }, None

@app.route('/vendor/add_lot', methods=['GET', 'POST'])
@app.route('/admin/add_lot',  methods=['GET', 'POST'])
@login_required
def add_lot():
    if current_user.role not in ('vendor', 'admin'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        try:
            data, err = _parse_lot_form(request.form, request.files)
            if err:
                flash(err, 'danger'); return render_template('add_lot.html')
            # Admin-created lots are instantly active. Vendor-created need approval.
            is_active = (current_user.role == 'admin')
            lot = ParkingLot(
                owner_id=current_user.id,
                name=data['name'], address=data['address'], city=data['city'],
                latitude=data['latitude'], longitude=data['longitude'],
                total_slots=data['total'],
                rate_2w=data['rate_2w'], rate_4w=data['rate_4w'],
                upi_id=data['upi_id'], upi_qr_path=data['upi_qr_path'],
                is_active=is_active,
            )
            db.session.add(lot); db.session.flush()
            for i in range(1, data['n2w']+1):
                db.session.add(ParkingSlot(lot_id=lot.id, label=f'2W-{i:03d}',
                                           slot_type='2w', status='available'))
            for i in range(1, data['n4w']+1):
                db.session.add(ParkingSlot(lot_id=lot.id, label=f'4W-{i:03d}',
                                           slot_type='4w', status='available'))
            db.session.commit()
            if is_active:
                flash(f'Lot "{data["name"]}" added & live!', 'success')
                push_notification(current_user.id, 'Lot added',
                                  f'{data["name"]} is live.', '🅿️',
                                  url_for('vendor_lot_grid', lid=lot.id))
            else:
                flash(f'Lot "{data["name"]}" submitted for admin approval.', 'success')
                notify_admins('New lot pending approval',
                              f'{data["name"]} ({data["city"]}) by {current_user.name}',
                              '🆕', url_for('admin_dashboard'))
                push_notification(current_user.id, 'Lot submitted',
                                  'Awaiting admin approval.', '⏳')
            return redirect_by_role()
        except Exception as e:
            db.session.rollback(); print('[AddLot]', e)
            flash(f'Error: {e}', 'danger')
            return render_template('add_lot.html')
    return render_template('add_lot.html')

# ────────────────────────────────────────────────────────────────────
# Edit lot — VENDOR (creates pending edit) or ADMIN (instant)
# ────────────────────────────────────────────────────────────────────
@app.route('/lot/<int:lid>/edit', methods=['GET', 'POST'])
@login_required
def edit_lot(lid):
    if current_user.role not in ('vendor', 'admin'):
        return redirect(url_for('index'))
    lot = db.session.get(ParkingLot, lid)
    if not lot:
        flash('Lot not found.', 'danger'); return redirect_by_role()
    if current_user.role == 'vendor' and lot.owner_id != current_user.id:
        flash('Not your lot.', 'danger'); return redirect(url_for('vendor_dashboard'))

    if request.method == 'POST':
        try:
            data, err = _parse_lot_form(request.form, request.files)
            if err:
                flash(err, 'danger')
                return render_template('edit_lot.html', lot=lot, pending=lot.get_pending_edit())
            payload = {
                'name': data['name'], 'address': data['address'], 'city': data['city'],
                'latitude': data['latitude'], 'longitude': data['longitude'],
                'rate_2w': str(data['rate_2w']), 'rate_4w': str(data['rate_4w']),
                'upi_id': data['upi_id'],
            }
            # Only update QR path if a new file was uploaded
            if data['upi_qr_path']:
                payload['upi_qr_path'] = data['upi_qr_path']

            if current_user.role == 'admin':
                # Apply instantly
                for k, v in payload.items():
                    if k in ('rate_2w','rate_4w'): setattr(lot, k, _safe_decimal(v))
                    else: setattr(lot, k, v)
                lot.pending_edit = None
                db.session.commit()
                push_notification(lot.owner_id, 'Lot updated by admin',
                                  f'{lot.name} was updated.', '✏️',
                                  url_for('vendor_dashboard'))
                flash('Lot updated.', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                # Vendor: queue for approval. Lot stays LIVE with old values.
                lot.pending_edit = json.dumps(payload)
                db.session.commit()
                notify_admins('Lot edit pending approval',
                              f'{current_user.name} edited {lot.name}',
                              '📝', url_for('admin_dashboard'))
                push_notification(current_user.id, 'Edit submitted',
                                  'Your changes are awaiting admin approval. The lot stays live with old values until approved.',
                                  '⏳', url_for('vendor_dashboard'))
                flash('Edit submitted. Lot stays live with old values until admin approves.', 'info')
                return redirect(url_for('vendor_dashboard'))
        except Exception as e:
            db.session.rollback(); print('[EditLot]', e)
            flash(f'Error: {e}', 'danger')
    return render_template('edit_lot.html', lot=lot, pending=lot.get_pending_edit())

@app.route('/admin/lot/<int:lid>/approve_edit', methods=['POST'])
@login_required
def approve_lot_edit(lid):
    if current_user.role != 'admin': return redirect(url_for('index'))
    lot = db.session.get(ParkingLot, lid)
    if not lot or not lot.pending_edit:
        flash('No pending edit.', 'warning'); return redirect(url_for('admin_dashboard'))
    p = lot.get_pending_edit() or {}
    for k, v in p.items():
        if k in ('rate_2w','rate_4w'): setattr(lot, k, _safe_decimal(v))
        else: setattr(lot, k, v)
    lot.pending_edit = None
    db.session.commit()
    push_notification(lot.owner_id, 'Lot edit approved',
                      f'Your changes to {lot.name} are now live.',
                      '✅', url_for('vendor_dashboard'))
    flash('Edit approved & applied.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/lot/<int:lid>/reject_edit', methods=['POST'])
@login_required
def reject_lot_edit(lid):
    if current_user.role != 'admin': return redirect(url_for('index'))
    lot = db.session.get(ParkingLot, lid)
    if not lot:
        flash('Lot not found.', 'danger'); return redirect(url_for('admin_dashboard'))
    lot.pending_edit = None
    db.session.commit()
    push_notification(lot.owner_id, 'Lot edit rejected',
                      f'Your changes to {lot.name} were rejected by admin.',
                      '❌', url_for('vendor_dashboard'))
    flash('Edit rejected.', 'info')
    return redirect(url_for('admin_dashboard'))

# ────────────────────────────────────────────────────────────────────
# Admin
# ────────────────────────────────────────────────────────────────────
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin': return redirect_by_role()
    return render_template('dashboard_admin.html',
        vendors=User.query.filter_by(role='vendor').all(),
        customers=User.query.filter_by(role='customer').all(),
        lots=ParkingLot.query.all(),
        pending_edits=[l for l in ParkingLot.query.all() if l.pending_edit],
        reservations=Reservation.query.order_by(Reservation.created_at.desc()).limit(20).all())

@app.route('/admin/approve_vendor/<int:uid>', methods=['POST'])
@login_required
def approve_vendor(uid):
    if current_user.role != 'admin': return redirect(url_for('index'))
    u = db.session.get(User, uid)
    if u and u.role == 'vendor':
        u.is_approved = True; db.session.commit()
        push_notification(u.id, 'Vendor account approved',
                          'You can now manage your lots.', '🎉',
                          url_for('vendor_dashboard'))
        flash(f'Vendor {u.name} approved.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve_lot/<int:lid>', methods=['POST'])
@login_required
def approve_lot(lid):
    if current_user.role != 'admin': return redirect(url_for('index'))
    lot = db.session.get(ParkingLot, lid)
    if lot:
        lot.is_active = True; db.session.commit()
        push_notification(lot.owner_id, 'Lot approved',
                          f'{lot.name} is now live!', '🎉',
                          url_for('vendor_lot_grid', lid=lot.id))
        flash(f'Lot "{lot.name}" is live.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:uid>', methods=['POST'])
@login_required
def admin_delete_user(uid):
    if current_user.role != 'admin': return redirect(url_for('index'))
    u = db.session.get(User, uid)
    if not u: flash('User not found.', 'danger'); return redirect(url_for('admin_dashboard'))
    if u.role == 'admin': flash('Cannot delete admin.', 'danger'); return redirect(url_for('admin_dashboard'))
    try:
        db.session.delete(u); db.session.commit()
        flash(f'User {u.name} deleted.', 'success')
    except Exception as e:
        db.session.rollback(); flash(str(e), 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_lot/<int:lid>', methods=['POST'])
@login_required
def admin_delete_lot(lid):
    if current_user.role != 'admin': return redirect(url_for('index'))
    lot = db.session.get(ParkingLot, lid)
    if not lot: flash('Lot not found.', 'danger'); return redirect(url_for('admin_dashboard'))
    try:
        db.session.delete(lot); db.session.commit()
        flash(f'Lot "{lot.name}" deleted.', 'success')
    except Exception as e:
        db.session.rollback(); flash(str(e), 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/notify', methods=['GET', 'POST'])
@login_required
def admin_notify():
    if current_user.role != 'admin': return redirect(url_for('index'))
    if request.method == 'POST':
        title  = request.form.get('title', '').strip() or 'Notice'
        body   = request.form.get('body', '').strip()
        target = request.form.get('user_id', 'all')
        users  = User.query.all() if target == 'all' else User.query.filter_by(id=int(target)).all()
        for u in users:
            push_notification(u.id, title, body, '📢')
        flash(f'Sent to {len(users)} user(s).', 'success')
        return redirect(url_for('admin_notify'))
    return render_template('admin_notify.html', all_users=User.query.all())

@app.route('/admin/db')
@login_required
def db_view():
    if current_user.role != 'admin': return redirect(url_for('index'))
    return render_template('db_view.html',
        users=User.query.all(),
        lots=ParkingLot.query.all(),
        reservations=Reservation.query.order_by(Reservation.created_at.desc()).all())

@app.route('/admin/export/<string:table>')
@login_required
def export_csv(table):
    if current_user.role != 'admin': return redirect(url_for('index'))
    out = io.StringIO(); w = csv.writer(out)
    if table == 'users':
        w.writerow(['ID','Name','Email','Role','Phone','Approved','Created'])
        for u in User.query.all():
            w.writerow([u.id, u.name, u.email, u.role, u.phone or '', u.is_approved, u.created_at])
    elif table == 'lots':
        w.writerow(['ID','Name','City','Address','Slots','R2W','R4W','Active','Owner'])
        for l in ParkingLot.query.all():
            w.writerow([l.id, l.name, l.city, l.address, l.total_slots,
                        l.rate_2w, l.rate_4w, l.is_active, l.owner.email if l.owner else ''])
    elif table == 'reservations':
        w.writerow(['ID','Customer','Vehicle','Type','Lot','Slot','Entry','Exit','Amount','Status','Pay','TxnID'])
        for r in Reservation.query.order_by(Reservation.created_at.desc()).all():
            w.writerow([r.id, r.customer.name if r.customer else '', r.vehicle_no, r.vehicle_type,
                        r.slot.lot.name if r.slot else '', r.slot.label if r.slot else '',
                        r.entry_time, r.exit_time or '', r.amount_paid or 0,
                        r.status, r.payment_method or 'cash', r.txn_id or ''])
    else:
        return 'Unknown table', 404
    resp = make_response(out.getvalue())
    resp.headers['Content-Type'] = 'text/csv'
    resp.headers['Content-Disposition'] = f'attachment; filename=spoteasy_{table}.csv'
    return resp

# ────────────────────────────────────────────────────────────────────
# Notifications API
# ────────────────────────────────────────────────────────────────────
@app.route('/api/notifications')
@login_required
def api_notifications():
    after = request.args.get('after_id', type=int)
    q = Notification.query.filter_by(user_id=current_user.id)
    if after:
        q = q.filter(Notification.id > after)
    items = q.order_by(Notification.id.desc()).limit(20).all()
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({
        'ok': True,
        'unread': unread,
        'items': [n.to_dict() for n in items],
    })

@app.route('/api/notifications/read', methods=['POST'])
@login_required
def api_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
                      .update({'is_read': True})
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/notifications/<int:nid>/read', methods=['POST'])
@login_required
def api_notification_read_one(nid):
    n = db.session.get(Notification, nid)
    if not n or n.user_id != current_user.id:
        return jsonify({'error': 'Not found'}), 404
    n.is_read = True; db.session.commit()
    return jsonify({'ok': True})

@app.route('/notifications')
@login_required
def notifications_page():
    items = Notification.query.filter_by(user_id=current_user.id)\
                              .order_by(Notification.id.desc()).limit(100).all()
    return render_template('notifications.html', items=items)

# ────────────────────────────────────────────────────────────────────
# Account
# ────────────────────────────────────────────────────────────────────
@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            name = request.form.get('name', '').strip()
            if name and len(name) >= 3:
                current_user.name  = name
                current_user.phone = request.form.get('phone', '').strip()
                db.session.commit(); flash('Profile updated.', 'success')
            else:
                flash('Name must be at least 3 characters.', 'danger')
        elif action == 'change_password':
            old = request.form.get('old_password', '')
            new = request.form.get('new_password', '')
            con = request.form.get('confirm_password', '')
            if not current_user.check_password(old):
                flash('Current password is incorrect.', 'danger')
            elif len(new) < 8:
                flash('New password must be at least 8 characters.', 'danger')
            elif new != con:
                flash('Passwords do not match.', 'danger')
            else:
                current_user.set_password(new); db.session.commit()
                flash('Password changed.', 'success')
        elif action == 'notify_prefs':
            current_user.notify_browser = bool(request.form.get('notify_browser'))
            current_user.notify_email   = bool(request.form.get('notify_email'))
            db.session.commit()
            flash('Notification preferences saved.', 'success')
        return redirect(url_for('account'))

    stats = {}
    reservations = []
    if current_user.role == 'customer':
        reservations = Reservation.query.filter_by(customer_id=current_user.id)\
                                        .order_by(Reservation.created_at.desc()).limit(5).all()
        all_res = Reservation.query.filter_by(customer_id=current_user.id).all()
        spent = sum(float(r.amount_paid or 0) for r in all_res if r.status=='completed')
        stats = {'total_bookings': len(all_res),
                 'active': sum(1 for r in all_res if r.status=='active'),
                 'completed': sum(1 for r in all_res if r.status=='completed'),
                 'total_spent': round(spent, 2)}
    elif current_user.role == 'vendor':
        lots = ParkingLot.query.filter_by(owner_id=current_user.id).all()
        stats = {'total_lots': len(lots),
                 'total_slots': sum(l.total_slots for l in lots),
                 'active_lots': sum(1 for l in lots if l.is_active)}
    return render_template('account.html', stats=stats, reservations=reservations)

# ────────────────────────────────────────────────────────────────────
# Misc
# ────────────────────────────────────────────────────────────────────
@app.route('/health')
def health():
    try:
        db_type = 'postgresql' if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] else 'sqlite'
        return jsonify({'status': 'ok', 'db': f'connected ({db_type})',
                        'time_ist': now_ist().strftime('%d %b %Y %I:%M %p IST'),
                        'users': User.query.count(),
                        'lots': ParkingLot.query.count(),
                        'reservations': Reservation.query.count()})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/favicon.ico')
def favicon():
    icon_path = os.path.join(app.root_path, 'static', 'icons', 'icon-96.png')
    if os.path.exists(icon_path):
        return send_from_directory('static/icons', 'icon-96.png', mimetype='image/png')
    return ('', 204)

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/sw.js')
def service_worker():
    resp = make_response(send_from_directory('static', 'sw.js'))
    resp.headers['Content-Type']  = 'application/javascript'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp

@app.route('/offline')
def offline():
    return render_template('offline.html')

@app.errorhandler(404)
def err404(e): return render_template('404.html'), 404

@app.errorhandler(500)
def err500(e):
    db.session.rollback()
    try: return render_template('500.html'), 500
    except Exception: return '<h1>500</h1><a href="/">Home</a>', 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
