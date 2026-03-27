"""
ParkSmart India — Database Models
No IoT hardware required. Slot status managed via web UI.
"""
from datetime import datetime, timezone
from decimal import Decimal
import uuid
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey,
    Integer, Numeric, String, Text
)
from sqlalchemy.orm import relationship
import enum

db = SQLAlchemy()

def _uuid():
    return str(uuid.uuid4())

def _now():
    return datetime.now(timezone.utc)

# ── Enums ────────────────────────────────────────────────────────
class UserRole(enum.Enum):
    super_admin = "super_admin"
    vendor      = "vendor"
    customer    = "customer"

class SlotType(enum.Enum):
    TW = "2W"   # Two Wheeler
    FW = "4W"   # Four Wheeler

class SlotStatus(enum.Enum):
    available   = "available"
    occupied    = "occupied"
    reserved    = "reserved"
    maintenance = "maintenance"

class ReservationStatus(enum.Enum):
    pending   = "pending"
    active    = "active"
    completed = "completed"
    cancelled = "cancelled"

class LotStatus(enum.Enum):
    pending  = "pending"
    active   = "active"
    inactive = "inactive"
    rejected = "rejected"

# ── Models ───────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id            = Column(String(36), primary_key=True, default=_uuid)
    role          = Column(Enum(UserRole), nullable=False, default=UserRole.customer)
    full_name     = Column(String(120), nullable=False)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    phone         = Column(String(15))
    password_hash = Column(String(255), nullable=False)
    is_active     = Column(Boolean, default=True)
    is_verified   = Column(Boolean, default=False)
    business_name = Column(String(200))
    created_at    = Column(DateTime(timezone=True), default=_now)

    lots         = relationship("ParkingLot",  back_populates="owner",
                                foreign_keys="ParkingLot.owner_id",
                                cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="customer",
                                foreign_keys="Reservation.customer_id")

    def __repr__(self):
        return f"<User {self.email} [{self.role.value}]>"


class ParkingLot(db.Model):
    __tablename__ = "parking_lots"
    id          = Column(String(36), primary_key=True, default=_uuid)
    owner_id    = Column(String(36), ForeignKey("users.id"), nullable=False)
    name        = Column(String(200), nullable=False)
    address     = Column(Text, nullable=False)
    city        = Column(String(100), nullable=False)
    state       = Column(String(100), default="Uttar Pradesh")
    latitude    = Column(Numeric(9, 6), nullable=False)
    longitude   = Column(Numeric(9, 6), nullable=False)
    rate_2w     = Column(Numeric(6, 2), default=Decimal("10.00"))
    rate_4w     = Column(Numeric(6, 2), default=Decimal("30.00"))
    opens_at    = Column(String(5), default="00:00")
    closes_at   = Column(String(5), default="23:59")
    status      = Column(Enum(LotStatus), default=LotStatus.pending)
    photo_url   = Column(String(512))
    created_at  = Column(DateTime(timezone=True), default=_now)

    owner  = relationship("User", back_populates="lots", foreign_keys=[owner_id])
    slots  = relationship("ParkingSlot", back_populates="lot",
                          cascade="all, delete-orphan")

    @property
    def available_2w(self):
        return sum(1 for s in self.slots
                   if s.slot_type == SlotType.TW and s.status == SlotStatus.available)

    @property
    def available_4w(self):
        return sum(1 for s in self.slots
                   if s.slot_type == SlotType.FW and s.status == SlotStatus.available)

    @property
    def total_available(self):
        return sum(1 for s in self.slots if s.status == SlotStatus.available)

    def to_dict(self):
        return {
            "id":       self.id,
            "name":     self.name,
            "address":  self.address,
            "city":     self.city,
            "lat":      float(self.latitude),
            "lng":      float(self.longitude),
            "rate_2w":  float(self.rate_2w),
            "rate_4w":  float(self.rate_4w),
            "avail_2w": self.available_2w,
            "avail_4w": self.available_4w,
            "total":    len(self.slots),
        }


class ParkingSlot(db.Model):
    __tablename__ = "parking_slots"
    id          = Column(String(36), primary_key=True, default=_uuid)
    lot_id      = Column(String(36), ForeignKey("parking_lots.id"), nullable=False)
    slot_number = Column(String(20), nullable=False)
    slot_type   = Column(Enum(SlotType), nullable=False)
    status      = Column(Enum(SlotStatus), default=SlotStatus.available)
    floor       = Column(String(10), default="G")
    updated_at  = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    lot          = relationship("ParkingLot", back_populates="slots")
    reservations = relationship("Reservation", back_populates="slot")

    def to_dict(self):
        return {
            "id":     self.id,
            "number": self.slot_number,
            "type":   self.slot_type.value,
            "status": self.status.value,
            "floor":  self.floor,
        }


class Reservation(db.Model):
    __tablename__ = "reservations"
    id             = Column(String(36), primary_key=True, default=_uuid)
    customer_id    = Column(String(36), ForeignKey("users.id"), nullable=False)
    slot_id        = Column(String(36), ForeignKey("parking_slots.id"), nullable=False)
    vehicle_number = Column(String(20), nullable=False)
    vehicle_type   = Column(Enum(SlotType), nullable=False)
    status         = Column(Enum(ReservationStatus), default=ReservationStatus.pending)
    qr_token       = Column(String(64), unique=True, default=lambda: uuid.uuid4().hex)
    booked_at      = Column(DateTime(timezone=True), default=_now)
    entry_time     = Column(DateTime(timezone=True))
    exit_time      = Column(DateTime(timezone=True))
    duration_mins  = Column(Integer)
    amount_charged = Column(Numeric(8, 2))
    is_grace       = Column(Boolean, default=False)

    customer = relationship("User", back_populates="reservations",
                            foreign_keys=[customer_id])
    slot     = relationship("ParkingSlot", back_populates="reservations")
