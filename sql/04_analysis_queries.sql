-- Executive overview
SELECT * FROM analytics.vw_kpi_summary;

SELECT * FROM analytics.vw_monthly_sales;

SELECT * FROM analytics.vw_state_performance;

SELECT * FROM analytics.vw_category_performance;

-- Customer analytics
SELECT
    customer_state,
    COUNT(DISTINCT customer_unique_id) AS unique_customers,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(price)::NUMERIC, 2) AS revenue
FROM analytics.fact_order_items
GROUP BY customer_state
ORDER BY revenue DESC;

SELECT
    customer_unique_id,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(price)::NUMERIC, 2) AS total_spend
FROM analytics.fact_order_items
GROUP BY customer_unique_id
HAVING COUNT(DISTINCT order_id) > 1
ORDER BY total_spend DESC
LIMIT 20;

-- Product and seller performance
SELECT
    seller_id,
    seller_state,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(price)::NUMERIC, 2) AS revenue
FROM analytics.fact_order_items
GROUP BY seller_id, seller_state
ORDER BY revenue DESC
LIMIT 20;

SELECT
    product_category_name_english,
    ROUND(SUM(price)::NUMERIC, 2) AS revenue,
    ROUND(SUM(freight_value)::NUMERIC, 2) AS freight_cost
FROM analytics.fact_order_items
GROUP BY product_category_name_english
ORDER BY revenue DESC;

-- Operations and delivery
SELECT * FROM analytics.vw_delivery_performance;

SELECT
    product_category_name_english,
    ROUND(AVG(delivery_days)::NUMERIC, 2) AS avg_delivery_days,
    ROUND(100.0 * AVG(is_delayed)::NUMERIC, 2) AS delayed_order_pct
FROM analytics.fact_order_items
GROUP BY product_category_name_english
ORDER BY delayed_order_pct DESC, avg_delivery_days DESC;

-- Customer satisfaction
SELECT
    review_score,
    COUNT(*) AS review_count
FROM raw.order_reviews
GROUP BY review_score
ORDER BY review_score;

SELECT * FROM analytics.vw_review_delivery_impact;

SELECT
    p.payment_type,
    ROUND(AVG(r.review_score)::NUMERIC, 2) AS avg_review_score,
    COUNT(DISTINCT p.order_id) AS total_orders
FROM analytics.fact_order_payments p
LEFT JOIN raw.order_reviews r
    ON p.order_id = r.order_id
GROUP BY p.payment_type
ORDER BY avg_review_score DESC;

-- Optional RFM starter
WITH customer_rfm AS (
    SELECT
        customer_unique_id,
        MAX(order_purchase_date) AS last_order_date,
        COUNT(DISTINCT order_id) AS frequency,
        SUM(price) AS monetary
    FROM analytics.fact_order_items
    GROUP BY customer_unique_id
)
SELECT
    customer_unique_id,
    (SELECT MAX(order_purchase_date) FROM analytics.fact_order_items) - last_order_date AS recency_days,
    frequency,
    ROUND(monetary::NUMERIC, 2) AS monetary
FROM customer_rfm
ORDER BY monetary DESC
LIMIT 50;
