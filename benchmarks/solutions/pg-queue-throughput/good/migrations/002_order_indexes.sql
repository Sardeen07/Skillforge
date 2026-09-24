-- Postgres does not index foreign keys: the account page filters on customer_id.
create index orders_customer_id_idx on orders (customer_id);
-- Supports keyset pagination of the orders report.
create index orders_created_at_id_idx on orders (created_at desc, id desc);
