# Global Business Intelligence & Customer Analytics Platform

This project should be built as a PostgreSQL-first analytics system on top of the Olist e-commerce dataset. Python and Streamlit can support cleaning and presentation, but PostgreSQL should be the source of truth for the cleaned model, KPIs, and dashboard-ready views.

## 1. Project goal

Build an end-to-end business intelligence project that answers:

- How is the business performing over time?
- Which customers, sellers, categories, and states drive revenue?
- Where do delivery delays happen?
- How do logistics issues affect customer satisfaction?

## 2. Required deliverables

- PostgreSQL database schema
- SQL-based transformations and KPI queries
- Python notebook for optional profiling/cleaning support
- Power BI dashboard
- Streamlit web app
- Final report / presentation
- GitHub-ready documentation

## 3. Dataset summary

The workspace already contains the required CSV files in `Important Dataset/`.

- `olist_orders_dataset.csv` - 99,441 rows
- `olist_customers_dataset.csv` - 99,441 rows
- `olist_order_items_dataset.csv` - 112,650 rows
- `olist_order_payments_dataset.csv` - 103,886 rows
- `olist_order_reviews_dataset.csv` - 104,164 rows
- `olist_products_dataset.csv` - 32,951 rows
- `olist_sellers_dataset.csv` - 3,095 rows
- `olist_geolocation_dataset.csv` - 1,000,163 rows
- `product_category_name_translation.csv` - 71 rows

## 4. Recommended architecture

Use three layers in PostgreSQL:

1. `raw`
Load CSV files exactly as provided.

2. `analytics`
Create cleaned dimensions, facts, and dashboard-ready views using SQL.

3. BI / App layer
Power BI and Streamlit should query the `analytics` layer, not the raw CSV files.

## 5. Suggested project structure

```text
sql/
  01_create_schema.sql
  02_load_data.sql
  03_build_marts.sql
  04_analysis_queries.sql
notebooks/
app/
powerbi/
reports/
```

## 6. Execution order

### Phase 1: Database foundation

- Install PostgreSQL locally
- Create a database, for example `olist_bi`
- Run `sql/01_create_schema.sql`
- Run `sql/02_load_data.sql`

### Phase 2: Build the analytics model

- Run `sql/03_build_marts.sql`
- Validate row counts and key joins
- Check null handling and timestamp conversions

### Phase 3: SQL analysis

- Run and adapt `sql/04_analysis_queries.sql`
- Save your final SQL screenshots/results for the report
- Use these queries to define dashboard metrics

### Phase 4: Power BI dashboard

Create pages for:

- Executive Overview
- Customer Analytics
- Product and Seller Performance
- Operations and Delivery
- Customer Satisfaction

### Phase 5: Streamlit web app

Connect Streamlit to PostgreSQL and expose:

- Sidebar filters
- KPI cards
- Plotly charts
- Downloadable filtered tables
- Insight callout text blocks

### Phase 6: Final presentation

Tell the story in this order:

1. Business problem
2. Data model
3. SQL/PostgreSQL workflow
4. KPI findings
5. Power BI dashboard
6. Streamlit app walkthrough
7. Recommendations

## 7. KPIs to prioritize

- Total revenue
- Total orders
- Unique customers
- Average order value
- Average review score
- Delayed order percentage
- Average delivery days
- Top category by revenue
- Top seller by revenue
- Revenue by state

## 8. What to do next

Start with PostgreSQL before building notebooks or dashboards. Your best first milestone is:

1. Load all CSV files into PostgreSQL
2. Create the analytics views
3. Validate 5 to 10 KPI queries
4. Build Power BI and Streamlit on top of those SQL outputs

If you follow that order, the project stays clean, explainable, and aligned with your requirement to use SQL/PostgreSQL strictly.
