# Raat Ka Dabba

Late-night shared food ordering web app for **Tower 3 Boys Hostel** (`t3.raatkadabba.in`), built for **Grains and Gossip** (10:00 PM – 3:00 AM).

## Key Rules & Features
- **Tower 3 Boys Hostel Only**: Registration and login enforce `@college.edu` student email and `T3-XXX` room numbers.
- **₹350 Minimum Shared Cart**: Students pool their individual cravings into one shared group cart; checkout unlocks at `₹350`.
- **Pay Only Your Own Share**: No equal splits. Each student pays only for their own items plus `₹10` per food container (drinks are free of packing charges).
- **Real Grains & Gossip Menu**: 58 items across 9 categories with All / Veg / Non-Veg / Under ₹100 filters and live search.
- **Slide-Over Shared Cart Drawer**: Live updates via Server-Sent Events (`/api/stream`), quick top-up suggestions below `₹350`, and individual UPI / Razorpay webhook-verified checkout.

## Run Locally

```bash
python3 server.py
# Open http://127.0.0.1:8765
```

## Run Self-Check Tests

```bash
python3 self_check.py
```
