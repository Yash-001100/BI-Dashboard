from __future__ import annotations

from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.io as pio
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BRAND = {
    "navy": "#101a6b",
    "gold": "#ffea00",
    "sky": "#6fb0ff",
    "coral": "#ff8a5b",
    "cream": "#f8f4ea",
    "ink": "#243447",
    "mist": "#d9e3f0",
}


def _safe_mean(series: pd.Series) -> float:
    series = pd.to_numeric(series, errors="coerce").dropna()
    return float(series.mean()) if not series.empty else 0.0


def _safe_sum(series: pd.Series) -> float:
    return float(pd.to_numeric(series, errors="coerce").fillna(0).sum())


def _safe_nunique(series: pd.Series) -> int:
    return int(series.dropna().nunique())


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=28,
            alignment=TA_CENTER,
            textColor=colors.HexColor(BRAND["navy"]),
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=20,
            textColor=colors.HexColor(BRAND["navy"]),
            spaceBefore=8,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Narrative",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=16,
            textColor=colors.HexColor(BRAND["ink"]),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Meta",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#5b6472"),
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Confidential",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor(BRAND["navy"]),
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Subhead",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=15,
            textColor=colors.HexColor(BRAND["navy"]),
            spaceBefore=6,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=12,
            textColor=colors.black,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.4,
            leading=12,
            textColor=colors.whitesmoke,
        )
    )
    return styles


def _draw_page_number(canvas, doc) -> None:
    page_num = canvas.getPageNumber()
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#5b6472"))
    canvas.drawRightString(doc.pagesize[0] - 40, 20, f"Page {page_num}")
    canvas.restoreState()


def _logo_path() -> str | None:
    for candidate in (
        Path("assets/mercado-livre-logo.png"),
        Path("assets/mercado-livre-logo.jpg"),
        Path("assets/mercado-livre-logo.jpeg"),
        Path("assets/mercado-livre-logo.webp"),
    ):
        if candidate.exists():
            return str(candidate)
    return None


def _section_table(title: str, rows: list[list[str]], styles):
    data = [[Paragraph(title, styles["TableHeader"]), Paragraph("Value", styles["TableHeader"])]]
    for left, right in rows:
        data.append(
            [
                Paragraph(str(left), styles["TableCell"]),
                Paragraph(str(right), styles["TableCell"]),
            ]
        )
    table = Table(data, colWidths=[2.95 * inch, 3.45 * inch], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND["navy"])),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#fffdfa"), colors.HexColor("#f7f3e8")]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c4cad3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _empty_chart(message: str) -> BytesIO:
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.axis("off")
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=12, color=BRAND["ink"])
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf


def _bar_chart(df: pd.DataFrame, x: str, y: str, title: str, color: str = BRAND["navy"], horizontal: bool = False) -> BytesIO:
    if df.empty:
        return _empty_chart(f"No data available for {title}")
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    if horizontal:
        ax.barh(df[y].astype(str), df[x], color=color)
        ax.set_xlabel(x.replace("_", " ").title())
        ax.set_ylabel("")
    else:
        ax.bar(df[x].astype(str), df[y], color=color)
        ax.set_ylabel(y.replace("_", " ").title())
        ax.set_xlabel("")
    ax.set_title(title, fontsize=12, color=BRAND["navy"], pad=12, fontweight="bold")
    ax.grid(axis="y" if not horizontal else "x", linestyle="--", alpha=0.22)
    ax.set_facecolor("white")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white", dpi=160)
    plt.close(fig)
    buf.seek(0)
    return buf


def _line_chart(df: pd.DataFrame, x: str, y: str, title: str, color: str = BRAND["sky"]) -> BytesIO:
    if df.empty:
        return _empty_chart(f"No data available for {title}")
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.plot(df[x].astype(str), df[y], color=color, marker="o", linewidth=2.2)
    ax.set_title(title, fontsize=12, color=BRAND["navy"], pad=12, fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.22)
    ax.set_xlabel("")
    ax.set_ylabel(y.replace("_", " ").title())
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    plt.xticks(rotation=35, ha="right")
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white", dpi=160)
    plt.close(fig)
    buf.seek(0)
    return buf


def _story_image(buf: BytesIO, width: float = 6.5 * inch, height: float = 3.0 * inch) -> Image:
    buf.seek(0)
    return Image(buf, width=width, height=height, hAlign="CENTER")


def _bullet_paragraphs(items: list[str], style) -> list[Paragraph]:
    return [Paragraph(f"- {item}", style) for item in items]


def _review_benchmark_text(score: float) -> str:
    if score >= 4.2:
        return "above the internal benchmark band used in this report (4.2+ viewed as strong)"
    if score >= 4.0:
        return "slightly below the internal benchmark band used in this report (4.2+ viewed as strong)"
    return "below the internal benchmark band used in this report and should be treated as a service-quality concern"


def _delay_benchmark_text(delay_rate: float) -> str:
    if delay_rate <= 5:
        return "within the internal benchmark band used in this report (under 5% viewed as healthy)"
    if delay_rate <= 8:
        return "above the internal benchmark band used in this report and should be monitored closely"
    return "materially above the internal benchmark band used in this report and likely affecting customer experience"


def _repeat_benchmark_text(repeat_rate: float) -> str:
    if repeat_rate >= 10:
        return "healthy versus the benchmark band used in this report (10%+ viewed as a stronger retention base, though mature e-commerce programs often target materially higher repeat behavior)"
    if repeat_rate >= 5:
        return "below the benchmark band used in this report and suggests retention has room to improve"
    return "critically low versus common e-commerce expectations, where repeat purchase behavior is often expected to trend closer to 15-30% depending on category and lifecycle maturity"


def _metrics(orders: pd.DataFrame, items: pd.DataFrame) -> dict[str, object]:
    customer_rollup = (
        orders.groupby(["customer_unique_id", "customer_state"], as_index=False)
        .agg(total_orders=("order_id", "nunique"), total_spend=("order_revenue", "sum"))
    )
    category_perf = (
        items.groupby("product_category_name_english", as_index=False)
        .agg(revenue=("price", "sum"), freight=("freight_value", "sum"), total_orders=("order_id", "nunique"))
        .sort_values("revenue", ascending=False)
    )
    seller_perf = (
        items.groupby(["seller_id", "seller_state"], as_index=False)
        .agg(revenue=("price", "sum"), total_orders=("order_id", "nunique"))
        .sort_values("revenue", ascending=False)
    )
    delayed_states = (
        orders.groupby("customer_state", as_index=False)
        .agg(delayed_order_pct=("is_delayed", "mean"), total_orders=("order_id", "nunique"))
    )
    delayed_states["delayed_order_pct"] = delayed_states["delayed_order_pct"] * 100
    delayed_states = delayed_states.sort_values("delayed_order_pct", ascending=False)
    scored_orders = orders.dropna(subset=["review_score"]).copy()
    payment_review = (
        scored_orders.assign(primary_payment_type=scored_orders["payment_types"].str.split(",").str[0].str.strip())
        .groupby("primary_payment_type", as_index=False)
        .agg(avg_review_score=("review_score", "mean"), total_orders=("order_id", "nunique"))
        .sort_values("avg_review_score", ascending=False)
    )
    monthly = (
        orders.groupby("order_month", as_index=False)
        .agg(revenue=("order_revenue", "sum"), total_orders=("order_id", "nunique"))
        .sort_values("order_month")
    )
    monthly["month_label"] = pd.to_datetime(monthly["order_month"]).dt.strftime("%b %Y")
    return {
        "customer_rollup": customer_rollup,
        "category_perf": category_perf,
        "seller_perf": seller_perf,
        "delayed_states": delayed_states,
        "scored_orders": scored_orders,
        "payment_review": payment_review,
        "monthly": monthly,
    }


def generate_pdf_report(orders: pd.DataFrame, items: pd.DataFrame) -> bytes:
    styles = _styles()
    metrics = _metrics(orders, items)
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=34,
        leftMargin=34,
        topMargin=36,
        bottomMargin=34,
        title="Mercado Livre Marketplace Performance Report",
    )

    story = []
    logo = _logo_path()
    if logo:
        story.append(Image(logo, width=1.6 * inch, height=1.6 * inch, hAlign="CENTER"))
        story.append(Spacer(1, 8))

    date_min = orders["order_purchase_date"].min()
    date_max = orders["order_purchase_date"].max()
    total_revenue = _safe_sum(orders["order_revenue"])
    total_orders = _safe_nunique(orders["order_id"])
    unique_customers = _safe_nunique(orders["customer_unique_id"])
    avg_order_value = _safe_mean(orders["order_revenue"])
    avg_review = _safe_mean(orders["review_score"])
    delayed_rate = _safe_mean(orders["is_delayed"]) * 100

    story.append(Paragraph("Mercado Livre Marketplace Performance Report", styles["ReportTitle"]))
    story.append(
        Paragraph(
            f"Formal performance report generated from the interactive BI dashboard.<br/>"
            f"Reporting window: {date_min:%d %b %Y} to {date_max:%d %b %Y}",
            styles["Meta"],
        )
    )
    story.append(
        Paragraph(
            "Confidential: this report is intended solely for authorized Mercado Livre leadership, analytics, and operational stakeholders.",
            styles["Confidential"],
        )
    )
    revenue_per_customer = total_revenue / unique_customers if unique_customers else 0
    top_states_full = orders.groupby("customer_state", as_index=False).agg(revenue=("order_revenue", "sum")).sort_values("revenue", ascending=False)
    sp_share = 0.0
    if not top_states_full.empty:
        sp_candidate = top_states_full.iloc[0]
        sp_share = (float(sp_candidate["revenue"]) / total_revenue * 100) if total_revenue else 0
    story.append(Paragraph("Executive Summary", styles["SectionTitle"]))
    story.append(
        Paragraph(
            "This summary isolates the highest-priority takeaways for leadership review before the detailed sections that follow.",
            styles["Narrative"],
        )
    )
    story.append(
        _section_table(
            "Top 5 Takeaways",
            [
                ["1. Revenue Scale", f"${total_revenue:,.2f} across {total_orders:,} orders"],
                ["2. Retention Risk", f"Repeat rate {0 if unique_customers == 0 else ((metrics['customer_rollup']['total_orders'] > 1).mean() * 100):.2f}%"],
                ["3. Service Quality", f"Average review {avg_review:.2f} and delay rate {delayed_rate:.2f}%"],
                ["4. Geographic Concentration", f"Top revenue state contributes {sp_share:.2f}% of filtered revenue"],
                ["5. Immediate Focus", "Retention improvement plus delay reduction"],
            ],
            styles,
        )
    )
    story.append(Spacer(1, 10))
    story.append(Paragraph("Key Risks", styles["Subhead"]))
    story.extend(
        _bullet_paragraphs(
            [
                f"[High Impact] Retention gap: repeat purchase behavior is weak, increasing reliance on one-time buyers for revenue continuity.",
                f"[High Impact] Logistics risk: delayed orders at {delayed_rate:.2f}% may be weakening customer trust and satisfaction.",
                f"[Medium Impact] Geographic concentration: the leading state contributes a disproportionate share of revenue, which can create concentration risk if local performance softens.",
            ],
            styles["Narrative"],
        )
    )
    story.append(Paragraph("Simple Financial View", styles["Subhead"]))
    story.extend(
        _bullet_paragraphs(
            [
                f"Revenue per customer is approximately ${revenue_per_customer:,.2f}, which is a useful base indicator for customer value.",
                f"Average order value is ${avg_order_value:,.2f}, and should be interpreted alongside repeat behavior to understand sustainable customer lifetime value.",
            ],
            styles["Narrative"],
        )
    )

    story.append(PageBreak())

    story.append(Paragraph("Executive Overview", styles["SectionTitle"]))
    story.append(
        Paragraph(
            "This section summarizes commercial health, order activity, customer reach, and service quality. "
            "The figures below are the same business views used in the dashboard, now assembled into a formal report format.",
            styles["Narrative"],
        )
    )
    story.append(
        _section_table(
            "Metric",
            [
                ["Total Revenue", f"${total_revenue:,.2f}"],
                ["Total Orders", f"{total_orders:,}"],
                ["Unique Customers", f"{unique_customers:,}"],
                ["Average Order Value", f"${avg_order_value:,.2f}"],
                ["Average Review Score", f"{avg_review:,.2f}"],
                ["Delayed Order Rate", f"{delayed_rate:.2f}%"],
            ],
            styles,
        )
    )
    story.append(Spacer(1, 10))
    story.append(_story_image(_line_chart(metrics["monthly"].tail(12), "month_label", "revenue", "Revenue Trend by Month")))
    story.append(Spacer(1, 8))
    top_states = orders.groupby("customer_state", as_index=False).agg(revenue=("order_revenue", "sum")).sort_values("revenue", ascending=False).head(8)
    story.append(_story_image(_bar_chart(top_states, "customer_state", "revenue", "Top States by Revenue", BRAND["navy"])))
    story.append(Paragraph("Key Insights", styles["Subhead"]))
    exec_insights = [
        f"[Medium Impact] Revenue reached ${total_revenue:,.2f} across {total_orders:,} orders, showing meaningful marketplace scale in the selected reporting window.",
        f"[Medium Impact] The average review score of {avg_review:.2f} is {_review_benchmark_text(avg_review)}.",
        f"[High Impact] The delayed order rate of {delayed_rate:.2f}% is {_delay_benchmark_text(delayed_rate)}.",
    ]
    if not top_states.empty:
        exec_insights.append(f"[Medium Impact] {top_states.iloc[0]['customer_state']} is the strongest revenue state in the current slice, suggesting geographic concentration in commercial performance.")
    monthly_tail = metrics["monthly"].tail(3)
    if len(monthly_tail) >= 2:
        first_rev = float(monthly_tail.iloc[0]["revenue"])
        last_rev = float(monthly_tail.iloc[-1]["revenue"])
        direction = "grew" if last_rev >= first_rev else "declined"
        exec_insights.append(f"[Low Impact] Recent monthly revenue {direction} across the latest visible periods. If the last visible period drops sharply, this should be treated cautiously because incomplete end-period data can create an artificial decline rather than a true business contraction.")
    story.extend(_bullet_paragraphs(exec_insights, styles["Narrative"]))
    story.append(Paragraph("Business Questions", styles["Subhead"]))
    story.extend(
        _bullet_paragraphs(
            [
                "Which states are driving revenue concentration, and does that create execution risk if demand softens there?",
                "Is the end-of-period revenue movement driven by seasonality, incomplete data, or weakening demand momentum?",
                "Are delivery delays contributing to satisfaction drag in the same states that generate the most revenue?",
            ],
            styles["Narrative"],
        )
    )

    story.append(PageBreak())

    customer_rollup = metrics["customer_rollup"]
    repeat_rate = ((customer_rollup["total_orders"] > 1).mean() * 100) if not customer_rollup.empty else 0
    avg_spend_customer = _safe_mean(customer_rollup["total_spend"])
    top_states_by_customer = (
        customer_rollup.groupby("customer_state", as_index=False)
        .agg(unique_customers=("customer_unique_id", "nunique"))
        .sort_values("unique_customers", ascending=False)
        .head(8)
    )
    story.append(Paragraph("Customer Analytics", styles["SectionTitle"]))
    story.append(
        Paragraph(
            "Customer Analytics explains where demand is concentrated, how strong repeat purchasing is, and which customer segments drive the most spend. "
            "The visual summaries make the page easier to interpret at a glance while the tables preserve the exact figures.",
            styles["Narrative"],
        )
    )
    story.append(
        _section_table(
            "Customer Metric",
            [
                ["Unique Customers", f"{_safe_nunique(customer_rollup['customer_unique_id']):,}"],
                ["Repeat Customer Rate", f"{repeat_rate:.2f}%"],
                ["Average Spend per Customer", f"${avg_spend_customer:,.2f}"],
            ],
            styles,
        )
    )
    story.append(Spacer(1, 10))
    story.append(_story_image(_bar_chart(top_states_by_customer, "customer_state", "unique_customers", "Customers by State", BRAND["gold"])))
    repeat_mix = pd.DataFrame({"segment": ["One-time", "Repeat"], "customers": [(customer_rollup["total_orders"] == 1).sum(), (customer_rollup["total_orders"] > 1).sum()]})
    story.append(Spacer(1, 8))
    story.append(_story_image(_bar_chart(repeat_mix, "segment", "customers", "Repeat vs One-time Customers", BRAND["coral"])))
    story.append(Paragraph("Key Insights", styles["Subhead"]))
    cust_insights = [
        f"[High Impact] The repeat customer rate is {repeat_rate:.2f}%, which is {_repeat_benchmark_text(repeat_rate)}.",
        f"[Medium Impact] Average spend per customer is ${avg_spend_customer:,.2f}, which indicates the value captured per customer is meaningful, but sustainability depends on retention improving.",
    ]
    if not top_states_by_customer.empty:
        cust_insights.append(f"[Medium Impact] {top_states_by_customer.iloc[0]['customer_state']} contributes the highest concentration of customers in the current slice.")
    story.extend(_bullet_paragraphs(cust_insights, styles["Narrative"]))
    story.append(Paragraph("Business Recommendations", styles["Subhead"]))
    story.extend(
        _bullet_paragraphs(
            [
                "Introduce retention actions such as loyalty benefits, post-purchase email journeys, and personalized recommendations to reduce dependence on one-time buyers.",
                "Prioritize customer lifecycle analysis in high-volume states to understand why acquisition is not converting into repeat behavior.",
                "Build a repeat-purchase target into commercial planning so growth is measured beyond first-order acquisition.",
            ],
            styles["Narrative"],
        )
    )
    story.append(Paragraph("Business Questions", styles["Subhead"]))
    story.extend(
        _bullet_paragraphs(
            [
                "Why is repeat purchase behavior limited despite strong order volume?",
                "Are low-repeat segments concentrated in specific states, categories, or delivery experiences?",
                "Which interventions are most likely to increase repeat orders without materially increasing acquisition cost?",
            ],
            styles["Narrative"],
        )
    )

    story.append(PageBreak())

    category_perf = metrics["category_perf"]
    seller_perf = metrics["seller_perf"]
    top_category_name = str(category_perf.iloc[0]["product_category_name_english"]) if not category_perf.empty else "N/A"
    top_category_revenue = float(category_perf.iloc[0]["revenue"]) if not category_perf.empty else 0
    top_seller_id = str(seller_perf.iloc[0]["seller_id"]) if not seller_perf.empty else "N/A"
    top_seller_revenue = float(seller_perf.iloc[0]["revenue"]) if not seller_perf.empty else 0
    story.append(Paragraph("Product & Seller Performance", styles["SectionTitle"]))
    story.append(
        Paragraph(
            "This section shows which product categories and sellers are leading the marketplace. "
            "It combines ranked figures with visual comparisons so commercial winners and freight-heavy areas are easy to identify.",
            styles["Narrative"],
        )
    )
    story.append(
        _section_table(
            "Performance Metric",
            [
                ["Top Category", top_category_name],
                ["Top Category Revenue", f"${top_category_revenue:,.2f}"],
                ["Best Seller", top_seller_id],
                ["Best Seller Revenue", f"${top_seller_revenue:,.2f}"],
                ["Average Revenue per Seller", f"${_safe_mean(seller_perf['revenue']):,.2f}"],
            ],
            styles,
        )
    )
    story.append(Spacer(1, 10))
    story.append(_story_image(_bar_chart(category_perf.head(8), "revenue", "product_category_name_english", "Top Categories by Revenue", BRAND["navy"], horizontal=True)))
    story.append(Spacer(1, 8))
    story.append(_story_image(_bar_chart(seller_perf.head(8), "revenue", "seller_id", "Top Sellers by Revenue", BRAND["sky"], horizontal=True)))
    story.append(Paragraph("Key Insights", styles["Subhead"]))
    prod_insights = [
        f"[Medium Impact] The highest-performing category is {top_category_name}, generating ${top_category_revenue:,.2f} in revenue.",
        f"[Medium Impact] The strongest seller in the current slice is {top_seller_id}, contributing ${top_seller_revenue:,.2f}.",
        f"[Low Impact] Average revenue per seller is ${_safe_mean(seller_perf['revenue']):,.2f}, which helps separate broad marketplace participation from concentrated seller dependence.",
    ]
    if not category_perf.empty:
        freight_leader = category_perf.sort_values("freight", ascending=False).iloc[0]
        prod_insights.append(f"[Medium Impact] {freight_leader['product_category_name_english']} carries the highest freight burden in the current slice, which may pressure contribution margins.")
    story.extend(_bullet_paragraphs(prod_insights, styles["Narrative"]))
    story.append(Paragraph("Business Recommendations", styles["Subhead"]))
    story.extend(
        _bullet_paragraphs(
            [
                "Scale commercial investment behind the top categories while monitoring whether high freight cost is eroding value.",
                "Develop seller performance scorecards that balance revenue contribution with delivery reliability and freight efficiency.",
                "Use category-level profitability analysis to decide whether high-revenue but high-freight categories require pricing or logistics adjustments.",
            ],
            styles["Narrative"],
        )
    )

    story.append(PageBreak())

    delayed_states = metrics["delayed_states"]
    avg_delivery = _safe_mean(orders["delivery_days"])
    on_time_rate = 100 - (_safe_mean(orders["is_delayed"]) * 100)
    avg_freight = _safe_mean(items["freight_value"])
    delivery_by_category = (
        items.groupby("product_category_name_english", as_index=False)
        .agg(avg_delivery_days=("delivery_days", "mean"), total_orders=("order_id", "nunique"))
        .sort_values("avg_delivery_days", ascending=False)
        .head(8)
    )
    story.append(Paragraph("Operations & Delivery", styles["SectionTitle"]))
    story.append(
        Paragraph(
            "Operations & Delivery focuses on logistics speed, reliability, and shipping cost. "
            "The figures below help identify where delay pressure is strongest and which categories may require operational attention.",
            styles["Narrative"],
        )
    )
    story.append(
        _section_table(
            "Operations Metric",
            [
                ["Average Delivery Days", f"{avg_delivery:.2f}"],
                ["On-time Rate", f"{on_time_rate:.2f}%"],
                ["Delayed Order Rate", f"{delayed_rate:.2f}%"],
                ["Average Freight Value", f"${avg_freight:,.2f}"],
            ],
            styles,
        )
    )
    story.append(Spacer(1, 10))
    story.append(_story_image(_bar_chart(delayed_states.head(8), "customer_state", "delayed_order_pct", "Delayed Orders by State", BRAND["coral"])))
    story.append(Spacer(1, 8))
    story.append(_story_image(_bar_chart(delivery_by_category, "avg_delivery_days", "product_category_name_english", "Delivery Days by Category", BRAND["gold"], horizontal=True)))
    story.append(Paragraph("Key Insights", styles["Subhead"]))
    ops_insights = [
        f"[High Impact] Average delivery time is {avg_delivery:.2f} days, while the delayed order rate of {delayed_rate:.2f}% is {_delay_benchmark_text(delayed_rate)}.",
        f"[Medium Impact] Average freight value is ${avg_freight:,.2f}, which should be monitored alongside category mix and seller performance.",
    ]
    if not delayed_states.empty:
        ops_insights.append(f"[High Impact] {delayed_states.iloc[0]['customer_state']} shows the highest delay pressure in the current slice and should be treated as an operational priority.")
    story.extend(_bullet_paragraphs(ops_insights, styles["Narrative"]))
    story.append(Paragraph("Business Recommendations", styles["Subhead"]))
    story.extend(
        _bullet_paragraphs(
            [
                "Prioritize process diagnostics in the highest-delay states to identify carrier, warehouse, or routing bottlenecks.",
                "Track delay rate and freight cost together by seller and category so operational fixes target the most material areas first.",
                "Set service-level thresholds for delayed orders and escalate outlier states or sellers before they affect customer sentiment at scale.",
            ],
            styles["Narrative"],
        )
    )

    story.append(PageBreak())

    scored_orders = metrics["scored_orders"]
    low_review_pct = ((scored_orders["review_score"] <= 2).mean() * 100) if not scored_orders.empty else 0
    delayed_low_reviews = scored_orders[(scored_orders["review_score"] <= 2) & (scored_orders["is_delayed"] == 1)]
    delayed_low_review_pct = (len(delayed_low_reviews) / len(scored_orders) * 100) if not scored_orders.empty else 0
    payment_review = metrics["payment_review"].head(8)
    review_dist = (
        scored_orders.groupby("review_score", as_index=False)
        .agg(review_count=("order_id", "nunique"))
        .sort_values("review_score")
    )
    story.append(Paragraph("Customer Satisfaction", styles["SectionTitle"]))
    story.append(
        Paragraph(
            "Customer Satisfaction links review outcomes with delivery reliability and payment behavior. "
            "The figures make it easier to explain where customer experience is strongest and which operational issues may be dragging ratings lower.",
            styles["Narrative"],
        )
    )
    story.append(
        _section_table(
            "Satisfaction Metric",
            [
                ["Average Review Score", f"{_safe_mean(scored_orders['review_score']):.2f}"],
                ["Low Review Rate", f"{low_review_pct:.2f}%"],
                ["Delayed + Low Review Rate", f"{delayed_low_review_pct:.2f}%"],
            ],
            styles,
        )
    )
    story.append(Spacer(1, 10))
    story.append(_story_image(_bar_chart(review_dist, "review_score", "review_count", "Review Score Distribution", BRAND["gold"])))
    story.append(Spacer(1, 8))
    story.append(_story_image(_bar_chart(payment_review, "primary_payment_type", "avg_review_score", "Review Score by Payment Type", BRAND["navy"])))
    story.append(Paragraph("Key Insights", styles["Subhead"]))
    sat_insights = [
        f"[High Impact] The average review score is {avg_review:.2f}, which is {_review_benchmark_text(avg_review)}.",
        f"[High Impact] The low-review rate is {low_review_pct:.2f}%, and delayed plus low-rated orders account for {delayed_low_review_pct:.2f}% of reviewed orders.",
    ]
    if not payment_review.empty:
        sat_insights.append(f"[Low Impact] {payment_review.iloc[0]['primary_payment_type']} shows the highest average review score in the current slice, suggesting payment experience may shape perceived convenience or trust.")
    story.extend(_bullet_paragraphs(sat_insights, styles["Narrative"]))
    story.append(Paragraph("Business Recommendations", styles["Subhead"]))
    story.extend(
        _bullet_paragraphs(
            [
                "Use low-rated delayed orders as a priority root-cause segment for service recovery and operational investigation.",
                "Review whether payment-type friction, refund handling, or post-purchase communication is influencing satisfaction differences.",
                "Create a closed-loop feedback process linking ratings to delivery quality, seller performance, and customer support action.",
            ],
            styles["Narrative"],
        )
    )

    story.append(Spacer(1, 16))
    story.append(Paragraph("Business Relationships", styles["SectionTitle"]))
    story.append(
        Paragraph(
            "The report is strongest when the sections are read together rather than in isolation. The main business relationships below show how operational and commercial performance connect across the marketplace.",
            styles["Narrative"],
        )
    )
    story.extend(
        _bullet_paragraphs(
            [
                f"Delayed orders at {delayed_rate:.2f}% are likely contributing to weaker customer sentiment, especially within the {delayed_low_review_pct:.2f}% of reviewed orders that are both delayed and poorly rated.",
                f"Low repeat purchase behavior at {repeat_rate:.2f}% suggests satisfaction and retention are key long-term growth levers, not just acquisition volume.",
                "High-performing categories and sellers drive revenue, but if they also carry higher freight or delay pressure, operational weaknesses can dilute commercial gains.",
            ],
            styles["Narrative"],
        )
    )
    story.append(Paragraph("Strategic Recommendations", styles["SectionTitle"]))
    story.extend(
        _bullet_paragraphs(
            [
                "Protect marketplace growth by pairing acquisition strategy with a measurable retention program aimed at improving repeat purchase behavior.",
                "Reduce operational risk by targeting the highest-delay states, sellers, and categories with service-level intervention plans.",
                "Scale investment behind leading categories and sellers only where logistics and satisfaction performance are supportive of sustainable growth.",
                "Adopt an operating rhythm that reviews revenue, delay, and review-score movement together rather than as separate reporting streams.",
            ],
            styles["Narrative"],
        )
    )
    story.append(Paragraph("Conclusion", styles["SectionTitle"]))
    story.append(
        Paragraph(
            "Overall, the report shows that marketplace performance should be assessed as a balance between growth, operational consistency, and customer experience. "
            "Revenue, order volume, customer reach, seller strength, logistics efficiency, and review outcomes should be monitored together, because changes in one area can materially influence the others. "
            "The strongest business decisions will come from using these findings to protect delivery quality, strengthen high-performing categories and sellers, and improve customer satisfaction in the areas where performance pressure is most visible.",
            styles["Narrative"],
        )
    )
    story.append(Paragraph("Impact Statement", styles["Subhead"]))
    story.extend(
        _bullet_paragraphs(
            [
                "Identified the main revenue drivers and the states, categories, and sellers shaping marketplace performance.",
                "Highlighted retention weakness as a strategic business risk through the low repeat-customer pattern.",
                "Connected logistics reliability to satisfaction outcomes and surfaced practical actions to improve service quality and sustainable growth.",
            ],
            styles["Narrative"],
        )
    )

    doc.build(story, onFirstPage=_draw_page_number, onLaterPages=_draw_page_number)
    return buffer.getvalue()


def generate_html_report(orders: pd.DataFrame, items: pd.DataFrame) -> str:
    metrics = _metrics(orders, items)
    date_min = orders["order_purchase_date"].min()
    date_max = orders["order_purchase_date"].max()

    monthly = metrics["monthly"].copy()
    monthly_fig = px.line(monthly, x="month_label", y="revenue", markers=True, title="Revenue Trend by Month", color_discrete_sequence=[BRAND["sky"]])
    state_fig = px.bar(
        orders.groupby("customer_state", as_index=False).agg(revenue=("order_revenue", "sum")).sort_values("revenue", ascending=False).head(10),
        x="customer_state",
        y="revenue",
        title="Top States by Revenue",
        color="revenue",
        color_continuous_scale=[BRAND["mist"], BRAND["navy"]],
    )
    customer_state_fig = px.bar(
        metrics["customer_rollup"].groupby("customer_state", as_index=False).agg(unique_customers=("customer_unique_id", "nunique")).sort_values("unique_customers", ascending=False).head(10),
        x="customer_state",
        y="unique_customers",
        title="Customers by State",
        color_discrete_sequence=[BRAND["gold"]],
    )
    category_fig = px.bar(
        metrics["category_perf"].head(10),
        x="revenue",
        y="product_category_name_english",
        title="Top Categories by Revenue",
        orientation="h",
        color="revenue",
        color_continuous_scale=[BRAND["mist"], BRAND["navy"]],
    )
    delay_fig = px.bar(
        metrics["delayed_states"].head(10),
        x="customer_state",
        y="delayed_order_pct",
        title="Delayed Orders by State",
        color="delayed_order_pct",
        color_continuous_scale=[BRAND["cream"], BRAND["coral"]],
    )
    review_fig = px.bar(
        metrics["scored_orders"].groupby("review_score", as_index=False).agg(review_count=("order_id", "nunique")).sort_values("review_score"),
        x="review_score",
        y="review_count",
        title="Review Score Distribution",
        color_discrete_sequence=[BRAND["gold"]],
    )

    figures = [monthly_fig, state_fig, customer_state_fig, category_fig, delay_fig, review_fig]
    for fig in figures:
        fig.update_layout(
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(color="#243447"),
            margin=dict(l=30, r=20, t=50, b=30),
        )

    fig_html = "".join(pio.to_html(fig, include_plotlyjs="cdn" if i == 0 else False, full_html=False) for i, fig in enumerate(figures))
    logo_html = ""
    logo = _logo_path()
    if logo:
        logo_uri = Path(logo).as_posix()
        logo_html = f'<img src="{logo_uri}" alt="Mercado Livre logo" style="width:120px;border-radius:16px;background:#fff;padding:10px;border:1px solid #d7dce5;" />'

    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Mercado Livre Interactive Report</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      background: linear-gradient(180deg, #f7f8fb 0%, #eef2f8 100%);
      color: #243447;
      margin: 0;
      padding: 32px;
    }}
    .shell {{ max-width: 1100px; margin: 0 auto; }}
    .hero {{
      display: flex; gap: 20px; align-items: center;
      background: white; border-radius: 24px; padding: 24px;
      box-shadow: 0 12px 30px rgba(16,26,107,0.08);
      border: 1px solid #dbe2ee;
    }}
    .section {{
      background: white; border-radius: 24px; padding: 24px; margin-top: 22px;
      box-shadow: 0 12px 30px rgba(16,26,107,0.06);
      border: 1px solid #dbe2ee;
    }}
    h1, h2 {{ color: #101a6b; }}
    .meta {{ color: #667085; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      margin-top: 18px;
    }}
    .metric {{
      background: #fffdfa;
      border: 1px solid #e6e2d8;
      border-radius: 18px;
      padding: 16px;
    }}
    .metric-label {{ font-size: 12px; text-transform: uppercase; color: #667085; letter-spacing: 0.07em; }}
    .metric-value {{ font-size: 30px; color: #101a6b; margin-top: 8px; font-weight: 700; }}
    .note {{ line-height: 1.7; }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="hero">
      <div>{logo_html}</div>
      <div>
        <h1>Mercado Livre Interactive Performance Report</h1>
        <p class="meta">Reporting window: {date_min:%d %b %Y} to {date_max:%d %b %Y}</p>
        <p class="note">This interactive report keeps the dashboard figures, explanations, and hoverable charts together in a single browser-ready document so the business story is easier to explore and understand.</p>
      </div>
    </div>

    <div class="section">
      <h2>Executive Overview</h2>
      <p class="note">This section provides the top-level view of marketplace health across revenue, order volume, customer reach, and service quality.</p>
      <div class="grid">
        <div class="metric"><div class="metric-label">Total Revenue</div><div class="metric-value">${_safe_sum(orders['order_revenue']):,.0f}</div></div>
        <div class="metric"><div class="metric-label">Total Orders</div><div class="metric-value">{_safe_nunique(orders['order_id']):,}</div></div>
        <div class="metric"><div class="metric-label">Unique Customers</div><div class="metric-value">{_safe_nunique(orders['customer_unique_id']):,}</div></div>
        <div class="metric"><div class="metric-label">Average Review Score</div><div class="metric-value">{_safe_mean(orders['review_score']):.2f}</div></div>
      </div>
    </div>

    <div class="section">
      <h2>Interactive Figures</h2>
      <p class="note">Hover, zoom, and inspect each chart directly in the browser.</p>
      {fig_html}
    </div>
  </div>
</body>
</html>
"""
