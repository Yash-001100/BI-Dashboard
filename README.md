# Mercado Livre Analytics Portal

An end-to-end business intelligence and customer analytics project built on top of the Olist e-commerce dataset, using PostgreSQL as the analytical backbone and Streamlit as the presentation layer.

This project turns raw marketplace data into a branded analytics portal for exploring revenue, customer behavior, seller performance, logistics efficiency, and customer satisfaction.

## Overview

The goal of this project is to simulate a realistic business intelligence workflow for a large digital marketplace environment. The app is designed to support:

- KPI monitoring
- operational performance review
- customer and seller analysis
- logistics and delivery diagnostics
- formal management reporting

The project is PostgreSQL-first. SQL is used as the source of truth for the cleaned data model, KPI logic, and analytics-ready views. Streamlit sits on top of that layer and provides the interactive web experience.

## What The Project Includes

This repository includes:

- a PostgreSQL schema and SQL scripts for loading and transforming the Olist dataset
- a multi-page Streamlit dashboard
- branded report generation in PDF format
- login, sign-up, password reset, and OAuth-ready authentication flows
- dataset upload support for compatible marketplace CSV files

## Main Features

### Dashboard Pages

The dashboard includes five core analytics pages:

- Executive Overview
- Customer Analytics
- Product & Seller Performance
- Operations & Delivery
- Customer Satisfaction

### KPI Cards And Visuals

The portal includes:

- KPI cards with animated counters
- interactive Plotly charts
- filter-driven analytics
- downloadable report outputs
- branded report emails

### Authentication

The app includes:

- local sign-up and sign-in
- email-based password reset flow
- Google / Gmail / Microsoft sign-in entry points
- terms and conditions acceptance for account creation

Note:
- local authentication works out of the box once secrets are configured
- OAuth sign-in requires real provider credentials

### Reporting

Users can generate a formal PDF report from the dashboard with:

- current filtered metrics
- charts and narrative insights
- branded styling
- professional email delivery

## Tech Stack

- PostgreSQL
- SQL
- Python
- Streamlit
- Plotly
- SQLAlchemy
- psycopg2
- ReportLab

## Project Structure

```text
.
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── assets/
│   ├── google_mail_gmail_logo_icon_159346.webp
│   └── mercado-livre-logo.png
├── dashboard/
│   ├── __init__.py
│   ├── auth.py
│   ├── data.py
│   ├── reporting.py
│   └── ui.py
├── sql/
│   ├── 01_create_schema.sql
│   ├── 02_load_data.sql
│   ├── 03_build_marts.sql
│   └── 04_analysis_queries.sql
├── app.py
├── PROJECT_GUIDE.md
└── requirements.txt
```

## Data Model Approach

The SQL layer is organized around two schemas:

- `raw`
  Purpose:
  load the source CSV files with minimal changes

- `analytics`
  Purpose:
  expose cleaned, dashboard-ready views for downstream reporting and app queries

This keeps the application logic cleaner and makes the project easier to explain in interviews, demos, and portfolio use.

## Database Setup

### 1. Install PostgreSQL

Install PostgreSQL locally and make sure `psql` is available.

### 2. Create the database

Example:

```powershell
psql -U postgres -c "CREATE DATABASE olist_bi;"
```

### 3. Run the SQL files in order

```powershell
psql -U postgres -d olist_bi -f sql/01_create_schema.sql
psql -U postgres -d olist_bi -f sql/02_load_data.sql
psql -U postgres -d olist_bi -f sql/03_build_marts.sql
psql -U postgres -d olist_bi -f sql/04_analysis_queries.sql
```

## Python Setup

Create and activate your environment, then install the dependencies:

```powershell
pip install -r requirements.txt
```

## Streamlit Configuration

The app reads configuration from `.streamlit/secrets.toml`.

This repository does **not** include personal secrets or live credentials.

Start from the example file:

```powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Then fill in the values you need.

### Required Config Sections

#### Database

```toml
[db]
host = "localhost"
port = 5432
database = "olist_bi"
user = "postgres"
password = "YOUR_POSTGRES_PASSWORD"
```

#### App URL

```toml
[app]
base_url = "http://localhost:8501"
```

#### Email / SMTP

Used for:

- password reset emails
- sending the formal report by email

```toml
[email]
smtp_host = "smtp.gmail.com"
smtp_port = 587
smtp_username = "YOUR_EMAIL"
smtp_password = "YOUR_APP_PASSWORD"
sender_email = "YOUR_EMAIL"
```

#### OAuth

Used for:

- Google / Gmail sign-in
- Microsoft sign-in

```toml
[oauth]
redirect_uri = "http://localhost:8501"

[oauth.google]
client_id = "YOUR_GOOGLE_CLIENT_ID"
client_secret = "YOUR_GOOGLE_CLIENT_SECRET"

[oauth.microsoft]
client_id = "YOUR_MICROSOFT_CLIENT_ID"
client_secret = "YOUR_MICROSOFT_CLIENT_SECRET"
```

## Running The App

From the project root:

```powershell
streamlit run app.py
```

Default local URL:

```text
http://localhost:8501
```

## How To Use The Dashboard

### Login

Users can:

- sign in
- create a new account
- reset their password by email

### Navigate Pages

Use the sidebar to move between the five business views.

### Apply Filters

Use the sidebar filters to adjust:

- date range
- customer state
- seller state
- product category
- payment type
- review band
- delivery status
- seller drill-down

### Generate Reports

From the report section, users can:

- download the formal PDF report
- download and email the PDF report

## Uploaded Dataset Mode

The portal supports a secondary mode for uploaded CSVs.

This allows a user to load another compatible marketplace dataset and regenerate the views without rewriting the app.

Required uploaded files:

- orders
- customers
- order_items
- order_payments
- order_reviews
- products
- sellers

Optional:

- category translation file

## Authentication Notes

### Local Sign-In

Local user data is stored in local app files during development.

These local files are intentionally excluded from Git:

- `.streamlit/secrets.toml`
- `.streamlit/oauth_states.json`
- `.streamlit/password_reset_tokens.json`
- `.streamlit/remembered_login.json`
- `.streamlit/users.json`

### OAuth

The dashboard is OAuth-ready in code, but provider-side setup is still required for live use.

Google and Gmail share the same Google OAuth configuration.

## Security And Repository Hygiene

This repository is configured to avoid pushing personal credentials and local user state.

Ignored items include:

- live secrets
- OAuth state
- password reset tokens
- remembered login state
- local user registry
- local credential JSON files
- raw dataset folder

## Current Scope

This project currently focuses on:

- SQL/PostgreSQL analytics modeling
- Streamlit dashboard delivery
- branded reporting
- realistic authentication and account management

It is suitable for:

- portfolio presentation
- case study demonstration
- resume project showcase
- interview walkthrough

## Known Notes

- OAuth sign-in requires valid Google and Microsoft app credentials
- SMTP must be configured for email features
- local development uses `localhost` redirect URLs unless deployed

## Deployment Notes

If you deploy this app:

- update the OAuth redirect URI from `http://localhost:8501` to your deployed URL
- update `[app].base_url` in secrets
- move live secrets to the deployment platform’s secret manager

## Suggested Next Improvements

Potential future upgrades:

- full production OAuth setup
- cloud deployment
- stronger audit/logging for authentication events
- richer admin/user management
- more advanced export options
- API-backed authentication instead of local file storage

## Author

GitHub:

- `Yash-001100`

Project:

- Mercado Livre Analytics Portal

