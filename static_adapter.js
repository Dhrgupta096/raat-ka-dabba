/* Static GitHub Pages Adapter for Raat Ka Dabba (used only when no Python backend is running) */
(function () {
  "use strict";
  const STORAGE_KEY = "rkd_static_db_v1";
  const MIN_INR = 350;
  const PACK_INR = 10;
  const MENU_CATEGORIES = ["Rice & Noodles", "Burgers", "Pizza", "Sandwiches", "Pasta", "Fries & Snacks", "Starters", "Juices & Shakes", "Hot Drinks"];
  const MENU_ITEMS = [{"id": "rn1", "category": "Rice & Noodles", "name": "Burned Chilly Garlic Fried Rice / Noodles", "price_inr": 159, "is_veg": 1, "is_drink": 0}, {"id": "rn2", "category": "Rice & Noodles", "name": "Corn & Bell Pepper Rice / Noodles", "price_inr": 159, "is_veg": 1, "is_drink": 0}, {"id": "rn3", "category": "Rice & Noodles", "name": "Paneer Fried Rice / Noodles", "price_inr": 169, "is_veg": 1, "is_drink": 0}, {"id": "rn4", "category": "Rice & Noodles", "name": "Schezwan Fried Rice / Noodles", "price_inr": 159, "is_veg": 1, "is_drink": 0}, {"id": "rn5", "category": "Rice & Noodles", "name": "Chilly Garlic Egg Fried Rice / Noodles", "price_inr": 179, "is_veg": 0, "is_drink": 0}, {"id": "rn6", "category": "Rice & Noodles", "name": "Schezwan Egg Fried Rice / Noodles", "price_inr": 179, "is_veg": 0, "is_drink": 0}, {"id": "rn7", "category": "Rice & Noodles", "name": "Stir Fried Egg Rice / Noodles", "price_inr": 179, "is_veg": 0, "is_drink": 0}, {"id": "rn8", "category": "Rice & Noodles", "name": "Chilly Garlic Chicken Fried Rice / Noodles", "price_inr": 209, "is_veg": 0, "is_drink": 0}, {"id": "rn9", "category": "Rice & Noodles", "name": "Schezwan Chicken Fried Rice / Noodles", "price_inr": 209, "is_veg": 0, "is_drink": 0}, {"id": "rn10", "category": "Rice & Noodles", "name": "Stir Fried Chicken Rice / Noodles", "price_inr": 209, "is_veg": 0, "is_drink": 0}, {"id": "bg1", "category": "Burgers", "name": "Classic Veg Burger", "price_inr": 119, "is_veg": 1, "is_drink": 0}, {"id": "bg2", "category": "Burgers", "name": "Juicy Cheese Burger", "price_inr": 139, "is_veg": 1, "is_drink": 0}, {"id": "bg3", "category": "Burgers", "name": "Juicy Chicken Burger", "price_inr": 159, "is_veg": 0, "is_drink": 0}, {"id": "bg4", "category": "Burgers", "name": "BBQ Chicken Burger", "price_inr": 169, "is_veg": 0, "is_drink": 0}, {"id": "bg5", "category": "Burgers", "name": "Chicken Cheese Burger", "price_inr": 169, "is_veg": 0, "is_drink": 0}, {"id": "bg6", "category": "Burgers", "name": "Grilled Chicken Burger", "price_inr": 169, "is_veg": 0, "is_drink": 0}, {"id": "pz1", "category": "Pizza", "name": "Spicy Paneer Tikka Pizza", "price_inr": 269, "is_veg": 1, "is_drink": 0}, {"id": "pz2", "category": "Pizza", "name": "Margherita", "price_inr": 199, "is_veg": 1, "is_drink": 0}, {"id": "pz3", "category": "Pizza", "name": "Garden Fresh Classic Pizza", "price_inr": 269, "is_veg": 1, "is_drink": 0}, {"id": "pz4", "category": "Pizza", "name": "Cheese Corn Pizza", "price_inr": 259, "is_veg": 1, "is_drink": 0}, {"id": "pz5", "category": "Pizza", "name": "Veg Cheese Garlic Pizza", "price_inr": 229, "is_veg": 1, "is_drink": 0}, {"id": "pz6", "category": "Pizza", "name": "Desi Chicken Tikka Pizza", "price_inr": 349, "is_veg": 0, "is_drink": 0}, {"id": "pz7", "category": "Pizza", "name": "BBQ Chicken Pizza", "price_inr": 349, "is_veg": 0, "is_drink": 0}, {"id": "pz8", "category": "Pizza", "name": "Grilled Chicken Pizza", "price_inr": 369, "is_veg": 0, "is_drink": 0}, {"id": "pz9", "category": "Pizza", "name": "Peri Peri Chicken Pizza", "price_inr": 359, "is_veg": 0, "is_drink": 0}, {"id": "sw1", "category": "Sandwiches", "name": "Paneer Tikka Sandwich", "price_inr": 119, "is_veg": 1, "is_drink": 0}, {"id": "sw2", "category": "Sandwiches", "name": "Juicy Veg Cheese Sandwich", "price_inr": 119, "is_veg": 1, "is_drink": 0}, {"id": "sw3", "category": "Sandwiches", "name": "Grilled Veg Sandwich", "price_inr": 119, "is_veg": 1, "is_drink": 0}, {"id": "sw4", "category": "Sandwiches", "name": "Egg Mayo Sandwich", "price_inr": 119, "is_veg": 0, "is_drink": 0}, {"id": "sw5", "category": "Sandwiches", "name": "Desi Chicken Tikka Sandwich", "price_inr": 159, "is_veg": 0, "is_drink": 0}, {"id": "ps1", "category": "Pasta", "name": "Veg Pasta in White and Red Sauce", "price_inr": 169, "is_veg": 1, "is_drink": 0}, {"id": "ps2", "category": "Pasta", "name": "Chicken Pasta in White and Red Sauce", "price_inr": 209, "is_veg": 0, "is_drink": 0}, {"id": "fs1", "category": "Fries & Snacks", "name": "French Fries", "price_inr": 69, "is_veg": 1, "is_drink": 0}, {"id": "fs2", "category": "Fries & Snacks", "name": "Peri Peri Fries", "price_inr": 79, "is_veg": 1, "is_drink": 0}, {"id": "fs3", "category": "Fries & Snacks", "name": "Cheese Fries", "price_inr": 99, "is_veg": 1, "is_drink": 0}, {"id": "fs4", "category": "Fries & Snacks", "name": "Nachos", "price_inr": 119, "is_veg": 1, "is_drink": 0}, {"id": "fs5", "category": "Fries & Snacks", "name": "Cheesy Nachos", "price_inr": 129, "is_veg": 1, "is_drink": 0}, {"id": "fs6", "category": "Fries & Snacks", "name": "Potato Wedges", "price_inr": 79, "is_veg": 1, "is_drink": 0}, {"id": "st1", "category": "Starters", "name": "Chilli Paneer", "price_inr": 119, "is_veg": 1, "is_drink": 0}, {"id": "st2", "category": "Starters", "name": "Honey Chilli Potato", "price_inr": 99, "is_veg": 1, "is_drink": 0}, {"id": "st3", "category": "Starters", "name": "Cheese Corn Nuggets", "price_inr": 109, "is_veg": 1, "is_drink": 0}, {"id": "st4", "category": "Starters", "name": "Cheese Corn Finger", "price_inr": 109, "is_veg": 1, "is_drink": 0}, {"id": "st5", "category": "Starters", "name": "Chicken Nuggets", "price_inr": 149, "is_veg": 0, "is_drink": 0}, {"id": "st6", "category": "Starters", "name": "Gossip Fried Chicken", "price_inr": 149, "is_veg": 0, "is_drink": 0}, {"id": "st7", "category": "Starters", "name": "Peri Peri Chicken Popcorn", "price_inr": 149, "is_veg": 0, "is_drink": 0}, {"id": "st8", "category": "Starters", "name": "BBQ Chicken Wings", "price_inr": 159, "is_veg": 0, "is_drink": 0}, {"id": "st9", "category": "Starters", "name": "Chicken Lollipop", "price_inr": 159, "is_veg": 0, "is_drink": 0}, {"id": "st10", "category": "Starters", "name": "Masala Omelette", "price_inr": 59, "is_veg": 0, "is_drink": 0}, {"id": "js1", "category": "Juices & Shakes", "name": "Watermelon Juice", "price_inr": 59, "is_veg": 1, "is_drink": 1}, {"id": "js2", "category": "Juices & Shakes", "name": "Fresh Lime", "price_inr": 39, "is_veg": 1, "is_drink": 1}, {"id": "js3", "category": "Juices & Shakes", "name": "Apple Juice", "price_inr": 99, "is_veg": 1, "is_drink": 1}, {"id": "js4", "category": "Juices & Shakes", "name": "Pineapple Juice", "price_inr": 89, "is_veg": 1, "is_drink": 1}, {"id": "js5", "category": "Juices & Shakes", "name": "Brownie Milk Shake", "price_inr": 129, "is_veg": 1, "is_drink": 1}, {"id": "js6", "category": "Juices & Shakes", "name": "Chocolate Milk Shake", "price_inr": 99, "is_veg": 1, "is_drink": 1}, {"id": "hd1", "category": "Hot Drinks", "name": "Cappuccino", "price_inr": 99, "is_veg": 1, "is_drink": 1}, {"id": "hd2", "category": "Hot Drinks", "name": "Cafe Latte", "price_inr": 99, "is_veg": 1, "is_drink": 1}, {"id": "hd3", "category": "Hot Drinks", "name": "Masala Tea", "price_inr": 29, "is_veg": 1, "is_drink": 1}, {"id": "hd4", "category": "Hot Drinks", "name": "Hot Chocolate Coffee", "price_inr": 99, "is_veg": 1, "is_drink": 1}];

  function loadDb() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (_) {}
    return { users: [], groups: [], notifications: [] };
  }

  function saveDb(db) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
  }

  function normalizeRoom(roomRaw, tower) {
    if (String(tower || "Tower 3").trim().toLowerCase() !== "tower 3") {
      throw new Error("Access restricted: Only Tower 3 Boys Hostel students can join.");
    }
    let r = String(roomRaw || "").trim().toUpperCase().replace(/\s+/g, "");
    if (r.startsWith("T3-")) r = r.slice(3);
    else if (r.startsWith("T3")) r = r.slice(2);
    if (!/^[1-9][0-9]{2}[A-Z]?$/.test(r)) {
      throw new Error("Invalid Tower 3 room number (use e.g. T3-204).");
    }
    return "T3-" + r;
  }

  function hydrateGroup(db, g) {
    const creator = db.users.find((u) => u.id === g.creator_id) || null;
    let sharedTotal = 0;
    let totalCount = 0;
    const participants = g.participant_ids.map((uid) => {
      const u = db.users.find((x) => x.id === uid) || { id: uid, student_name: "Student", room_number: "T3", student_id: "" };
      const itemsList = (g.cart_items || []).filter((ci) => ci.user_id === uid).map((ci) => {
        const lineTotal = ci.quantity * ci.unit_price_inr;
        sharedTotal += lineTotal;
        totalCount += ci.quantity;
        return Object.assign({}, ci, { line_total_inr: lineTotal });
      });
      const sub = itemsList.reduce((a, b) => a + b.line_total_inr, 0);
      const pack = itemsList.filter((i) => !i.is_drink).reduce((a, b) => a + b.quantity * PACK_INR, 0);
      const pay = (g.payments || {})[uid] || null;
      return {
        user_id: uid,
        student_name: u.student_name,
        room_number: u.room_number,
        student_id: u.student_id,
        items: itemsList,
        items_subtotal_inr: sub,
        packaging_fee_inr: pack,
        payable_amount_inr: sub + pack,
        payment: pay,
      };
    });
    const rem = Math.max(0, MIN_INR - sharedTotal);
    const pct = Math.min(100, Math.round((sharedTotal / MIN_INR) * 100));
    const unlocked = sharedTotal >= MIN_INR;
    const activeOrderers = participants.filter((p) => p.items_subtotal_inr > 0);
    const paidCount = activeOrderers.filter((p) => p.payment && p.payment.status === "paid" && p.payment.verified_by_server === 1).length;
    const allPaid = activeOrderers.length > 0 && paidCount === activeOrderers.length;
    const labels = {
      collecting: "Collecting orders",
      minimum_reached: "Minimum ₹350 reached",
      payments_completed: "All shares paid",
      order_placed: "Order sent to Grains and Gossip",
      closed: "Closed by creator",
    };
    return Object.assign({}, g, {
      creator,
      status_label: labels[g.status] || g.status,
      participant_count: participants.length,
      participants,
      total_item_count: totalCount,
      shared_cart_total_inr: sharedTotal,
      remaining_to_minimum_inr: rem,
      progress_percent: pct,
      checkout_unlocked: unlocked,
      active_ordering_count: activeOrderers.length,
      paid_verified_count: paidCount,
      all_payments_verified: allPaid,
      can_place_cafe_order: unlocked && allPaid,
    });
  }

  function buildDashboard(db, uid) {
    const user = db.users.find((u) => u.id === uid);
    if (!user) return null;
    const allGroups = db.groups.map((g) => hydrateGroup(db, g)).filter((g) => g.participant_ids.includes(uid));
    const active = allGroups.filter((g) => g.status !== "closed");
    let spent = 0;
    const pending = [];
    const food = [];
    allGroups.forEach((g) => {
      const sec = g.participants.find((p) => p.user_id === uid);
      if (!sec) return;
      sec.items.forEach((i) => food.push({ group_id: g.id, group_name: g.name, group_status_label: g.status_label, item_name: i.item_name, quantity: i.quantity, line_total_inr: i.line_total_inr }));
      if (sec.payment && sec.payment.status === "paid" && sec.payment.verified_by_server === 1) spent += sec.payment.payable_amount_inr;
      else if (sec.items_subtotal_inr > 0) pending.push({ group_id: g.id, group_name: g.name, checkout_unlocked: g.checkout_unlocked, items_subtotal_inr: sec.items_subtotal_inr, packaging_fee_inr: sec.packaging_fee_inr, payable_amount_inr: sec.payable_amount_inr });
    });
    return { user, active_groups: active, past_orders: [], personal_spending_inr: spent, pending_payments: pending, selected_food: food };
  }

  window.__RKD_STATIC_API = async function (path, options, currentUserId) {
    const db = loadDb();
    const method = (options && options.method) || "GET";
    const body = (options && options.body) || {};
    const uid = currentUserId || "";

    if (path.startsWith("/api/bootstrap")) {
      const qUid = new URLSearchParams(path.split("?")[1] || "").get("user_id") || uid;
      const user = db.users.find((u) => u.id === qUid) || null;
      return {
        app: {
          name: "Raat Ka Dabba",
          tower: "Tower 3",
          hostel_name: "Tower 3 Boys Hostel",
          custom_domain: "https://t3.raatkadabba.in",
          allowed_email_domain: "college.edu",
          cafe_name: "Grains and Gossip",
          minimum_cart_inr: MIN_INR,
          packing_fee_per_item_inr: PACK_INR,
        },
        current_user: user,
        menu: { cafe_name: "Grains and Gossip", minimum_cart_inr: MIN_INR, categories: MENU_CATEGORIES, items: MENU_ITEMS },
        groups: db.groups.map((g) => hydrateGroup(db, g)),
        dashboard: user ? buildDashboard(db, user.id) : null,
        notifications: user ? db.notifications.filter((n) => n.user_id === user.id) : [],
      };
    }

    if (path === "/api/auth/register" && method === "POST") {
      const email = String(body.college_email || "").trim().toLowerCase();
      if (!email.endsWith("@college.edu")) throw new Error("Use your official @college.edu student email address.");
      const room = normalizeRoom(body.room_number, body.tower);
      const user = {
        id: "u-" + Math.random().toString(36).slice(2, 9),
        student_name: String(body.student_name || "").trim(),
        college_email: email,
        student_id: String(body.student_id || "").trim().toUpperCase(),
        tower: "Tower 3",
        room_number: room,
        password: String(body.password || ""),
      };
      db.users.push(user);
      saveDb(db);
      return { user };
    }

    if (path === "/api/auth/login" && method === "POST") {
      const ident = String(body.identifier || "").trim().toLowerCase();
      const user = db.users.find((u) => (u.college_email === ident || u.student_id.toLowerCase() === ident || u.room_number.toLowerCase() === ident) && u.password === body.password);
      if (!user) throw new Error("Invalid credentials or account not registered in this browser yet.");
      return { user };
    }

    if (path === "/api/groups" && method === "POST") {
      const gid = "RKD-T3-" + Math.floor(1000 + Math.random() * 9000);
      const mins = Math.max(5, parseInt(body.deadline_minutes || 25, 10));
      const g = {
        id: gid,
        name: String(body.name || "Night Order").trim(),
        cafe_name: "Grains and Gossip",
        creator_id: uid,
        deadline: new Date(Date.now() + mins * 60000).toISOString(),
        participant_limit: body.participant_limit ? parseInt(body.participant_limit, 10) : null,
        minimum_cart_inr: MIN_INR,
        cart_frozen: 0,
        status: "collecting",
        share_link: "https://t3.raatkadabba.in/?group=" + gid,
        participant_ids: [uid],
        cart_items: [],
        payments: {},
      };
      db.groups.unshift(g);
      saveDb(db);
      return { group: hydrateGroup(db, g) };
    }

    const mJoin = path.match(/^\/api\/groups\/([^/]+)\/join$/);
    if (mJoin) {
      const g = db.groups.find((x) => x.id === mJoin[1]);
      if (!g) throw new Error("Group not found.");
      if (!g.participant_ids.includes(uid)) g.participant_ids.push(uid);
      saveDb(db);
      return { group: hydrateGroup(db, g) };
    }

    const mCart = path.match(/^\/api\/groups\/([^/]+)\/cart$/);
    if (mCart) {
      const g = db.groups.find((x) => x.id === mCart[1]);
      if (!g) throw new Error("Group not found.");
      if (g.cart_frozen) throw new Error("Cart is frozen for checkout.");
      const item = MENU_ITEMS.find((i) => i.id === body.menu_item_id);
      if (!item) throw new Error("Item not found.");
      if (!g.participant_ids.includes(uid)) g.participant_ids.push(uid);
      const existing = g.cart_items.find((ci) => ci.user_id === uid && ci.menu_item_id === item.id);
      const newQty = (existing ? existing.quantity : 0) + parseInt(body.quantity || 1, 10);
      if (newQty <= 0) g.cart_items = g.cart_items.filter((ci) => !(ci.user_id === uid && ci.menu_item_id === item.id));
      else if (existing) existing.quantity = newQty;
      else g.cart_items.push({ id: "ci-" + Math.random().toString(36).slice(2, 8), user_id: uid, menu_item_id: item.id, item_name: item.name, quantity: newQty, unit_price_inr: item.price_inr, is_drink: item.is_drink });
      saveDb(db);
      return { group: hydrateGroup(db, g) };
    }

    const mLock = path.match(/^\/api\/groups\/([^/]+)\/lock-checkout$/);
    if (mLock) {
      const g = db.groups.find((x) => x.id === mLock[1]);
      const hg = hydrateGroup(db, g);
      if (hg.shared_cart_total_inr < MIN_INR) throw new Error("Add ₹" + hg.remaining_to_minimum_inr + " more to reach ₹" + MIN_INR + ".");
      g.cart_frozen = 1;
      g.status = "minimum_reached";
      saveDb(db);
      return { group: hydrateGroup(db, g) };
    }

    const mPay = path.match(/^\/api\/groups\/([^/]+)\/payments\/initiate$/);
    if (mPay) {
      const g = db.groups.find((x) => x.id === mPay[1]);
      const hg = hydrateGroup(db, g);
      const sec = hg.participants.find((p) => p.user_id === uid);
      const orderId = "order_" + g.id.replace(/-/g, "") + "_" + uid.slice(-4);
      const payId = "pay_" + Math.random().toString(36).slice(2, 8);
      g.payments[uid] = {
        gateway_order_id: orderId,
        gateway_payment_id: null,
        status: "pending",
        verified_by_server: 0,
        payable_amount_inr: sec.payable_amount_inr,
        sandbox_webhook_helper: { gateway_order_id: orderId, sample_payment_id: payId, paid_signature: "static_ok", failed_signature: "static_fail" },
      };
      saveDb(db);
      return { group: hydrateGroup(db, g), payment_intent: g.payments[uid] };
    }

    if (path === "/api/payments/webhook") {
      const g = db.groups.find((x) => Object.values(x.payments || {}).some((p) => p.gateway_order_id === body.gateway_order_id));
      if (!g) throw new Error("Order not found.");
      const pay = Object.values(g.payments).find((p) => p.gateway_order_id === body.gateway_order_id);
      pay.status = body.outcome;
      pay.gateway_payment_id = body.gateway_payment_id;
      pay.verified_by_server = body.outcome === "paid" ? 1 : 0;
      const hg = hydrateGroup(db, g);
      if (hg.all_payments_verified) g.status = "payments_completed";
      saveDb(db);
      return { group: hydrateGroup(db, g) };
    }

    const mAdv = path.match(/^\/api\/groups\/([^/]+)\/advance-status$/);
    if (mAdv) {
      const g = db.groups.find((x) => x.id === mAdv[1]);
      g.status = "order_placed";
      saveDb(db);
      return { group: hydrateGroup(db, g) };
    }

    return {};
  };
})();
