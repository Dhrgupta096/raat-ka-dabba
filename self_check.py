#!/usr/bin/env python3
"""
Runnable self-check for Raat Ka Dabba (Tower 3 Boys Hostel - t3.raatkadabba.in).
Verifies SQL schema, frontend JS syntax, design tokens, and all server-side business rules.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import subprocess
import tempfile

from server import (
    RaatKaDabbaEngine,
    compute_gateway_signature,
    make_handler,
)

ROOT = Path(__file__).resolve().parent


def check_sql_schema() -> None:
    sql = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8").lower()
    required_tables = [
        "profiles",
        "group_orders",
        "group_participants",
        "menu_items",
        "cart_items",
        "payments",
        "notifications",
        "order_status_history",
    ]
    for tbl in required_tables:
        assert f"create table if not exists public.{tbl}" in sql, f"Missing table in schema.sql: {tbl}"
        assert f"alter table public.{tbl} enable row level security" in sql, f"Missing RLS on table: {tbl}"
    assert "supabase_realtime" in sql, "Missing Supabase Realtime publication"


def check_frontend_assets_and_js_syntax() -> None:
    css = (ROOT / "public" / "styles.css").read_text(encoding="utf-8")
    for token in ("#166534", "#111827"):
        assert token.lower() in css.lower(), f"Missing brand palette token {token} in styles.css"

    js_src = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
    assert "<img" not in js_src and "unsplash" not in js_src.lower(), "Menu UI must not use AI/stock images"
    assert "DEMO MODE" not in js_src and "bt-demo-strip" not in js_src, "Demo account strip must be removed"
    assert "t3.raatkadabba.in" in js_src, "Custom domain t3.raatkadabba.in must be present"
    assert "bt-drawer" in js_src, "Slide-over cart drawer must be present"

    payload = json.dumps(js_src)
    res = subprocess.run(
        ["/usr/bin/osascript", "-l", "JavaScript", "-e", f"new Function({payload}); 'ok';"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, f"Frontend JS syntax error:\n{res.stderr}"


def check_full_stack_business_rules() -> None:
    os.environ["BITETOGETHER_QUIET"] = "1"
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_bt.db"
        engine = RaatKaDabbaEngine(db_path=db_path, seed_demo=False)
        handler_cls = make_handler(engine)

        def req(method: str, path: str, body: dict | None = None, user_id: str | None = None) -> tuple[int, dict]:
            payload = json.dumps(body).encode("utf-8") if body is not None else b""
            lines = [
                f"{method} {path} HTTP/1.1",
                "Host: localhost",
                "Connection: close",
                "Content-Type: application/json",
                f"Content-Length: {len(payload)}",
            ]
            if user_id:
                lines.append(f"X-Student-Id: {user_id}")
            raw_req = ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8") + payload

            class InMemorySocket:
                def __init__(self, data: bytes):
                    self._rfile = io.BytesIO(data)
                    self._wfile = io.BytesIO()

                def makefile(self, mode: str, *args, **kwargs):
                    return self._rfile if "r" in mode else self._wfile

                def sendall(self, b: bytes) -> None:
                    self._wfile.write(b)

                def close(self) -> None:
                    pass

            mem_sock = InMemorySocket(raw_req)
            dummy_server = type("DummyServer", (), {"server_name": "localhost", "server_port": 8765})()
            handler_cls(mem_sock, ("127.0.0.1", 0), dummy_server)
            raw_resp = mem_sock._wfile.getvalue()

            header_bytes, body_bytes = raw_resp.split(b"\r\n\r\n", 1)
            status_line = header_bytes.splitlines()[0].decode("utf-8")
            status_code = int(status_line.split(" ")[1])
            return status_code, json.loads(body_bytes.decode("utf-8"))

        # 0. Bootstrap unauthenticated should have current_user = None and 0 seeded demo profiles
        st, boot = req("GET", "/api/bootstrap")
        assert st == 200 and boot["current_user"] is None
        assert boot["app"]["custom_domain"] == "https://t3.raatkadabba.in"
        assert boot["app"]["hostel_name"] == "Tower 3 Boys Hostel"

        # 1. Verify Tower 3 Boys Hostel & @college.edu domain exclusivity in Auth
        st, err = req(
            "POST",
            "/api/auth/register",
            {
                "student_name": "Outsider Student",
                "college_email": "out@college.edu",
                "student_id": "2024OUT01",
                "tower": "Tower 1",
                "room_number": "T1-102",
                "password": "secret",
            },
        )
        assert st == 403 and err["code"] == "tower_restricted"

        st, bad_email = req(
            "POST",
            "/api/auth/register",
            {
                "student_name": "Test Student",
                "college_email": "student@gmail.com",
                "student_id": "2024CS101",
                "tower": "Tower 3",
                "room_number": "204",
                "password": "secret",
            },
        )
        assert st == 400, "Must reject non-@college.edu email"

        st, r1 = req(
            "POST",
            "/api/auth/register",
            {
                "student_name": "Student One",
                "college_email": "s1@college.edu",
                "student_id": "2024CS204",
                "tower": "Tower 3",
                "room_number": "204",
                "password": "secret",
            },
        )
        assert st == 201 and r1["user"]["room_number"] == "T3-204"
        u1 = r1["user"]["id"]

        st, r2 = req(
            "POST",
            "/api/auth/register",
            {
                "student_name": "Student Two",
                "college_email": "s2@college.edu",
                "student_id": "2024CS308",
                "tower": "Tower 3",
                "room_number": "T3-308",
                "password": "secret",
            },
        )
        assert st == 201
        u2 = r2["user"]["id"]

        st, r3 = req(
            "POST",
            "/api/auth/register",
            {
                "student_name": "Student Three",
                "college_email": "s3@college.edu",
                "student_id": "2024CS502",
                "tower": "Tower 3",
                "room_number": "502",
                "password": "secret",
            },
        )
        assert st == 201
        u3 = r3["user"]["id"]

        # 2. Verify all 9 Grains and Gossip categories (58 items, text-only)
        st, menu_res = req("GET", "/api/menu")
        assert st == 200
        expected_cats = set(menu_res["categories"])
        assert len(menu_res["items"]) == 58
        assert all("image_url" not in i for i in menu_res["items"])
        actual_cats = {i["category"] for i in menu_res["items"]}
        assert expected_cats == actual_cats

        # 3. Create group order (participant_limit = 2, custom domain share link)
        st, bad_cafe = req(
            "POST",
            "/api/groups",
            {"name": "Wrong Cafe Test", "cafe_name": "Other Cafe", "deadline_minutes": 20},
            user_id=u1,
        )
        assert st == 400

        st, grp_res = req(
            "POST",
            "/api/groups",
            {"name": "Wing A Night Order", "deadline_minutes": 30, "participant_limit": 2},
            user_id=u1,
        )
        assert st == 201
        gid = grp_res["group"]["id"]
        assert grp_res["group"]["share_link"] == f"https://t3.raatkadabba.in/?group={gid}"

        st, dup_err = req("POST", f"/api/groups/{gid}/join", {"strict": True}, user_id=u1)
        assert st == 409 and dup_err["code"] == "duplicate_participant"

        st, _ = req("POST", f"/api/groups/{gid}/join", {"strict": True}, user_id=u2)
        assert st == 200

        st, full_err = req("POST", f"/api/groups/{gid}/join", {"strict": True}, user_id=u3)
        assert st == 409 and full_err["code"] == "group_full"

        # 4. Shared cart + ₹350 minimum rule + ownership enforcement
        st, c1 = req("POST", f"/api/groups/{gid}/cart", {"menu_item_id": "bg1", "quantity": 1, "mode": "set"}, user_id=u1)
        assert st == 200 and c1["group"]["shared_cart_total_inr"] == 119
        assert c1["group"]["remaining_to_minimum_inr"] == 231

        st, c2 = req("POST", f"/api/groups/{gid}/cart", {"menu_item_id": "sw1", "quantity": 1, "mode": "set"}, user_id=u2)
        assert st == 200 and c2["group"]["shared_cart_total_inr"] == 238
        assert c2["group"]["remaining_to_minimum_inr"] == 112

        u1_cart_item_id = next(i["id"] for i in c2["group"]["cart_items"] if i["user_id"] == u1)
        st, forbid1 = req("POST", f"/api/groups/{gid}/cart/{u1_cart_item_id}/delete", {}, user_id=u2)
        assert st == 403 and forbid1["code"] == "forbidden_other_user_cart"

        # 5. Lock below ₹350 must fail
        st, below_err = req("POST", f"/api/groups/{gid}/lock-checkout", {}, user_id=u1)
        assert st == 400 and below_err["code"] == "below_minimum"

        # u2 adds Brownie Milk Shake (₹129 drink -> free packing) -> combined ₹367 (>= ₹350)
        st, c3 = req("POST", f"/api/groups/{gid}/cart", {"menu_item_id": "js5", "quantity": 1, "mode": "set"}, user_id=u2)
        assert st == 200 and c3["group"]["shared_cart_total_inr"] == 367
        assert c3["group"]["checkout_unlocked"] is True

        # 6. Lock checkout -> freezes cart
        st, locked = req("POST", f"/api/groups/{gid}/lock-checkout", {}, user_id=u1)
        assert st == 200 and locked["group"]["cart_frozen"] == 1

        st, frozen_err = req("POST", f"/api/groups/{gid}/cart", {"menu_item_id": "bg2", "quantity": 1}, user_id=u1)
        assert st == 409 and frozen_err["code"] == "cart_frozen"

        # 7. Individual payments & HMAC webhook verification
        st, pay_1 = req("POST", f"/api/groups/{gid}/payments/initiate", {"method": "upi_qr"}, user_id=u1)
        assert st == 200 and pay_1["payment_intent"]["payable_amount_inr"] == 129
        order_1 = pay_1["payment_intent"]["gateway_order_id"]

        st, unpaid_err = req("POST", f"/api/groups/{gid}/advance-status", {"target_status": "order_placed"}, user_id=u1)
        assert st == 400 and unpaid_err["code"] == "unpaid_participants"

        sig_1 = compute_gateway_signature(order_1, "pay_u1_01", "paid")
        st, _ = req(
            "POST",
            "/api/payments/webhook",
            {"gateway_order_id": order_1, "gateway_payment_id": "pay_u1_01", "outcome": "paid", "gateway_signature": sig_1},
        )
        assert st == 200

        st, pay_2 = req("POST", f"/api/groups/{gid}/payments/initiate", {"method": "razorpay"}, user_id=u2)
        assert st == 200 and pay_2["payment_intent"]["payable_amount_inr"] == 258
        order_2 = pay_2["payment_intent"]["gateway_order_id"]
        sig_2 = compute_gateway_signature(order_2, "pay_u2_01", "paid")
        st, after_all_paid = req(
            "POST",
            "/api/payments/webhook",
            {"gateway_order_id": order_2, "gateway_payment_id": "pay_u2_01", "outcome": "paid", "gateway_signature": sig_2},
        )
        assert st == 200 and after_all_paid["group"]["status"] == "payments_completed"

        # 8. Submit final order to Grains & Gossip
        st, placed = req("POST", f"/api/groups/{gid}/advance-status", {"target_status": "order_placed"}, user_id=u1)
        assert st == 200 and placed["group"]["status"] == "order_placed"

        st, dash_1 = req("GET", "/api/dashboard", user_id=u1)
        assert st == 200 and dash_1["personal_spending_inr"] == 129


if __name__ == "__main__":
    check_sql_schema()
    check_frontend_assets_and_js_syntax()
    check_full_stack_business_rules()
    print("ALL BITETOGETHER SELF-CHECKS PASSED.")
