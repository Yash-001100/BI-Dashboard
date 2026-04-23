DROP VIEW IF EXISTS analytics.vw_review_delivery_impact;
DROP VIEW IF EXISTS analytics.vw_delivery_performance;
DROP VIEW IF EXISTS analytics.vw_category_performance;
DROP VIEW IF EXISTS analytics.vw_state_performance;
DROP VIEW IF EXISTS analytics.vw_monthly_sales;
DROP VIEW IF EXISTS analytics.vw_kpi_summary;
DROP VIEW IF EXISTS analytics.fact_order_metrics;
DROP VIEW IF EXISTS analytics.fact_order_payments;
DROP VIEW IF EXISTS analytics.fact_order_items;
DROP VIEW IF EXISTS analytics.fact_orders;
DROP VIEW IF EXISTS analytics.dim_products;
DROP VIEW IF EXISTS analytics.dim_sellers;
DROP VIEW IF EXISTS analytics.dim_customers;
DROP VIEW IF EXISTS analytics.dim_dates;

CREATE VIEW analytics.dim_dates AS
SELECT
    d::DATE AS date_day,
    EXTRACT(YEAR FROM d)::INT AS year_num,
    EXTRACT(MONTH FROM d)::INT AS month_num,
    TO_CHAR(d, 'YYYY-MM') AS year_month,
    TO_CHAR(d, 'Month') AS month_name,
    EXTRACT(QUARTER FROM d)::INT AS quarter_num
FROM GENERATE_SERIES(
    (SELECT MIN(order_purchase_timestamp)::DATE FROM raw.orders),
    (SELECT MAX(order_purchase_timestamp)::DATE FROM raw.orders),
    INTERVAL '1 day'
) AS d;

CREATE VIEW analytics.dim_customers AS
SELECT
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    INITCAP(customer_city) AS customer_city,
    customer_state
FROM raw.customers;

CREATE VIEW analytics.dim_sellers AS
SELECT
    seller_id,
    seller_zip_code_prefix,
    INITCAP(seller_city) AS seller_city,
    seller_state
FROM raw.sellers;

CREATE VIEW analytics.dim_products AS
SELECT
    p.product_id,
    p.product_category_name,
    COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS product_category_name_english,
    p.product_name_lenght,
    p.product_description_lenght,
    p.product_photos_qty,
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm
FROM raw.products p
LEFT JOIN raw.product_category_translation t
    ON p.product_category_name = t.product_category_name;

CREATE VIEW analytics.fact_orders AS
SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_purchase_timestamp::DATE AS order_purchase_date,
    TO_CHAR(o.order_purchase_timestamp, 'YYYY-MM') AS order_month,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    CASE
        WHEN o.order_delivered_customer_date IS NOT NULL
        THEN (o.order_delivered_customer_date::DATE - o.order_purchase_timestamp::DATE)
    END AS delivery_days,
    CASE
        WHEN o.order_delivered_customer_date IS NOT NULL
         AND o.order_estimated_delivery_date IS NOT NULL
         AND o.order_delivered_customer_date::DATE > o.order_estimated_delivery_date::DATE
        THEN 1
        ELSE 0
    END AS is_delayed,
    CASE
        WHEN o.order_delivered_customer_date IS NOT NULL
         AND o.order_estimated_delivery_date IS NOT NULL
        THEN GREATEST(
            o.order_delivered_customer_date::DATE - o.order_estimated_delivery_date::DATE,
            0
        )
    END AS delay_days
FROM raw.orders o
LEFT JOIN raw.customers c
    ON o.customer_id = c.customer_id;

CREATE VIEW analytics.fact_order_items AS
SELECT
    oi.order_id,
    oi.order_item_id,
    fo.customer_id,
    fo.customer_unique_id,
    dc.customer_state,
    dc.customer_city,
    oi.product_id,
    dp.product_category_name_english,
    oi.seller_id,
    ds.seller_state,
    ds.seller_city,
    fo.order_status,
    fo.order_purchase_timestamp,
    fo.order_purchase_date,
    fo.order_month,
    fo.delivery_days,
    fo.is_delayed,
    fo.delay_days,
    oi.shipping_limit_date,
    oi.price,
    oi.freight_value,
    (oi.price + oi.freight_value) AS total_item_value
FROM raw.order_items oi
LEFT JOIN analytics.fact_orders fo
    ON oi.order_id = fo.order_id
LEFT JOIN analytics.dim_customers dc
    ON fo.customer_id = dc.customer_id
LEFT JOIN analytics.dim_products dp
    ON oi.product_id = dp.product_id
LEFT JOIN analytics.dim_sellers ds
    ON oi.seller_id = ds.seller_id;

CREATE VIEW analytics.fact_order_payments AS
SELECT
    op.order_id,
    fo.customer_id,
    fo.customer_unique_id,
    fo.order_purchase_date,
    fo.order_month,
    op.payment_sequential,
    op.payment_type,
    op.payment_installments,
    op.payment_value
FROM raw.order_payments op
LEFT JOIN analytics.fact_orders fo
    ON op.order_id = fo.order_id;

CREATE VIEW analytics.fact_order_metrics AS
SELECT
    fo.order_id,
    fo.customer_id,
    fo.customer_unique_id,
    dc.customer_state,
    dc.customer_city,
    fo.order_status,
    fo.order_purchase_timestamp,
    fo.order_purchase_date,
    fo.order_month,
    fo.delivery_days,
    fo.is_delayed,
    fo.delay_days,
    COUNT(oi.order_item_id) AS item_count,
    ROUND(COALESCE(SUM(oi.price), 0)::NUMERIC, 2) AS order_revenue,
    ROUND(COALESCE(SUM(oi.freight_value), 0)::NUMERIC, 2) AS order_freight_value,
    ROUND(COALESCE(SUM(oi.price + oi.freight_value), 0)::NUMERIC, 2) AS order_total_value
FROM analytics.fact_orders fo
LEFT JOIN raw.order_items oi
    ON fo.order_id = oi.order_id
LEFT JOIN analytics.dim_customers dc
    ON fo.customer_id = dc.customer_id
GROUP BY
    fo.order_id,
    fo.customer_id,
    fo.customer_unique_id,
    dc.customer_state,
    dc.customer_city,
    fo.order_status,
    fo.order_purchase_timestamp,
    fo.order_purchase_date,
    fo.order_month,
    fo.delivery_days,
    fo.is_delayed,
    fo.delay_days;

CREATE VIEW analytics.vw_kpi_summary AS
SELECT
    om.total_orders,
    om.unique_customers,
    om.total_revenue,
    om.avg_order_value,
    om.avg_delivery_days,
    om.delayed_order_pct,
    rv.avg_review_score
FROM (
    SELECT
        COUNT(DISTINCT order_id) AS total_orders,
        COUNT(DISTINCT customer_unique_id) AS unique_customers,
        ROUND(SUM(order_revenue)::NUMERIC, 2) AS total_revenue,
        ROUND(AVG(order_revenue)::NUMERIC, 2) AS avg_order_value,
        ROUND(AVG(delivery_days)::NUMERIC, 2) AS avg_delivery_days,
        ROUND(100.0 * AVG(is_delayed)::NUMERIC, 2) AS delayed_order_pct
    FROM analytics.fact_order_metrics
) om
CROSS JOIN (
    SELECT ROUND(AVG(review_score)::NUMERIC, 2) AS avg_review_score
    FROM raw.order_reviews
) rv;

CREATE VIEW analytics.vw_monthly_sales AS
SELECT
    order_month,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(order_revenue)::NUMERIC, 2) AS revenue,
    ROUND(AVG(order_revenue)::NUMERIC, 2) AS avg_order_value
FROM analytics.fact_order_metrics
GROUP BY order_month
ORDER BY order_month;

CREATE VIEW analytics.vw_state_performance AS
SELECT
    customer_state,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(order_revenue)::NUMERIC, 2) AS revenue,
    ROUND(AVG(order_revenue)::NUMERIC, 2) AS avg_order_value,
    ROUND(AVG(delivery_days)::NUMERIC, 2) AS avg_delivery_days,
    ROUND(100.0 * AVG(is_delayed)::NUMERIC, 2) AS delayed_order_pct
FROM analytics.fact_order_metrics
GROUP BY customer_state
ORDER BY revenue DESC;

CREATE VIEW analytics.vw_category_performance AS
SELECT
    product_category_name_english,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(price)::NUMERIC, 2) AS revenue,
    ROUND(SUM(freight_value)::NUMERIC, 2) AS freight_cost,
    ROUND(AVG(price)::NUMERIC, 2) AS avg_item_value
FROM analytics.fact_order_items
GROUP BY product_category_name_english
ORDER BY revenue DESC;

CREATE VIEW analytics.vw_delivery_performance AS
SELECT
    seller_state,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(AVG(delivery_days)::NUMERIC, 2) AS avg_delivery_days,
    ROUND(100.0 * AVG(is_delayed)::NUMERIC, 2) AS delayed_order_pct,
    ROUND(AVG(freight_value)::NUMERIC, 2) AS avg_freight_value
FROM analytics.fact_order_items
GROUP BY seller_state
ORDER BY delayed_order_pct DESC, avg_delivery_days DESC;

CREATE VIEW analytics.vw_review_delivery_impact AS
SELECT
    r.review_score,
    COUNT(DISTINCT r.order_id) AS total_orders,
    ROUND(AVG(o.delivery_days)::NUMERIC, 2) AS avg_delivery_days,
    ROUND(100.0 * AVG(o.is_delayed)::NUMERIC, 2) AS delayed_order_pct
FROM raw.order_reviews r
LEFT JOIN analytics.fact_orders o
    ON r.order_id = o.order_id
GROUP BY r.review_score
ORDER BY r.review_score;
