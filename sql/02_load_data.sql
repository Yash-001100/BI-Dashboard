-- Run this file in psql after creating the tables.
-- These commands use \copy so the CSV files are read from your local machine.
-- Update the paths only if the project folder moves.
\encoding UTF8

TRUNCATE TABLE
    raw.customers,
    raw.orders,
    raw.order_items,
    raw.order_payments,
    raw.order_reviews,
    raw.products,
    raw.sellers,
    raw.geolocation,
    raw.product_category_translation;

\copy raw.customers FROM 'C:/Users/kalra/Downloads/Global Business Intelligence & Customer Analytics Platform/Important Dataset/olist_customers_dataset.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy raw.orders FROM 'C:/Users/kalra/Downloads/Global Business Intelligence & Customer Analytics Platform/Important Dataset/olist_orders_dataset.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy raw.order_items FROM 'C:/Users/kalra/Downloads/Global Business Intelligence & Customer Analytics Platform/Important Dataset/olist_order_items_dataset.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy raw.order_payments FROM 'C:/Users/kalra/Downloads/Global Business Intelligence & Customer Analytics Platform/Important Dataset/olist_order_payments_dataset.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy raw.order_reviews FROM 'C:/Users/kalra/Downloads/Global Business Intelligence & Customer Analytics Platform/Important Dataset/olist_order_reviews_dataset.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy raw.products FROM 'C:/Users/kalra/Downloads/Global Business Intelligence & Customer Analytics Platform/Important Dataset/olist_products_dataset.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy raw.sellers FROM 'C:/Users/kalra/Downloads/Global Business Intelligence & Customer Analytics Platform/Important Dataset/olist_sellers_dataset.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy raw.geolocation FROM 'C:/Users/kalra/Downloads/Global Business Intelligence & Customer Analytics Platform/Important Dataset/olist_geolocation_dataset.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy raw.product_category_translation FROM 'C:/Users/kalra/Downloads/Global Business Intelligence & Customer Analytics Platform/Important Dataset/product_category_name_translation.csv' WITH (FORMAT csv, HEADER true, NULL '')

SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM raw.customers
UNION ALL
SELECT 'orders', COUNT(*) FROM raw.orders
UNION ALL
SELECT 'order_items', COUNT(*) FROM raw.order_items
UNION ALL
SELECT 'order_payments', COUNT(*) FROM raw.order_payments
UNION ALL
SELECT 'order_reviews', COUNT(*) FROM raw.order_reviews
UNION ALL
SELECT 'products', COUNT(*) FROM raw.products
UNION ALL
SELECT 'sellers', COUNT(*) FROM raw.sellers
UNION ALL
SELECT 'geolocation', COUNT(*) FROM raw.geolocation
UNION ALL
SELECT 'product_category_translation', COUNT(*) FROM raw.product_category_translation;
