from __future__ import annotations

import html
import re
from uuid import uuid4
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

DEFAULT_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/9/9d/MercadoLibre_logo.PNG"


def apply_global_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #f4f2eb;
            --navy: #101a6b;
            --charcoal: #111827;
            --slate: #1f2937;
            --gold: #ffea00;
            --cream: #f8f4ea;
            --mist: #d9e3f0;
            --line: rgba(244, 242, 235, 0.14);
            --card-line: rgba(16, 26, 107, 0.12);
            --body-copy: rgba(17, 24, 39, 0.78);
        }

        .stApp {
            background:
                radial-gradient(circle at top right, rgba(255, 234, 0, 0.16), transparent 28%),
                radial-gradient(circle at bottom left, rgba(111, 176, 255, 0.14), transparent 24%),
                linear-gradient(180deg, #0f172a 0%, #172033 38%, #0b1220 100%);
            color: var(--ink);
        }

        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(16, 26, 107, 0.98), rgba(10, 18, 44, 0.98));
            border-right: 1px solid rgba(255, 234, 0, 0.14);
        }

        [data-testid="stSidebar"] * {
            color: #f9f6ef;
        }

        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.07);
            border: 1px solid rgba(255, 234, 0, 0.18);
            border-radius: 18px;
            padding: 0.85rem;
        }

        [data-testid="stSidebar"] [data-testid="stImage"] img {
            background: rgba(255, 255, 255, 0.94);
            border-radius: 18px;
            padding: 0.55rem;
            border: 1px solid rgba(255, 234, 0, 0.18);
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.18);
        }

        .page-shell {
            padding: 0.2rem 0 0.8rem 0;
        }

        .kpi-row {
            margin-bottom: 0.65rem;
        }

        .section-tight {
            margin-top: -0.15rem;
        }

        .brand-hero {
            display: flex;
            align-items: center;
            gap: 1.2rem;
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(244, 239, 226, 0.95));
            border: 1px solid rgba(255, 234, 0, 0.28);
            border-radius: 24px;
            box-shadow: 0 18px 36px rgba(0, 0, 0, 0.16);
            padding: 1.15rem 1.15rem;
            margin-bottom: 1rem;
        }

        .brand-logo-wrap img {
            width: 180px;
            max-width: 100%;
            border-radius: 18px;
            background: white;
            padding: 0.7rem;
            border: 1px solid rgba(16, 26, 107, 0.1);
            box-shadow: 0 12px 24px rgba(16, 26, 107, 0.08);
        }

        .brand-copy {
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
        }

        .brand-kicker {
            font-family: "Trebuchet MS", sans-serif;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.73rem;
            color: rgba(248, 244, 234, 0.78);
        }

        .brand-name {
            font-family: "Georgia", "Palatino Linotype", serif;
            font-size: 1.7rem;
            color: #fffdf6;
        }

        .brand-desc {
            font-family: "Trebuchet MS", sans-serif;
            color: rgba(248, 244, 234, 0.86);
            line-height: 1.55;
            max-width: 42rem;
        }

        .page-title {
            font-family: "Georgia", "Palatino Linotype", serif;
            font-size: 2.3rem;
            color: #f8f6ef;
            margin-bottom: 0.15rem;
            letter-spacing: 0.01em;
        }

        .page-subtitle {
            font-family: "Trebuchet MS", sans-serif;
            color: rgba(244, 242, 235, 0.8);
            max-width: 62rem;
            margin-bottom: 1.1rem;
            line-height: 1.6;
        }

        .metric-card {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.97), rgba(246, 241, 229, 0.96));
            border: 1px solid var(--card-line);
            border-radius: 22px;
            padding: 1rem 1rem 0.95rem 1rem;
            box-shadow: 0 16px 30px rgba(0, 0, 0, 0.12);
            min-height: 132px;
        }

        .metric-label {
            font-family: "Trebuchet MS", sans-serif;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            font-size: 0.76rem;
            color: rgba(16, 26, 107, 0.62);
        }

        .metric-value {
            font-family: "Georgia", "Palatino Linotype", serif;
            font-size: 1.9rem;
            color: var(--navy);
            margin-top: 0.45rem;
            margin-bottom: 0.35rem;
        }

        .metric-note {
            font-family: "Trebuchet MS", sans-serif;
            color: var(--body-copy);
            line-height: 1.45;
            font-size: 0.92rem;
        }

        .insight-box {
            background: linear-gradient(135deg, rgba(16, 26, 107, 0.98), rgba(25, 36, 78, 0.98));
            color: #f7f5ef;
            padding: 1rem 1.1rem;
            border-radius: 20px;
            border: 1px solid rgba(255, 234, 0, 0.18);
            box-shadow: 0 14px 30px rgba(0, 0, 0, 0.18);
            margin: 0.75rem 0 1rem 0;
            line-height: 1.6;
            font-family: "Trebuchet MS", sans-serif;
        }

        .insight-title {
            display: inline-block;
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.5rem;
            color: rgba(247, 245, 239, 0.76);
        }

        [data-testid="stPlotlyChart"] {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.97), rgba(247, 243, 234, 0.95));
            border: 1px solid var(--card-line);
            border-radius: 22px;
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12);
            padding: 0.25rem;
        }

        .block-container {
            padding-top: 1rem;
        }

        .auth-shell {
            margin-top: 0;
            padding-top: 0;
            min-height: auto;
        }

        .auth-panel {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.97), rgba(247, 243, 234, 0.95));
            border: 1px solid rgba(255, 234, 0, 0.24);
            border-radius: 28px;
            box-shadow: 0 18px 36px rgba(0, 0, 0, 0.16);
            padding: 1.4rem 1.5rem;
        }

        .auth-brand {
            background: linear-gradient(160deg, rgba(16, 26, 107, 0.96), rgba(13, 23, 58, 0.98));
            border: 1px solid rgba(255, 234, 0, 0.18);
            border-radius: 28px;
            box-shadow: 0 18px 36px rgba(0, 0, 0, 0.2);
            padding: 1.6rem 1.5rem;
            min-height: 100%;
            margin-top: 0.9rem;
        }

        .auth-brand-logo {
            margin-top: 1rem;
            margin-bottom: 1.2rem;
        }

        .auth-kicker {
            font-family: "Trebuchet MS", sans-serif;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.75rem;
            color: rgba(255, 234, 0, 0.9);
            margin-bottom: 0.45rem;
        }

        .auth-title {
            font-family: "Georgia", "Palatino Linotype", serif;
            font-size: 2.5rem;
            line-height: 1.1;
            color: #fffdf6;
            margin-bottom: 0.8rem;
        }

        .auth-copy {
            font-family: "Trebuchet MS", sans-serif;
            color: rgba(248, 244, 234, 0.85);
            line-height: 1.7;
            margin-bottom: 1rem;
        }

        .auth-bullets {
            font-family: "Trebuchet MS", sans-serif;
            color: rgba(248, 244, 234, 0.88);
            line-height: 1.8;
        }

        .auth-bullets div {
            margin-bottom: 0.35rem;
        }

        .auth-form-title {
            font-family: "Georgia", "Palatino Linotype", serif;
            font-size: 1.85rem;
            color: #fffdf6;
            margin-bottom: 0.35rem;
        }

        .auth-form-copy {
            font-family: "Trebuchet MS", sans-serif;
            color: rgba(248, 244, 234, 0.82);
            line-height: 1.65;
            margin-bottom: 0.9rem;
        }

        .auth-note {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 234, 0, 0.12);
            border-radius: 16px;
            padding: 0.85rem 1rem;
            color: rgba(248, 244, 234, 0.8);
            font-family: "Trebuchet MS", sans-serif;
            line-height: 1.55;
            margin-top: 0.85rem;
        }

        .terms-scroll-box {
            max-height: 220px;
            overflow-y: auto;
            background: #ffffff;
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            color: #172033;
            font-family: "Trebuchet MS", sans-serif;
            line-height: 1.65;
            margin: 0.35rem 0 0.75rem 0;
            white-space: normal;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.4);
        }

        .terms-link-label {
            font-family: "Trebuchet MS", sans-serif;
            color: rgba(248, 244, 234, 0.82);
            margin: 0.2rem 0 0.35rem 0;
        }

        .stButton button[kind="tertiary"] {
            background: transparent !important;
            border: 0 !important;
            padding: 0 !important;
            min-height: auto !important;
            color: #8fc3ff !important;
            text-decoration: underline !important;
            box-shadow: none !important;
            justify-content: flex-start !important;
            font-family: "Trebuchet MS", sans-serif;
            font-weight: 700;
        }

        .stButton button[kind="tertiary"]:hover {
            color: #c5defe !important;
            background: transparent !important;
        }

        .terms-modal-card {
            background: #fffdf9;
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 22px;
            padding: 0.85rem 0.9rem 1rem 0.9rem;
        }

        .terms-logo-wrap {
            display: flex;
            justify-content: center;
            margin: 0.6rem 0 1.3rem 0;
        }

        .terms-logo-wrap img {
            width: 120px;
            height: auto;
            background: #ffffff;
            border-radius: 18px;
            padding: 0.7rem;
            border: 1px solid rgba(16, 26, 107, 0.1);
            box-shadow: 0 10px 22px rgba(16, 26, 107, 0.08);
            display: block;
        }

        .terms-modal-heading {
            text-align: center;
            font-family: "Georgia", "Palatino Linotype", serif;
            font-size: 1.45rem;
            color: #101a6b;
            margin-bottom: 0.75rem;
            font-weight: 700;
        }

        .terms-modal-list {
            margin: 0;
            padding-left: 1.25rem;
            color: #172033;
        }

        .terms-modal-list li {
            margin-bottom: 0.7rem;
            padding-left: 0.2rem;
        }

        .auth-social-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.85rem;
            margin: 0.65rem 0 1rem 0;
        }

        .auth-social-link {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.65rem;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 234, 0, 0.14);
            color: #fffdf6 !important;
            text-decoration: none !important;
            border-radius: 16px;
            padding: 0.85rem 0.9rem;
            font-family: "Trebuchet MS", sans-serif;
            font-weight: 700;
            transition: transform 0.15s ease, border-color 0.15s ease, background 0.15s ease;
        }

        .auth-social-link:hover {
            transform: translateY(-1px);
            border-color: rgba(255, 234, 0, 0.35);
            background: rgba(255, 255, 255, 0.08);
        }

        .auth-social-icon {
            width: 2rem;
            height: 2rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            background: #fff;
            color: #101a6b;
            font-weight: 800;
            font-size: 1rem;
            flex-shrink: 0;
            overflow: hidden;
        }

        .auth-social-icon svg {
            width: 100%;
            height: 100%;
            display: block;
        }

        .auth-social-icon.microsoft {
            background: transparent;
            border-radius: 8px;
        }

        .auth-social-icon.gmail {
            background: transparent;
            border-radius: 8px;
            padding: 0.1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="page-shell">
            <div class="page-title">{html.escape(title)}</div>
            <div class="page-subtitle">{html.escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def resolve_logo_source() -> str:
    for relative_path in (
        "assets/mercado-livre-logo.png",
        "assets/mercado-livre-logo.jpg",
        "assets/mercado-livre-logo.jpeg",
        "assets/mercado-livre-logo.webp",
    ):
        asset_path = Path(relative_path)
        if asset_path.exists():
            return str(asset_path)
    return DEFAULT_LOGO_URL


def render_branding() -> None:
    st.sidebar.markdown("### Mercado Livre")

    st.markdown('<div class="brand-hero">', unsafe_allow_html=True)
    logo_col, text_col = st.columns((1, 4))
    with logo_col:
        st.image(resolve_logo_source(), use_container_width=True)
    with text_col:
        st.markdown(
            """
            <div class="brand-copy">
                <div class="brand-kicker">Company Context</div>
                <div class="brand-name">Mercado Livre Analytics Portal</div>
                <div class="brand-desc">
                    This dashboard provides a comprehensive overview of Mercado Libre’s
                    marketplace performance, highlighting key metrics across revenue,
                    customer behavior, order trends, logistics efficiency, and customer
                    satisfaction to support data-driven decision-making.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def _metric_value_markup(value: str) -> str:
    match = re.search(r"-?[\d,]+(?:\.\d+)?", value)
    if not match:
        return html.escape(value)

    numeric_text = match.group(0)
    prefix = value[: match.start()]
    suffix = value[match.end() :]
    numeric_value = float(numeric_text.replace(",", ""))
    decimals = len(numeric_text.split(".")[1]) if "." in numeric_text else 0
    element_id = f"metric-{uuid4().hex}"
    initial_value = f"{prefix}{'0' if decimals == 0 else f'{0:.{decimals}f}'}{suffix}"

    return f"""
    <span
        id="{element_id}"
        data-target="{numeric_value}"
        data-prefix="{html.escape(prefix, quote=True)}"
        data-suffix="{html.escape(suffix, quote=True)}"
        data-decimals="{decimals}"
    >{html.escape(initial_value)}</span>
    <script>
    (function() {{
        const el = document.getElementById("{element_id}");
        if (!el || el.dataset.animated === "1") return;
        el.dataset.animated = "1";

        const target = Number(el.dataset.target || "0");
        const prefix = el.dataset.prefix || "";
        const suffix = el.dataset.suffix || "";
        const decimals = Number(el.dataset.decimals || "0");
        const duration = 1100;

        function formatValue(value) {{
            return prefix + value.toLocaleString(undefined, {{
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals
            }}) + suffix;
        }}

        function animate(startTime) {{
            function step(now) {{
                const progress = Math.min((now - startTime) / duration, 1);
                const eased = 1 - Math.pow(1 - progress, 3);
                const current = target * eased;
                el.textContent = formatValue(progress >= 1 ? target : current);
                if (progress < 1) {{
                    window.requestAnimationFrame(step);
                }}
            }}
            window.requestAnimationFrame(step);
        }}

        window.requestAnimationFrame(animate);
    }})();
    </script>
    """


def metric_card(label: str, value: str, note: str) -> None:
    match = re.search(r"-?[\d,]+(?:\.\d+)?", value)
    value_markup = html.escape(value)

    if match:
        numeric_text = match.group(0)
        prefix = value[: match.start()]
        suffix = value[match.end() :]
        numeric_value = float(numeric_text.replace(",", ""))
        decimals = len(numeric_text.split(".")[1]) if "." in numeric_text else 0
        element_id = f"metric-{uuid4().hex}"
        initial_value = f"{prefix}{'0' if decimals == 0 else f'{0:.{decimals}f}'}{suffix}"
        value_markup = f'<span id="{element_id}">{html.escape(initial_value)}</span>'
        script_block = f"""
        <script>
        (function() {{
            const el = document.getElementById("{element_id}");
            if (!el) return;
            const target = {numeric_value};
            const decimals = {decimals};
            const prefix = {prefix!r};
            const suffix = {suffix!r};
            const duration = 1200;
            const start = performance.now();

            function formatValue(value) {{
                return prefix + value.toLocaleString(undefined, {{
                    minimumFractionDigits: decimals,
                    maximumFractionDigits: decimals
                }}) + suffix;
            }}

            function step(now) {{
                const progress = Math.min((now - start) / duration, 1);
                const eased = 1 - Math.pow(1 - progress, 3);
                const current = target * eased;
                el.textContent = formatValue(progress >= 1 ? target : current);
                if (progress < 1) {{
                    requestAnimationFrame(step);
                }}
            }}

            requestAnimationFrame(step);
        }})();
        </script>
        """
    else:
        script_block = ""

    components.html(
        f"""
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    background: transparent;
                    font-family: "Trebuchet MS", sans-serif;
                }}
                .metric-card {{
                    background: linear-gradient(180deg, rgba(255, 255, 255, 0.97), rgba(246, 241, 229, 0.96));
                    border: 1px solid rgba(16, 26, 107, 0.12);
                    border-radius: 22px;
                    padding: 1rem 1rem 0.95rem 1rem;
                    box-shadow: 0 16px 30px rgba(0, 0, 0, 0.12);
                    min-height: 132px;
                    box-sizing: border-box;
                }}
                .metric-label {{
                    text-transform: uppercase;
                    letter-spacing: 0.07em;
                    font-size: 0.76rem;
                    color: rgba(16, 26, 107, 0.62);
                }}
                .metric-value {{
                    font-family: "Georgia", "Palatino Linotype", serif;
                    font-size: 1.9rem;
                    color: #101a6b;
                    margin-top: 0.45rem;
                    margin-bottom: 0.35rem;
                }}
                .metric-note {{
                    color: rgba(17, 24, 39, 0.78);
                    line-height: 1.45;
                    font-size: 0.92rem;
                }}
            </style>
        </head>
        <body>
            <div class="metric-card">
                <div class="metric-label">{html.escape(label)}</div>
                <div class="metric-value">{value_markup}</div>
                <div class="metric-note">{html.escape(note)}</div>
            </div>
            {script_block}
        </body>
        </html>
        """,
        height=180,
    )


def insight_box(text: str) -> None:
    st.markdown(
        f"""
        <div class="insight-box">
            <div class="insight-title">Insight Callout</div>
            <div>{html.escape(text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_number(value: int) -> str:
    return f"{int(value):,}"


def open_kpi_row() -> None:
    st.markdown('<div class="kpi-row">', unsafe_allow_html=True)


def close_kpi_row() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def open_tight_section() -> None:
    st.markdown('<div class="section-tight">', unsafe_allow_html=True)


def close_tight_section() -> None:
    st.markdown("</div>", unsafe_allow_html=True)
