CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS analytics;

DROP TABLE IF EXISTS raw.order_reviews;
DROP TABLE IF EXISTS raw.order_payments;
DROP TABLE IF EXISTS raw.order_items;
DROP TABLE IF EXISTS raw.orders;
DROP TABLE IF EXISTS raw.customers;
DROP TABLE IF EXISTS raw.products;
DROP TABLE IF EXISTS raw.sellers;
DROP TABLE IF EXISTS raw.geolocation;
DROP TABLE IF EXISTS raw.product_category_translation;

CREATE TABLE raw.customers (
    customer_id TEXT PRIMARY KEY,
    customer_unique_id TEXT,
    customer_zip_code_prefix TEXT,
    customer_city TEXT,
    customer_state TEXT
);

CREATE TABLE raw.orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT,
    order_status TEXT,
    order_purchase_timestamp TIMESTAMP,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);

CREATE TABLE raw.order_items (
    order_id TEXT,
    order_item_id INTEGER,
    product_id TEXT,
    seller_id TEXT,
    shipping_limit_date TIMESTAMP,
    price NUMERIC(12,2),
    freight_value NUMERIC(12,2),
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE raw.order_payments (
    order_id TEXT,
    payment_sequential INTEGER,
    payment_type TEXT,
    payment_installments INTEGER,
    payment_value NUMERIC(12,2),
    PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE raw.order_reviews (
    review_id TEXT,
    order_id TEXT,
    review_score INTEGER,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP
);

CREATE TABLE raw.products (
    product_id TEXT PRIMARY KEY,
    product_category_name TEXT,
    product_name_lenght INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty INTEGER,
    product_weight_g NUMERIC(12,2),
    product_length_cm NUMERIC(12,2),
    product_height_cm NUMERIC(12,2),
    product_width_cm NUMERIC(12,2)
);

CREATE TABLE raw.sellers (
    seller_id TEXT PRIMARY KEY,
    seller_zip_code_prefix TEXT,
    seller_city TEXT,
    seller_state TEXT
);

CREATE TABLE raw.geolocation (
    geolocation_zip_code_prefix TEXT,
    geolocation_lat NUMERIC(18,10),
    geolocation_lng NUMERIC(18,10),
    geolocation_city TEXT,
    geolocation_state TEXT
);

CREATE TABLE raw.product_category_translation (
    product_category_name TEXT PRIMARY KEY,
    product_category_name_english TEXT
);

CREATE INDEX IF NOT EXISTS idx_orders_customer_id
    ON raw.orders (customer_id);

CREATE INDEX IF NOT EXISTS idx_orders_purchase_timestamp
    ON raw.orders (order_purchase_timestamp);

CREATE INDEX IF NOT EXISTS idx_order_items_product_id
    ON raw.order_items (product_id);

CREATE INDEX IF NOT EXISTS idx_order_items_seller_id
    ON raw.order_items (seller_id);

CREATE INDEX IF NOT EXISTS idx_order_payments_order_id
    ON raw.order_payments (order_id);

CREATE INDEX IF NOT EXISTS idx_order_reviews_order_id
    ON raw.order_reviews (order_id);

CREATE INDEX IF NOT EXISTS idx_customers_state
    ON raw.customers (customer_state);

CREATE INDEX IF NOT EXISTS idx_sellers_state
    ON raw.sellers (seller_state);
