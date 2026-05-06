from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets, json

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default='customer')   # customer | vendor | admin
    phone         = db.Column(db.String(15))
    is_approved   = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # Notifications
    notify_browser   = db.Column(db.Boolean, default=True)
    notify_email     = db.Column(db.Boolean, default=True)

    # For vendor / admin to receive UPI payments globally (used as fallback if lot has none)
    upi_id        = db.Column(db.String(120))
    upi_qr_path   = db.Column(db.String(255))

    lots          = db.relationship('ParkingLot', backref='owner', lazy=True, cascade='all, delete-orphan')
    reservations  = db.relationship('Reservation', backref='customer', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, pw):  self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'email': self.email, 'role': self.role}


class ParkingLot(db.Model):
    __tablename__ = 'parking_lots'
    id          = db.Column(db.Integer, primary_key=True)
    owner_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name        = db.Column(db.String(150), nullable=False)
    address     = db.Column(db.String(300), nullable=False)
    city        = db.Column(db.String(100), nullable=False)
    latitude    = db.Column(db.Float, nullable=False)
    longitude   = db.Column(db.Float, nullable=False)
    total_slots = db.Column(db.Integer, nullable=False)
    rate_2w     = db.Column(db.Numeric(8, 2), nullable=False)
    rate_4w     = db.Column(db.Numeric(8, 2), nullable=False)
    is_active   = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    # UPI payment details for this lot
    upi_id      = db.Column(db.String(120))
    upi_qr_path = db.Column(db.String(255))

    # Pending edit (JSON blob of fields awaiting admin approval) — stays LIVE with old values
    pending_edit = db.Column(db.Text)   # JSON string or NULL

    slots = db.relationship('ParkingSlot', backref='lot', lazy=True, cascade='all, delete-orphan')

    @property
    def available_count(self):
        return sum(1 for s in self.slots if s.status == 'available')

    @property
    def occupied_count(self):
        return sum(1 for s in self.slots if s.status == 'occupied')

    @property
    def has_pending_edit(self):
        return bool(self.pending_edit)

    def get_pending_edit(self):
        try:
            return json.loads(self.pending_edit) if self.pending_edit else None
        except Exception:
            return None

    def to_dict(self, include_pending=False):
        d = {
            'id': self.id, 'name': self.name, 'address': self.address,
            'city': self.city, 'lat': self.latitude, 'lng': self.longitude,
            'total': self.total_slots, 'available': self.available_count,
            'occupied': self.occupied_count,
            'rate_2w': float(self.rate_2w), 'rate_4w': float(self.rate_4w),
            'avail_2w': sum(1 for s in self.slots if s.slot_type == '2w' and s.status == 'available'),
            'avail_4w': sum(1 for s in self.slots if s.slot_type == '4w' and s.status == 'available'),
            'is_active': self.is_active,
            'has_pending_edit': self.has_pending_edit,
            'upi_id': self.upi_id or '',
            'upi_qr_path': self.upi_qr_path or '',
        }
        if include_pending:
            d['pending_edit'] = self.get_pending_edit()
        return d


class ParkingSlot(db.Model):
    __tablename__ = 'parking_slots'
    id        = db.Column(db.Integer, primary_key=True)
    lot_id    = db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable=False)
    label     = db.Column(db.String(10), nullable=False)
    status    = db.Column(db.String(20), nullable=False, default='available')
    slot_type = db.Column(db.String(5), default='4w')

    reservations = db.relationship('Reservation', backref='slot', lazy=True)

    def to_dict(self):
        return {'id': self.id, 'label': self.label, 'status': self.status,
                'slot_type': self.slot_type, 'is_occupied': self.status == 'occupied'}


class Reservation(db.Model):
    __tablename__ = 'reservations'
    id              = db.Column(db.Integer, primary_key=True)
    customer_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    slot_id         = db.Column(db.Integer, db.ForeignKey('parking_slots.id'), nullable=False)
    vehicle_no      = db.Column(db.String(20), nullable=False)
    vehicle_type    = db.Column(db.String(5), nullable=False)
    entry_time      = db.Column(db.DateTime, default=datetime.utcnow)
    exit_time       = db.Column(db.DateTime)
    amount_paid     = db.Column(db.Numeric(10, 2), default=0)
    status          = db.Column(db.String(20), default='active')  # active | completed | cancelled
    qr_token        = db.Column(db.String(64), unique=True, default=lambda: secrets.token_hex(32))

    payment_method  = db.Column(db.String(20), default='cash')   # cash | upi
    payment_status  = db.Column(db.String(20), default='pending')  # pending | verified | failed
    txn_id          = db.Column(db.String(120))                    # UPI transaction id

    created_at      = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title      = db.Column(db.String(150), nullable=False)
    body       = db.Column(db.String(500))
    icon       = db.Column(db.String(20), default='🔔')
    url        = db.Column(db.String(255))     # optional click-through URL
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'body': self.body or '',
            'icon': self.icon or '🔔', 'url': self.url or '',
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else '',
        }
