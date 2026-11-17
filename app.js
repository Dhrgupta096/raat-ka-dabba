/* ==========================================================================
   Raat Ka Dabba — Tower 3 Boys Hostel (t3.raatkadabba.in)
   Storefront + Slide-Over Shared Cart Drawer + Individual Checkout
   ========================================================================== */

(function () {
  "use strict";

  const state = {
    appMeta: null,
    currentUser: null,
    menu: { categories: [], items: [], minimum_cart_inr: 350 },
    selectedCategory: "All",
    dietFilter: "all", // 'all' | 'veg' | 'nonveg'
    priceFilter: "all", // 'all' | 'under100'
    menuSearch: "",
    groups: [],
    activeGroupId: null,
    dashboard: null,
    notifications: [],
    activeView: "store", // 'store' | 'checkout' | 'account' | 'alerts'
    cartDrawerOpen: false,
    modal: null, // null | 'auth' | 'createGroup' | 'joinByCode'
    authModeTab: "login", // 'login' | 'register'
    paymentDraft: {
      method: "upi_qr",
      upiVpa: "",
    },
    sseConnected: false,
  };

  function escapeHtml(val) {
    return String(val ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatRemainingTime(isoStr) {
    if (!isoStr) return "Open";
    const diffMs = new Date(isoStr).getTime() - Date.now();
    if (diffMs <= 0) return "Deadline passed";
    const mins = Math.ceil(diffMs / 60000);
    if (mins < 60) return `${mins}m left`;
    const hrs = Math.floor(mins / 60);
    return `${hrs}h ${mins % 60}m left`;
  }

  function renderUpiQrSvg(upiUri) {
    let hash = 2166136261;
    for (let i = 0; i < upiUri.length; i++) {
      hash ^= upiUri.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    const size = 21;
    const cell = 6;
    let rects = "";
    const isFinder = (r, c) =>
      (r < 7 && c < 7) || (r < 7 && c >= size - 7) || (r >= size - 7 && c < 7);

    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        let on = false;
        if (isFinder(r, c)) {
          const lr = r >= size - 7 ? r - (size - 7) : r;
          const lc = c >= size - 7 ? c - (size - 7) : c;
          on =
            lr === 0 ||
            lr === 6 ||
            lc === 0 ||
            lc === 6 ||
            (lr >= 2 && lr <= 4 && lc >= 2 && lc <= 4);
        } else {
          const bit = ((hash >>> ((r * size + c) % 24)) ^ (r * 13 + c * 7)) & 1;
          on = bit === 1;
        }
        if (on) {
          rects += `<rect x="${(c + 2) * cell}" y="${(r + 2) * cell}" width="${cell}" height="${cell}" fill="#202020" rx="1"/>`;
        }
      }
    }
    const dim = (size + 4) * cell;
    return `<svg width="${dim}" height="${dim}" viewBox="0 0 ${dim} ${dim}" xmlns="http://www.w3.org/2000/svg" style="background:#FFFFFF;border-radius:8px;border:1px solid #E5E7EB;">${rects}</svg>`;
  }

  function showToast(title, subtitle = "", isError = false) {
    const root = document.getElementById("toast-root");
    if (!root) return;
    const el = document.createElement("div");
    el.className = "bt-toast";
    if (isError) el.style.borderLeftColor = "#EF4444";
    el.innerHTML = `<div style="font-weight:800;margin-bottom:2px;">${escapeHtml(title)}</div>
      ${subtitle ? `<div style="opacity:0.86;font-size:0.75rem;">${escapeHtml(subtitle)}</div>` : ""}`;
    root.appendChild(el);
    setTimeout(() => el.remove(), 3800);
  }

  async function api(path, options = {}) {
    const headers = Object.assign(
      { "Content-Type": "application/json" },
      options.headers || {}
    );
    if (state.currentUser && state.currentUser.id) {
      headers["X-Student-Id"] = state.currentUser.id;
    }
    const resp = await fetch(path, {
      method: options.method || "GET",
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      throw new Error(data.error || `Request failed (${resp.status})`);
    }
    return data;
  }

  async function loadBootstrap(preferredUserId = null) {
    const storedUid =
      preferredUserId !== undefined && preferredUserId !== null
        ? preferredUserId
        : localStorage.getItem("bt_user_id") || "";
    const qs = storedUid ? `?user_id=${encodeURIComponent(storedUid)}` : "";
    const data = await api(`/api/bootstrap${qs}`);

    state.appMeta = data.app;
    state.currentUser = data.current_user || null;
    if (state.currentUser) {
      localStorage.setItem("bt_user_id", state.currentUser.id);
    } else {
      localStorage.removeItem("bt_user_id");
    }
    state.menu = data.menu || { categories: [], items: [], minimum_cart_inr: 350 };
    state.groups = data.groups || [];
    state.dashboard = data.dashboard || null;
    state.notifications = data.notifications || [];

    const params = new URLSearchParams(window.location.search);
    const sharedGroupId = params.get("group");
    if (sharedGroupId && state.groups.some((g) => g.id === sharedGroupId)) {
      state.activeGroupId = sharedGroupId;
      state.cartDrawerOpen = true;
    } else if (
      !state.activeGroupId ||
      !state.groups.some((g) => g.id === state.activeGroupId)
    ) {
      state.activeGroupId = state.groups.length > 0 ? state.groups[0].id : null;
    }
    render();
  }

  function connectRealtimeSSE() {
    if (typeof EventSource === "undefined") return;
    const es = new EventSource("/api/stream");
    es.onopen = () => {
      state.sseConnected = true;
    };
    es.onmessage = () => {
      loadBootstrap(state.currentUser ? state.currentUser.id : "").catch(() => {});
    };
    es.onerror = () => {
      state.sseConnected = false;
    };
  }

  function getActiveGroup() {
    if (!state.activeGroupId) return state.groups[0] || null;
    return (
      state.groups.find((g) => g.id === state.activeGroupId) ||
      state.groups[0] ||
      null
    );
  }

  function unreadNotificationCount() {
    return state.notifications.filter((n) => !n.is_read).length;
  }

  function requireLoginOrRun() {
    if (!state.currentUser) {
      state.modal = "auth";
      state.authModeTab = "login";
      render();
      showToast("Login Required", "Sign in with your Tower 3 Boys Hostel account.");
      return false;
    }
    return true;
  }

  // ==========================================================================
  // HEADER & CATEGORY BAR (ZEPTO-INSPIRED)
  // ==========================================================================

  function renderHeader() {
    const activeGroup = getActiveGroup();
    const cartCount = activeGroup ? activeGroup.total_item_count : 0;
    const cartTotal = activeGroup ? activeGroup.shared_cart_total_inr : 0;
    const unread = unreadNotificationCount();
    const categories = ["All", ...(state.menu.categories || [])];

    return `
      <header class="bt-header">
        <div class="bt-header-main">
          <div class="bt-brand-area">
            <a class="bt-brand" data-action="nav-view" data-view="store">
              Raat Ka Dabba
            </a>
            <div class="bt-location-block">
              <span class="bt-location-title">Tower 3 Boys Hostel · Reception</span>
              <span class="bt-location-sub">t3.raatkadabba.in · Grains &amp; Gossip</span>
            </div>
          </div>

          <div class="bt-search-wrap">
            <input id="menu-search-input" type="search" class="bt-search-input"
              value="${escapeHtml(state.menuSearch)}"
              placeholder='Search "Schezwan Fried Rice", "Classic Veg Burger", "Masala Tea"...'
              data-action="search-menu" />
          </div>

          <div class="bt-header-actions">
            ${
              state.currentUser
                ? `<button type="button" class="bt-icon-btn" data-action="nav-view" data-view="account">
                    <span>${escapeHtml(state.currentUser.student_name.split(" ")[0])} · ${escapeHtml(state.currentUser.room_number)}</span>
                  </button>
                  <button type="button" class="bt-icon-btn" data-action="nav-view" data-view="alerts">
                    <span>Alerts ${unread > 0 ? `(${unread})` : ""}</span>
                  </button>`
                : `<button type="button" class="bt-icon-btn" data-action="open-modal" data-modal="auth">
                    <span>Login / Register</span>
                  </button>`
            }

            <button type="button" class="bt-icon-btn bt-cart-trigger" data-action="toggle-cart-drawer">
              <span>Cart${cartCount > 0 ? ` (${cartCount} · ₹${cartTotal})` : ""}</span>
            </button>
          </div>
        </div>

        ${
          state.activeView === "store"
            ? `<div class="bt-cat-bar">
                <div class="bt-cat-inner">
                  ${categories
                    .map(
                      (cat) => `
                    <button type="button" class="bt-cat-tab ${state.selectedCategory === cat ? "active" : ""}" data-action="filter-category" data-category="${escapeHtml(cat)}">
                      ${escapeHtml(cat)}
                    </button>`
                    )
                    .join("")}
                </div>
              </div>`
            : ""
        }
      </header>
    `;
  }

  // ==========================================================================
  // STOREFRONT VIEW (BANNER + ACTIVE GROUPS + CLEAN TEXT MENU)
  // ==========================================================================

  function renderStorefrontView() {
    const activeGroup = getActiveGroup();
    const q = state.menuSearch.trim().toLowerCase();

    const filteredItems = (state.menu.items || []).filter((item) => {
      const catMatch =
        state.selectedCategory === "All" ||
        item.category === state.selectedCategory;
      const dietMatch =
        state.dietFilter === "all" ||
        (state.dietFilter === "veg" && item.is_veg === 1) ||
        (state.dietFilter === "nonveg" && item.is_veg === 0);
      const priceMatch =
        state.priceFilter === "all" || item.price_inr <= 100;
      const searchMatch =
        !q ||
        item.name.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q);
      return catMatch && dietMatch && priceMatch && searchMatch;
    });

    const groupedByCat = [];
    const catOrder =
      state.selectedCategory === "All"
        ? state.menu.categories || []
        : [state.selectedCategory];
    catOrder.forEach((catName) => {
      const rows = filteredItems.filter((i) => i.category === catName);
      if (rows.length > 0) groupedByCat.push({ category: catName, items: rows });
    });

    const myCartMap = {};
    if (activeGroup && state.currentUser) {
      activeGroup.cart_items
        .filter((ci) => ci.user_id === state.currentUser.id)
        .forEach((ci) => {
          myCartMap[ci.menu_item_id] = ci.quantity;
        });
    }

    return `
      <section class="bt-landing-hero">
        <div class="bt-landing-grid">
          <div>
            <div class="bt-hero-kicker">TOWER 3 BOYS HOSTEL · AFTER 9 PM MESS SHUTDOWN</div>
            <h1 class="bt-hero-h1">Mess closed.<br/>Don't pay <em>₹350</em> alone.</h1>
            <p class="bt-hero-copy">
              Pool your ₹79 fries or ₹119 burger with Tower 3 wingmates in one shared Grains &amp; Gossip cart. Hit ₹350 together, pay only for your own dabba.
            </p>
            <div style="display:flex;gap:0.55rem;flex-wrap:wrap;">
              <button type="button" class="bt-btn bt-btn-primary" data-action="open-create-group">
                + Start a Group Order
              </button>
              <button type="button" class="bt-btn bt-btn-outline" data-action="open-modal" data-modal="joinByCode">
                Join by Group ID
              </button>
              <button type="button" class="bt-btn bt-btn-outline" data-action="scroll-menu">
                Browse 58-Item Menu ↓
              </button>
            </div>
          </div>

          <!-- Clean Typographic Dabba Pool Breakdown -->
          <div class="bt-math-card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.7rem;">
              <strong style="font-size:0.86rem;">How Tower 3 Beats the ₹350 Minimum</strong>
              <span class="bt-badge bt-badge-green">NO EQUAL SPLIT</span>
            </div>

            <div style="display:flex;flex-direction:column;gap:0.45rem;">
              <div class="bt-math-row" style="opacity:0.75;">
                <span><strong>Ordering Solo:</strong> Classic Veg Burger</span>
                <span style="color:var(--bt-danger);font-weight:800;">₹119 · Blocked (Need ₹231 more)</span>
              </div>
              <div class="bt-math-row" style="border-color:var(--bt-primary);">
                <span><strong>Room A:</strong> Classic Veg Burger</span>
                <strong>Pays ₹119 + ₹10 pack</strong>
              </div>
              <div class="bt-math-row" style="border-color:var(--bt-primary);">
                <span><strong>Room B:</strong> Schezwan Fried Rice</span>
                <strong>Pays ₹159 + ₹10 pack</strong>
              </div>
              <div class="bt-math-row" style="border-color:var(--bt-primary);">
                <span><strong>Room C:</strong> Peri Peri Fries + Masala Tea</span>
                <strong>Pays ₹108 + ₹10 pack</strong>
              </div>
            </div>

            <div style="margin-top:0.7rem;padding-top:0.65rem;border-top:1px solid var(--bt-border);display:flex;justify-content:space-between;align-items:center;font-size:0.82rem;">
              <span style="color:var(--bt-muted);">Combined Food Total: <strong style="color:var(--bt-ink);">₹386 / ₹350</strong></span>
              <span style="color:var(--bt-primary);font-weight:800;">Checkout Unlocked · Free Reception Drop</span>
            </div>
          </div>
        </div>
      </section>

      <div class="bt-fact-bar">
        <div class="bt-fact-bar-inner">
          <span>Cafe: <strong>Grains &amp; Gossip</strong></span>
          <span>Timings: <strong>9:30 PM – 3:00 AM</strong></span>
          <span>Min Shared Cart: <strong>₹350</strong></span>
          <span>Packing: <strong>₹10 / food item</strong> (Drinks free)</span>
          <span>Delivery: <strong>Free · Hostel Reception (~30 min)</strong></span>
          <span>Contact: <strong>+91 99809 25507</strong></span>
        </div>
      </div>

      <div id="menu-anchor" class="bt-container" style="padding-bottom:4rem;">
        <!-- Active Tower 3 Boys Hostel Groups -->
        <section style="margin-top:1.25rem;margin-bottom:1.5rem;">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.75rem;">
            <h2 style="margin:0;font-size:1.05rem;font-weight:800;">
              Active Tower 3 Boys Hostel Groups (${state.groups.length})
            </h2>
            <div style="display:flex;gap:0.4rem;">
              <button type="button" class="bt-btn bt-btn-sm ${state.dietFilter === "all" ? "bt-btn-dark" : "bt-btn-outline"}" data-action="filter-diet" data-diet="all">All</button>
              <button type="button" class="bt-btn bt-btn-sm ${state.dietFilter === "veg" ? "bt-btn-dark" : "bt-btn-outline"}" data-action="filter-diet" data-diet="veg">
                <span class="bt-diet-box veg" style="width:12px;height:12px;"></span> Veg
              </button>
              <button type="button" class="bt-btn bt-btn-sm ${state.dietFilter === "nonveg" ? "bt-btn-dark" : "bt-btn-outline"}" data-action="filter-diet" data-diet="nonveg">
                <span class="bt-diet-box nonveg" style="width:12px;height:12px;"></span> Non-Veg
              </button>
              <button type="button" class="bt-btn bt-btn-sm ${state.priceFilter === "under100" ? "bt-btn-primary" : "bt-btn-outline"}" data-action="toggle-under100">
                Under ₹100
              </button>
            </div>
          </div>

          ${
            state.groups.length === 0
              ? `<div class="bt-card" style="margin-top:0.75rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem;">
                  <div>
                    <div style="font-weight:800;font-size:0.95rem;">No active Tower 3 Boys Hostel group orders right now.</div>
                    <div style="font-size:0.82rem;color:var(--bt-muted);">Start a group order and share the t3.raatkadabba.in link with your wingmates to reach ₹350 together.</div>
                  </div>
                  <button type="button" class="bt-btn bt-btn-primary bt-btn-sm" data-action="open-create-group">Start First Group Order</button>
                </div>`
              : `<div class="bt-groups-strip">
                  ${state.groups
                    .map((g) => {
                      const isSelected = activeGroup && activeGroup.id === g.id;
                      const isMember =
                        state.currentUser &&
                        g.participant_ids.includes(state.currentUser.id);
                      const unlocked = g.checkout_unlocked;
                      return `<div class="bt-card" style="padding:0.95rem;${isSelected ? "border-color:var(--bt-primary);border-width:1.5px;" : ""}">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;margin-bottom:0.55rem;">
                          <div>
                            <div style="display:flex;align-items:center;gap:0.35rem;margin-bottom:0.2rem;">
                              <span class="bt-badge bt-badge-dark">${escapeHtml(g.id)}</span>
                              <span class="bt-badge ${unlocked ? "bt-badge-green" : "bt-badge-green"}">${unlocked ? "₹350 Reached" : `₹${g.remaining_to_minimum_inr} to ₹350`}</span>
                            </div>
                            <div style="font-weight:800;font-size:0.95rem;">${escapeHtml(g.name)}</div>
                            <div style="font-size:0.75rem;color:var(--bt-muted);">
                              Host: ${escapeHtml(g.creator ? g.creator.student_name : "")} (${escapeHtml(g.creator ? g.creator.room_number : "")}) · ${escapeHtml(formatRemainingTime(g.deadline))}
                            </div>
                          </div>
                          <div style="font-weight:900;font-size:0.95rem;">₹${g.shared_cart_total_inr}/₹350</div>
                        </div>

                        <div class="bt-progress-track" style="margin-bottom:0.65rem;">
                          <div class="bt-progress-fill ${unlocked ? "unlocked" : ""}" style="width:${g.progress_percent}%;"></div>
                        </div>

                        <div style="display:flex;justify-content:space-between;align-items:center;gap:0.4rem;">
                          <span style="font-size:0.75rem;color:var(--bt-muted);">${g.participant_count} student(s)</span>
                          <div style="display:flex;gap:0.35rem;">
                            <button type="button" class="bt-btn bt-btn-outline bt-btn-sm" data-action="copy-share-link" data-group-id="${escapeHtml(g.id)}">Share</button>
                            ${
                              isMember
                                ? `<button type="button" class="bt-btn bt-btn-dark bt-btn-sm" data-action="select-group-and-open-cart" data-group-id="${escapeHtml(g.id)}">Selected</button>`
                                : `<button type="button" class="bt-btn bt-btn-primary bt-btn-sm" data-action="join-group" data-group-id="${escapeHtml(g.id)}" ${g.cart_frozen || g.status === "closed" ? "disabled" : ""}>Join Group</button>`
                            }
                          </div>
                        </div>
                      </div>`;
                    })
                    .join("")}
                </div>`
          }
        </section>

        <!-- Clean Text-Only 58-Item Menu Board -->
        <section>
          ${
            groupedByCat.length === 0
              ? `<div class="bt-card" style="text-align:center;color:var(--bt-muted);">No items match "${escapeHtml(state.menuSearch)}".</div>`
              : groupedByCat
                  .map(
                    (sec) => `
                  <div class="bt-menu-section">
                    <div class="bt-menu-section-header">
                      <h3 class="bt-menu-section-title">${escapeHtml(sec.category)}</h3>
                      <span style="font-size:0.74rem;color:var(--bt-muted);font-weight:600;">
                        ${sec.items[0] && sec.items[0].is_drink ? "No packing fee on drinks" : "Packing: ₹10 / food item"}
                      </span>
                    </div>
                    <div class="bt-menu-grid-2col">
                      ${sec.items
                        .map((item) => {
                          const myQty = myCartMap[item.id] || 0;
                          const frozen =
                            activeGroup &&
                            (activeGroup.cart_frozen ||
                              activeGroup.status === "closed");
                          return `<div class="bt-menu-row ${myQty > 0 ? "in-cart" : ""}">
                            <div class="bt-menu-item-left">
                              <span class="bt-diet-box ${item.is_veg ? "veg" : "nonveg"}"></span>
                              <div class="bt-menu-item-name">${escapeHtml(item.name)}</div>
                            </div>
                            <div class="bt-menu-item-right">
                              <div class="bt-menu-item-price">₹${item.price_inr}</div>
                              ${
                                myQty > 0
                                  ? `<div class="bt-qty-ctrl active-stepper">
                                      <button type="button" class="bt-qty-btn" data-action="cart-delta" data-group-id="${escapeHtml(activeGroup.id)}" data-item-id="${escapeHtml(item.id)}" data-delta="-1" ${frozen ? "disabled" : ""}>−</button>
                                      <span class="bt-qty-val">${myQty}</span>
                                      <button type="button" class="bt-qty-btn" data-action="cart-delta" data-group-id="${escapeHtml(activeGroup.id)}" data-item-id="${escapeHtml(item.id)}" data-delta="1" ${frozen ? "disabled" : ""}>+</button>
                                    </div>`
                                  : `<button type="button" class="bt-btn bt-btn-outline bt-btn-sm" data-action="add-to-cart" data-item-id="${escapeHtml(item.id)}" ${frozen ? "disabled" : ""}>
                                      + Add
                                    </button>`
                              }
                            </div>
                          </div>`;
                        })
                        .join("")}
                    </div>
                  </div>`
                  )
                  .join("")
          }
        </section>
      </div>
    `;
  }

  // ==========================================================================
  // SLIDE-OVER CART DRAWER (ZEPTO REFERENCE)
  // ==========================================================================

  function renderCartDrawer() {
    if (!state.cartDrawerOpen) return "";
    const group = getActiveGroup();

    let bodyHtml = "";
    let footerHtml = "";

    if (!group || group.total_item_count === 0) {
      bodyHtml = `
        <div class="bt-empty-cart">
          <div style="font-size:1rem;font-weight:800;margin-bottom:0.35rem;">Your shared cart is empty</div>
          <div style="font-size:0.82rem;color:var(--bt-muted);margin-bottom:1.1rem;">
            ${
              group
                ? `Add items from Grains &amp; Gossip to reach the ₹350 minimum in ${escapeHtml(group.name)}.`
                : "Start or join a Tower 3 Boys Hostel group order to begin adding items."
            }
          </div>
          <button type="button" class="bt-btn bt-btn-dark" data-action="close-cart-drawer">
            Browse Menu
          </button>
        </div>
      `;
    } else {
      const unlocked = group.checkout_unlocked;
      const isCreator =
        state.currentUser && group.creator_id === state.currentUser.id;

      const topupItems = !unlocked && !group.cart_frozen
        ? (state.menu.items || [])
            .filter((i) => i.price_inr <= 100)
            .sort((a, b) => Math.abs(a.price_inr - group.remaining_to_minimum_inr) - Math.abs(b.price_inr - group.remaining_to_minimum_inr))
            .slice(0, 3)
        : [];

      bodyHtml = `
        <div style="background:var(--bt-primary-soft);padding:0.85rem;border-radius:10px;margin-bottom:0.9rem;border:1px solid ${unlocked ? "#86EFAC" : "#D4D4D8"};">
          <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:0.35rem;">
            <span style="font-size:0.84rem;font-weight:800;">
              Shared Total: ₹${group.shared_cart_total_inr} / ₹${group.minimum_cart_inr}
            </span>
            <span style="font-size:0.75rem;font-weight:800;">${group.progress_percent}%</span>
          </div>
          <div class="bt-progress-track" style="background:rgba(255,255,255,0.75);">
            <div class="bt-progress-fill" style="width:${group.progress_percent}%;"></div>
          </div>
          <div style="font-size:0.78rem;font-weight:700;margin-top:0.4rem;color:var(--bt-primary);">
            ${
              unlocked
                ? "₹350 minimum reached! Ready for individual checkout."
                : `Add ₹${group.remaining_to_minimum_inr} more to unlock checkout.`
            }
          </div>
        </div>

        ${
          topupItems.length > 0
            ? `<div class="bt-topup-strip">
                <div style="font-size:0.75rem;font-weight:700;color:var(--bt-muted);">Quick add to reach ₹350:</div>
                <div class="bt-topup-chips">
                  ${topupItems
                    .map(
                      (ti) => `<button type="button" class="bt-topup-chip" data-action="add-to-cart" data-item-id="${escapeHtml(ti.id)}">
                        + ${escapeHtml(ti.name)} (₹${ti.price_inr})
                      </button>`
                    )
                    .join("")}
                </div>
              </div>`
            : ""
        }

        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;font-size:0.78rem;color:var(--bt-muted);">
          <span>Group: <strong>${escapeHtml(group.name)}</strong> (${escapeHtml(group.id)})</span>
          <button type="button" class="bt-btn bt-btn-outline bt-btn-sm" data-action="copy-share-link" data-group-id="${escapeHtml(group.id)}">Share Link</button>
        </div>

        ${group.participants
          .map((p) => {
            const isMe =
              state.currentUser && p.user_id === state.currentUser.id;
            return `<div class="bt-participant-box ${isMe ? "is-me" : ""}">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem;">
                <div>
                  <strong style="font-size:0.84rem;">${escapeHtml(p.student_name)}</strong>
                  <span class="bt-badge" style="background:var(--bt-bg);margin-left:3px;">${escapeHtml(p.room_number)}</span>
                  ${isMe ? `<span class="bt-badge bt-badge-green" style="margin-left:3px;">YOU</span>` : ""}
                </div>
                <div style="font-size:0.8rem;font-weight:800;">
                  ₹${p.items_subtotal_inr}${p.packaging_fee_inr > 0 ? ` + ₹${p.packaging_fee_inr} pack` : ""}
                </div>
              </div>
              ${
                p.items.length === 0
                  ? `<div style="font-size:0.75rem;color:var(--bt-muted);">No items yet.</div>`
                  : p.items
                      .map(
                        (ci) => `
                      <div style="display:flex;justify-content:space-between;align-items:center;padding:0.35rem 0;border-top:1px dashed var(--bt-border);font-size:0.8rem;">
                        <div>
                          <div style="font-weight:600;">${escapeHtml(ci.item_name)}</div>
                          <div style="font-size:0.72rem;color:var(--bt-muted);">
                            ₹${ci.unit_price_inr} × ${ci.quantity} = <strong>₹${ci.line_total_inr}</strong>
                            ${ci.is_drink ? " · Free packing" : ` · +₹${ci.quantity * 10} pack`}
                          </div>
                        </div>
                        ${
                          isMe && !group.cart_frozen && group.status !== "closed"
                            ? `<div class="bt-qty-ctrl" style="height:26px;">
                                <button type="button" class="bt-qty-btn" style="width:24px;" data-action="cart-delta" data-group-id="${escapeHtml(group.id)}" data-item-id="${escapeHtml(ci.menu_item_id)}" data-delta="-1">−</button>
                                <span class="bt-qty-val" style="min-width:20px;font-size:0.76rem;">${ci.quantity}</span>
                                <button type="button" class="bt-qty-btn" style="width:24px;" data-action="cart-delta" data-group-id="${escapeHtml(group.id)}" data-item-id="${escapeHtml(ci.menu_item_id)}" data-delta="1">+</button>
                              </div>`
                            : `<span style="font-size:0.7rem;color:var(--bt-muted);">${isMe ? "Locked" : "Owner only"}</span>`
                        }
                      </div>`
                      )
                      .join("")
              }
            </div>`;
          })
          .join("")}

        ${
          isCreator && group.cart_frozen && group.status !== "order_placed" && group.status !== "closed"
            ? `<button type="button" class="bt-btn bt-btn-outline bt-btn-sm" style="width:100%;margin-top:0.4rem;" data-action="reopen-cart" data-group-id="${escapeHtml(group.id)}">
                Unfreeze / Reopen Cart
              </button>`
            : ""
        }
      `;

      footerHtml = `
        <div class="bt-drawer-footer">
          ${
            !unlocked
              ? `<button type="button" class="bt-btn bt-btn-dark" style="width:100%;" disabled>
                  Add ₹${group.remaining_to_minimum_inr} More to Unlock Checkout
                </button>`
              : group.cart_frozen
              ? `<button type="button" class="bt-btn bt-btn-primary" style="width:100%;" data-action="go-checkout">
                  Proceed to Individual Payment →
                </button>`
              : `<button type="button" class="bt-btn bt-btn-primary" style="width:100%;" data-action="lock-checkout" data-group-id="${escapeHtml(group.id)}">
                  Freeze Cart &amp; Pay Individual Share (₹${group.shared_cart_total_inr})
                </button>`
          }
        </div>
      `;
    }

    return `
      <div class="bt-drawer-backdrop" data-action="close-drawer-backdrop">
        <aside class="bt-drawer" aria-label="Shared Cart Drawer">
          <div class="bt-drawer-header">
            <div style="display:flex;align-items:center;gap:0.6rem;">
              <button type="button" class="bt-btn bt-btn-outline bt-btn-sm" data-action="close-cart-drawer">‹ Back</button>
              <strong style="font-size:1rem;">Shared Cart</strong>
            </div>
            ${
              group
                ? `<span class="bt-badge bt-badge-dark">${escapeHtml(group.id)}</span>`
                : ""
            }
          </div>
          <div class="bt-drawer-body">${bodyHtml}</div>
          ${footerHtml}
        </aside>
      </div>
    `;
  }

  // ==========================================================================
  // CHECKOUT VIEW (NO TRACKING PIPELINE — ONLY INDIVIDUAL PAYMENT & CAFE SUBMIT)
  // ==========================================================================

  function renderCheckoutView() {
    if (!state.currentUser) {
      return `<div class="bt-container" style="padding:2rem 0;">
        <div class="bt-card">Please log in with your Tower 3 Boys Hostel account to pay your share.
          <button type="button" class="bt-btn bt-btn-primary bt-btn-sm" style="margin-left:0.5rem;" data-action="open-modal" data-modal="auth">Login</button>
        </div>
      </div>`;
    }

    const group = getActiveGroup();
    if (!group) {
      return `<div class="bt-container" style="padding:2rem 0;"><div class="bt-card">No active group selected.</div></div>`;
    }

    const mySection = group.participants.find(
      (p) => p.user_id === state.currentUser.id
    );
    const myPay = mySection ? mySection.payment : null;
    const isMySharePaid =
      myPay && myPay.status === "paid" && myPay.verified_by_server === 1;
    const foodCount = mySection
      ? mySection.items.filter((i) => !i.is_drink).reduce((a, i) => a + i.quantity, 0)
      : 0;

    return `
      <div class="bt-container" style="padding:1.5rem 1.25rem 3rem;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.75rem;margin-bottom:1.15rem;">
          <div>
            <button type="button" class="bt-btn bt-btn-outline bt-btn-sm" data-action="nav-view" data-view="store">← Back to Menu</button>
            <h2 style="margin:0.5rem 0 0;font-size:1.35rem;font-weight:850;">
              Individual Checkout — ${escapeHtml(group.name)} (${escapeHtml(group.id)})
            </h2>
            <div style="font-size:0.82rem;color:var(--bt-muted);">
              Shared Total: <strong>₹${group.shared_cart_total_inr}</strong> (Min ₹350) · Delivery: <strong>Free to Tower 3 Boys Hostel Reception</strong>
            </div>
          </div>

          ${
            group.can_place_cafe_order && group.status !== "order_placed"
              ? `<button type="button" class="bt-btn bt-btn-primary" data-action="place-cafe-order" data-group-id="${escapeHtml(group.id)}">
                  Submit Final Order to Grains &amp; Gossip
                </button>`
              : group.status === "order_placed"
              ? `<span class="bt-badge bt-badge-green" style="font-size:0.84rem;padding:0.4rem 0.85rem;">Order Sent to Grains &amp; Gossip (+91 99809 25507)</span>`
              : ""
          }
        </div>

        <div class="bt-workspace-grid">
          <!-- LEFT: Individual Itemized Bill -->
          <div class="bt-card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.85rem;">
              <div>
                <h3 style="margin:0;font-size:1.08rem;font-weight:850;">
                  Your Bill (${escapeHtml(state.currentUser.student_name)} · ${escapeHtml(state.currentUser.room_number)})
                </h3>
                <div style="font-size:0.76rem;color:var(--bt-muted);">
                  You pay only for your own items + ₹10 per food container (drinks free).
                </div>
              </div>
              <span class="bt-badge ${isMySharePaid ? "bt-badge-green" : "bt-badge-warning"}">
                ${isMySharePaid ? "PAID" : escapeHtml(myPay ? myPay.status.toUpperCase() : "PENDING")}
              </span>
            </div>

            ${
              !mySection || mySection.items_subtotal_inr === 0
                ? `<div style="padding:1rem;background:var(--bt-bg);border-radius:8px;font-size:0.85rem;">You have no items in this group cart.</div>`
                : `
              <div style="background:var(--bt-bg);border:1px solid var(--bt-border);border-radius:8px;padding:0.9rem;margin-bottom:0.95rem;">
                ${mySection.items
                  .map(
                    (i) => `
                  <div style="display:flex;justify-content:space-between;font-size:0.84rem;margin-bottom:0.35rem;">
                    <span>${escapeHtml(i.item_name)} × ${i.quantity}</span>
                    <strong>₹${i.line_total_inr}</strong>
                  </div>`
                  )
                  .join("")}
                <div style="border-top:1px dashed var(--bt-border);margin-top:0.45rem;padding-top:0.45rem;display:flex;justify-content:space-between;font-size:0.82rem;color:var(--bt-muted);">
                  <span>Your Items Subtotal</span>
                  <span>₹${mySection.items_subtotal_inr}</span>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:0.82rem;color:var(--bt-muted);margin-top:0.2rem;">
                  <span>Packing (${foodCount} food item${foodCount === 1 ? "" : "s"} × ₹10; drinks free)</span>
                  <span>₹${mySection.packaging_fee_inr}</span>
                </div>
                <div style="border-top:1px solid var(--bt-border);margin-top:0.45rem;padding-top:0.45rem;display:flex;justify-content:space-between;font-size:1rem;font-weight:850;">
                  <span>Final Payable Amount</span>
                  <span style="color:var(--bt-primary);">₹${mySection.payable_amount_inr}</span>
                </div>
              </div>

              ${
                !group.checkout_unlocked
                  ? `<div style="padding:0.8rem;background:var(--bt-danger-bg);color:var(--bt-danger);border-radius:8px;font-size:0.82rem;font-weight:700;">
                      Checkout locked until group reaches ₹350 (₹${group.remaining_to_minimum_inr} remaining).
                    </div>`
                  : isMySharePaid
                  ? `<div style="padding:0.85rem;background:var(--bt-primary-soft);color:var(--bt-primary);border-radius:8px;font-size:0.84rem;">
                      <strong>Payment Verified</strong> · Ref: <code>${escapeHtml(myPay.gateway_payment_id)}</code>
                    </div>`
                  : `
                <div class="bt-form-group">
                  <label for="pay-method-select" class="bt-label">Payment Mode</label>
                  <select id="pay-method-select" class="bt-select" data-action="change-pay-method">
                    <option value="upi_qr" ${state.paymentDraft.method === "upi_qr" ? "selected" : ""}>UPI QR Scan</option>
                    <option value="upi_id" ${state.paymentDraft.method === "upi_id" ? "selected" : ""}>UPI ID Collect</option>
                    <option value="razorpay" ${state.paymentDraft.method === "razorpay" ? "selected" : ""}>Razorpay Checkout</option>
                  </select>
                </div>
                ${
                  state.paymentDraft.method === "upi_id"
                    ? `<div class="bt-form-group">
                        <label for="upi-vpa-input" class="bt-label">Your UPI ID</label>
                        <input id="upi-vpa-input" type="text" class="bt-input" value="${escapeHtml(state.paymentDraft.upiVpa)}" placeholder="yourname@okaxis" data-action="input-upi-vpa" />
                      </div>`
                    : ""
                }
                <button type="button" class="bt-btn bt-btn-primary" style="width:100%;margin-bottom:0.9rem;" data-action="initiate-payment" data-group-id="${escapeHtml(group.id)}">
                  Pay ₹${mySection.payable_amount_inr} via ${state.paymentDraft.method === "upi_qr" ? "UPI QR" : state.paymentDraft.method === "upi_id" ? "UPI ID" : "Razorpay"}
                </button>

                ${
                  myPay && myPay.gateway_order_id
                    ? `<div style="border:1px solid var(--bt-charcoal);border-radius:10px;padding:0.9rem;background:#FAFAFA;">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.55rem;">
                          <span class="bt-badge bt-badge-dark">${escapeHtml(myPay.gateway_order_id)}</span>
                          <span class="bt-badge bt-badge-warning">PENDING WEBHOOK</span>
                        </div>
                        <div style="display:flex;gap:0.85rem;align-items:center;flex-wrap:wrap;margin-bottom:0.75rem;">
                          ${renderUpiQrSvg(`upi://pay?tr=${myPay.gateway_order_id}&am=${mySection.payable_amount_inr}`)}
                          <div style="flex:1;min-width:180px;font-size:0.76rem;color:var(--bt-muted);">
                            Payment stays <strong>pending</strong> until the Razorpay/UPI gateway webhook confirms it on the server.
                          </div>
                        </div>
                        ${
                          myPay.sandbox_webhook_helper
                            ? `<div style="display:flex;gap:0.45rem;flex-wrap:wrap;">
                                <button type="button" class="bt-btn bt-btn-dark bt-btn-sm" data-action="simulate-webhook"
                                  data-order-id="${escapeHtml(myPay.sandbox_webhook_helper.gateway_order_id)}"
                                  data-payment-id="${escapeHtml(myPay.sandbox_webhook_helper.sample_payment_id)}"
                                  data-outcome="paid"
                                  data-signature="${escapeHtml(myPay.sandbox_webhook_helper.paid_signature)}">
                                  Confirm Gateway Webhook (Paid ₹${mySection.payable_amount_inr})
                                </button>
                                <button type="button" class="bt-btn bt-btn-danger bt-btn-sm" data-action="simulate-webhook"
                                  data-order-id="${escapeHtml(myPay.sandbox_webhook_helper.gateway_order_id)}"
                                  data-payment-id="${escapeHtml(myPay.sandbox_webhook_helper.sample_payment_id)}"
                                  data-outcome="failed"
                                  data-signature="${escapeHtml(myPay.sandbox_webhook_helper.failed_signature)}">
                                  Simulate Failure
                                </button>
                              </div>`
                            : ""
                        }
                      </div>`
                    : ""
                }
              `
              }
            `
            }
          </div>

          <!-- RIGHT: Group Payment Ledger -->
          <div class="bt-card">
            <h3 style="margin:0 0 0.65rem;font-size:1.08rem;font-weight:850;">
              Participant Payments (${group.paid_verified_count} / ${group.active_ordering_count} Paid)
            </h3>
            <p style="margin:0 0 0.85rem;font-size:0.78rem;color:var(--bt-muted);">
              The group order is submitted to Grains &amp; Gossip only after all ordering students complete verified payment.
            </p>
            <div style="display:flex;flex-direction:column;gap:0.5rem;">
              ${group.participants
                .map((p) => {
                  const pay = p.payment;
                  const verifiedPaid =
                    pay && pay.status === "paid" && pay.verified_by_server === 1;
                  const statusText =
                    p.items_subtotal_inr === 0
                      ? "No items"
                      : verifiedPaid
                      ? "PAID"
                      : pay && pay.status === "failed"
                      ? "FAILED"
                      : "PENDING";
                  const badgeCls =
                    p.items_subtotal_inr === 0
                      ? "bt-badge-dark"
                      : verifiedPaid
                      ? "bt-badge-green"
                      : pay && pay.status === "failed"
                      ? "bt-badge-danger"
                      : "bt-badge-warning";

                  return `<div style="display:flex;justify-content:space-between;align-items:center;padding:0.65rem;border:1px solid var(--bt-border);border-radius:8px;background:var(--bt-bg);">
                    <div>
                      <div style="font-weight:800;font-size:0.86rem;">${escapeHtml(p.student_name)} (${escapeHtml(p.room_number)})</div>
                      <div style="font-size:0.75rem;color:var(--bt-muted);">
                        Items: ₹${p.items_subtotal_inr} + Packing: ₹${p.packaging_fee_inr} = <strong>₹${p.payable_amount_inr}</strong>
                      </div>
                    </div>
                    <span class="bt-badge ${badgeCls}">${escapeHtml(statusText)}</span>
                  </div>`;
                })
                .join("")}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // ==========================================================================
  // STUDENT ACCOUNT & ALERTS VIEWS
  // ==========================================================================

  function renderAccountView() {
    const dash = state.dashboard;
    if (!state.currentUser || !dash) {
      return `<div class="bt-container" style="padding:2rem 0;"><div class="bt-card">Please log in to view your account.</div></div>`;
    }

    return `
      <div class="bt-container" style="padding:1.5rem 1.25rem 3rem;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem;margin-bottom:1.25rem;">
          <div>
            <button type="button" class="bt-btn bt-btn-outline bt-btn-sm" data-action="nav-view" data-view="store">← Back to Menu</button>
            <h2 style="margin:0.5rem 0 0;font-size:1.35rem;font-weight:850;">
              ${escapeHtml(dash.user.student_name)} (${escapeHtml(dash.user.room_number)})
            </h2>
            <div style="font-size:0.82rem;color:var(--bt-muted);">
              ${escapeHtml(dash.user.college_email)} · ID: ${escapeHtml(dash.user.student_id)} · Tower 3 Boys Hostel
            </div>
          </div>
          <button type="button" class="bt-btn bt-btn-danger bt-btn-sm" data-action="logout">Log Out</button>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:0.85rem;margin-bottom:1.25rem;">
          <div class="bt-card">
            <div style="font-size:0.74rem;color:var(--bt-muted);font-weight:700;">ACTIVE GROUPS</div>
            <div style="font-size:1.6rem;font-weight:900;">${dash.active_groups.length}</div>
          </div>
          <div class="bt-card">
            <div style="font-size:0.74rem;color:var(--bt-muted);font-weight:700;">PERSONAL SPENDING</div>
            <div style="font-size:1.6rem;font-weight:900;color:var(--bt-primary);">₹${dash.personal_spending_inr}</div>
          </div>
          <div class="bt-card">
            <div style="font-size:0.74rem;color:var(--bt-muted);font-weight:700;">PENDING PAYMENTS</div>
            <div style="font-size:1.6rem;font-weight:900;">${dash.pending_payments.length}</div>
          </div>
        </div>

        <div class="bt-workspace-grid">
          <div class="bt-card">
            <h3 style="margin:0 0 0.65rem;font-size:1.05rem;font-weight:850;">Your Groups</h3>
            ${
              dash.active_groups.length === 0
                ? `<div style="font-size:0.83rem;color:var(--bt-muted);">No active groups yet.</div>`
                : dash.active_groups
                    .map(
                      (g) => `
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:0.65rem;border:1px solid var(--bt-border);border-radius:8px;margin-bottom:0.45rem;">
                      <div>
                        <div style="font-weight:800;font-size:0.86rem;">${escapeHtml(g.name)} (${escapeHtml(g.id)})</div>
                        <div style="font-size:0.75rem;color:var(--bt-muted);">Cart: ₹${g.shared_cart_total_inr}/₹350 · ${escapeHtml(g.status_label)}</div>
                      </div>
                      <button type="button" class="bt-btn bt-btn-outline bt-btn-sm" data-action="select-group-and-open-cart" data-group-id="${escapeHtml(g.id)}">Open</button>
                    </div>`
                    )
                    .join("")
            }
          </div>

          <div class="bt-card">
            <h3 style="margin:0 0 0.65rem;font-size:1.05rem;font-weight:850;">Your Selected Items</h3>
            ${
              dash.selected_food.length === 0
                ? `<div style="font-size:0.83rem;color:var(--bt-muted);">No items added yet.</div>`
                : dash.selected_food
                    .map(
                      (sf) => `
                    <div style="display:flex;justify-content:space-between;padding:0.45rem 0;border-bottom:1px solid var(--bt-border);font-size:0.83rem;">
                      <span><strong>${escapeHtml(sf.item_name)}</strong> × ${sf.quantity} (${escapeHtml(sf.group_id)})</span>
                      <strong>₹${sf.line_total_inr}</strong>
                    </div>`
                    )
                    .join("")
            }
          </div>
        </div>
      </div>
    `;
  }

  function renderAlertsView() {
    return `
      <div class="bt-container" style="padding:1.5rem 1.25rem 3rem;max-width:780px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
          <div>
            <button type="button" class="bt-btn bt-btn-outline bt-btn-sm" data-action="nav-view" data-view="store">← Back to Menu</button>
            <h2 style="margin:0.5rem 0 0;font-size:1.35rem;font-weight:850;">Alerts</h2>
          </div>
          <button type="button" class="bt-btn bt-btn-outline bt-btn-sm" data-action="mark-all-read">Mark All Read</button>
        </div>

        <div style="display:flex;flex-direction:column;gap:0.5rem;">
          ${
            state.notifications.length === 0
              ? `<div class="bt-card">No alerts yet.</div>`
              : state.notifications
                  .map(
                    (n) => `
                  <div class="bt-card" style="padding:0.9rem;border-left:4px solid ${n.is_read ? "var(--bt-border)" : "var(--bt-primary)"};">
                    <div style="display:flex;justify-content:space-between;font-size:0.88rem;font-weight:800;">
                      <span>${escapeHtml(n.title)}</span>
                      <span style="font-size:0.72rem;color:var(--bt-muted);font-weight:600;">${escapeHtml(new Date(n.created_at).toLocaleTimeString())}</span>
                    </div>
                    <div style="font-size:0.8rem;color:var(--bt-muted);margin-top:0.25rem;">${escapeHtml(n.message)}</div>
                  </div>`
                  )
                  .join("")
          }
        </div>
      </div>
    `;
  }

  // ==========================================================================
  // MODALS (LOGIN / REGISTER, CREATE GROUP, JOIN GROUP)
  // ==========================================================================

  function renderModal() {
    if (!state.modal) return "";

    if (state.modal === "auth") {
      const emailDomain = (state.appMeta && state.appMeta.allowed_email_domain) || "college.edu";
      return `<div class="bt-modal-backdrop" data-action="close-modal-backdrop">
        <div class="bt-modal" role="dialog" aria-modal="true">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.85rem;">
            <div>
              <h3 style="margin:0;font-size:1.15rem;font-weight:850;">Tower 3 Boys Hostel Login</h3>
              <div style="font-size:0.76rem;color:var(--bt-muted);">t3.raatkadabba.in · Exclusively for Tower 3 Boys Hostel residents</div>
            </div>
            <button type="button" class="bt-btn bt-btn-outline bt-btn-sm" data-action="close-modal">✕</button>
          </div>

          <div style="display:flex;gap:0.45rem;margin-bottom:1rem;">
            <button type="button" class="bt-btn bt-btn-sm ${state.authModeTab === "login" ? "bt-btn-dark" : "bt-btn-outline"}" data-action="switch-auth-tab" data-auth-tab="login">
              Sign In
            </button>
            <button type="button" class="bt-btn bt-btn-sm ${state.authModeTab === "register" ? "bt-btn-dark" : "bt-btn-outline"}" data-action="switch-auth-tab" data-auth-tab="register">
              Create Student Account
            </button>
          </div>

          ${
            state.authModeTab === "login"
              ? `<form id="auth-login-form">
                  <div class="bt-form-group">
                    <label for="login-ident" class="bt-label">College Email, Student ID, or Room Number</label>
                    <input id="login-ident" name="identifier" type="text" class="bt-input" placeholder="name@${escapeHtml(emailDomain)} or T3-204" required />
                  </div>
                  <div class="bt-form-group">
                    <label for="login-pass" class="bt-label">Password</label>
                    <input id="login-pass" name="password" type="password" class="bt-input" required />
                  </div>
                  <button type="submit" class="bt-btn bt-btn-primary" style="width:100%;">Sign In</button>
                </form>`
              : `<form id="auth-register-form">
                  <div class="bt-form-group">
                    <label for="reg-name" class="bt-label">Full Name</label>
                    <input id="reg-name" name="student_name" type="text" class="bt-input" placeholder="Your full name" required />
                  </div>
                  <div class="bt-form-group">
                    <label for="reg-email" class="bt-label">College Email (@${escapeHtml(emailDomain)})</label>
                    <input id="reg-email" name="college_email" type="email" class="bt-input" placeholder="yourname@${escapeHtml(emailDomain)}" required />
                  </div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.65rem;">
                    <div class="bt-form-group">
                      <label for="reg-sid" class="bt-label">Student ID / Roll No.</label>
                      <input id="reg-sid" name="student_id" type="text" class="bt-input" placeholder="2024CS101" required />
                    </div>
                    <div class="bt-form-group">
                      <label for="reg-room" class="bt-label">Tower 3 Room Number</label>
                      <input id="reg-room" name="room_number" type="text" class="bt-input" placeholder="T3-204" required />
                    </div>
                  </div>
                  <div class="bt-form-group">
                    <label for="reg-tower" class="bt-label">Hostel</label>
                    <select id="reg-tower" name="tower" class="bt-select">
                      <option value="Tower 3" selected>Tower 3 Boys Hostel (Eligible)</option>
                      <option value="Tower 1">Other Hostel (Restricted)</option>
                    </select>
                  </div>
                  <div class="bt-form-group">
                    <label for="reg-pass" class="bt-label">Password</label>
                    <input id="reg-pass" name="password" type="password" class="bt-input" minlength="4" required />
                  </div>
                  <button type="submit" class="bt-btn bt-btn-primary" style="width:100%;">Verify Tower 3 &amp; Register</button>
                </form>`
          }
        </div>
      </div>`;
    }

    if (state.modal === "createGroup") {
      return `<div class="bt-modal-backdrop" data-action="close-modal-backdrop">
        <div class="bt-modal" role="dialog" aria-modal="true">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.85rem;">
            <h3 style="margin:0;font-size:1.15rem;font-weight:850;">Start a Tower 3 Group Order</h3>
            <button type="button" class="bt-btn bt-btn-outline bt-btn-sm" data-action="close-modal">✕</button>
          </div>
          <form id="create-group-form">
            <div class="bt-form-group">
              <label for="cg-name" class="bt-label">Group Order Name</label>
              <input id="cg-name" name="name" type="text" class="bt-input" placeholder="e.g. 2nd Floor Wing-A Night Order" required />
            </div>
            <div class="bt-form-group">
              <label for="cg-cafe" class="bt-label">Cafe</label>
              <input id="cg-cafe" type="text" class="bt-input" value="Grains and Gossip (Min ₹350 · Hostel Reception Pickup)" disabled />
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.65rem;">
              <div class="bt-form-group">
                <label for="cg-deadline" class="bt-label">Deadline (Minutes)</label>
                <input id="cg-deadline" name="deadline_minutes" type="number" min="5" max="180" class="bt-input" value="25" required />
              </div>
              <div class="bt-form-group">
                <label for="cg-limit" class="bt-label">Max Students (Optional)</label>
                <input id="cg-limit" name="participant_limit" type="number" min="2" max="20" class="bt-input" placeholder="6" />
              </div>
            </div>
            <div style="display:flex;justify-content:flex-end;gap:0.5rem;">
              <button type="button" class="bt-btn bt-btn-outline" data-action="close-modal">Cancel</button>
              <button type="submit" class="bt-btn bt-btn-primary">Create Group</button>
            </div>
          </form>
        </div>
      </div>`;
    }

    if (state.modal === "joinByCode") {
      return `<div class="bt-modal-backdrop" data-action="close-modal-backdrop">
        <div class="bt-modal" role="dialog" aria-modal="true">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.85rem;">
            <h3 style="margin:0;font-size:1.15rem;font-weight:850;">Join Group Order</h3>
            <button type="button" class="bt-btn bt-btn-outline bt-btn-sm" data-action="close-modal">✕</button>
          </div>
          <form id="join-code-form">
            <div class="bt-form-group">
              <label for="jc-id" class="bt-label">Group ID or t3.raatkadabba.in Link</label>
              <input id="jc-id" name="group_id" type="text" class="bt-input" placeholder="RKD-T3-XXXX" required />
            </div>
            <div style="display:flex;justify-content:flex-end;gap:0.5rem;">
              <button type="button" class="bt-btn bt-btn-outline" data-action="close-modal">Cancel</button>
              <button type="submit" class="bt-btn bt-btn-primary">Join Group</button>
            </div>
          </form>
        </div>
      </div>`;
    }

    return "";
  }

  function renderFloatingCartBar() {
    if (state.activeView !== "store" || state.cartDrawerOpen) return "";
    const group = getActiveGroup();
    if (!group || group.total_item_count === 0) return "";
    const unlocked = group.checkout_unlocked;
    return `
      <div class="bt-floating-cart" data-action="toggle-cart-drawer" role="button" tabindex="0">
        <div>
          <div style="font-size:0.86rem;font-weight:800;">
            ${group.total_item_count} item${group.total_item_count === 1 ? "" : "s"} · ₹${group.shared_cart_total_inr} / ₹${group.minimum_cart_inr}
          </div>
          <div style="font-size:0.74rem;opacity:0.9;">
            ${unlocked ? "₹350 minimum reached · Ready to pay your share" : `Add ₹${group.remaining_to_minimum_inr} more to unlock checkout`}
          </div>
        </div>
        <div style="font-weight:800;font-size:0.86rem;white-space:nowrap;">
          View Cart ›
        </div>
      </div>
    `;
  }

  function render() {
    const appEl = document.getElementById("app");
    const modalEl = document.getElementById("modal-root");
    if (!appEl || !state.appMeta) return;

    let mainView = "";
    if (state.activeView === "store") mainView = renderStorefrontView();
    else if (state.activeView === "checkout") mainView = renderCheckoutView();
    else if (state.activeView === "account") mainView = renderAccountView();
    else if (state.activeView === "alerts") mainView = renderAlertsView();

    appEl.innerHTML = `
      ${renderHeader()}
      <main>${mainView}</main>
      ${renderFloatingCartBar()}
      ${renderCartDrawer()}
    `;
    if (modalEl) modalEl.innerHTML = renderModal();
  }

  // ==========================================================================
  // EVENT DELEGATION
  // ==========================================================================

  document.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-action]");
    if (!btn) return;
    const action = btn.getAttribute("data-action");

    try {
      if (action === "nav-view") {
        state.activeView = btn.getAttribute("data-view");
        state.cartDrawerOpen = false;
        render();
        return;
      }

      if (action === "scroll-menu") {
        const el = document.getElementById("menu-anchor");
        if (el) el.scrollIntoView({ behavior: "smooth" });
        return;
      }

      if (action === "toggle-cart-drawer") {
        state.cartDrawerOpen = !state.cartDrawerOpen;
        render();
        return;
      }

      if (action === "close-cart-drawer" || (action === "close-drawer-backdrop" && e.target === btn)) {
        state.cartDrawerOpen = false;
        render();
        return;
      }

      if (action === "open-modal") {
        state.modal = btn.getAttribute("data-modal");
        render();
        return;
      }

      if (action === "open-create-group") {
        if (!requireLoginOrRun()) return;
        state.modal = "createGroup";
        render();
        return;
      }

      if (action === "close-modal" || (action === "close-modal-backdrop" && e.target === btn)) {
        state.modal = null;
        render();
        return;
      }

      if (action === "switch-auth-tab") {
        state.authModeTab = btn.getAttribute("data-auth-tab");
        render();
        return;
      }

      if (action === "logout") {
        state.currentUser = null;
        state.dashboard = null;
        state.notifications = [];
        state.activeView = "store";
        localStorage.removeItem("bt_user_id");
        await loadBootstrap("");
        showToast("Signed Out");
        return;
      }

      if (action === "filter-category") {
        state.selectedCategory = btn.getAttribute("data-category");
        render();
        return;
      }

      if (action === "filter-diet") {
        state.dietFilter = btn.getAttribute("data-diet");
        render();
        return;
      }

      if (action === "toggle-under100") {
        state.priceFilter = state.priceFilter === "under100" ? "all" : "under100";
        render();
        return;
      }

      if (action === "copy-share-link") {
        const gid = btn.getAttribute("data-group-id");
        const domain = (state.appMeta && state.appMeta.custom_domain) || "https://t3.raatkadabba.in";
        const url = `${domain}/?group=${gid}`;
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(url).catch(() => {});
        }
        showToast("Invite Link Copied", url);
        return;
      }

      if (action === "select-group-and-open-cart") {
        state.activeGroupId = btn.getAttribute("data-group-id");
        state.activeView = "store";
        state.cartDrawerOpen = true;
        render();
        return;
      }

      if (action === "join-group") {
        if (!requireLoginOrRun()) return;
        const gid = btn.getAttribute("data-group-id");
        await api(`/api/groups/${encodeURIComponent(gid)}/join`, {
          method: "POST",
          body: { strict: true },
        });
        state.activeGroupId = gid;
        state.cartDrawerOpen = true;
        await loadBootstrap(state.currentUser.id);
        showToast(`Joined ${gid}`);
        return;
      }

      if (action === "add-to-cart") {
        if (!requireLoginOrRun()) return;
        let activeGroup = getActiveGroup();
        if (!activeGroup) {
          state.modal = "createGroup";
          render();
          showToast("Start a Group First", "Create a Tower 3 group order to add items.");
          return;
        }
        const itemId = btn.getAttribute("data-item-id");
        const res = await api(
          `/api/groups/${encodeURIComponent(activeGroup.id)}/cart`,
          {
            method: "POST",
            body: { menu_item_id: itemId, quantity: 1, mode: "delta" },
          }
        );
        await loadBootstrap(state.currentUser.id);
        const rem = res.group.remaining_to_minimum_inr;
        showToast(
          "Added to Shared Cart",
          rem === 0
            ? `₹${res.group.shared_cart_total_inr} total — ₹350 minimum reached!`
            : `₹${res.group.shared_cart_total_inr}/₹350 (₹${rem} more needed)`
        );
        return;
      }

      if (action === "cart-delta") {
        if (!requireLoginOrRun()) return;
        const gid = btn.getAttribute("data-group-id");
        const itemId = btn.getAttribute("data-item-id");
        const delta = parseInt(btn.getAttribute("data-delta"), 10);
        await api(`/api/groups/${encodeURIComponent(gid)}/cart`, {
          method: "POST",
          body: { menu_item_id: itemId, quantity: delta, mode: "delta" },
        });
        await loadBootstrap(state.currentUser.id);
        return;
      }

      if (action === "lock-checkout") {
        if (!requireLoginOrRun()) return;
        const gid = btn.getAttribute("data-group-id");
        await api(`/api/groups/${encodeURIComponent(gid)}/lock-checkout`, {
          method: "POST",
          body: {},
        });
        state.cartDrawerOpen = false;
        state.activeView = "checkout";
        await loadBootstrap(state.currentUser.id);
        showToast("Cart Frozen", "Each participant can now pay their own share.");
        return;
      }

      if (action === "go-checkout") {
        state.cartDrawerOpen = false;
        state.activeView = "checkout";
        render();
        return;
      }

      if (action === "reopen-cart") {
        const gid = btn.getAttribute("data-group-id");
        await api(`/api/groups/${encodeURIComponent(gid)}/reopen-cart`, {
          method: "POST",
          body: {},
        });
        await loadBootstrap(state.currentUser.id);
        showToast("Cart Reopened");
        return;
      }

      if (action === "initiate-payment") {
        const gid = btn.getAttribute("data-group-id");
        const res = await api(
          `/api/groups/${encodeURIComponent(gid)}/payments/initiate`,
          {
            method: "POST",
            body: {
              method: state.paymentDraft.method,
              upi_vpa: state.paymentDraft.upiVpa,
            },
          }
        );
        await loadBootstrap(state.currentUser.id);
        showToast(
          `Order Created (${res.payment_intent.gateway_order_id})`,
          "Confirm via gateway webhook below."
        );
        return;
      }

      if (action === "simulate-webhook") {
        const orderId = btn.getAttribute("data-order-id");
        const paymentId = btn.getAttribute("data-payment-id");
        const outcome = btn.getAttribute("data-outcome");
        const signature = btn.getAttribute("data-signature");
        await api("/api/payments/webhook", {
          method: "POST",
          body: {
            gateway_order_id: orderId,
            gateway_payment_id: paymentId,
            outcome,
            gateway_signature: signature,
          },
        });
        await loadBootstrap(state.currentUser.id);
        showToast(
          outcome === "paid" ? "Payment Verified" : "Payment Failed",
          orderId,
          outcome !== "paid"
        );
        return;
      }

      if (action === "place-cafe-order") {
        const gid = btn.getAttribute("data-group-id");
        await api(`/api/groups/${encodeURIComponent(gid)}/advance-status`, {
          method: "POST",
          body: { target_status: "order_placed" },
        });
        await loadBootstrap(state.currentUser.id);
        showToast("Order Submitted to Grains & Gossip!", "Collect from Tower 3 Boys Hostel Reception.");
        return;
      }

      if (action === "mark-all-read") {
        await api("/api/notifications/read", { method: "POST", body: {} });
        await loadBootstrap(state.currentUser.id);
        return;
      }
    } catch (err) {
      showToast("Error", err.message, true);
    }
  });

  document.addEventListener("change", (e) => {
    const el = e.target;
    if (el.getAttribute("data-action") === "change-pay-method") {
      state.paymentDraft.method = el.value;
      render();
    }
  });

  document.addEventListener("input", (e) => {
    const el = e.target;
    const action = el.getAttribute("data-action");
    if (action === "search-menu") {
      state.menuSearch = el.value;
      render();
      const input = document.getElementById("menu-search-input");
      if (input) {
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
      }
    } else if (action === "input-upi-vpa") {
      state.paymentDraft.upiVpa = el.value;
    }
  });

  document.addEventListener("submit", async (e) => {
    const form = e.target;
    e.preventDefault();

    try {
      if (form.id === "auth-login-form") {
        const fd = new FormData(form);
        const res = await api("/api/auth/login", {
          method: "POST",
          body: {
            identifier: fd.get("identifier"),
            password: fd.get("password"),
            tower: "Tower 3",
          },
        });
        state.modal = null;
        await loadBootstrap(res.user.id);
        showToast(`Signed in as ${res.user.student_name} (${res.user.room_number})`);
        return;
      }

      if (form.id === "auth-register-form") {
        const fd = new FormData(form);
        const res = await api("/api/auth/register", {
          method: "POST",
          body: {
            student_name: fd.get("student_name"),
            college_email: fd.get("college_email"),
            student_id: fd.get("student_id"),
            tower: fd.get("tower"),
            room_number: fd.get("room_number"),
            password: fd.get("password"),
          },
        });
        state.modal = null;
        await loadBootstrap(res.user.id);
        showToast(`Welcome ${res.user.student_name} (${res.user.room_number})`);
        return;
      }

      if (form.id === "create-group-form") {
        const fd = new FormData(form);
        const res = await api("/api/groups", {
          method: "POST",
          body: {
            name: fd.get("name"),
            deadline_minutes: parseInt(fd.get("deadline_minutes"), 10) || 25,
            participant_limit: fd.get("participant_limit") || null,
            cafe_name: "Grains and Gossip",
          },
        });
        state.modal = null;
        state.activeGroupId = res.group.id;
        state.cartDrawerOpen = true;
        await loadBootstrap(state.currentUser.id);
        showToast(`Created ${res.group.name} (${res.group.id})`);
        return;
      }

      if (form.id === "join-code-form") {
        if (!requireLoginOrRun()) return;
        const fd = new FormData(form);
        let raw = String(fd.get("group_id") || "").trim();
        if (raw.includes("group=")) {
          raw = raw.split("group=")[1].split("&")[0];
        }
        const gid = raw.toUpperCase();
        await api(`/api/groups/${encodeURIComponent(gid)}/join`, {
          method: "POST",
          body: { strict: false },
        });
        state.modal = null;
        state.activeGroupId = gid;
        state.cartDrawerOpen = true;
        await loadBootstrap(state.currentUser.id);
        showToast(`Joined ${gid}`);
        return;
      }
    } catch (err) {
      showToast("Error", err.message, true);
    }
  });

  loadBootstrap().then(() => {
    connectRealtimeSSE();
  });
})();
