"""Enums for constrained model fields."""

import enum


class UserRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    hookah_master = "hookah_master"


class BookingStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class OrderStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    preparing = "preparing"
    served = "served"
    cancelled = "cancelled"


class TableShape(str, enum.Enum):
    rect = "rect"
    circle = "circle"


class OrderSource(str, enum.Enum):
    booking_preorder = "booking_preorder"
    qr_table = "qr_table"
    telegram = "telegram"
