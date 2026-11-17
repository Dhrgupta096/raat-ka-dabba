#!/usr/bin/env python3
"""
Raat Ka Dabba — Full-Stack Server & Core Business Engine
Exclusively for Tower 3 Hostel Students | Cafe: Grains and Gossip | Minimum Shared Cart: ₹350
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
import re
import secrets
import sqlite3
import threading
from urllib.parse import parse_qs, urlparse

ROOT_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT_DIR / "public"
DEFAULT_DB_PATH = ROOT_DIR / "bitetogether.db"

MINIMUM_CART_INR = 350  # cafe's printed minimum order value (food only)
PACKING_FEE_PER_ITEM_INR = 10  # Rs 10 per container; drinks are free
CAFE_INFO = {
    "phone": "+91 99809 25507",
    "timings": "10:00 PM – 3:00 AM",
    "pickup": "Hostel Reception",
    "delivery_fee": "Free",
    "eta": "30 min or more",
}
CAFE_NAME = "Grains and Gossip"
ALLOWED_TOWER = "Tower 3"
HOSTEL_NAME = "Tower 3 Boys Hostel"
CUSTOM_DOMAIN = os.environ.get("BITETOGETHER_DOMAIN", "https://t3.raatkadabba.in")
ALLOWED_EMAIL_DOMAIN = os.environ.get("ALLOWED_EMAIL_DOMAIN", "college.edu").lower()
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_Raat Ka DabbaT3")
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "bt_tower3_hmac_secret_2026")
SUPABASE_CONFIGURED = bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_ANON_KEY"))

ORDER_PIPELINE = [
    "collecting",
    "minimum_reached",
    "payments_completed",
    "order_placed",
]

STATUS_LABELS = {
    "collecting": "Collecting orders",
    "minimum_reached": "Minimum ₹350 reached",
    "payments_completed": "All shares paid",
    "order_placed": "Order sent to Grains and Gossip",
    "closed": "Closed by creator",
}

# Real Grains and Gossip late-night menu (prices include GST). Edit here to update the menu.
MENU_CATEGORIES = [
    "Rice & Noodles",
    "Burgers",
    "Pizza",
    "Sandwiches",
    "Pasta",
    "Fries & Snacks",
    "Starters",
    "Juices & Shakes",
    "Hot Drinks",
]
DRINK_CATEGORIES = {"Juices & Shakes", "Hot Drinks"}  # no packing charge on these

V, NV = 1, 0
MENU = [
    ("rn1", "Rice & Noodles", "Burned Chilly Garlic Fried Rice / Noodles", 159, V),
    ("rn2", "Rice & Noodles", "Corn & Bell Pepper Rice / Noodles", 159, V),
    ("rn3", "Rice & Noodles", "Paneer Fried Rice / Noodles", 169, V),
    ("rn4", "Rice & Noodles", "Schezwan Fried Rice / Noodles", 159, V),
    ("rn5", "Rice & Noodles", "Chilly Garlic Egg Fried Rice / Noodles", 179, NV),
    ("rn6", "Rice & Noodles", "Schezwan Egg Fried Rice / Noodles", 179, NV),
    ("rn7", "Rice & Noodles", "Stir Fried Egg Rice / Noodles", 179, NV),
    ("rn8", "Rice & Noodles", "Chilly Garlic Chicken Fried Rice / Noodles", 209, NV),
    ("rn9", "Rice & Noodles", "Schezwan Chicken Fried Rice / Noodles", 209, NV),
    ("rn10", "Rice & Noodles", "Stir Fried Chicken Rice / Noodles", 209, NV),
    ("bg1", "Burgers", "Classic Veg Burger", 119, V),
    ("bg2", "Burgers", "Juicy Cheese Burger", 139, V),
    ("bg3", "Burgers", "Juicy Chicken Burger", 159, NV),
    ("bg4", "Burgers", "BBQ Chicken Burger", 169, NV),
    ("bg5", "Burgers", "Chicken Cheese Burger", 169, NV),
    ("bg6", "Burgers", "Grilled Chicken Burger", 169, NV),
    ("pz1", "Pizza", "Spicy Paneer Tikka Pizza", 269, V),
    ("pz2", "Pizza", "Margherita", 199, V),
    ("pz3", "Pizza", "Garden Fresh Classic Pizza", 269, V),
    ("pz4", "Pizza", "Cheese Corn Pizza", 259, V),
    ("pz5", "Pizza", "Veg Cheese Garlic Pizza", 229, V),
    ("pz6", "Pizza", "Desi Chicken Tikka Pizza", 349, NV),
    ("pz7", "Pizza", "BBQ Chicken Pizza", 349, NV),
    ("pz8", "Pizza", "Grilled Chicken Pizza", 369, NV),
    ("pz9", "Pizza", "Peri Peri Chicken Pizza", 359, NV),
    ("sw1", "Sandwiches", "Paneer Tikka Sandwich", 119, V),
    ("sw2", "Sandwiches", "Juicy Veg Cheese Sandwich", 119, V),
    ("sw3", "Sandwiches", "Grilled Veg Sandwich", 119, V),
    ("sw4", "Sandwiches", "Egg Mayo Sandwich", 119, NV),
    ("sw5", "Sandwiches", "Desi Chicken Tikka Sandwich", 159, NV),
    ("ps1", "Pasta", "Veg Pasta in White and Red Sauce", 169, V),
    ("ps2", "Pasta", "Chicken Pasta in White and Red Sauce", 209, NV),
    ("fs1", "Fries & Snacks", "French Fries", 69, V),
    ("fs2", "Fries & Snacks", "Peri Peri Fries", 79, V),
    ("fs3", "Fries & Snacks", "Cheese Fries", 99, V),
    ("fs4", "Fries & Snacks", "Nachos", 119, V),
    ("fs5", "Fries & Snacks", "Cheesy Nachos", 129, V),
    ("fs6", "Fries & Snacks", "Potato Wedges", 79, V),
    ("st1", "Starters", "Chilli Paneer", 119, V),
    ("st2", "Starters", "Honey Chilli Potato", 99, V),
    ("st3", "Starters", "Cheese Corn Nuggets", 109, V),
    ("st4", "Starters", "Cheese Corn Finger", 109, V),
    ("st5", "Starters", "Chicken Nuggets", 149, NV),
    ("st6", "Starters", "Gossip Fried Chicken", 149, NV),
    ("st7", "Starters", "Peri Peri Chicken Popcorn", 149, NV),
    ("st8", "Starters", "BBQ Chicken Wings", 159, NV),
    ("st9", "Starters", "Chicken Lollipop", 159, NV),
    ("st10", "Starters", "Masala Omelette", 59, NV),
    ("js1", "Juices & Shakes", "Watermelon Juice", 59, V),
    ("js2", "Juices & Shakes", "Fresh Lime", 39, V),
    ("js3", "Juices & Shakes", "Apple Juice", 99, V),
    ("js4", "Juices & Shakes", "Pineapple Juice", 89, V),
    ("js5", "Juices & Shakes", "Brownie Milk Shake", 129, V),
    ("js6", "Juices & Shakes", "Chocolate Milk Shake", 99, V),
    ("hd1", "Hot Drinks", "Cappuccino", 99, V),
    ("hd2", "Hot Drinks", "Cafe Latte", 99, V),
    ("hd3", "Hot Drinks", "Masala Tea", 29, V),
    ("hd4", "Hot Drinks", "Hot Chocolate Coffee", 99, V),
]


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "bad_request"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str) -> str:
    return hashlib.sha256(f"bt_t3_salt::{password}".encode("utf-8")).hexdigest()


def compute_gateway_signature(gateway_order_id: str, gateway_payment_id: str, outcome: str) -> str:
    payload = f"{gateway_order_id}|{gateway_payment_id}|{outcome}".encode("utf-8")
    return hmac.new(RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def normalize_tower3_room(room_raw: str, tower_raw: str = "Tower 3") -> str:
    tower_clean = (tower_raw or "").strip()
    if tower_clean.lower() not in ("tower 3", "t3", "tower-3", ""):
        raise AppError(
            "Access restricted: Raat Ka Dabba is exclusively for Tower 3 hostel students.",
            status_code=403,
            code="tower_restricted",
        )
    room = (room_raw or "").strip().upper().replace(" ", "")
    if re.match(r"^T[12456789]-", room) or "TOWER1" in room or "TOWER2" in room or "TOWER4" in room:
        raise AppError(
            "Access restricted: Only Tower 3 room numbers (e.g., T3-304) are eligible.",
            status_code=403,
            code="tower_restricted",
        )
    if room.startswith("T3-"):
        suffix = room[3:]
    elif room.startswith("T3"):
        suffix = room[2:]
    else:
        suffix = room
    if not re.match(r"^[1-9][0-9]{2}[A-Z]?$", suffix):
        raise AppError(
            "Invalid Tower 3 room number. Use a 3-digit room like T3-204 or 304.",
            status_code=400,
            code="invalid_room",
        )
    return f"T3-{suffix}"


class RaatKaDabbaEngine:
    """Thread-safe SQLite + SSE Real-Time Engine enforcing all Raat Ka Dabba rules."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH, seed_demo: bool = False):
        self.db_path = Path(db_path)
        # ponytail: single process-wide lock serializes writes; upgrade to PostgreSQL/Supabase pool when scaling multi-node
        self._lock = threading.RLock()
        self._sse_clients: list[queue.Queue] = []
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _broadcast(self, event_type: str, payload: dict) -> None:
        msg = json.dumps({"event": event_type, "data": payload, "ts": now_iso()})
        with self._lock:
            stale = []
            for q in self._sse_clients:
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    stale.append(q)
            for q in stale:
                if q in self._sse_clients:
                    self._sse_clients.remove(q)

    def subscribe_sse(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=64)
        with self._lock:
            self._sse_clients.append(q)
        return q

    def unsubscribe_sse(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._sse_clients:
                self._sse_clients.remove(q)

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    id TEXT PRIMARY KEY,
                    student_name TEXT NOT NULL,
                    college_email TEXT NOT NULL UNIQUE,
                    student_id TEXT NOT NULL UNIQUE,
                    tower TEXT NOT NULL DEFAULT 'Tower 3' CHECK (tower = 'Tower 3'),
                    room_number TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    auth_mode TEXT NOT NULL DEFAULT 'demo',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS menu_items (
                    id TEXT PRIMARY KEY,
                    cafe_name TEXT NOT NULL DEFAULT 'Grains and Gossip' CHECK (cafe_name = 'Grains and Gossip'),
                    category TEXT NOT NULL,
                    name TEXT NOT NULL,
                    price_inr INTEGER NOT NULL CHECK (price_inr > 0),
                    is_veg INTEGER NOT NULL DEFAULT 1,
                    is_drink INTEGER NOT NULL DEFAULT 0,
                    is_available INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS group_orders (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    cafe_name TEXT NOT NULL DEFAULT 'Grains and Gossip' CHECK (cafe_name = 'Grains and Gossip'),
                    creator_id TEXT NOT NULL REFERENCES profiles(id),
                    tower TEXT NOT NULL DEFAULT 'Tower 3' CHECK (tower = 'Tower 3'),
                    deadline TEXT NOT NULL,
                    participant_limit INTEGER,
                    minimum_cart_inr INTEGER NOT NULL DEFAULT 350 CHECK (minimum_cart_inr = 350),
                    cart_frozen INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'collecting',
                    share_link TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS group_participants (
                    id TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL REFERENCES group_orders(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                    joined_at TEXT NOT NULL,
                    UNIQUE (group_id, user_id)
                );

                CREATE TABLE IF NOT EXISTS cart_items (
                    id TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL REFERENCES group_orders(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                    menu_item_id TEXT NOT NULL REFERENCES menu_items(id),
                    quantity INTEGER NOT NULL CHECK (quantity > 0 AND quantity <= 20),
                    unit_price_inr INTEGER NOT NULL CHECK (unit_price_inr > 0),
                    updated_at TEXT NOT NULL,
                    UNIQUE (group_id, user_id, menu_item_id)
                );

                CREATE TABLE IF NOT EXISTS payments (
                    id TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL REFERENCES group_orders(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                    items_subtotal_inr INTEGER NOT NULL CHECK (items_subtotal_inr > 0),
                    packaging_fee_inr INTEGER NOT NULL DEFAULT 0,
                    payable_amount_inr INTEGER NOT NULL CHECK (payable_amount_inr = items_subtotal_inr + packaging_fee_inr),
                    method TEXT NOT NULL DEFAULT 'upi_qr',
                    upi_vpa TEXT,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'failed')),
                    gateway_order_id TEXT UNIQUE,
                    gateway_payment_id TEXT,
                    gateway_signature TEXT,
                    verified_by_server INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    verified_at TEXT,
                    UNIQUE (group_id, user_id)
                );

                CREATE TABLE IF NOT EXISTS notifications (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                    group_id TEXT REFERENCES group_orders(id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    is_read INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS order_status_history (
                    id TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL REFERENCES group_orders(id) ON DELETE CASCADE,
                    status TEXT NOT NULL,
                    note TEXT NOT NULL,
                    changed_by TEXT REFERENCES profiles(id),
                    created_at TEXT NOT NULL
                );
                """
            )

            for item_id, category, name, price, is_veg in MENU:
                conn.execute(
                    """
                    INSERT INTO menu_items (id, cafe_name, category, name, price_inr, is_veg, is_drink, is_available)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    ON CONFLICT(id) DO UPDATE SET
                        category = excluded.category, name = excluded.name, price_inr = excluded.price_inr,
                        is_veg = excluded.is_veg, is_drink = excluded.is_drink
                    """,
                    (item_id, CAFE_NAME, category, name, price, is_veg, int(category in DRINK_CATEGORIES)),
                )

    def _seed_initial_data(self) -> None:
        with self._lock, self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
            if count > 0:
                return

            ts = now_iso()
            demo_students = [
                ("u-aarav", "Aarav Sharma", "aarav.t3@college.edu", "2024CS104", "T3-204"),
                ("u-priya", "Priya Nair", "priya.t3@college.edu", "2024EC211", "T3-412"),
                ("u-rohan", "Rohan Verma", "rohan.t3@college.edu", "2024ME309", "T3-108"),
                ("u-sneha", "Sneha Kulkarni", "sneha.t3@college.edu", "2024AI118", "T3-315"),
            ]
            for uid, name, email, sid, room in demo_students:
                conn.execute(
                    """
                    INSERT INTO profiles (id, student_name, college_email, student_id, tower, room_number, password_hash, auth_mode, created_at)
                    VALUES (?, ?, ?, ?, 'Tower 3', ?, ?, 'demo', ?)
                    """,
                    (uid, name, email, sid, room, hash_password("tower3pass"), ts),
                )

            # Group 1: below the minimum (Rs 198 of Rs 350) so students can see the locked state
            g1_id = "RKD-T3-2041"
            deadline_1 = (datetime.now(timezone.utc) + timedelta(minutes=25)).isoformat()
            conn.execute(
                """
                INSERT INTO group_orders
                (id, name, cafe_name, creator_id, tower, deadline, participant_limit, minimum_cart_inr, cart_frozen, status, share_link, created_at)
                VALUES (?, ?, ?, ?, 'Tower 3', ?, 5, ?, 0, 'collecting', ?, ?)
                """,
                (g1_id, "2nd Floor Midnight Cravings", CAFE_NAME, "u-aarav", deadline_1, MINIMUM_CART_INR, f"/?group={g1_id}", ts),
            )
            for uid in ("u-aarav", "u-priya"):
                conn.execute(
                    "INSERT INTO group_participants (id, group_id, user_id, joined_at) VALUES (?, ?, ?, ?)",
                    (f"gp-{secrets.token_hex(4)}", g1_id, uid, ts),
                )
            seed_items = [
                ("ci-seed-1", g1_id, "u-aarav", "bg1"),  # Classic Veg Burger 119
                ("ci-seed-2", g1_id, "u-priya", "fs2"),  # Peri Peri Fries 79
            ]
            conn.execute(
                "INSERT INTO order_status_history (id, group_id, status, note, changed_by, created_at) VALUES (?, ?, 'collecting', ?, 'u-aarav', ?)",
                ("osh-seed-1", g1_id, "Group created by Aarav Sharma (T3-204).", ts),
            )

            # Group 2: above the minimum (Rs 417) so checkout can be demoed straight away
            g2_id = "RKD-T3-4129"
            deadline_2 = (datetime.now(timezone.utc) + timedelta(minutes=18)).isoformat()
            conn.execute(
                """
                INSERT INTO group_orders
                (id, name, cafe_name, creator_id, tower, deadline, participant_limit, minimum_cart_inr, cart_frozen, status, share_link, created_at)
                VALUES (?, ?, ?, ?, 'Tower 3', ?, 4, ?, 0, 'collecting', ?, ?)
                """,
                (g2_id, "Wing-B Exam Study Fuel", CAFE_NAME, "u-rohan", deadline_2, MINIMUM_CART_INR, f"/?group={g2_id}", ts),
            )
            for uid in ("u-rohan", "u-sneha", "u-aarav"):
                conn.execute(
                    "INSERT INTO group_participants (id, group_id, user_id, joined_at) VALUES (?, ?, ?, ?)",
                    (f"gp-{secrets.token_hex(4)}", g2_id, uid, ts),
                )
            seed_items += [
                ("ci-seed-3", g2_id, "u-rohan", "pz2"),  # Margherita 199
                ("ci-seed-4", g2_id, "u-sneha", "sw1"),  # Paneer Tikka Sandwich 119
                ("ci-seed-5", g2_id, "u-aarav", "js6"),  # Chocolate Milk Shake 99
            ]
            for cid, gid, uid, mid in seed_items:
                price = conn.execute("SELECT price_inr FROM menu_items WHERE id = ?", (mid,)).fetchone()[0]
                conn.execute(
                    "INSERT INTO cart_items (id, group_id, user_id, menu_item_id, quantity, unit_price_inr, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
                    (cid, gid, uid, mid, price, ts),
                )
            conn.execute(
                "INSERT INTO order_status_history (id, group_id, status, note, changed_by, created_at) VALUES (?, ?, 'collecting', ?, 'u-rohan', ?)",
                ("osh-seed-2", g2_id, "Group created by Rohan Verma (T3-108).", ts),
            )

            self._notify_conn(
                conn,
                "u-aarav",
                g1_id,
                "food_added",
                "Priya added Peri Peri Fries",
                "2nd Floor Midnight Cravings is at ₹198. ₹152 more to unlock checkout.",
            )
            self._notify_conn(
                conn,
                "u-aarav",
                g2_id,
                "minimum_reached",
                f"Wing-B Exam Study Fuel crossed ₹{MINIMUM_CART_INR}",
                "Checkout is unlocked. You only pay for your own Chocolate Milk Shake.",
            )

    def _packing_fee_conn(self, conn: sqlite3.Connection, group_id: str, user_id: str) -> int:
        qty = conn.execute(
            """
            SELECT COALESCE(SUM(ci.quantity), 0) FROM cart_items ci
            JOIN menu_items m ON m.id = ci.menu_item_id
            WHERE ci.group_id = ? AND ci.user_id = ? AND m.is_drink = 0
            """,
            (group_id, user_id),
        ).fetchone()[0]
        return PACKING_FEE_PER_ITEM_INR * int(qty)

    def _notify_conn(
        self,
        conn: sqlite3.Connection,
        user_id: str,
        group_id: str | None,
        event_type: str,
        title: str,
        message: str,
    ) -> None:
        conn.execute(
            """
            INSERT INTO notifications (id, user_id, group_id, event_type, title, message, is_read, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (f"notif-{secrets.token_hex(6)}", user_id, group_id, event_type, title, message, now_iso()),
        )

    def _notify_group_conn(
        self,
        conn: sqlite3.Connection,
        group_id: str,
        event_type: str,
        title: str,
        message: str,
    ) -> None:
        rows = conn.execute(
            "SELECT user_id FROM group_participants WHERE group_id = ?", (group_id,)
        ).fetchall()
        for r in rows:
            self._notify_conn(conn, r["user_id"], group_id, event_type, title, message)

    # -------------------------------------------------------------------------
    # AUTHENTICATION (Tower 3 Only)
    # -------------------------------------------------------------------------
    def get_user(self, user_id: str) -> dict:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT id, student_name, college_email, student_id, tower, room_number, auth_mode, created_at FROM profiles WHERE id = ?",
                (user_id,),
            ).fetchone()
            if not row:
                raise AppError("Tower 3 student session not found. Please sign in.", status_code=401, code="unauthorized")
            if row["tower"] != ALLOWED_TOWER:
                raise AppError("Access restricted to Tower 3 hostel students only.", status_code=403, code="tower_restricted")
            return dict(row)

    def list_demo_profiles(self) -> list[dict]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT id, student_name, college_email, student_id, tower, room_number, auth_mode FROM profiles ORDER BY created_at ASC"
            ).fetchall()
            return [dict(r) for r in rows]

    def register_student(
        self,
        student_name: str,
        college_email: str,
        student_id: str,
        room_number: str,
        password: str,
        tower: str = "Tower 3",
    ) -> dict:
        name_clean = (student_name or "").strip()
        email_clean = (college_email or "").strip().lower()
        sid_clean = (student_id or "").strip().upper()
        if len(name_clean) < 2:
            raise AppError("Student name must be at least 2 characters.")
        if "@" not in email_clean or not email_clean.endswith(f"@{ALLOWED_EMAIL_DOMAIN}"):
            raise AppError(f"Use your official @{ALLOWED_EMAIL_DOMAIN} student email address.")
        if len(sid_clean) < 3:
            raise AppError("Enter a valid college student ID.")
        if not password or len(password) < 4:
            raise AppError("Password must be at least 4 characters.")

        normalized_room = normalize_tower3_room(room_number, tower)
        uid = f"u-{secrets.token_hex(5)}"
        ts = now_iso()

        with self._lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM profiles WHERE college_email = ? OR student_id = ?",
                (email_clean, sid_clean),
            ).fetchone()
            if existing:
                raise AppError("A Tower 3 Boys Hostel student with this email or student ID is already registered.", status_code=409)

            conn.execute(
                """
                INSERT INTO profiles (id, student_name, college_email, student_id, tower, room_number, password_hash, auth_mode, created_at)
                VALUES (?, ?, ?, ?, 'Tower 3', ?, ?, 'standard', ?)
                """,
                (uid, name_clean, email_clean, sid_clean, normalized_room, hash_password(password), ts),
            )
            self._notify_conn(
                conn,
                uid,
                None,
                "group_joined",
                f"Welcome to Raat Ka Dabba ({HOSTEL_NAME})",
                f"Verified {name_clean} ({normalized_room}). Join a shared cart or start a group order from Grains and Gossip.",
            )
        user = self.get_user(uid)
        self._broadcast("profile_registered", {"user": user})
        return user

    def login_student(self, identifier: str, password: str, tower: str = "Tower 3") -> dict:
        if (tower or "Tower 3").strip().lower() not in ("tower 3", "t3"):
            raise AppError("Access restricted: Raat Ka Dabba is exclusively for Tower 3 students.", status_code=403, code="tower_restricted")
        ident = (identifier or "").strip()
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, password_hash, tower FROM profiles
                WHERE lower(college_email) = lower(?) OR upper(student_id) = upper(?) OR upper(room_number) = upper(?)
                """,
                (ident, ident, ident),
            ).fetchone()
            if not row or row["password_hash"] != hash_password(password):
                raise AppError("Invalid credentials or student not found in Tower 3 registry.", status_code=401)
            if row["tower"] != ALLOWED_TOWER:
                raise AppError("Only Tower 3 residents can access Raat Ka Dabba.", status_code=403)
            return self.get_user(row["id"])

    # -------------------------------------------------------------------------
    # MENU
    # -------------------------------------------------------------------------
    def get_menu(self) -> dict:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT id, category, name, price_inr, is_veg, is_drink FROM menu_items WHERE is_available = 1"
            ).fetchall()
            items = [dict(r) for r in rows]
        return {
            "cafe_name": CAFE_NAME,
            "minimum_cart_inr": MINIMUM_CART_INR,
            "categories": MENU_CATEGORIES,
            "items": items,
        }

    # -------------------------------------------------------------------------
    # GROUP ORDERS & SHARED CART HYDRATION
    # -------------------------------------------------------------------------
    def _hydrate_group_conn(self, conn: sqlite3.Connection, group_row: sqlite3.Row) -> dict:
        group = dict(group_row)
        gid = group["id"]

        creator = conn.execute(
            "SELECT id, student_name, room_number, student_id FROM profiles WHERE id = ?",
            (group["creator_id"],),
        ).fetchone()
        group["creator"] = dict(creator) if creator else None

        participants_rows = conn.execute(
            """
            SELECT gp.user_id, gp.joined_at, p.student_name, p.room_number, p.student_id, p.college_email
            FROM group_participants gp
            JOIN profiles p ON p.id = gp.user_id
            WHERE gp.group_id = ?
            ORDER BY gp.joined_at ASC
            """,
            (gid,),
        ).fetchall()

        cart_rows = conn.execute(
            """
            SELECT ci.id, ci.group_id, ci.user_id, ci.menu_item_id, ci.quantity, ci.unit_price_inr, ci.updated_at,
                   m.name AS item_name, m.category, m.is_veg, m.is_drink,
                   p.student_name, p.room_number
            FROM cart_items ci
            JOIN menu_items m ON m.id = ci.menu_item_id
            JOIN profiles p ON p.id = ci.user_id
            WHERE ci.group_id = ?
            ORDER BY ci.updated_at ASC
            """,
            (gid,),
        ).fetchall()

        payment_rows = conn.execute(
            """
            SELECT id, group_id, user_id, items_subtotal_inr, packaging_fee_inr, payable_amount_inr,
                   method, upi_vpa, status, gateway_order_id, gateway_payment_id, verified_by_server,
                   created_at, verified_at
            FROM payments
            WHERE group_id = ?
            """,
            (gid,),
        ).fetchall()
        payments_by_user = {r["user_id"]: dict(r) for r in payment_rows}

        items_by_user: dict[str, list[dict]] = {}
        shared_total = 0
        total_item_count = 0

        for cr in cart_rows:
            c_dict = dict(cr)
            line_total = c_dict["quantity"] * c_dict["unit_price_inr"]
            c_dict["line_total_inr"] = line_total
            shared_total += line_total
            total_item_count += c_dict["quantity"]
            items_by_user.setdefault(c_dict["user_id"], []).append(c_dict)

        participant_sections = []
        participant_ids = {r["user_id"] for r in participants_rows}

        for pr in participants_rows:
            uid = pr["user_id"]
            user_items = items_by_user.get(uid, [])
            user_subtotal = sum(i["line_total_inr"] for i in user_items)
            packaging_fee = PACKING_FEE_PER_ITEM_INR * sum(i["quantity"] for i in user_items if not i["is_drink"])
            payable = user_subtotal + packaging_fee
            pay_record = payments_by_user.get(uid)
            if pay_record and pay_record.get("gateway_order_id"):
                pay_record = dict(pay_record)
                sample_pay_id = pay_record.get("gateway_payment_id") or f"pay_{gid.replace('-', '')}_{uid[-4:]}"
                pay_record["sandbox_webhook_helper"] = {
                    "gateway_order_id": pay_record["gateway_order_id"],
                    "sample_payment_id": sample_pay_id,
                    "paid_signature": compute_gateway_signature(pay_record["gateway_order_id"], sample_pay_id, "paid"),
                    "failed_signature": compute_gateway_signature(pay_record["gateway_order_id"], sample_pay_id, "failed"),
                }

            participant_sections.append(
                {
                    "user_id": uid,
                    "student_name": pr["student_name"],
                    "room_number": pr["room_number"],
                    "student_id": pr["student_id"],
                    "joined_at": pr["joined_at"],
                    "is_creator": uid == group["creator_id"],
                    "items": user_items,
                    "items_subtotal_inr": user_subtotal,
                    "packaging_fee_inr": packaging_fee,
                    "payable_amount_inr": payable,
                    "payment": pay_record,
                }
            )

        remaining_inr = max(0, MINIMUM_CART_INR - shared_total)
        progress_pct = min(100, int(round((shared_total / MINIMUM_CART_INR) * 100))) if MINIMUM_CART_INR else 100
        checkout_unlocked = shared_total >= MINIMUM_CART_INR

        active_ordering_users = [s for s in participant_sections if s["items_subtotal_inr"] > 0]
        paid_verified_users = [
            s
            for s in active_ordering_users
            if s["payment"] and s["payment"]["status"] == "paid" and s["payment"]["verified_by_server"] == 1
        ]
        all_active_paid = len(active_ordering_users) > 0 and len(paid_verified_users) == len(active_ordering_users)

        history_rows = conn.execute(
            """
            SELECT h.id, h.status, h.note, h.created_at, p.student_name, p.room_number
            FROM order_status_history h
            LEFT JOIN profiles p ON p.id = h.changed_by
            WHERE h.group_id = ?
            ORDER BY h.created_at ASC
            """,
            (gid,),
        ).fetchall()

        group.update(
            {
                "status_label": STATUS_LABELS.get(group["status"], group["status"]),
                "participant_count": len(participant_sections),
                "participant_ids": list(participant_ids),
                "participants": participant_sections,
                "cart_items": [dict(r) for r in cart_rows],
                "total_item_count": total_item_count,
                "shared_cart_total_inr": shared_total,
                "remaining_to_minimum_inr": remaining_inr,
                "progress_percent": progress_pct,
                "checkout_unlocked": checkout_unlocked,
                "active_ordering_count": len(active_ordering_users),
                "paid_verified_count": len(paid_verified_users),
                "all_payments_verified": all_active_paid,
                "can_place_cafe_order": checkout_unlocked and all_active_paid,
                "status_history": [dict(r) for r in history_rows],
                "pipeline": ORDER_PIPELINE,
            }
        )
        return group

    def list_groups(self) -> list[dict]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM group_orders ORDER BY created_at DESC").fetchall()
            return [self._hydrate_group_conn(conn, r) for r in rows]

    def get_group(self, group_id: str) -> dict:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM group_orders WHERE id = ?", (group_id,)).fetchone()
            if not row:
                raise AppError(f"Group order '{group_id}' not found.", status_code=404, code="not_found")
            return self._hydrate_group_conn(conn, row)

    def create_group(
        self,
        user_id: str,
        name: str,
        deadline_minutes: int = 30,
        participant_limit: int | None = None,
        cafe_name: str = CAFE_NAME,
    ) -> dict:
        user = self.get_user(user_id)
        if cafe_name and cafe_name.strip() != CAFE_NAME:
            raise AppError(f"Only '{CAFE_NAME}' is supported for Tower 3 late-night group orders.", status_code=400)
        clean_name = (name or "").strip()
        if len(clean_name) < 3:
            raise AppError("Group name must be at least 3 characters.")
        mins = max(5, min(240, int(deadline_minutes or 30)))
        limit_val = None
        if participant_limit not in (None, "", 0, "0"):
            limit_val = int(participant_limit)
            if limit_val < 2 or limit_val > 25:
                raise AppError("Participant limit must be between 2 and 25 students (or left blank for unlimited).")

        gid = f"RKD-T3-{secrets.randbelow(9000) + 1000}"
        ts = now_iso()
        deadline_iso = (datetime.now(timezone.utc) + timedelta(minutes=mins)).isoformat()
        share_link = f"{CUSTOM_DOMAIN}/?group={gid}"

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO group_orders
                (id, name, cafe_name, creator_id, tower, deadline, participant_limit, minimum_cart_inr, cart_frozen, status, share_link, created_at)
                VALUES (?, ?, ?, ?, 'Tower 3', ?, ?, ?, 0, 'collecting', ?, ?)
                """,
                (gid, clean_name, CAFE_NAME, user["id"], deadline_iso, limit_val, MINIMUM_CART_INR, share_link, ts),
            )
            conn.execute(
                "INSERT INTO group_participants (id, group_id, user_id, joined_at) VALUES (?, ?, ?, ?)",
                (f"gp-{secrets.token_hex(4)}", gid, user["id"], ts),
            )
            conn.execute(
                "INSERT INTO order_status_history (id, group_id, status, note, changed_by, created_at) VALUES (?, ?, 'collecting', ?, ?, ?)",
                (
                    f"osh-{secrets.token_hex(4)}",
                    gid,
                    f"Group created by {user['student_name']} ({user['room_number']}). Collecting orders for {CAFE_NAME}.",
                    user["id"],
                    ts,
                ),
            )
            self._notify_conn(
                conn,
                user["id"],
                gid,
                "group_joined",
                f"Created group {clean_name} ({gid})",
                f"Share link {share_link} with Tower 3 wingmates to hit ₹{MINIMUM_CART_INR} together!",
            )

        group = self.get_group(gid)
        self._broadcast("group_created", {"group": group})
        return group

    def join_group(self, user_id: str, group_id: str, strict_duplicate_check: bool = True) -> dict:
        user = self.get_user(user_id)
        with self._lock, self._connect() as conn:
            group_row = conn.execute("SELECT * FROM group_orders WHERE id = ?", (group_id,)).fetchone()
            if not group_row:
                raise AppError("Group order not found.", status_code=404)
            if group_row["status"] in ("closed", "completed", "order_placed", "preparing", "ready_for_pickup"):
                raise AppError(f"Cannot join group: order is already '{STATUS_LABELS.get(group_row['status'], group_row['status'])}'.", status_code=409)
            if group_row["cart_frozen"]:
                raise AppError("Cannot join group while shared cart is frozen for checkout.", status_code=409)

            existing = conn.execute(
                "SELECT id FROM group_participants WHERE group_id = ? AND user_id = ?",
                (group_id, user["id"]),
            ).fetchone()
            if existing:
                if strict_duplicate_check:
                    raise AppError(
                        f"{user['student_name']} ({user['room_number']}) is already a participant in {group_id}.",
                        status_code=409,
                        code="duplicate_participant",
                    )
                return self._hydrate_group_conn(conn, group_row)

            current_count = conn.execute(
                "SELECT COUNT(*) FROM group_participants WHERE group_id = ?", (group_id,)
            ).fetchone()[0]
            if group_row["participant_limit"] and current_count >= group_row["participant_limit"]:
                raise AppError(
                    f"Group has reached its participant limit of {group_row['participant_limit']} students.",
                    status_code=409,
                    code="group_full",
                )

            conn.execute(
                "INSERT INTO group_participants (id, group_id, user_id, joined_at) VALUES (?, ?, ?, ?)",
                (f"gp-{secrets.token_hex(4)}", group_id, user["id"], now_iso()),
            )
            self._notify_group_conn(
                conn,
                group_id,
                "group_joined",
                f"{user['student_name']} ({user['room_number']}) joined the group",
                f"{user['student_name']} joined '{group_row['name']}' ({group_id}).",
            )
            hydrated = self._hydrate_group_conn(conn, group_row)

        self._broadcast("group_updated", {"group": hydrated})
        return hydrated

    # -------------------------------------------------------------------------
    # SHARED CART MUTATIONS & SERVER-SIDE MINIMUM ORDER VALIDATION
    # -------------------------------------------------------------------------
    def mutate_cart_item(
        self,
        actor_user_id: str,
        group_id: str,
        menu_item_id: str,
        delta_or_quantity: int,
        mode: str = "delta",  # 'delta' (+1/-1) or 'set' (exact quantity, 0 removes)
        target_user_id: str | None = None,
    ) -> dict:
        actor = self.get_user(actor_user_id)
        if target_user_id and target_user_id != actor["id"]:
            raise AppError(
                "Security violation: Students can only edit or remove their own items in the shared cart.",
                status_code=403,
                code="forbidden_other_user_cart",
            )

        with self._lock, self._connect() as conn:
            group_row = conn.execute("SELECT * FROM group_orders WHERE id = ?", (group_id,)).fetchone()
            if not group_row:
                raise AppError("Group order not found.", status_code=404)
            if group_row["status"] == "closed":
                raise AppError("This group order has been closed by the creator.", status_code=409)
            if group_row["cart_frozen"] or group_row["status"] not in ("collecting", "minimum_reached"):
                raise AppError(
                    "Shared cart is frozen for checkout. Reopen the cart if changes are needed.",
                    status_code=409,
                    code="cart_frozen",
                )

            menu_row = conn.execute(
                "SELECT id, name, price_inr, is_available FROM menu_items WHERE id = ?",
                (menu_item_id,),
            ).fetchone()
            if not menu_row or not menu_row["is_available"]:
                raise AppError("Menu item not found or unavailable at Grains and Gossip.", status_code=404)

            # Ensure student is in group_participants (respecting participant limit)
            in_group = conn.execute(
                "SELECT id FROM group_participants WHERE group_id = ? AND user_id = ?",
                (group_id, actor["id"]),
            ).fetchone()
            if not in_group:
                curr_cnt = conn.execute(
                    "SELECT COUNT(*) FROM group_participants WHERE group_id = ?", (group_id,)
                ).fetchone()[0]
                if group_row["participant_limit"] and curr_cnt >= group_row["participant_limit"]:
                    raise AppError(
                        f"Cannot add items: group reached participant limit ({group_row['participant_limit']}).",
                        status_code=409,
                    )
                conn.execute(
                    "INSERT INTO group_participants (id, group_id, user_id, joined_at) VALUES (?, ?, ?, ?)",
                    (f"gp-{secrets.token_hex(4)}", group_id, actor["id"], now_iso()),
                )
                self._notify_group_conn(
                    conn,
                    group_id,
                    "group_joined",
                    f"{actor['student_name']} ({actor['room_number']}) joined '{group_row['name']}'",
                    f"{actor['student_name']} joined and started adding items to the shared cart.",
                )

            prev_total = conn.execute(
                "SELECT COALESCE(SUM(quantity * unit_price_inr), 0) FROM cart_items WHERE group_id = ?",
                (group_id,),
            ).fetchone()[0]

            existing_item = conn.execute(
                "SELECT id, quantity FROM cart_items WHERE group_id = ? AND user_id = ? AND menu_item_id = ?",
                (group_id, actor["id"], menu_item_id),
            ).fetchone()

            current_qty = existing_item["quantity"] if existing_item else 0
            new_qty = (current_qty + int(delta_or_quantity)) if mode == "delta" else int(delta_or_quantity)

            if new_qty > 20:
                raise AppError("Maximum 20 units per item allowed.", status_code=400)

            ts = now_iso()
            action_desc = ""
            if new_qty <= 0:
                if existing_item:
                    conn.execute("DELETE FROM cart_items WHERE id = ?", (existing_item["id"],))
                    action_desc = f"removed {menu_row['name']}"
            elif existing_item:
                conn.execute(
                    "UPDATE cart_items SET quantity = ?, unit_price_inr = ?, updated_at = ? WHERE id = ?",
                    (new_qty, menu_row["price_inr"], ts, existing_item["id"]),
                )
                action_desc = f"updated {menu_row['name']} (×{new_qty})"
            else:
                conn.execute(
                    """
                    INSERT INTO cart_items (id, group_id, user_id, menu_item_id, quantity, unit_price_inr, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (f"ci-{secrets.token_hex(5)}", group_id, actor["id"], menu_item_id, new_qty, menu_row["price_inr"], ts),
                )
                action_desc = f"added {menu_row['name']} (×{new_qty}, ₹{new_qty * menu_row['price_inr']})"

            new_total = conn.execute(
                "SELECT COALESCE(SUM(quantity * unit_price_inr), 0) FROM cart_items WHERE group_id = ?",
                (group_id,),
            ).fetchone()[0]

            if action_desc and new_qty > current_qty:
                rem = max(0, MINIMUM_CART_INR - new_total)
                rem_msg = "Minimum reached! Checkout unlocked." if rem == 0 else f"₹{rem} more needed to reach ₹{MINIMUM_CART_INR}."
                self._notify_group_conn(
                    conn,
                    group_id,
                    "food_added",
                    f"{actor['student_name']} ({actor['room_number']}) {action_desc}",
                    f"Shared cart is now ₹{new_total}. {rem_msg}",
                )

            if prev_total < MINIMUM_CART_INR and new_total >= MINIMUM_CART_INR:
                self._notify_group_conn(
                    conn,
                    group_id,
                    "minimum_reached",
                    f"₹{MINIMUM_CART_INR} minimum reached in '{group_row['name']}'",
                    f"Combined cart hit ₹{new_total} (minimum ₹{MINIMUM_CART_INR}). Checkout is now unlocked!",
                )

            updated_row = conn.execute("SELECT * FROM group_orders WHERE id = ?", (group_id,)).fetchone()
            hydrated = self._hydrate_group_conn(conn, updated_row)

        self._broadcast("cart_updated", {"group": hydrated})
        return hydrated

    def delete_cart_item_by_id(self, actor_user_id: str, group_id: str, cart_item_id: str) -> dict:
        actor = self.get_user(actor_user_id)
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT id, user_id, menu_item_id FROM cart_items WHERE id = ? AND group_id = ?",
                (cart_item_id, group_id),
            ).fetchone()
            if not row:
                raise AppError("Cart item not found.", status_code=404)
            if row["user_id"] != actor["id"]:
                raise AppError(
                    "Security violation: You cannot remove another student's item from the shared cart.",
                    status_code=403,
                    code="forbidden_other_user_cart",
                )
        return self.mutate_cart_item(actor_user_id, group_id, row["menu_item_id"], 0, mode="set")

    # -------------------------------------------------------------------------
    # CHECKOUT LOCK, FREEZE & INDIVIDUAL PAYMENTS
    # -------------------------------------------------------------------------
    def lock_checkout(self, actor_user_id: str, group_id: str) -> dict:
        actor = self.get_user(actor_user_id)
        with self._lock, self._connect() as conn:
            group_row = conn.execute("SELECT * FROM group_orders WHERE id = ?", (group_id,)).fetchone()
            if not group_row:
                raise AppError("Group order not found.", status_code=404)
            if group_row["status"] == "closed":
                raise AppError("Group order is closed.", status_code=409)

            # Anyone in the group (or creator) can lock once the minimum is reached
            in_group = conn.execute(
                "SELECT id FROM group_participants WHERE group_id = ? AND user_id = ?",
                (group_id, actor["id"]),
            ).fetchone()
            if not in_group and group_row["creator_id"] != actor["id"]:
                raise AppError("Only group participants can proceed to checkout.", status_code=403)

            shared_total = conn.execute(
                "SELECT COALESCE(SUM(quantity * unit_price_inr), 0) FROM cart_items WHERE group_id = ?",
                (group_id,),
            ).fetchone()[0]

            if shared_total < MINIMUM_CART_INR:
                remaining = MINIMUM_CART_INR - shared_total
                raise AppError(
                    f"Checkout locked: Shared cart is ₹{shared_total}. Add ₹{remaining} more to reach the ₹{MINIMUM_CART_INR} minimum for {CAFE_NAME}.",
                    status_code=400,
                    code="below_minimum",
                )

            ts = now_iso()
            conn.execute(
                "UPDATE group_orders SET cart_frozen = 1, status = 'minimum_reached' WHERE id = ?",
                (group_id,),
            )

            # Generate/update individual payment records for every participant who ordered items
            user_subtotals = conn.execute(
                """
                SELECT user_id, SUM(quantity * unit_price_inr) AS subtotal
                FROM cart_items
                WHERE group_id = ?
                GROUP BY user_id
                HAVING subtotal > 0
                """,
                (group_id,),
            ).fetchall()

            for us in user_subtotals:
                uid = us["user_id"]
                subtotal = int(us["subtotal"])
                fee = self._packing_fee_conn(conn, group_id, uid)
                payable = subtotal + fee
                existing_pay = conn.execute(
                    "SELECT id, status, verified_by_server FROM payments WHERE group_id = ? AND user_id = ?",
                    (group_id, uid),
                ).fetchone()
                order_ref = f"order_{group_id.replace('-', '')}_{uid[-4:]}_{secrets.token_hex(2)}"
                if not existing_pay:
                    conn.execute(
                        """
                        INSERT INTO payments
                        (id, group_id, user_id, items_subtotal_inr, packaging_fee_inr, payable_amount_inr, method, status, gateway_order_id, verified_by_server, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, 'upi_qr', 'pending', ?, 0, ?)
                        """,
                        (f"payrec-{secrets.token_hex(5)}", group_id, uid, subtotal, fee, payable, order_ref, ts),
                    )
                elif not (existing_pay["status"] == "paid" and existing_pay["verified_by_server"] == 1):
                    conn.execute(
                        """
                        UPDATE payments
                        SET items_subtotal_inr = ?, packaging_fee_inr = ?, payable_amount_inr = ?, status = 'pending', verified_by_server = 0
                        WHERE id = ?
                        """,
                        (subtotal, fee, payable, existing_pay["id"]),
                    )

                self._notify_conn(
                    conn,
                    uid,
                    group_id,
                    "payment_pending",
                    f"Action Required: Pay your ₹{payable} share for '{group_row['name']}'",
                    f"Cart is frozen at ₹{shared_total}. Your itemized total is ₹{subtotal} + ₹{fee} packaging = ₹{payable}.",
                )

            conn.execute(
                "INSERT INTO order_status_history (id, group_id, status, note, changed_by, created_at) VALUES (?, ?, 'minimum_reached', ?, ?, ?)",
                (
                    f"osh-{secrets.token_hex(4)}",
                    group_id,
                    f"Minimum reached (₹{shared_total}). Shared cart frozen for individual student payments.",
                    actor["id"],
                    ts,
                ),
            )
            updated_row = conn.execute("SELECT * FROM group_orders WHERE id = ?", (group_id,)).fetchone()
            hydrated = self._hydrate_group_conn(conn, updated_row)

        self._broadcast("checkout_locked", {"group": hydrated})
        return hydrated

    def reopen_cart(self, actor_user_id: str, group_id: str) -> dict:
        actor = self.get_user(actor_user_id)
        with self._lock, self._connect() as conn:
            group_row = conn.execute("SELECT * FROM group_orders WHERE id = ?", (group_id,)).fetchone()
            if not group_row:
                raise AppError("Group order not found.", status_code=404)
            if group_row["creator_id"] != actor["id"]:
                raise AppError("Only the group creator can unfreeze/reopen the shared cart.", status_code=403)
            if group_row["status"] in ("order_placed", "preparing", "ready_for_pickup", "completed", "closed"):
                raise AppError("Cannot reopen cart after the order has been placed with the cafe.", status_code=409)

            conn.execute(
                "UPDATE group_orders SET cart_frozen = 0, status = 'collecting' WHERE id = ?",
                (group_id,),
            )
            updated_row = conn.execute("SELECT * FROM group_orders WHERE id = ?", (group_id,)).fetchone()
            hydrated = self._hydrate_group_conn(conn, updated_row)

        self._broadcast("cart_reopened", {"group": hydrated})
        return hydrated

    def close_group(self, actor_user_id: str, group_id: str) -> dict:
        actor = self.get_user(actor_user_id)
        with self._lock, self._connect() as conn:
            group_row = conn.execute("SELECT * FROM group_orders WHERE id = ?", (group_id,)).fetchone()
            if not group_row:
                raise AppError("Group order not found.", status_code=404)
            if group_row["creator_id"] != actor["id"]:
                raise AppError("Only the group creator can close this group order.", status_code=403, code="creator_only")

            ts = now_iso()
            conn.execute(
                "UPDATE group_orders SET status = 'closed', cart_frozen = 1 WHERE id = ?",
                (group_id,),
            )
            conn.execute(
                "INSERT INTO order_status_history (id, group_id, status, note, changed_by, created_at) VALUES (?, ?, 'closed', ?, ?, ?)",
                (f"osh-{secrets.token_hex(4)}", group_id, f"Group closed by creator {actor['student_name']}.", actor["id"], ts),
            )
            updated_row = conn.execute("SELECT * FROM group_orders WHERE id = ?", (group_id,)).fetchone()
            hydrated = self._hydrate_group_conn(conn, updated_row)

        self._broadcast("group_closed", {"group": hydrated})
        return hydrated

    def initiate_individual_payment(
        self,
        actor_user_id: str,
        group_id: str,
        method: str = "upi_qr",
        upi_vpa: str = "",
    ) -> dict:
        """
        Initiates a payment intent for ONLY the authenticated student's items.
        NEVER marks payment as 'paid' — status stays 'pending' until verified by gateway webhook.
        """
        actor = self.get_user(actor_user_id)
        if method not in ("upi_qr", "upi_id", "razorpay"):
            raise AppError("Unsupported payment method. Choose upi_qr, upi_id, or razorpay.")
        if method == "upi_id" and ("@" not in (upi_vpa or "")):
            raise AppError("Enter a valid UPI ID (e.g., student@oksbi or rollno@ybl).")

        with self._lock, self._connect() as conn:
            group_row = conn.execute("SELECT * FROM group_orders WHERE id = ?", (group_id,)).fetchone()
            if not group_row:
                raise AppError("Group order not found.", status_code=404)

            shared_total = conn.execute(
                "SELECT COALESCE(SUM(quantity * unit_price_inr), 0) FROM cart_items WHERE group_id = ?",
                (group_id,),
            ).fetchone()[0]
            if shared_total < MINIMUM_CART_INR:
                raise AppError(
                    f"Cannot initiate payment before the group reaches ₹{MINIMUM_CART_INR} (currently ₹{shared_total}).",
                    status_code=400,
                )

            # Ensure cart is frozen once payment starts
            if not group_row["cart_frozen"]:
                conn.execute(
                    "UPDATE group_orders SET cart_frozen = 1, status = 'minimum_reached' WHERE id = ?",
                    (group_id,),
                )

            user_subtotal = conn.execute(
                "SELECT COALESCE(SUM(quantity * unit_price_inr), 0) FROM cart_items WHERE group_id = ? AND user_id = ?",
                (group_id, actor["id"]),
            ).fetchone()[0]
            if user_subtotal <= 0:
                raise AppError("You have no items in this shared cart to pay for.", status_code=400)

            fee = self._packing_fee_conn(conn, group_id, actor["id"])
            payable = int(user_subtotal) + fee
            order_ref = f"order_{group_id.replace('-', '')}_{actor['id'][-4:]}_{secrets.token_hex(3)}"
            ts = now_iso()

            existing = conn.execute(
                "SELECT id, status, verified_by_server FROM payments WHERE group_id = ? AND user_id = ?",
                (group_id, actor["id"]),
            ).fetchone()
            if existing and existing["status"] == "paid" and existing["verified_by_server"] == 1:
                raise AppError("Your share for this group order is already paid and verified.", status_code=409)

            if existing:
                conn.execute(
                    """
                    UPDATE payments
                    SET items_subtotal_inr = ?, packaging_fee_inr = ?, payable_amount_inr = ?,
                        method = ?, upi_vpa = ?, status = 'pending', gateway_order_id = ?, verified_by_server = 0
                    WHERE id = ?
                    """,
                    (user_subtotal, fee, payable, method, upi_vpa.strip(), order_ref, existing["id"]),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO payments
                    (id, group_id, user_id, items_subtotal_inr, packaging_fee_inr, payable_amount_inr, method, upi_vpa, status, gateway_order_id, verified_by_server, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, 0, ?)
                    """,
                    (
                        f"payrec-{secrets.token_hex(5)}",
                        group_id,
                        actor["id"],
                        user_subtotal,
                        fee,
                        payable,
                        method,
                        upi_vpa.strip(),
                        order_ref,
                        ts,
                    ),
                )

            updated_row = conn.execute("SELECT * FROM group_orders WHERE id = ?", (group_id,)).fetchone()
            hydrated = self._hydrate_group_conn(conn, updated_row)

        sample_payment_id = f"pay_{secrets.token_hex(5)}"
        upi_uri = (
            f"upi://pay?pa=grainsandgossip@razorpay&pn=Grains%20and%20Gossip%20(Raat Ka Dabba)"
            f"&tr={order_ref}&am={payable}.00&cu=INR&tn=Raat Ka Dabba%20{group_id}%20{actor['room_number']}"
        )
        intent_info = {
            "gateway_order_id": order_ref,
            "razorpay_key_id": RAZORPAY_KEY_ID,
            "payable_amount_inr": payable,
            "items_subtotal_inr": user_subtotal,
            "packaging_fee_inr": fee,
            "method": method,
            "status": "pending",
            "upi_uri": upi_uri,
            "sandbox_webhook_helper": {
                "gateway_order_id": order_ref,
                "sample_payment_id": sample_payment_id,
                "paid_signature": compute_gateway_signature(order_ref, sample_payment_id, "paid"),
                "failed_signature": compute_gateway_signature(order_ref, sample_payment_id, "failed"),
            },
        }
        self._broadcast("payment_initiated", {"group": hydrated, "payment_intent": intent_info})
        return {"group": hydrated, "payment_intent": intent_info}

    def process_payment_webhook(
        self,
        gateway_order_id: str,
        gateway_payment_id: str,
        outcome: str,
        gateway_signature: str,
    ) -> dict:
        """
        Server-side Razorpay / UPI Gateway Webhook verification.
        Validates HMAC-SHA256 signature before marking any payment 'paid' or 'failed'.
        """
        if outcome not in ("paid", "failed"):
            raise AppError("Invalid webhook outcome; must be 'paid' or 'failed'.", status_code=400)
        if not gateway_order_id or not gateway_payment_id or not gateway_signature:
            raise AppError("Missing gateway_order_id, gateway_payment_id, or gateway_signature.", status_code=400)

        expected_sig = compute_gateway_signature(gateway_order_id, gateway_payment_id, outcome)
        if not hmac.compare_digest(expected_sig, gateway_signature):
            raise AppError(
                "Invalid payment gateway HMAC-SHA256 signature. Unverified client requests cannot mark payments as paid.",
                status_code=401,
                code="invalid_signature",
            )

        with self._lock, self._connect() as conn:
            pay_row = conn.execute(
                "SELECT * FROM payments WHERE gateway_order_id = ?",
                (gateway_order_id,),
            ).fetchone()
            if not pay_row:
                raise AppError("Payment order reference not found.", status_code=404)

            group_id = pay_row["group_id"]
            user_id = pay_row["user_id"]
            ts = now_iso()

            if outcome == "paid":
                conn.execute(
                    """
                    UPDATE payments
                    SET status = 'paid', gateway_payment_id = ?, gateway_signature = ?,
                        verified_by_server = 1, verified_at = ?
                    WHERE id = ?
                    """,
                    (gateway_payment_id, gateway_signature, ts, pay_row["id"]),
                )
                self._notify_conn(
                    conn,
                    user_id,
                    group_id,
                    "status_changed",
                    f"Payment Verified (₹{pay_row['payable_amount_inr']})",
                    f"Gateway confirmed ₹{pay_row['payable_amount_inr']} (Ref: {gateway_payment_id}) for group {group_id}.",
                )
            else:
                conn.execute(
                    """
                    UPDATE payments
                    SET status = 'failed', gateway_payment_id = ?, gateway_signature = ?,
                        verified_by_server = 0, verified_at = ?
                    WHERE id = ?
                    """,
                    (gateway_payment_id, gateway_signature, ts, pay_row["id"]),
                )
                self._notify_conn(
                    conn,
                    user_id,
                    group_id,
                    "payment_pending",
                    f"Payment Failed (₹{pay_row['payable_amount_inr']})",
                    f"Gateway reported failure for {gateway_order_id}. Please retry your individual payment.",
                )

            group_row = conn.execute("SELECT * FROM group_orders WHERE id = ?", (group_id,)).fetchone()
            hydrated = self._hydrate_group_conn(conn, group_row)

            if hydrated["all_payments_verified"] and hydrated["status"] in ("collecting", "minimum_reached"):
                conn.execute(
                    "UPDATE group_orders SET status = 'payments_completed', cart_frozen = 1 WHERE id = ?",
                    (group_id,),
                )
                conn.execute(
                    "INSERT INTO order_status_history (id, group_id, status, note, changed_by, created_at) VALUES (?, ?, 'payments_completed', ?, ?, ?)",
                    (
                        f"osh-{secrets.token_hex(4)}",
                        group_id,
                        f"All {hydrated['paid_verified_count']} ordering participants completed verified individual payments.",
                        user_id,
                        ts,
                    ),
                )
                self._notify_group_conn(
                    conn,
                    group_id,
                    "status_changed",
                    f"All Payments Completed for '{group_row['name']}'!",
                    "Every participant's share is verified. Group order is ready to submit to Grains and Gossip!",
                )
                group_row = conn.execute("SELECT * FROM group_orders WHERE id = ?", (group_id,)).fetchone()
                hydrated = self._hydrate_group_conn(conn, group_row)

        self._broadcast("payment_webhook_processed", {"group": hydrated, "outcome": outcome})
        return hydrated

    # -------------------------------------------------------------------------
    # ORDER TRACKING PIPELINE (7 STAGES)
    # -------------------------------------------------------------------------
    def advance_order_status(self, actor_user_id: str, group_id: str, target_status: str | None = None) -> dict:
        actor = self.get_user(actor_user_id)
        with self._lock, self._connect() as conn:
            group_row = conn.execute("SELECT * FROM group_orders WHERE id = ?", (group_id,)).fetchone()
            if not group_row:
                raise AppError("Group order not found.", status_code=404)
            hydrated = self._hydrate_group_conn(conn, group_row)

            current_status = hydrated["status"]
            if current_status == "closed":
                raise AppError("Closed group orders cannot advance.", status_code=409)

            if not target_status:
                if current_status not in ORDER_PIPELINE:
                    raise AppError("Order cannot be advanced further.", status_code=400)
                idx = ORDER_PIPELINE.index(current_status)
                if idx + 1 >= len(ORDER_PIPELINE):
                    raise AppError("Order is already Completed.", status_code=400)
                target_status = ORDER_PIPELINE[idx + 1]

            if target_status not in ORDER_PIPELINE:
                raise AppError(f"Invalid order status '{target_status}'.", status_code=400)

            # Enforce the minimum for any stage beyond 'collecting'
            if target_status != "collecting" and hydrated["shared_cart_total_inr"] < MINIMUM_CART_INR:
                raise AppError(
                    f"Cannot advance to '{STATUS_LABELS[target_status]}': shared cart (₹{hydrated['shared_cart_total_inr']}) is below ₹{MINIMUM_CART_INR}.",
                    status_code=400,
                    code="below_minimum",
                )

            # Enforce verified individual payments before payments_completed / order_placed / preparing / ready_for_pickup / completed
            if target_status in ("payments_completed", "order_placed", "preparing", "ready_for_pickup", "completed"):
                if not hydrated["all_payments_verified"]:
                    unpaid_names = [
                        f"{p['student_name']} ({p['room_number']})"
                        for p in hydrated["participants"]
                        if p["items_subtotal_inr"] > 0
                        and not (p["payment"] and p["payment"]["status"] == "paid" and p["payment"]["verified_by_server"] == 1)
                    ]
                    raise AppError(
                        f"Cannot submit or advance order until all participants pay their share. Waiting on: {', '.join(unpaid_names)}.",
                        status_code=400,
                        code="unpaid_participants",
                    )

            ts = now_iso()
            conn.execute(
                "UPDATE group_orders SET status = ?, cart_frozen = 1 WHERE id = ?",
                (target_status, group_id),
            )

            stage_notes = {
                "minimum_reached": f"Minimum ₹{MINIMUM_CART_INR} reached (₹{hydrated['shared_cart_total_inr']}). Cart frozen for individual payments.",
                "payments_completed": "All individual student payments verified via gateway.",
                "order_placed": f"Group order officially transmitted to {CAFE_NAME} kitchen!",
                "preparing": f"{CAFE_NAME} chefs are preparing {hydrated['total_item_count']} items for Tower 3.",
                "ready_for_pickup": "Food has arrived. Collect it from the Hostel Reception.",
                "completed": "Order delivered and picked up by Tower 3 group members.",
            }
            note = stage_notes.get(target_status, f"Status updated to {STATUS_LABELS[target_status]}.")
            conn.execute(
                "INSERT INTO order_status_history (id, group_id, status, note, changed_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (f"osh-{secrets.token_hex(4)}", group_id, target_status, note, actor["id"], ts),
            )

            notif_type = "status_changed"
            if target_status == "order_placed":
                notif_type = "order_placed"
            elif target_status == "ready_for_pickup":
                notif_type = "food_ready"

            self._notify_group_conn(
                conn,
                group_id,
                notif_type,
                f"Order Update: {STATUS_LABELS[target_status]} ({group_id})",
                note,
            )

            updated_row = conn.execute("SELECT * FROM group_orders WHERE id = ?", (group_id,)).fetchone()
            hydrated = self._hydrate_group_conn(conn, updated_row)

        self._broadcast("status_updated", {"group": hydrated})
        return hydrated

    def trigger_deadline_reminder(self, actor_user_id: str, group_id: str) -> dict:
        actor = self.get_user(actor_user_id)
        with self._lock, self._connect() as conn:
            group_row = conn.execute("SELECT * FROM group_orders WHERE id = ?", (group_id,)).fetchone()
            if not group_row:
                raise AppError("Group order not found.", status_code=404)
            hydrated = self._hydrate_group_conn(conn, group_row)
            rem = hydrated["remaining_to_minimum_inr"]
            msg = (
                f"Order deadline for '{group_row['name']}' is approaching! "
                + (f"Add ₹{rem} more to hit ₹{MINIMUM_CART_INR}." if rem > 0 else "Complete your pending individual payment now!")
            )
            self._notify_group_conn(
                conn,
                group_id,
                "deadline_approaching",
                f"Deadline Approaching: {group_row['name']}",
                msg,
            )
        self._broadcast("notifications_updated", {"group_id": group_id, "by": actor["id"]})
        return {"ok": True, "message": "Deadline alert sent to all group participants."}

    # -------------------------------------------------------------------------
    # STUDENT DASHBOARD & NOTIFICATIONS
    # -------------------------------------------------------------------------
    def get_dashboard(self, user_id: str) -> dict:
        user = self.get_user(user_id)
        all_groups = self.list_groups()

        my_groups = [g for g in all_groups if user["id"] in g["participant_ids"]]
        active_groups = [g for g in my_groups if g["status"] not in ("completed", "closed")]
        past_orders = [g for g in my_groups if g["status"] in ("completed", "closed")]

        selected_food = []
        pending_payments = []
        personal_spending_inr = 0

        for g in my_groups:
            my_sec = next((p for p in g["participants"] if p["user_id"] == user["id"]), None)
            if not my_sec:
                continue
            for item in my_sec["items"]:
                selected_food.append(
                    {
                        "group_id": g["id"],
                        "group_name": g["name"],
                        "group_status": g["status"],
                        "group_status_label": g["status_label"],
                        "item_name": item["item_name"],
                        "quantity": item["quantity"],
                        "unit_price_inr": item["unit_price_inr"],
                        "line_total_inr": item["line_total_inr"],
                    }
                )
            pay = my_sec.get("payment")
            if pay and pay["status"] == "paid" and pay["verified_by_server"] == 1:
                personal_spending_inr += pay["payable_amount_inr"]
            elif my_sec["items_subtotal_inr"] > 0 and g["status"] not in ("completed", "closed"):
                pending_payments.append(
                    {
                        "group_id": g["id"],
                        "group_name": g["name"],
                        "shared_cart_total_inr": g["shared_cart_total_inr"],
                        "checkout_unlocked": g["checkout_unlocked"],
                        "items_subtotal_inr": my_sec["items_subtotal_inr"],
                        "packaging_fee_inr": my_sec["packaging_fee_inr"],
                        "payable_amount_inr": my_sec["payable_amount_inr"],
                        "payment_status": pay["status"] if pay else "awaiting_checkout_lock",
                        "gateway_order_id": pay["gateway_order_id"] if pay else None,
                    }
                )

        return {
            "user": user,
            "active_groups": active_groups,
            "past_orders": past_orders,
            "personal_spending_inr": personal_spending_inr,
            "pending_payments": pending_payments,
            "selected_food": selected_food,
        }

    def get_notifications(self, user_id: str) -> list[dict]:
        self.get_user(user_id)
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_notifications_read(self, user_id: str, notification_id: str | None = None) -> list[dict]:
        self.get_user(user_id)
        with self._lock, self._connect() as conn:
            if notification_id:
                conn.execute(
                    "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
                    (notification_id, user_id),
                )
            else:
                conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
        return self.get_notifications(user_id)


# =============================================================================
# HTTP & SSE REQUEST HANDLER
# =============================================================================

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
}


def make_handler(engine: RaatKaDabbaEngine):
    class RaatKaDabbaHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args) -> None:
            if os.environ.get("BITETOGETHER_QUIET") == "1":
                return
            super().log_message(fmt, *args)

        def _send_json(self, data: dict | list, status: int = 200) -> None:
            body = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if self.headers.get("Connection", "").lower() == "close":
                self.close_connection = True
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8"))

        def _actor_id(self, body: dict | None = None, query: dict | None = None) -> str:
            header_uid = self.headers.get("X-Student-Id")
            if header_uid:
                return header_uid
            if body and body.get("user_id"):
                return str(body["user_id"])
            if query and query.get("user_id"):
                return str(query["user_id"][0])
            raise AppError("Authentication required: missing Tower 3 student session.", status_code=401)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)

            try:
                if path == "/api/stream":
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "keep-alive")
                    self.end_headers()
                    q = engine.subscribe_sse()
                    try:
                        self.wfile.write(b"event: connected\ndata: {\"ok\":true}\n\n")
                        self.wfile.flush()
                        while True:
                            try:
                                msg = q.get(timeout=15)
                                self.wfile.write(f"data: {msg}\n\n".encode("utf-8"))
                                self.wfile.flush()
                            except queue.Empty:
                                self.wfile.write(b": keepalive\n\n")
                                self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        pass
                    finally:
                        engine.unsubscribe_sse(q)
                    return

                if path == "/api/bootstrap":
                    uid = self.headers.get("X-Student-Id") or (query.get("user_id", [None])[0])
                    user = None
                    if uid:
                        try:
                            user = engine.get_user(uid)
                        except AppError:
                            user = None
                    self._send_json(
                        {
                            "app": {
                                "name": "Raat Ka Dabba",
                                "tagline": "Don't order alone. Bite together.",
                                "tower": ALLOWED_TOWER,
                                "hostel_name": HOSTEL_NAME,
                                "custom_domain": CUSTOM_DOMAIN,
                                "allowed_email_domain": ALLOWED_EMAIL_DOMAIN,
                                "cafe_name": CAFE_NAME,
                                "minimum_cart_inr": MINIMUM_CART_INR,
                                "packing_fee_per_item_inr": PACKING_FEE_PER_ITEM_INR,
                                "cafe_info": CAFE_INFO,
                                "razorpay_key_id": RAZORPAY_KEY_ID,
                            },
                            "current_user": user,
                            "menu": engine.get_menu(),
                            "groups": engine.list_groups(),
                            "dashboard": engine.get_dashboard(user["id"]) if user else None,
                            "notifications": engine.get_notifications(user["id"]) if user else [],
                        }
                    )
                    return

                if path == "/api/menu":
                    self._send_json(engine.get_menu())
                    return

                if path == "/api/groups":
                    self._send_json({"groups": engine.list_groups()})
                    return

                m_group = re.match(r"^/api/groups/([^/]+)$", path)
                if m_group:
                    self._send_json({"group": engine.get_group(m_group.group(1))})
                    return

                if path == "/api/dashboard":
                    uid = self._actor_id(query=query)
                    self._send_json(engine.get_dashboard(uid))
                    return

                if path == "/api/notifications":
                    uid = self._actor_id(query=query)
                    self._send_json({"notifications": engine.get_notifications(uid)})
                    return

                # Serve static frontend files
                rel = "index.html" if path in ("/", "/index.html") else path.lstrip("/")
                file_path = (PUBLIC_DIR / rel).resolve()
                if not str(file_path).startswith(str(PUBLIC_DIR.resolve())) or not file_path.is_file():
                    file_path = PUBLIC_DIR / "index.html"
                ext = file_path.suffix.lower()
                content = file_path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", MIME_TYPES.get(ext, "application/octet-stream"))
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

            except AppError as exc:
                self._send_json({"error": exc.message, "code": exc.code}, status=exc.status_code)
            except Exception as exc:
                self._send_json({"error": f"Internal server error: {exc}", "code": "internal_error"}, status=500)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            try:
                body = self._read_json()

                if path == "/api/auth/register":
                    user = engine.register_student(
                        student_name=body.get("student_name", ""),
                        college_email=body.get("college_email", ""),
                        student_id=body.get("student_id", ""),
                        room_number=body.get("room_number", ""),
                        password=body.get("password", ""),
                        tower=body.get("tower", "Tower 3"),
                    )
                    self._send_json({"user": user}, status=201)
                    return

                if path == "/api/auth/login":
                    user = engine.login_student(
                        identifier=body.get("identifier", ""),
                        password=body.get("password", ""),
                        tower=body.get("tower", "Tower 3"),
                    )
                    self._send_json({"user": user})
                    return

                if path == "/api/groups":
                    uid = self._actor_id(body=body)
                    group = engine.create_group(
                        user_id=uid,
                        name=body.get("name", ""),
                        deadline_minutes=body.get("deadline_minutes", 30),
                        participant_limit=body.get("participant_limit"),
                        cafe_name=body.get("cafe_name", CAFE_NAME),
                    )
                    self._send_json({"group": group}, status=201)
                    return

                m_join = re.match(r"^/api/groups/([^/]+)/join$", path)
                if m_join:
                    uid = self._actor_id(body=body)
                    strict = bool(body.get("strict", True))
                    group = engine.join_group(uid, m_join.group(1), strict_duplicate_check=strict)
                    self._send_json({"group": group})
                    return

                m_cart = re.match(r"^/api/groups/([^/]+)/cart$", path)
                if m_cart:
                    uid = self._actor_id(body=body)
                    group = engine.mutate_cart_item(
                        actor_user_id=uid,
                        group_id=m_cart.group(1),
                        menu_item_id=body.get("menu_item_id", ""),
                        delta_or_quantity=int(body.get("quantity", body.get("delta", 1))),
                        mode=body.get("mode", "delta"),
                        target_user_id=body.get("target_user_id"),
                    )
                    self._send_json({"group": group})
                    return

                m_cart_del = re.match(r"^/api/groups/([^/]+)/cart/([^/]+)/delete$", path)
                if m_cart_del:
                    uid = self._actor_id(body=body)
                    group = engine.delete_cart_item_by_id(uid, m_cart_del.group(1), m_cart_del.group(2))
                    self._send_json({"group": group})
                    return

                m_lock = re.match(r"^/api/groups/([^/]+)/lock-checkout$", path)
                if m_lock:
                    uid = self._actor_id(body=body)
                    group = engine.lock_checkout(uid, m_lock.group(1))
                    self._send_json({"group": group})
                    return

                m_reopen = re.match(r"^/api/groups/([^/]+)/reopen-cart$", path)
                if m_reopen:
                    uid = self._actor_id(body=body)
                    group = engine.reopen_cart(uid, m_reopen.group(1))
                    self._send_json({"group": group})
                    return

                m_close = re.match(r"^/api/groups/([^/]+)/close$", path)
                if m_close:
                    uid = self._actor_id(body=body)
                    group = engine.close_group(uid, m_close.group(1))
                    self._send_json({"group": group})
                    return

                m_pay = re.match(r"^/api/groups/([^/]+)/payments/initiate$", path)
                if m_pay:
                    uid = self._actor_id(body=body)
                    res = engine.initiate_individual_payment(
                        actor_user_id=uid,
                        group_id=m_pay.group(1),
                        method=body.get("method", "upi_qr"),
                        upi_vpa=body.get("upi_vpa", ""),
                    )
                    self._send_json(res)
                    return

                if path == "/api/payments/webhook":
                    group = engine.process_payment_webhook(
                        gateway_order_id=body.get("gateway_order_id", ""),
                        gateway_payment_id=body.get("gateway_payment_id", ""),
                        outcome=body.get("outcome", ""),
                        gateway_signature=body.get("gateway_signature", ""),
                    )
                    self._send_json({"group": group})
                    return

                m_status = re.match(r"^/api/groups/([^/]+)/advance-status$", path)
                if m_status:
                    uid = self._actor_id(body=body)
                    group = engine.advance_order_status(uid, m_status.group(1), body.get("target_status"))
                    self._send_json({"group": group})
                    return

                m_deadline = re.match(r"^/api/groups/([^/]+)/nudge-deadline$", path)
                if m_deadline:
                    uid = self._actor_id(body=body)
                    self._send_json(engine.trigger_deadline_reminder(uid, m_deadline.group(1)))
                    return

                if path == "/api/notifications/read":
                    uid = self._actor_id(body=body)
                    notifs = engine.mark_notifications_read(uid, body.get("notification_id"))
                    self._send_json({"notifications": notifs})
                    return

                self._send_json({"error": f"Unknown endpoint {path}"}, status=404)

            except AppError as exc:
                self._send_json({"error": exc.message, "code": exc.code}, status=exc.status_code)
            except Exception as exc:
                self._send_json({"error": f"Internal server error: {exc}", "code": "internal_error"}, status=500)

    return RaatKaDabbaHandler


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    engine = RaatKaDabbaEngine()
    server = ThreadingHTTPServer((host, port), make_handler(engine))
    print(f"Raat Ka Dabba (Tower 3) server listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    port_num = int(os.environ.get("PORT", "8765"))
    run_server(port=port_num)
