create table customers (
  id bigint generated always as identity primary key,
  email text not null unique,
  created_at timestamptz not null default now()
);

create table orders (
  id bigint generated always as identity primary key,
  customer_id bigint not null references customers(id) on delete cascade,
  total numeric(10,2) not null,
  created_at timestamptz not null default now()
);

create table jobs (
  id bigint generated always as identity primary key,
  order_id bigint not null references orders(id),
  amount numeric(10,2) not null,
  status text not null default 'pending',
  worker_id text,
  started_at timestamptz,
  receipt text,
  created_at timestamptz not null default now()
);
