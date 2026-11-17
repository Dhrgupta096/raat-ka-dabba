-- ============================================================================
-- BiteTogether — Production PostgreSQL & Supabase Schema (Tower 3 Exclusively)
-- Cafe: Grains and Gossip | Minimum Shared Cart: ₹350 | Packing ₹10 per food item (drinks free)
-- ============================================================================

create extension if not exists "pgcrypto";

-- 1. PROFILES (Tower 3 Students Only)
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  student_name text not null check (char_length(trim(student_name)) >= 2),
  college_email text not null unique,
  student_id text not null unique,
  tower text not null default 'Tower 3' check (tower = 'Tower 3'),
  room_number text not null check (room_number ~ '^(T3-)?[0-9]{3}[A-Z]?$'),
  created_at timestamptz not null default now()
);

-- 2. MENU ITEMS (Grains and Gossip Cafe Menu)
create table if not exists public.menu_items (
  id text primary key,
  cafe_name text not null default 'Grains and Gossip' check (cafe_name = 'Grains and Gossip'),
  category text not null check (category in ('Rice & Noodles', 'Burgers', 'Pizza', 'Sandwiches', 'Pasta', 'Fries & Snacks', 'Starters', 'Juices & Shakes', 'Hot Drinks')),
  name text not null,
  price_inr integer not null check (price_inr > 0),
  is_drink boolean not null default false, -- drinks carry no packing charge
  is_veg boolean not null default true,
  is_available boolean not null default true,
  created_at timestamptz not null default now()
);

-- 3. GROUP ORDERS
create table if not exists public.group_orders (
  id text primary key, -- e.g. BT-T3-4821
  name text not null check (char_length(trim(name)) >= 3),
  cafe_name text not null default 'Grains and Gossip' check (cafe_name = 'Grains and Gossip'),
  creator_id uuid not null references public.profiles(id) on delete restrict,
  tower text not null default 'Tower 3' check (tower = 'Tower 3'),
  deadline timestamptz not null,
  participant_limit integer check (participant_limit is null or participant_limit >= 2),
  minimum_cart_inr integer not null default 350 check (minimum_cart_inr = 350),
  cart_frozen boolean not null default false,
  status text not null default 'collecting' check (
    status in (
      'collecting',
      'minimum_reached',
      'payments_completed',
      'order_placed',
      'preparing',
      'ready_for_pickup',
      'completed',
      'closed'
    )
  ),
  share_link text not null,
  created_at timestamptz not null default now()
);

-- 4. GROUP PARTICIPANTS (Prevent duplicate participation via unique constraint)
create table if not exists public.group_participants (
  id uuid primary key default gen_random_uuid(),
  group_id text not null references public.group_orders(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  joined_at timestamptz not null default now(),
  unique (group_id, user_id)
);

-- 5. CART ITEMS (Each student manages only their own items in the shared cart)
create table if not exists public.cart_items (
  id uuid primary key default gen_random_uuid(),
  group_id text not null references public.group_orders(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  menu_item_id text not null references public.menu_items(id) on delete restrict,
  quantity integer not null check (quantity > 0 and quantity <= 20),
  unit_price_inr integer not null check (unit_price_inr > 0),
  updated_at timestamptz not null default now(),
  unique (group_id, user_id, menu_item_id)
);

-- 6. PAYMENTS (Individual itemized payments; verified via Razorpay webhook/HMAC)
create table if not exists public.payments (
  id uuid primary key default gen_random_uuid(),
  group_id text not null references public.group_orders(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  items_subtotal_inr integer not null check (items_subtotal_inr > 0),
  packaging_fee_inr integer not null default 0 check (packaging_fee_inr >= 0),
  payable_amount_inr integer not null check (payable_amount_inr = items_subtotal_inr + packaging_fee_inr),
  method text not null check (method in ('upi_id', 'upi_qr', 'razorpay')),
  status text not null default 'pending' check (status in ('pending', 'paid', 'failed')),
  gateway_order_id text unique,
  gateway_payment_id text,
  gateway_signature text,
  verified_by_server boolean not null default false,
  created_at timestamptz not null default now(),
  verified_at timestamptz,
  unique (group_id, user_id)
);

-- 7. NOTIFICATIONS
create table if not exists public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  group_id text references public.group_orders(id) on delete cascade,
  event_type text not null check (
    event_type in (
      'group_joined',
      'food_added',
      'minimum_reached',
      'payment_pending',
      'deadline_approaching',
      'order_placed',
      'food_ready',
      'status_changed'
    )
  ),
  title text not null,
  message text not null,
  is_read boolean not null default false,
  created_at timestamptz not null default now()
);

-- 8. ORDER STATUS HISTORY
create table if not exists public.order_status_history (
  id uuid primary key default gen_random_uuid(),
  group_id text not null references public.group_orders(id) on delete cascade,
  status text not null,
  note text not null,
  changed_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now()
);

-- ============================================================================
-- SERVER-SIDE BUSINESS RULE TRIGGERS
-- ============================================================================

-- Enforce cart freeze & creator-only status rules on cart_items mutation
create or replace function public.enforce_cart_mutable()
returns trigger
language plpgsql
security definer
as $$
declare
  v_frozen boolean;
  v_status text;
  v_group_id text;
begin
  v_group_id := coalesce(new.group_id, old.group_id);
  select cart_frozen, status into v_frozen, v_status
  from public.group_orders
  where id = v_group_id;

  if v_frozen or v_status not in ('collecting', 'minimum_reached') then
    raise exception 'Cart is frozen for checkout or group is closed.';
  end if;
  return coalesce(new, old);
end;
$$;

drop trigger if exists trg_enforce_cart_mutable on public.cart_items;
create trigger trg_enforce_cart_mutable
before insert or update or delete on public.cart_items
for each row execute function public.enforce_cart_mutable();

-- Enforce ₹350 minimum & verified individual payments before order placement
create or replace function public.enforce_group_order_transitions()
returns trigger
language plpgsql
security definer
as $$
declare
  v_cart_total integer;
  v_unpaid_count integer;
begin
  select coalesce(sum(quantity * unit_price_inr), 0)
  into v_cart_total
  from public.cart_items
  where group_id = new.id;

  if new.status in ('minimum_reached', 'payments_completed', 'order_placed', 'preparing', 'ready_for_pickup', 'completed')
     and v_cart_total < 350 then
    raise exception 'Shared cart total (₹%) is below the ₹350 minimum for Grains and Gossip.', v_cart_total;
  end if;

  if new.status in ('payments_completed', 'order_placed', 'preparing', 'ready_for_pickup', 'completed') then
    -- Every participant with items in the cart must have a server-verified 'paid' payment
    select count(distinct ci.user_id)
    into v_unpaid_count
    from public.cart_items ci
    left join public.payments p
      on p.group_id = ci.group_id
      and p.user_id = ci.user_id
      and p.status = 'paid'
      and p.verified_by_server = true
    where ci.group_id = new.id
      and p.id is null;

    if v_unpaid_count > 0 then
      raise exception 'Cannot place order: % participant(s) have unpaid or unverified shares.', v_unpaid_count;
    end if;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_enforce_group_order_transitions on public.group_orders;
create trigger trg_enforce_group_order_transitions
before update of status on public.group_orders
for each row execute function public.enforce_group_order_transitions();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

alter table public.profiles enable row level security;
alter table public.menu_items enable row level security;
alter table public.group_orders enable row level security;
alter table public.group_participants enable row level security;
alter table public.cart_items enable row level security;
alter table public.payments enable row level security;
alter table public.notifications enable row level security;
alter table public.order_status_history enable row level security;

-- Helper: verify current user is a registered Tower 3 student
create or replace function public.is_tower3_student()
returns boolean
language sql
stable
security definer
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and tower = 'Tower 3'
  );
$$;

-- Profiles: Tower 3 students can view Tower 3 peers; update only own profile
create policy "Tower 3 view profiles" on public.profiles
  for select using (public.is_tower3_student());

create policy "Insert own Tower 3 profile" on public.profiles
  for insert with check (auth.uid() = id and tower = 'Tower 3');

-- Menu items: readable by all Tower 3 students
create policy "Tower 3 read menu" on public.menu_items
  for select using (public.is_tower3_student());

-- Group orders: Tower 3 can read/create; only group creator can update/close
create policy "Tower 3 read groups" on public.group_orders
  for select using (public.is_tower3_student());

create policy "Tower 3 create groups" on public.group_orders
  for insert with check (public.is_tower3_student() and creator_id = auth.uid() and tower = 'Tower 3');

create policy "Creator updates group" on public.group_orders
  for update using (creator_id = auth.uid());

-- Group participants: Tower 3 students can join; cannot join on someone else's behalf
create policy "Tower 3 read participants" on public.group_participants
  for select using (public.is_tower3_student());

create policy "Student joins group" on public.group_participants
  for insert with check (public.is_tower3_student() and user_id = auth.uid());

-- Cart items: Everyone in Tower 3 can view shared cart; students can ONLY insert/update/delete THEIR OWN items
create policy "Tower 3 view shared cart" on public.cart_items
  for select using (public.is_tower3_student());

create policy "Student adds own cart item" on public.cart_items
  for insert with check (public.is_tower3_student() and user_id = auth.uid());

create policy "Student updates own cart item" on public.cart_items
  for update using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy "Student deletes own cart item" on public.cart_items
  for delete using (user_id = auth.uid());

-- Payments: Students view group payment statuses; initiate only own pending record.
-- Marking 'paid' + verified_by_server=true is restricted to service_role webhook handler.
create policy "Tower 3 view group payments" on public.payments
  for select using (public.is_tower3_student());

create policy "Student creates own pending payment" on public.payments
  for insert with check (
    public.is_tower3_student()
    and user_id = auth.uid()
    and status = 'pending'
    and verified_by_server = false
  );

-- Notifications: strictly own notifications
create policy "Student reads own notifications" on public.notifications
  for select using (user_id = auth.uid());

create policy "Student marks own notifications read" on public.notifications
  for update using (user_id = auth.uid());

-- Order status history: readable by Tower 3 students
create policy "Tower 3 view order history" on public.order_status_history
  for select using (public.is_tower3_student());

-- Enable Supabase Realtime on live tables
alter publication supabase_realtime add table public.group_orders;
alter publication supabase_realtime add table public.group_participants;
alter publication supabase_realtime add table public.cart_items;
alter publication supabase_realtime add table public.payments;
alter publication supabase_realtime add table public.notifications;
alter publication supabase_realtime add table public.order_status_history;
