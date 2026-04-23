from __future__ import annotations

import os
from io import BytesIO
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine


ORDER_LEVEL_SQL = """
WITH review_scores AS (
    SELECT
        order_id,
        AVG(review_score)::NUMERIC(10, 2) AS review_score
    FROM raw.order_reviews
    GROUP BY order_id
),
payment_types AS (
    SELECT
        order_id,
        STRING_AGG(DISTINCT payment_type, ', ' ORDER BY payment_type) AS payment_types
    FROM analytics.fact_order_payments
    GROUP BY order_id
)
SELECT
    om.order_id,
    om.customer_id,
    om.customer_unique_id,
    om.customer_state,
    om.customer_city,
    om.order_status,
    om.order_purchase_date,
    om.order_month,
    om.delivery_days,
    om.is_delayed,
    om.delay_days,
    om.item_count,
    om.order_revenue,
    om.order_freight_value,
    om.order_total_value,
    rs.review_score,
    COALESCE(pt.payment_types, 'Unknown') AS payment_types
FROM analytics.fact_order_metrics om
LEFT JOIN review_scores rs
    ON om.order_id = rs.order_id
LEFT JOIN payment_types pt
    ON om.order_id = pt.order_id;
"""


ITEM_LEVEL_SQL = """
WITH review_scores AS (
    SELECT
        order_id,
        AVG(review_score)::NUMERIC(10, 2) AS review_score
    FROM raw.order_reviews
    GROUP BY order_id
),
payment_types AS (
    SELECT
        order_id,
        STRING_AGG(DISTINCT payment_type, ', ' ORDER BY payment_type) AS payment_types
    FROM analytics.fact_order_payments
    GROUP BY order_id
)
SELECT
    foi.order_id,
    foi.order_item_id,
    foi.customer_id,
    foi.customer_unique_id,
    foi.customer_state,
    foi.customer_city,
    foi.product_id,
    COALESCE(foi.product_category_name_english, 'unknown') AS product_category_name_english,
    foi.seller_id,
    foi.seller_state,
    foi.seller_city,
    foi.order_status,
    foi.order_purchase_date,
    foi.order_month,
    foi.delivery_days,
    foi.is_delayed,
    foi.delay_days,
    foi.price,
    foi.freight_value,
    foi.total_item_value,
    rs.review_score,
    COALESCE(pt.payment_types, 'Unknown') AS payment_types
FROM analytics.fact_order_items foi
LEFT JOIN review_scores rs
    ON foi.order_id = rs.order_id
LEFT JOIN payment_types pt
    ON foi.order_id = pt.order_id;
"""


def _read_secret_config() -> dict[str, str]:
    if "db" not in st.secrets:
        return {}

    secret = st.secrets["db"]
    return {
        "host": secret.get("host", "localhost"),
        "port": str(secret.get("port", "5432")),
        "database": secret.get("database", "olist_bi"),
        "user": secret.get("user", "postgres"),
        "password": secret.get("password", ""),
    }


def get_database_config() -> dict[str, str]:
    config = _read_secret_config()
    if config:
        return config

    return {
        "host": os.getenv("PGHOST", "localhost"),
        "port": os.getenv("PGPORT", "5432"),
        "database": os.getenv("PGDATABASE", "olist_bi"),
        "user": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD", ""),
    }


def _sanitize_password(password: str) -> str:
    if password in {"", "YOUR_POSTGRES_PASSWORD", None}:
        return ""
    return password


@st.cache_resource(show_spinner=False)
def get_engine(password_override: str = ""):
    config = get_database_config()
    password = _sanitize_password(password_override) or _sanitize_password(config["password"])
    if not password:
        raise RuntimeError(
            "Database password not found. Add PGPASSWORD as an environment variable "
            "or create `.streamlit/secrets.toml` with your PostgreSQL credentials."
        )

    connection_url = (
        f"postgresql+psycopg2://{quote_plus(config['user'])}:{quote_plus(password)}"
        f"@{config['host']}:{config['port']}/{config['database']}"
    )
    return create_engine(connection_url, pool_pre_ping=True)


def _apply_common_types(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = dataframe.copy()
    dataframe["order_purchase_date"] = pd.to_datetime(dataframe["order_purchase_date"])
    dataframe["order_month"] = pd.to_datetime(dataframe["order_month"])
    dataframe["review_score"] = pd.to_numeric(dataframe["review_score"], errors="coerce")
    dataframe["delivery_days"] = pd.to_numeric(dataframe["delivery_days"], errors="coerce")
    dataframe["delay_days"] = pd.to_numeric(dataframe["delay_days"], errors="coerce")
    dataframe["is_delayed"] = pd.to_numeric(dataframe["is_delayed"], errors="coerce").fillna(0).astype(int)
    dataframe["review_band"] = dataframe["review_score"].apply(_review_band)
    return dataframe


def _review_band(value: float) -> str:
    if pd.isna(value):
        return "Not reviewed"
    if value <= 2:
        return "Low (1-2)"
    if value == 3:
        return "Mid (3)"
    return "High (4-5)"


UPLOAD_FILE_ALIASES = {
    "orders": ["olist_orders_dataset.csv", "orders.csv"],
    "customers": ["olist_customers_dataset.csv", "customers.csv"],
    "order_items": ["olist_order_items_dataset.csv", "order_items.csv"],
    "order_payments": ["olist_order_payments_dataset.csv", "order_payments.csv"],
    "order_reviews": ["olist_order_reviews_dataset.csv", "order_reviews.csv"],
    "products": ["olist_products_dataset.csv", "products.csv"],
    "sellers": ["olist_sellers_dataset.csv", "sellers.csv"],
    "translation": ["product_category_name_translation.csv", "category_translation.csv"],
}


def _read_uploaded_csv(uploaded_file) -> pd.DataFrame:
    uploaded_file.seek(0)
    raw_bytes = uploaded_file.read()
    uploaded_file.seek(0)
    return pd.read_csv(BytesIO(raw_bytes))


def _uploaded_file_map(uploaded_files) -> dict[str, object]:
    file_map: dict[str, object] = {}
    for uploaded_file in uploaded_files or []:
        lower_name = uploaded_file.name.lower()
        for key, aliases in UPLOAD_FILE_ALIASES.items():
            if lower_name in aliases:
                file_map[key] = uploaded_file
                break
    return file_map


def uploaded_dataset_status(uploaded_files) -> tuple[bool, list[str], list[str]]:
    file_map = _uploaded_file_map(uploaded_files)
    required = ["orders", "customers", "order_items", "order_payments", "order_reviews", "products", "sellers"]
    missing = [key for key in required if key not in file_map]
    recognized = sorted(file_map.keys())
    return len(missing) == 0, missing, recognized


def _build_uploaded_datasets(file_map: dict[str, object]) -> tuple[pd.DataFrame, pd.DataFrame]:
    orders_raw = _read_uploaded_csv(file_map["orders"])
    customers_raw = _read_uploaded_csv(file_map["customers"])
    order_items_raw = _read_uploaded_csv(file_map["order_items"])
    order_payments_raw = _read_uploaded_csv(file_map["order_payments"])
    order_reviews_raw = _read_uploaded_csv(file_map["order_reviews"])
    products_raw = _read_uploaded_csv(file_map["products"])
    sellers_raw = _read_uploaded_csv(file_map["sellers"])
    translation_raw = (
        _read_uploaded_csv(file_map["translation"])
        if "translation" in file_map
        else pd.DataFrame(columns=["product_category_name", "product_category_name_english"])
    )

    orders_raw["order_purchase_timestamp"] = pd.to_datetime(orders_raw["order_purchase_timestamp"], errors="coerce")
    orders_raw["order_delivered_customer_date"] = pd.to_datetime(orders_raw["order_delivered_customer_date"], errors="coerce")
    orders_raw["order_estimated_delivery_date"] = pd.to_datetime(orders_raw["order_estimated_delivery_date"], errors="coerce")

    review_scores = (
        order_reviews_raw.assign(review_score=pd.to_numeric(order_reviews_raw["review_score"], errors="coerce"))
        .groupby("order_id", as_index=False)
        .agg(review_score=("review_score", "mean"))
    )

    payment_types = (
        order_payments_raw.groupby("order_id")["payment_type"]
        .apply(lambda values: ", ".join(sorted({str(v).strip() for v in values if pd.notna(v) and str(v).strip()})))
        .reset_index(name="payment_types")
    )

    products_enriched = products_raw.merge(translation_raw, on="product_category_name", how="left")
    products_enriched["product_category_name_english"] = (
        products_enriched["product_category_name_english"]
        .fillna(products_enriched["product_category_name"])
        .fillna("unknown")
    )

    order_metrics = (
        order_items_raw.groupby("order_id", as_index=False)
        .agg(
            item_count=("order_item_id", "count"),
            order_revenue=("price", "sum"),
            order_freight_value=("freight_value", "sum"),
        )
    )
    order_metrics["order_total_value"] = order_metrics["order_revenue"] + order_metrics["order_freight_value"]

    orders_enriched = (
        orders_raw.merge(customers_raw, on="customer_id", how="left")
        .merge(order_metrics, on="order_id", how="left")
        .merge(review_scores, on="order_id", how="left")
        .merge(payment_types, on="order_id", how="left")
    )
    orders_enriched["order_purchase_date"] = orders_enriched["order_purchase_timestamp"].dt.normalize()
    orders_enriched["order_month"] = orders_enriched["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
    orders_enriched["delivery_days"] = (
        orders_enriched["order_delivered_customer_date"].dt.normalize()
        - orders_enriched["order_purchase_timestamp"].dt.normalize()
    ).dt.days
    orders_enriched["is_delayed"] = (
        orders_enriched["order_delivered_customer_date"].dt.normalize()
        > orders_enriched["order_estimated_delivery_date"].dt.normalize()
    ).fillna(False).astype(int)
    orders_enriched["delay_days"] = (
        orders_enriched["order_delivered_customer_date"].dt.normalize()
        - orders_enriched["order_estimated_delivery_date"].dt.normalize()
    ).dt.days.clip(lower=0)

    order_level = orders_enriched[
        [
            "order_id",
            "customer_id",
            "customer_unique_id",
            "customer_state",
            "customer_city",
            "order_status",
            "order_purchase_date",
            "order_month",
            "delivery_days",
            "is_delayed",
            "delay_days",
            "item_count",
            "order_revenue",
            "order_freight_value",
            "order_total_value",
            "review_score",
            "payment_types",
        ]
    ].copy()
    order_level["payment_types"] = order_level["payment_types"].fillna("Unknown")

    item_level = (
        order_items_raw.merge(
            order_level[
                [
                    "order_id",
                    "customer_id",
                    "customer_unique_id",
                    "customer_state",
                    "customer_city",
                    "order_status",
                    "order_purchase_date",
                    "order_month",
                    "delivery_days",
                    "is_delayed",
                    "delay_days",
                    "review_score",
                    "payment_types",
                ]
            ],
            on="order_id",
            how="left",
        )
        .merge(products_enriched[["product_id", "product_category_name_english"]], on="product_id", how="left")
        .merge(sellers_raw[["seller_id", "seller_city", "seller_state"]], on="seller_id", how="left")
    )
    item_level["product_category_name_english"] = item_level["product_category_name_english"].fillna("unknown")
    item_level["total_item_value"] = (
        pd.to_numeric(item_level["price"], errors="coerce").fillna(0)
        + pd.to_numeric(item_level["freight_value"], errors="coerce").fillna(0)
    )

    item_level = item_level[
        [
            "order_id",
            "order_item_id",
            "customer_id",
            "customer_unique_id",
            "customer_state",
            "customer_city",
            "product_id",
            "product_category_name_english",
            "seller_id",
            "seller_state",
            "seller_city",
            "order_status",
            "order_purchase_date",
            "order_month",
            "delivery_days",
            "is_delayed",
            "delay_days",
            "price",
            "freight_value",
            "total_item_value",
            "review_score",
            "payment_types",
        ]
    ].copy()

    return _apply_common_types(order_level), _apply_common_types(item_level)


@st.cache_data(show_spinner="Building analytics from uploaded CSV files...")
def load_uploaded_datasets(uploaded_files) -> tuple[pd.DataFrame, pd.DataFrame]:
    return _build_uploaded_datasets(_uploaded_file_map(uploaded_files))


@st.cache_data(ttl=600, show_spinner="Loading order-level data from PostgreSQL...")
def load_order_level_data(password_override: str = "") -> pd.DataFrame:
    dataframe = pd.read_sql_query(ORDER_LEVEL_SQL, get_engine(password_override))
    return _apply_common_types(dataframe)


@st.cache_data(ttl=600, show_spinner="Loading item-level data from PostgreSQL...")
def load_item_level_data(password_override: str = "") -> pd.DataFrame:
    dataframe = pd.read_sql_query(ITEM_LEVEL_SQL, get_engine(password_override))
    return _apply_common_types(dataframe)
