from __future__ import annotations

import base64
import json
import secrets
import mimetypes
import smtplib
from io import StringIO
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from email.message import EmailMessage

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.auth import (
    authenticate_user,
    clear_remembered_login,
    consume_oauth_state,
    create_or_update_oauth_user,
    create_user,
    remembered_login,
    request_password_reset,
    reset_password_with_token,
    set_remembered_login,
    store_oauth_state,
)
from dashboard.data import (
    load_item_level_data,
    load_order_level_data,
    load_uploaded_datasets,
    uploaded_dataset_status,
)
from dashboard.reporting import generate_pdf_report
from dashboard.ui import (
    apply_global_styles,
    close_kpi_row,
    close_tight_section,
    format_number,
    insight_box,
    metric_card,
    open_kpi_row,
    open_tight_section,
    page_header,
    render_branding,
)

BRAND = {
    "ink": "#0f172a",
    "navy": "#101a6b",
    "gold": "#ffea00",
    "mist": "#d9e3f0",
    "sky": "#6fb0ff",
    "coral": "#ff8a5b",
    "slate": "#334155",
    "cream": "#f8f4ea",
}

st.set_page_config(
    page_title="Olist BI Platform",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_styles()

LOGO_PATH = Path("assets/mercado-livre-logo.png")
TERMS_AND_CONDITIONS = """
1. Access to this analytics portal is limited to authorized users and approved stakeholders.
2. Users must provide accurate registration details, including a valid phone number and email address.
3. Marketplace data, customer information, seller information, and internal metrics must be treated as confidential.
4. Users must not export, share, or distribute restricted data outside approved business use without authorization.
5. Passwords must be kept secure and must not be shared with any other individual.
6. Users are responsible for all activity performed under their account credentials.
7. Password reset, sign-in, and account recovery features must be used only for legitimate access to your own account.
8. Any misuse of the dashboard, unauthorized access, scraping, copying, or reverse engineering is prohibited.
9. The platform may be updated, restricted, or suspended for maintenance, security, or compliance reasons.
10. By creating an account, you agree to use this dashboard responsibly and in compliance with internal policy, privacy requirements, and applicable law.
"""


def _secret_path(*keys: str, default: str = "") -> str:
    node = st.secrets
    for key in keys:
        try:
            node = node[key]
        except Exception:
            return default
    return str(node)


def _oauth_redirect_uri() -> str:
    return _secret_path("oauth", "redirect_uri", default="http://localhost:8501")


def _app_base_url() -> str:
    return _secret_path("app", "base_url", default=_oauth_redirect_uri())


def _smtp_settings() -> dict[str, str | int]:
    port_raw = _secret_path("email", "smtp_port", default="587")
    try:
        smtp_port = int(port_raw)
    except ValueError:
        smtp_port = 587

    return {
        "smtp_host": _secret_path("email", "smtp_host"),
        "smtp_port": smtp_port,
        "smtp_username": _secret_path("email", "smtp_username"),
        "smtp_password": _secret_path("email", "smtp_password"),
        "sender_email": _secret_path("email", "sender_email"),
    }


def _terms_html_list() -> str:
    items = [line.strip() for line in TERMS_AND_CONDITIONS.strip().splitlines() if line.strip()]
    cleaned_items = []
    for item in items:
        if ". " in item:
            _, text = item.split(". ", 1)
        else:
            text = item
        cleaned_items.append(f"<li>{text}</li>")
    return "".join(cleaned_items)


def _inline_logo_data_url() -> str:
    if not LOGO_PATH.exists():
        return ""
    mime_type, _ = mimetypes.guess_type(str(LOGO_PATH))
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
    return f"data:{mime_type or 'image/png'};base64,{encoded}"


@st.dialog("Terms and Conditions")
def _render_terms_dialog() -> None:
    st.markdown('<div class="terms-modal-card">', unsafe_allow_html=True)
    inline_logo = _inline_logo_data_url()
    if inline_logo:
        st.markdown(
            f'''
            <div class="terms-logo-wrap">
                <img src="{inline_logo}" alt="Mercado Livre logo" />
            </div>
            ''',
            unsafe_allow_html=True,
        )
    st.markdown(
        f"""
        <div class="terms-scroll-box">
            <div class="terms-modal-heading">Terms and Conditions</div>
            <ol class="terms-modal-list">
                {_terms_html_list()}
            </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Review the terms, then confirm below to unlock acceptance.")
    if st.button("I have reviewed the terms", use_container_width=True, key="unlock_terms_btn"):
        st.session_state["terms_acceptance_unlocked"] = True
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _oauth_provider_configs() -> dict[str, dict[str, str]]:
    redirect_uri = _oauth_redirect_uri()
    return {
        "google": {
            "client_id": _secret_path("oauth", "google", "client_id"),
            "client_secret": _secret_path("oauth", "google", "client_secret"),
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": "openid email profile",
            "redirect_uri": redirect_uri,
            "label": "Google",
        },
        "gmail": {
            "client_id": _secret_path("oauth", "google", "client_id"),
            "client_secret": _secret_path("oauth", "google", "client_secret"),
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": "openid email profile",
            "redirect_uri": redirect_uri,
            "label": "Gmail",
        },
        "microsoft": {
            "client_id": _secret_path("oauth", "microsoft", "client_id"),
            "client_secret": _secret_path("oauth", "microsoft", "client_secret"),
            "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            "scopes": "openid email profile",
            "redirect_uri": redirect_uri,
            "label": "Microsoft",
        },
    }


def _provider_ready(provider: str) -> bool:
    config = _oauth_provider_configs()[provider]
    return bool(config["client_id"] and config["client_secret"] and config["redirect_uri"])


def _provider_authorize_url(provider: str) -> str:
    config = _oauth_provider_configs()[provider]
    state_token = secrets.token_urlsafe(24)
    store_oauth_state(state_token, provider)
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": config["scopes"],
        "prompt": "select_account",
        "state": state_token,
    }
    if provider in {"google", "gmail"}:
        params["access_type"] = "offline"
    query = urlencode(params)
    return f"{config['authorize_url']}?{query}"


def _decode_jwt_payload(id_token: str) -> dict:
    token_parts = id_token.split(".")
    if len(token_parts) != 3:
        raise ValueError("OAuth provider returned an invalid identity token.")

    payload = token_parts[1]
    payload += "=" * (-len(payload) % 4)
    decoded = base64.urlsafe_b64decode(payload.encode("utf-8"))
    return json.loads(decoded.decode("utf-8"))


def _exchange_oauth_code(provider: str, code: str) -> dict:
    config = _oauth_provider_configs()[provider]
    body = urlencode(
        {
            "code": code,
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "redirect_uri": config["redirect_uri"],
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    request = Request(
        config["token_url"],
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _complete_oauth_login_from_query() -> str | None:
    query_params = st.query_params
    if "error" in query_params:
        error_text = str(query_params.get("error", "OAuth sign-in was cancelled."))
        query_params.clear()
        return f"OAuth sign-in was not completed: {error_text.replace('_', ' ')}."

    code = query_params.get("code")
    state = query_params.get("state")
    if not code:
        return None

    provider = consume_oauth_state(str(state))
    if not provider:
        query_params.clear()
        return "OAuth sign-in could not be verified. Please try the provider button again."

    try:
        token_payload = _exchange_oauth_code(provider, str(code))
        claims = _decode_jwt_payload(str(token_payload.get("id_token", "")))
        email = (
            claims.get("email")
            or claims.get("preferred_username")
            or claims.get("upn")
            or ""
        )
        name = claims.get("name") or claims.get("given_name") or email
        if not email:
            raise ValueError("The provider did not return an email address for this account.")

        user = create_or_update_oauth_user(
            provider="google" if provider in {"google", "gmail"} else provider,
            email=str(email),
            name=str(name),
        )
    except Exception as exc:
        query_params.clear()
        return f"OAuth sign-in failed: {exc}"

    query_params.clear()
    _handle_successful_login(user, remember_me=False)
    return None


def _payment_mask(series: pd.Series, selected_types: list[str]) -> pd.Series:
    if not selected_types:
        return pd.Series(True, index=series.index)

    wanted = {value.lower() for value in selected_types}

    def matches(cell: str) -> bool:
        cell_values = {part.strip().lower() for part in str(cell).split(",") if part.strip()}
        return bool(cell_values.intersection(wanted))

    return series.fillna("").apply(matches)


def _apply_filters(
    orders: pd.DataFrame,
    items: pd.DataFrame,
    *,
    date_range: tuple[pd.Timestamp, pd.Timestamp],
    customer_states: list[str],
    seller_states: list[str],
    categories: list[str],
    payment_types: list[str],
    review_bands: list[str],
    delayed_view: str,
    seller_ids: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    filtered_orders = orders.copy()
    filtered_items = items.copy()

    start_date, end_date = date_range
    filtered_orders = filtered_orders[
        filtered_orders["order_purchase_date"].between(start_date, end_date)
    ]

    if customer_states:
        filtered_orders = filtered_orders[
            filtered_orders["customer_state"].isin(customer_states)
        ]

    if payment_types:
        filtered_orders = filtered_orders[
            _payment_mask(filtered_orders["payment_types"], payment_types)
        ]

    if review_bands:
        filtered_orders = filtered_orders[
            filtered_orders["review_band"].isin(review_bands)
        ]

    if delayed_view == "Delayed only":
        filtered_orders = filtered_orders[filtered_orders["is_delayed"] == 1]
    elif delayed_view == "On-time only":
        filtered_orders = filtered_orders[filtered_orders["is_delayed"] == 0]

    allowed_order_ids = set(filtered_orders["order_id"])
    filtered_items = filtered_items[filtered_items["order_id"].isin(allowed_order_ids)]

    if seller_states:
        filtered_items = filtered_items[filtered_items["seller_state"].isin(seller_states)]

    if categories:
        filtered_items = filtered_items[
            filtered_items["product_category_name_english"].isin(categories)
        ]

    if seller_ids:
        filtered_items = filtered_items[filtered_items["seller_id"].isin(seller_ids)]

    if seller_states or categories or seller_ids:
        filtered_orders = filtered_orders[
            filtered_orders["order_id"].isin(filtered_items["order_id"].unique())
        ]

    filtered_items = filtered_items[
        filtered_items["order_id"].isin(filtered_orders["order_id"].unique())
    ]

    return filtered_orders, filtered_items


def _download_button(label: str, dataframe: pd.DataFrame, file_name: str) -> None:
    csv_buffer = StringIO()
    dataframe.to_csv(csv_buffer, index=False)
    st.download_button(
        label=label,
        data=csv_buffer.getvalue(),
        file_name=file_name,
        mime="text/csv",
        use_container_width=True,
    )


def _report_download_button(orders: pd.DataFrame, items: pd.DataFrame) -> None:
    pdf_bytes = generate_pdf_report(orders, items)
    st.download_button(
        label="Download formal PDF report",
        data=pdf_bytes,
        file_name="mercado_livre_marketplace_report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )


def _send_report_email(
    *,
    recipient_email: str,
    provider_label: str,
    pdf_bytes: bytes,
    file_name: str,
) -> tuple[bool, str]:
    smtp_settings = _smtp_settings()
    if not all(
        [
            smtp_settings["smtp_host"],
            smtp_settings["smtp_port"],
            smtp_settings["smtp_username"],
            smtp_settings["smtp_password"],
            smtp_settings["sender_email"],
        ]
    ):
        return False, "Email delivery is not configured yet. Add SMTP settings first."

    email_candidate = recipient_email.strip()
    if "@" not in email_candidate or "." not in email_candidate.split("@")[-1]:
        return False, "Enter a valid recipient email address."

    subject = "Mercado Livre Analytics Report"
    text_body = (
        "Please find attached the latest Mercado Livre analytics report generated from the dashboard.\n\n"
        f"Delivery option selected: {provider_label}\n\n"
        "This report includes the current filtered KPI views, charts, and formal commentary.\n\n"
        "Regards,\nMercado Livre Analytics Portal"
    )
    logo_cid = "mercado-livre-logo"
    html_body = f"""
    <html>
      <body style="margin:0;padding:0;background:#f5f7fb;font-family:Segoe UI,Arial,sans-serif;color:#172033;">
        <div style="max-width:680px;margin:24px auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:20px;overflow:hidden;box-shadow:0 18px 36px rgba(15,23,42,0.08);">
          <div style="background:linear-gradient(135deg,#101a6b 0%,#0f172a 100%);padding:28px 32px 22px;text-align:center;">
            <img src="cid:{logo_cid}" alt="Mercado Livre" style="width:110px;height:auto;background:#ffffff;border-radius:18px;padding:10px;border:1px solid rgba(255,255,255,0.35);" />
            <div style="font-family:Georgia,'Palatino Linotype',serif;font-size:28px;line-height:1.2;color:#fffdf6;margin-top:18px;">Mercado Livre Analytics Report</div>
            <div style="font-size:14px;line-height:1.6;color:rgba(248,244,234,0.86);margin-top:10px;">
              Formal performance report generated from the analytics dashboard.
            </div>
          </div>
          <div style="padding:28px 32px;">
            <p style="margin:0 0 16px;font-size:16px;line-height:1.7;color:#25324a;">
              Please find attached the latest Mercado Livre analytics report generated from the dashboard.
            </p>
            <div style="background:#f8f4ea;border:1px solid #e7dcc1;border-radius:16px;padding:16px 18px;margin:0 0 18px;">
              <div style="font-size:12px;text-transform:uppercase;letter-spacing:0.08em;color:#6b7280;margin-bottom:8px;">Delivery summary</div>
              <div style="font-size:15px;line-height:1.7;color:#172033;"><strong>Delivery option:</strong> {provider_label}</div>
              <div style="font-size:15px;line-height:1.7;color:#172033;"><strong>Attachment:</strong> {file_name}</div>
            </div>
            <p style="margin:0 0 16px;font-size:15px;line-height:1.75;color:#334155;">
              This report includes the current filtered KPI views, charts, and formal business commentary prepared for easier review and sharing.
            </p>
            <p style="margin:0 0 20px;font-size:15px;line-height:1.75;color:#334155;">
              The attached PDF is intended to support performance review across executive health, customer behavior, seller and product performance, operations, and customer satisfaction.
            </p>
            <div style="border-top:1px solid #e5e7eb;padding-top:16px;font-size:13px;line-height:1.7;color:#667085;">
              Confidential: this report is intended for approved business review and should be shared only with authorized stakeholders.
            </div>
          </div>
          <div style="background:#f9fafb;border-top:1px solid #e5e7eb;padding:16px 32px;font-size:13px;color:#6b7280;">
            Sent by Mercado Livre Analytics Portal
          </div>
        </div>
      </body>
    </html>
    """

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = str(smtp_settings["sender_email"])
    message["To"] = email_candidate
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")
    if LOGO_PATH.exists():
        mime_type, _ = mimetypes.guess_type(str(LOGO_PATH))
        maintype, subtype = (mime_type or "image/png").split("/", 1)
        with LOGO_PATH.open("rb") as logo_file:
            message.get_payload()[1].add_related(
                logo_file.read(),
                maintype=maintype,
                subtype=subtype,
                cid=f"<{logo_cid}>",
            )
    message.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=file_name,
    )

    try:
        with smtplib.SMTP(str(smtp_settings["smtp_host"]), int(smtp_settings["smtp_port"]), timeout=20) as smtp:
            smtp.starttls()
            smtp.login(str(smtp_settings["smtp_username"]), str(smtp_settings["smtp_password"]))
            smtp.send_message(message)
    except Exception as exc:
        return False, f"The report email could not be sent: {exc}"

    return True, f"The report was sent successfully to {email_candidate}."


def _formal_report_menu(orders: pd.DataFrame, items: pd.DataFrame) -> None:
    pdf_bytes = generate_pdf_report(orders, items)
    file_name = "mercado_livre_marketplace_report.pdf"
    with st.popover("Download formal PDF report", use_container_width=True):
        st.write("Choose how you want to receive the formal PDF report.")
        st.download_button(
            label="Download only",
            data=pdf_bytes,
            file_name=file_name,
            mime="application/pdf",
            use_container_width=True,
            key="download_only_pdf_btn",
        )
        st.markdown("#### Download and email")
        gmail_tab, outlook_tab = st.tabs(["Gmail", "Outlook"])

        with gmail_tab:
            gmail_recipient = st.text_input(
                "Recipient email",
                placeholder="name@gmail.com",
                key="gmail_report_recipient",
            )
            gmail_send = st.button("Download and email via Gmail", use_container_width=True, key="send_report_gmail")
            if gmail_send:
                ok, message = _send_report_email(
                    recipient_email=gmail_recipient,
                    provider_label="Gmail",
                    pdf_bytes=pdf_bytes,
                    file_name=file_name,
                )
                if ok:
                    st.success(message)
                else:
                    st.error(message)

        with outlook_tab:
            outlook_recipient = st.text_input(
                "Recipient email",
                placeholder="name@outlook.com",
                key="outlook_report_recipient",
            )
            outlook_send = st.button("Download and email via Outlook", use_container_width=True, key="send_report_outlook")
            if outlook_send:
                ok, message = _send_report_email(
                    recipient_email=outlook_recipient,
                    provider_label="Outlook",
                    pdf_bytes=pdf_bytes,
                    file_name=file_name,
                )
                if ok:
                    st.success(message)
                else:
                    st.error(message)


def _kpi_row(metrics: list[tuple[str, str, str]]) -> None:
    columns = st.columns(len(metrics))
    for column, (label, value, note) in zip(columns, metrics):
        with column:
            metric_card(label, value, note)


def _plot_monthly_trends(orders: pd.DataFrame) -> None:
    monthly = (
        orders.groupby("order_month", as_index=False)
        .agg(revenue=("order_revenue", "sum"), total_orders=("order_id", "nunique"))
        .sort_values("order_month")
    )
    monthly["month_label"] = pd.to_datetime(monthly["order_month"]).dt.strftime("%b %Y")

    revenue_fig = px.line(
        monthly,
        x="month_label",
        y="revenue",
        markers=True,
        color_discrete_sequence=[BRAND["sky"]],
    )
    revenue_fig.update_layout(
        title="Revenue Trend by Month",
        xaxis_title="Month",
        yaxis_title="Revenue",
        margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(revenue_fig, use_container_width=True)

    orders_fig = px.bar(
        monthly,
        x="month_label",
        y="total_orders",
        color_discrete_sequence=[BRAND["gold"]],
    )
    orders_fig.update_layout(
        title="Orders Trend by Month",
        xaxis_title="Month",
        yaxis_title="Orders",
        margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(orders_fig, use_container_width=True)


def render_executive_overview(orders: pd.DataFrame, items: pd.DataFrame) -> None:
    page_header(
        "Executive Overview",
        "A one-screen business health check with the headline commercial, delivery, and satisfaction metrics.",
    )

    avg_review = orders["review_score"].dropna().mean()
    delayed_pct = orders["is_delayed"].mean() * 100 if not orders.empty else 0

    open_kpi_row()
    _kpi_row(
        [
            ("Total Revenue", f"${orders['order_revenue'].sum():,.0f}", "Revenue from filtered orders"),
            ("Total Orders", format_number(orders["order_id"].nunique()), "Distinct completed and non-completed orders"),
            ("Unique Customers", format_number(orders["customer_unique_id"].nunique()), "Customers represented in the current slice"),
            ("Average Order Value", f"${orders['order_revenue'].mean():,.2f}" if not orders.empty else "$0.00", "Average order revenue"),
            ("Average Review Score", f"{avg_review:.2f}" if pd.notna(avg_review) else "N/A", "Mean review score across matched orders"),
            ("Delayed Order Rate", f"{delayed_pct:.2f}%", "Orders delivered after the estimated date"),
        ]
    )
    close_kpi_row()

    open_tight_section()
    trend_left, trend_right = st.columns((1.2, 1))
    with trend_left:
        _plot_monthly_trends(orders)
    with trend_right:
        state_revenue = (
            orders.groupby("customer_state", as_index=False)
            .agg(revenue=("order_revenue", "sum"))
            .sort_values("revenue", ascending=False)
            .head(10)
        )
        state_fig = px.bar(
            state_revenue,
            x="customer_state",
            y="revenue",
            color="revenue",
            color_continuous_scale=[BRAND["mist"], BRAND["navy"]],
        )
        state_fig.update_layout(
            title="Top States by Revenue",
            xaxis_title="Customer State",
            yaxis_title="Revenue",
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(state_fig, use_container_width=True)

        category_revenue = (
            items.groupby("product_category_name_english", as_index=False)
            .agg(revenue=("price", "sum"))
            .sort_values("revenue", ascending=False)
            .head(10)
        )
        category_fig = px.bar(
            category_revenue,
            x="revenue",
            y="product_category_name_english",
            orientation="h",
            color="revenue",
            color_continuous_scale=[BRAND["cream"], BRAND["coral"]],
        )
        category_fig.update_layout(
            title="Top Categories by Revenue",
            xaxis_title="Revenue",
            yaxis_title="Category",
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(category_fig, use_container_width=True)
    close_tight_section()

    top_state = (
        state_revenue.iloc[0]["customer_state"]
        if not state_revenue.empty
        else "N/A"
    )
    top_category = (
        category_revenue.iloc[0]["product_category_name_english"]
        if not category_revenue.empty
        else "N/A"
    )
    insight_box(
        f"{top_state} is the strongest revenue state in the current slice, while "
        f"{top_category} is the top-performing category. Use this page to spot where "
        "commercial growth and delivery risk are moving together."
    )

    _download_button("Download filtered orders", orders, "executive_overview_orders.csv")


def render_customer_analytics(orders: pd.DataFrame, items: pd.DataFrame) -> None:
    page_header(
        "Customer Analytics",
        "Understand where customers come from, how often they return, and who contributes the most spend.",
    )

    customer_rollup = (
        orders.groupby(["customer_unique_id", "customer_state"], as_index=False)
        .agg(total_orders=("order_id", "nunique"), total_spend=("order_revenue", "sum"))
    )
    repeat_rate = (
        (customer_rollup["total_orders"] > 1).mean() * 100 if not customer_rollup.empty else 0
    )
    avg_spend = customer_rollup["total_spend"].mean() if not customer_rollup.empty else 0

    open_kpi_row()
    _kpi_row(
        [
            ("Unique Customers", format_number(customer_rollup["customer_unique_id"].nunique()), "Customers in the filtered market view"),
            ("Repeat Customer Rate", f"{repeat_rate:.2f}%", "Share of customers with more than one order"),
            ("Average Spend per Customer", f"${avg_spend:,.2f}", "Mean customer revenue"),
        ]
    )
    close_kpi_row()

    open_tight_section()
    top_left, top_right = st.columns(2)
    with top_left:
        customers_by_state = (
            customer_rollup.groupby("customer_state", as_index=False)
            .agg(unique_customers=("customer_unique_id", "nunique"))
            .sort_values("unique_customers", ascending=False)
            .head(12)
        )
        customer_state_fig = px.bar(
            customers_by_state,
            x="customer_state",
            y="unique_customers",
            color_discrete_sequence=[BRAND["gold"]],
        )
        customer_state_fig.update_layout(
            title="Customers by State",
            xaxis_title="State",
            yaxis_title="Unique Customers",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(customer_state_fig, use_container_width=True)

    with top_right:
        repeat_mix = pd.DataFrame(
            {
                "segment": ["One-time", "Repeat"],
                "customers": [
                    int((customer_rollup["total_orders"] == 1).sum()),
                    int((customer_rollup["total_orders"] > 1).sum()),
                ],
            }
        )
        repeat_fig = px.pie(
            repeat_mix,
            names="segment",
            values="customers",
            hole=0.55,
            color="segment",
            color_discrete_map={"One-time": BRAND["cream"], "Repeat": BRAND["navy"]},
        )
        repeat_fig.update_layout(title="Repeat vs One-time Customers", margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(repeat_fig, use_container_width=True)

    bottom_left, bottom_right = st.columns(2)
    with bottom_left:
        top_customers = customer_rollup.sort_values("total_spend", ascending=False).head(15)
        top_customer_fig = px.bar(
            top_customers,
            x="customer_unique_id",
            y="total_spend",
            color="total_spend",
            color_continuous_scale=[BRAND["cream"], BRAND["coral"]],
        )
        top_customer_fig.update_layout(
            title="Top Customers by Spend",
            xaxis_title="Customer",
            yaxis_title="Total Spend",
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(top_customer_fig, use_container_width=True)

    with bottom_right:
        frequency_fig = px.histogram(
            customer_rollup,
            x="total_orders",
            nbins=min(15, max(5, customer_rollup["total_orders"].nunique() if not customer_rollup.empty else 5)),
            color_discrete_sequence=[BRAND["coral"]],
        )
        frequency_fig.update_layout(
            title="Order Frequency Distribution",
            xaxis_title="Orders per Customer",
            yaxis_title="Customer Count",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(frequency_fig, use_container_width=True)
    close_tight_section()

    insight_box(
        "This page is useful for spotting whether growth is broad-based or concentrated in a small group of repeat buyers. "
        "If repeat rate is low, that is an opportunity for retention campaigns and post-purchase engagement."
    )

    customer_export = customer_rollup.sort_values("total_spend", ascending=False)
    _download_button("Download customer view", customer_export, "customer_analytics.csv")


def render_product_seller_performance(orders: pd.DataFrame, items: pd.DataFrame) -> None:
    page_header(
        "Product & Seller Performance",
        "See which categories and sellers are driving revenue and how freight cost shifts across the catalog.",
    )

    category_perf = (
        items.groupby("product_category_name_english", as_index=False)
        .agg(
            revenue=("price", "sum"),
            freight=("freight_value", "sum"),
            total_orders=("order_id", "nunique"),
        )
        .sort_values("revenue", ascending=False)
    )
    seller_perf = (
        items.groupby(["seller_id", "seller_state"], as_index=False)
        .agg(revenue=("price", "sum"), total_orders=("order_id", "nunique"))
        .sort_values("revenue", ascending=False)
    )

    top_category = category_perf.iloc[0] if not category_perf.empty else None
    top_seller = seller_perf.iloc[0] if not seller_perf.empty else None
    avg_seller_revenue = seller_perf["revenue"].mean() if not seller_perf.empty else 0

    open_kpi_row()
    _kpi_row(
        [
            (
                "Top Category",
                top_category["product_category_name_english"] if top_category is not None else "N/A",
                f"${top_category['revenue']:,.0f} revenue" if top_category is not None else "No category data",
            ),
            ("Average Revenue per Seller", f"${avg_seller_revenue:,.2f}", "Mean seller revenue in current filters"),
            (
                "Best Seller Revenue",
                f"${top_seller['revenue']:,.0f}" if top_seller is not None else "$0",
                top_seller["seller_id"] if top_seller is not None else "No seller data",
            ),
        ]
    )
    close_kpi_row()

    open_tight_section()
    top_left, top_right = st.columns(2)
    with top_left:
        top_categories_fig = px.bar(
            category_perf.head(12),
            x="revenue",
            y="product_category_name_english",
            orientation="h",
            color="revenue",
            color_continuous_scale=[BRAND["mist"], BRAND["navy"]],
        )
        top_categories_fig.update_layout(
            title="Top Categories",
            xaxis_title="Revenue",
            yaxis_title="Category",
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(top_categories_fig, use_container_width=True)

    with top_right:
        top_sellers_fig = px.bar(
            seller_perf.head(12),
            x="seller_id",
            y="revenue",
            color="seller_state",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        top_sellers_fig.update_layout(
            title="Top Sellers by Revenue",
            xaxis_title="Seller",
            yaxis_title="Revenue",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(top_sellers_fig, use_container_width=True)

    bottom_left, bottom_right = st.columns(2)
    with bottom_left:
        seller_state_perf = (
            seller_perf.groupby("seller_state", as_index=False)
            .agg(revenue=("revenue", "sum"), sellers=("seller_id", "nunique"))
            .sort_values("revenue", ascending=False)
        )
        seller_state_fig = px.bar(
            seller_state_perf,
            x="seller_state",
            y="revenue",
            color="sellers",
            color_continuous_scale=[BRAND["cream"], BRAND["coral"]],
        )
        seller_state_fig.update_layout(
            title="Seller Revenue by State",
            xaxis_title="Seller State",
            yaxis_title="Revenue",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(seller_state_fig, use_container_width=True)

    with bottom_right:
        freight_by_category = category_perf.head(12).sort_values("freight", ascending=True)
        freight_fig = px.bar(
            freight_by_category,
            x="freight",
            y="product_category_name_english",
            orientation="h",
            color_discrete_sequence=[BRAND["coral"]],
        )
        freight_fig.update_layout(
            title="Freight Cost by Top Category",
            xaxis_title="Freight Cost",
            yaxis_title="Category",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(freight_fig, use_container_width=True)
    close_tight_section()

    insight_box(
        "Use this page to separate commercial winners from costly categories. "
        "A category with strong revenue but heavy freight can still compress margin and operational efficiency."
    )

    _download_button("Download seller and category slice", items, "product_seller_performance.csv")


def render_operations_delivery(orders: pd.DataFrame, items: pd.DataFrame) -> None:
    page_header(
        "Operations & Delivery",
        "Track delivery speed, delay hotspots, and the freight patterns behind logistics performance.",
    )

    avg_delivery = orders["delivery_days"].mean() if not orders.empty else 0
    on_time_rate = 100 - (orders["is_delayed"].mean() * 100 if not orders.empty else 0)
    delayed_pct = orders["is_delayed"].mean() * 100 if not orders.empty else 0
    avg_freight = items["freight_value"].mean() if not items.empty else 0

    open_kpi_row()
    _kpi_row(
        [
            ("Average Delivery Days", f"{avg_delivery:.2f}", "Time from purchase to delivery"),
            ("On-time Rate", f"{on_time_rate:.2f}%", "Orders that arrived on or before estimate"),
            ("Delayed Order Rate", f"{delayed_pct:.2f}%", "Orders delivered after estimate"),
            ("Average Freight Value", f"${avg_freight:,.2f}", "Mean freight charge per item"),
        ]
    )
    close_kpi_row()

    open_tight_section()
    top_left, top_right = st.columns(2)
    with top_left:
        delivery_fig = px.histogram(
            orders.dropna(subset=["delivery_days"]),
            x="delivery_days",
            nbins=25,
            color_discrete_sequence=[BRAND["sky"]],
        )
        delivery_fig.update_layout(
            title="Delivery Time Distribution",
            xaxis_title="Delivery Days",
            yaxis_title="Orders",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(delivery_fig, use_container_width=True)

    with top_right:
        delayed_states = (
            orders.groupby("customer_state", as_index=False)
            .agg(delayed_order_pct=("is_delayed", "mean"), total_orders=("order_id", "nunique"))
        )
        delayed_states["delayed_order_pct"] = delayed_states["delayed_order_pct"] * 100
        delayed_states = delayed_states.sort_values("delayed_order_pct", ascending=False).head(12)
        delayed_state_fig = px.bar(
            delayed_states,
            x="customer_state",
            y="delayed_order_pct",
            color="total_orders",
            color_continuous_scale=[BRAND["cream"], BRAND["coral"]],
        )
        delayed_state_fig.update_layout(
            title="Delayed Orders by State",
            xaxis_title="Customer State",
            yaxis_title="Delayed Order %",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(delayed_state_fig, use_container_width=True)

    bottom_left, bottom_right = st.columns(2)
    with bottom_left:
        delivery_by_category = (
            items.groupby("product_category_name_english", as_index=False)
            .agg(avg_delivery_days=("delivery_days", "mean"), total_orders=("order_id", "nunique"))
            .sort_values("avg_delivery_days", ascending=False)
            .head(12)
        )
        category_delivery_fig = px.bar(
            delivery_by_category,
            x="avg_delivery_days",
            y="product_category_name_english",
            orientation="h",
            color="total_orders",
            color_continuous_scale=[BRAND["mist"], BRAND["gold"]],
        )
        category_delivery_fig.update_layout(
            title="Delivery Days by Category",
            xaxis_title="Average Delivery Days",
            yaxis_title="Category",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(category_delivery_fig, use_container_width=True)

    with bottom_right:
        seller_delivery = (
            items.groupby("seller_id", as_index=False)
            .agg(
                revenue=("price", "sum"),
                avg_delivery_days=("delivery_days", "mean"),
                total_orders=("order_id", "nunique"),
            )
            .query("total_orders >= 10")
        )
        seller_delivery_fig = px.scatter(
            seller_delivery,
            x="avg_delivery_days",
            y="revenue",
            size="total_orders",
            color="avg_delivery_days",
            color_continuous_scale=[BRAND["mist"], BRAND["sky"], BRAND["coral"]],
            hover_name="seller_id",
        )
        seller_delivery_fig.update_layout(
            title="Seller Revenue vs Delivery Time",
            xaxis_title="Average Delivery Days",
            yaxis_title="Revenue",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(seller_delivery_fig, use_container_width=True)
    close_tight_section()

    worst_state = (
        delayed_states.iloc[0]["customer_state"]
        if not delayed_states.empty
        else "N/A"
    )
    insight_box(
        f"{worst_state} currently has the highest delay pressure in this filtered view. "
        "Use this page to isolate where logistics issues are concentrated and whether they are tied to specific sellers or categories."
    )

    _download_button("Download operations dataset", orders, "operations_delivery.csv")


def render_customer_satisfaction(orders: pd.DataFrame, items: pd.DataFrame) -> None:
    page_header(
        "Customer Satisfaction",
        "Connect review outcomes to delivery performance, category mix, and payment behavior.",
    )

    scored_orders = orders.dropna(subset=["review_score"]).copy()
    avg_review = scored_orders["review_score"].mean() if not scored_orders.empty else 0
    low_review_pct = (
        (scored_orders["review_score"] <= 2).mean() * 100 if not scored_orders.empty else 0
    )
    delayed_low_reviews = scored_orders[
        (scored_orders["review_score"] <= 2) & (scored_orders["is_delayed"] == 1)
    ]
    delayed_low_review_pct = (
        len(delayed_low_reviews) / len(scored_orders) * 100 if not scored_orders.empty else 0
    )

    open_kpi_row()
    _kpi_row(
        [
            ("Average Review Score", f"{avg_review:.2f}" if not scored_orders.empty else "N/A", "Mean score across reviewed orders"),
            ("Low Review Rate", f"{low_review_pct:.2f}%", "Share of orders with review score 1 or 2"),
            ("Delayed + Low Review Rate", f"{delayed_low_review_pct:.2f}%", "Orders that are both delayed and poorly rated"),
        ]
    )
    close_kpi_row()

    open_tight_section()
    top_left, top_right = st.columns(2)
    with top_left:
        review_dist = (
            scored_orders.groupby("review_score", as_index=False)
            .agg(review_count=("order_id", "nunique"))
            .sort_values("review_score")
        )
        review_fig = px.bar(
            review_dist,
            x="review_score",
            y="review_count",
            color_discrete_sequence=[BRAND["gold"]],
        )
        review_fig.update_layout(
            title="Review Score Distribution",
            xaxis_title="Review Score",
            yaxis_title="Orders",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(review_fig, use_container_width=True)

    with top_right:
        review_delay = (
            scored_orders.groupby("is_delayed", as_index=False)
            .agg(avg_review_score=("review_score", "mean"), total_orders=("order_id", "nunique"))
        )
        review_delay["delivery_status"] = review_delay["is_delayed"].map({0: "On-time", 1: "Delayed"})
        review_delay_fig = px.bar(
            review_delay,
            x="delivery_status",
            y="avg_review_score",
            color="total_orders",
            color_continuous_scale=[BRAND["mist"], BRAND["coral"]],
        )
        review_delay_fig.update_layout(
            title="Average Review Score vs Delay",
            xaxis_title="Delivery Status",
            yaxis_title="Average Review Score",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(review_delay_fig, use_container_width=True)

    bottom_left, bottom_right = st.columns(2)
    with bottom_left:
        item_reviews = items.dropna(subset=["review_score"])
        review_by_category = (
            item_reviews.groupby("product_category_name_english", as_index=False)
            .agg(avg_review_score=("review_score", "mean"), total_orders=("order_id", "nunique"))
            .query("total_orders >= 20")
            .sort_values("avg_review_score", ascending=False)
            .head(12)
        )
        category_review_fig = px.bar(
            review_by_category,
            x="avg_review_score",
            y="product_category_name_english",
            orientation="h",
            color="total_orders",
            color_continuous_scale=[BRAND["mist"], BRAND["navy"]],
        )
        category_review_fig.update_layout(
            title="Review Score by Category",
            xaxis_title="Average Review Score",
            yaxis_title="Category",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(category_review_fig, use_container_width=True)

    with bottom_right:
        payment_review = (
            scored_orders.assign(
                primary_payment_type=scored_orders["payment_types"].str.split(",").str[0].str.strip()
            )
            .groupby("primary_payment_type", as_index=False)
            .agg(avg_review_score=("review_score", "mean"), total_orders=("order_id", "nunique"))
            .sort_values("avg_review_score", ascending=False)
        )
        payment_review_fig = px.bar(
            payment_review,
            x="primary_payment_type",
            y="avg_review_score",
            color="total_orders",
            color_continuous_scale=[BRAND["cream"], BRAND["coral"]],
        )
        payment_review_fig.update_layout(
            title="Review Score by Payment Type",
            xaxis_title="Payment Type",
            yaxis_title="Average Review Score",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(payment_review_fig, use_container_width=True)
    close_tight_section()

    insight_box(
        "This view helps connect customer sentiment to operational reality. "
        "If delayed orders and low ratings rise together, delivery performance is likely one of the strongest experience levers."
    )

    _download_button("Download satisfaction dataset", scored_orders, "customer_satisfaction.csv")


def _init_auth_state() -> None:
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("auth_user", None)
    st.session_state.setdefault("magic_link_identifier", "")
    st.session_state.setdefault("magic_link_token", "")
    st.session_state.setdefault("login_identifier_prefill", remembered_login())
    st.session_state.setdefault("terms_acceptance_unlocked", False)


def _render_about_menu() -> None:
    top_left, top_right = st.columns((10, 1))
    with top_right:
        with st.popover("⋮", use_container_width=True):
            account_tab, about_tab, faq_tab, contact_tab = st.tabs(["Account", "About", "FAQs", "Contact Us"])

            with account_tab:
                auth_user = st.session_state.get("auth_user") or {}
                account_email = auth_user.get("email", "Not available")
                account_phone = auth_user.get("phone", "Not available")
                st.markdown("### Account")
                st.write(f"Signed in as: `{account_email}`")
                if account_phone:
                    st.write(f"Phone: `{account_phone}`")

            with about_tab:
                st.markdown("### About Mercado Livre")
                st.write(
                    "Mercado Livre is a leading Latin American e-commerce company of Argentine origin, "
                    "headquartered in Montevideo, Uruguay, with incorporation in Delaware, United States. "
                    "It operates large-scale online marketplace platforms across multiple countries in Latin America "
                    "and has grown into one of the region's most influential digital commerce businesses."
                )
                st.write(
                    "The company is widely recognized for its scale, marketplace reach, and strong presence across "
                    "major regional economies, making it a key player in Latin American e-commerce."
                )

                st.markdown("### About the Dashboard")
                st.write(
                    "This web app is a Mercado Livre analytics dashboard built to explore marketplace revenue, "
                    "customer behavior, seller performance, logistics efficiency, and customer satisfaction."
                )
                st.write(
                    "Use the left-side filters to adjust the date range, geography, product categories, "
                    "payment types, delivery status, and other business slices."
                )
                st.write(
                    "The dashboard is designed to help users monitor performance, identify patterns, and "
                    "generate insights from the connected enterprise warehouse or uploaded marketplace datasets."
                )

            with faq_tab:
                st.markdown("### FAQs")
                faq_items = [
                    (
                        "1. What does this dashboard show?",
                        "It shows marketplace performance across revenue, customers, sellers, delivery operations, and customer satisfaction.",
                    ),
                    (
                        "2. How do I use the filters?",
                        "Use the sidebar filters to narrow the dashboard by date range, state, category, payment type, seller, review band, or delivery status.",
                    ),
                    (
                        "3. Can I use another dataset?",
                        "Yes. The dashboard supports uploaded marketplace CSV files so you can generate insights from another period or compatible dataset.",
                    ),
                    (
                        "4. Why do some charts change after filtering?",
                        "All charts and KPIs react to the active filter selection, so the figures always reflect the current slice of data.",
                    ),
                    (
                        "5. Can I download results?",
                        "Yes. You can download formal reports and data extracts from the dashboard based on the current view.",
                    ),
                    (
                        "6. What should I do if I forget my password?",
                        "Use the Forgot Password option on the login screen. A reset link will be sent to the email used for your account.",
                    ),
                    (
                        "7. What data source is the dashboard using?",
                        "The app can read from the enterprise data warehouse or from uploaded marketplace datasets, depending on the selected source.",
                    ),
                ]
                for question, answer in faq_items:
                    with st.expander(question):
                        st.write(answer)

            with contact_tab:
                st.markdown("### Contact Us")
                contact_email = _secret_path("email", "sender_email", default="yashkalra211@gmail.com")
                st.write(f"For support or questions, contact: `{contact_email}`")

            st.divider()
            if st.button("Log out", use_container_width=True):
                st.session_state["authenticated"] = False
                st.session_state["auth_user"] = None
                st.rerun()


def _handle_successful_login(user: dict, remember_me: bool) -> None:
    st.session_state["authenticated"] = True
    st.session_state["auth_user"] = user
    if remember_me:
        set_remembered_login(user.get("email", "") or user.get("phone", ""))
    else:
        clear_remembered_login()
    st.rerun()


def _render_login_screen() -> None:
    remembered_identifier = st.session_state.get("login_identifier_prefill", remembered_login())
    oauth_feedback = _complete_oauth_login_from_query()
    reset_token = str(st.query_params.get("reset_token", ""))
    provider_configs = _oauth_provider_configs()
    provider_status = {
        "google": _provider_ready("google"),
        "gmail": _provider_ready("gmail"),
        "microsoft": _provider_ready("microsoft"),
    }
    google_href = (
        _provider_authorize_url("google")
        if provider_status["google"]
        else "https://accounts.google.com/"
    )
    gmail_href = (
        _provider_authorize_url("gmail")
        if provider_status["gmail"]
        else "https://mail.google.com/"
    )
    microsoft_href = (
        _provider_authorize_url("microsoft")
        if provider_status["microsoft"]
        else "https://login.microsoftonline.com/"
    )
    st.markdown('<div class="auth-shell"></div>', unsafe_allow_html=True)
    left_col, right_col = st.columns((1.05, 1))

    with left_col:
        st.markdown('<div class="auth-brand">', unsafe_allow_html=True)
        if LOGO_PATH.exists():
            st.markdown('<div class="auth-brand-logo">', unsafe_allow_html=True)
            st.image(str(LOGO_PATH), width=180)
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="auth-kicker">Secure Access</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-title">Mercado Livre Analytics Portal</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="auth-panel">', unsafe_allow_html=True)
        st.markdown('<div class="auth-form-title">Welcome back</div>', unsafe_allow_html=True)
        if oauth_feedback:
            st.error(oauth_feedback)
        if reset_token:
            st.markdown("#### Reset your password")
            with st.form("reset_password_link_form"):
                new_password = st.text_input("New password", type="password")
                confirm_password = st.text_input("Confirm new password", type="password")
                reset_link_submit = st.form_submit_button("Set new password", use_container_width=True)
            if reset_link_submit:
                if new_password != confirm_password:
                    st.error("The new password and confirmation do not match.")
                else:
                    ok, message = reset_password_with_token(reset_token, new_password)
                    if ok:
                        st.query_params.clear()
                        st.session_state["login_identifier_prefill"] = ""
                        st.session_state["password_reset_success"] = message
                        st.rerun()
                    else:
                        st.error(message)
            st.markdown("</div>", unsafe_allow_html=True)
            return

        login_tab, signup_tab = st.tabs(["Log In", "Sign Up"])

        with login_tab:
            if st.session_state.get("password_reset_success"):
                st.success(st.session_state.pop("password_reset_success"))
            show_password = st.checkbox("Show password", key="show_login_password")
            with st.form("login_form", clear_on_submit=False):
                identifier = st.text_input(
                    "Phone / Email",
                    value=remembered_identifier,
                    placeholder="Enter your phone number or email",
                )
                password = st.text_input(
                    "Password",
                    type="default" if show_password else "password",
                    placeholder="Enter your password",
                )
                remember_me = st.checkbox("Remember me on this device")
                submitted = st.form_submit_button("Log In", use_container_width=True)
            st.caption("Tip: check Caps Lock if your password is not being accepted.")
            if submitted:
                ok, message, user = authenticate_user(identifier, password)
                if not ok:
                    st.error(message)
                else:
                    st.success(message)
                    _handle_successful_login(user, remember_me)

            with st.expander("Forgot Password"):
                with st.form("forgot_password_form"):
                    reset_email = st.text_input("Email", placeholder="Enter the email used for the account")
                    reset_submit = st.form_submit_button("Send password reset link", use_container_width=True)
                if reset_submit:
                    ok, message = request_password_reset(
                        reset_email,
                        app_base_url=_app_base_url(),
                        **_smtp_settings(),
                    )
                    if ok:
                        st.success(message)
                    else:
                        st.error(message)

            st.markdown("#### Continue with")
            st.markdown(
                f"""
                <div class="auth-social-grid">
                    <a class="auth-social-link" href="{google_href}" target="{"_self" if provider_status["google"] else "_blank"}" rel="noopener noreferrer">
                        <span class="auth-social-icon google" aria-hidden="true">
                            <svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
                                <path fill="#EA4335" d="M24 9.5c3.54 0 6.73 1.22 9.24 3.61l6.9-6.9C35.95 2.42 30.46 0 24 0 14.64 0 6.57 5.38 2.63 13.22l8.03 6.23C12.58 13.39 17.82 9.5 24 9.5z"/>
                                <path fill="#4285F4" d="M46.5 24.55c0-1.58-.14-3.1-.4-4.55H24v8.62h12.72c-.55 2.94-2.21 5.43-4.71 7.1l7.61 5.91c4.45-4.1 6.88-10.15 6.88-17.08z"/>
                                <path fill="#FBBC05" d="M10.66 28.55A14.5 14.5 0 0 1 9.9 24c0-1.58.27-3.12.76-4.55l-8.03-6.23A23.95 23.95 0 0 0 0 24c0 3.85.92 7.49 2.63 10.78l8.03-6.23z"/>
                                <path fill="#34A853" d="M24 48c6.48 0 11.92-2.13 15.9-5.8l-7.61-5.91c-2.11 1.42-4.82 2.26-8.29 2.26-6.18 0-11.42-3.89-13.34-9.95l-8.03 6.23C6.57 42.62 14.64 48 24 48z"/>
                            </svg>
                        </span>
                        <span>Google</span>
                    </a>
                    <a class="auth-social-link" href="{gmail_href}" target="{"_self" if provider_status["gmail"] else "_blank"}" rel="noopener noreferrer">
                        <span class="auth-social-icon gmail" aria-hidden="true">
                            <svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
                                <path fill="#4285F4" d="M10 38V14.5l10 7.8V38H10Z"/>
                                <path fill="#34A853" d="M28 38V22.3l10-7.8V38H28Z"/>
                                <path fill="#FBBC04" d="M28 22.3 38 14.5V12c0-1.1-.9-2-2-2h-3.2L24 16.9 28 22.3Z"/>
                                <path fill="#EA4335" d="M10 14.5 20 22.3l4-5.4L15.2 10H12c-1.1 0-2 .9-2 2v2.5Z"/>
                                <path fill="#EA4335" d="M20 22.3 24 25.6 28 22.3 38 14.5 32.8 10 24 17.6 15.2 10 10 14.5 20 22.3Z"/>
                            </svg>
                        </span>
                        <span>Gmail</span>
                    </a>
                    <a class="auth-social-link" href="{microsoft_href}" target="{"_self" if provider_status["microsoft"] else "_blank"}" rel="noopener noreferrer">
                        <span class="auth-social-icon microsoft" aria-hidden="true">
                            <svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
                                <rect x="2" y="2" width="20" height="20" fill="#F25022"/>
                                <rect x="26" y="2" width="20" height="20" fill="#7FBA00"/>
                                <rect x="2" y="26" width="20" height="20" fill="#00A4EF"/>
                                <rect x="26" y="26" width="20" height="20" fill="#FFB900"/>
                            </svg>
                        </span>
                        <span>Microsoft</span>
                    </a>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with signup_tab:
            show_signup_password = st.checkbox("Show password fields", key="show_signup_password")
            signup_phone = st.text_input("Phone Number", placeholder="Enter your phone number", key="signup_phone")
            signup_email = st.text_input("Email", placeholder="Enter your email", key="signup_email")
            signup_password = st.text_input(
                "Password",
                type="default" if show_signup_password else "password",
                placeholder="Create a password",
                key="signup_password",
            )
            signup_confirm = st.text_input(
                "Confirm password",
                type="default" if show_signup_password else "password",
                placeholder="Re-enter your password",
                key="signup_confirm",
            )
            st.markdown(
                '<div class="terms-link-label">Please review our Terms and Conditions before creating your account.</div>',
                unsafe_allow_html=True,
            )
            if st.button("Terms and Conditions", key="terms_link_button", type="tertiary"):
                _render_terms_dialog()
            accept_terms = st.checkbox(
                "I accept the Terms and Conditions",
                key="accept_terms_checkbox",
                disabled=not st.session_state.get("terms_acceptance_unlocked", False),
            )
            sign_up_submit = st.button("Create account", use_container_width=True, key="create_account_btn")
            if sign_up_submit:
                if signup_password != signup_confirm:
                    st.error("The password confirmation does not match.")
                elif not accept_terms:
                    st.error("You must accept the Terms and Conditions before creating an account.")
                else:
                    ok, message = create_user(signup_phone, signup_email, signup_password)
                    if ok:
                        st.success(message)
                        st.session_state["terms_acceptance_unlocked"] = False
                        st.session_state["accept_terms_checkbox"] = False
                    else:
                        st.error(message)


def main() -> None:
    _init_auth_state()
    if not st.session_state.get("authenticated"):
        _render_login_screen()
        return

    _render_about_menu()
    render_branding()

    data_source = st.sidebar.radio(
        "Data source",
        ["Enterprise Data Warehouse", "Uploaded CSVs"],
        help="Use the primary governed data source or upload another structured marketplace dataset, such as a different year, to regenerate the dashboard.",
    )
    uploaded_files = []
    if data_source == "Uploaded CSVs":
        st.sidebar.markdown("### Upload dataset")
        uploaded_files = st.sidebar.file_uploader(
            "Upload marketplace CSV files",
            type=["csv"],
            accept_multiple_files=True,
            help="Required: orders, customers, order_items, order_payments, order_reviews, products, sellers. Category translation is optional.",
        )
        ready, missing_files, recognized = uploaded_dataset_status(uploaded_files)
        if recognized:
            st.sidebar.caption("Recognized files: " + ", ".join(recognized))
        if ready:
            st.sidebar.success("Uploaded dataset is ready.")
        elif uploaded_files:
            st.sidebar.warning("Missing files: " + ", ".join(missing_files))

    try:
        if data_source == "Uploaded CSVs":
            ready, missing_files, _ = uploaded_dataset_status(uploaded_files)
            if not ready:
                st.info(
                    "Upload a complete marketplace dataset to use this mode. Required files: orders, customers, "
                    "order_items, order_payments, order_reviews, products, and sellers."
                )
                return
            orders, items = load_uploaded_datasets(uploaded_files)
        else:
            orders = load_order_level_data()
            items = load_item_level_data()
    except Exception as exc:  # pragma: no cover - Streamlit runtime path
        st.error("The app could not load the selected data source.")
        st.code(str(exc))
        st.info(
            "Store the PostgreSQL credentials in `.streamlit/secrets.toml` or environment variables "
            "(`PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`) and restart Streamlit, "
            "or switch to Uploaded CSVs mode."
        )
        return

    page_name = st.sidebar.radio(
        "Navigate",
        [
            "Executive Overview",
            "Customer Analytics",
            "Product & Seller Performance",
            "Operations & Delivery",
            "Customer Satisfaction",
        ],
    )

    min_date = orders["order_purchase_date"].min()
    max_date = orders["order_purchase_date"].max()

    selected_dates = st.sidebar.date_input(
        "Date range",
        value=(min_date.date(), max_date.date()),
        min_value=min_date.date(),
        max_value=max_date.date(),
    )
    if len(selected_dates) != 2:
        selected_dates = (min_date.date(), max_date.date())

    customer_states = st.sidebar.multiselect(
        "Customer state",
        sorted(orders["customer_state"].dropna().unique().tolist()),
    )
    seller_states = st.sidebar.multiselect(
        "Seller state",
        sorted(items["seller_state"].dropna().unique().tolist()),
    )
    categories = st.sidebar.multiselect(
        "Product category",
        sorted(items["product_category_name_english"].dropna().unique().tolist()),
    )
    payment_types = st.sidebar.multiselect(
        "Payment type",
        sorted(
            {
                part.strip()
                for value in orders["payment_types"].dropna().tolist()
                for part in value.split(",")
                if part.strip()
            }
        ),
    )
    review_bands = st.sidebar.multiselect(
        "Review band",
        ["Low (1-2)", "Mid (3)", "High (4-5)", "Not reviewed"],
    )
    delayed_view = st.sidebar.selectbox(
        "Delivery status",
        ["All orders", "Delayed only", "On-time only"],
    )
    seller_ids = st.sidebar.multiselect(
        "Seller drill-down",
        sorted(items["seller_id"].dropna().unique().tolist())[:250],
        help="Optional deep dive on specific sellers. The list is trimmed for usability.",
    )

    filtered_orders, filtered_items = _apply_filters(
        orders,
        items,
        date_range=(pd.Timestamp(selected_dates[0]), pd.Timestamp(selected_dates[1])),
        customer_states=customer_states,
        seller_states=seller_states,
        categories=categories,
        payment_types=payment_types,
        review_bands=review_bands,
        delayed_view=delayed_view,
        seller_ids=seller_ids,
    )

    st.sidebar.metric("Filtered orders", format_number(filtered_orders["order_id"].nunique()))
    st.sidebar.metric("Filtered revenue", f"${filtered_orders['order_revenue'].sum():,.0f}")

    if filtered_orders.empty or filtered_items.empty:
        st.warning("No data matches the current filter combination. Adjust the sidebar filters and try again.")
        return

    if page_name == "Executive Overview":
        render_executive_overview(filtered_orders, filtered_items)
    elif page_name == "Customer Analytics":
        render_customer_analytics(filtered_orders, filtered_items)
    elif page_name == "Product & Seller Performance":
        render_product_seller_performance(filtered_orders, filtered_items)
    elif page_name == "Operations & Delivery":
        render_operations_delivery(filtered_orders, filtered_items)
    else:
        render_customer_satisfaction(filtered_orders, filtered_items)

    st.markdown("### Formal Report")
    st.write(
        "Open the formal report menu to either download the branded PDF report or send it by email."
    )
    _formal_report_menu(filtered_orders, filtered_items)


if __name__ == "__main__":
    main()
