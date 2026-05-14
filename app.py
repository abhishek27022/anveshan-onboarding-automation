"""
Chemelex Demand Forecasting Cockpit  —  Executive view.

Plain-English dashboard for senior leadership: forecast accuracy, where we
are off-track, and how AI compares to the manual demand plan.

Data files (auto-loaded if present in the working directory):
    corrected_dashboard_forecast_accuracy_levelled.csv   (required)
    ibp_vs_model_comparison_2025.csv                     (optional)
    ibp_reconciliation.csv                               (optional)
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# =============================================================================
# CONFIG
# =============================================================================
st.set_page_config(
    page_title="Chemelex Demand Forecasting Cockpit",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PRIMARY_FILE     = "corrected_dashboard_forecast_accuracy_levelled.csv"
COMPARISON_FILE  = "ibp_vs_model_comparison_2025.csv"
RECON_FILE       = "ibp_reconciliation.csv"

OFFICIAL_ZONES = [
    "BUFFER (at CODP)",
    "Pull / FG",
    "Pull / Kanban",
    "Push / MPS",
    "Push / RM",
]

LEVELS       = ["Total", "CODP Zone", "Plant", "Product Category", "Group"]
MONTH_NAMES  = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

TARGET_LABELS = {
    "order_value_usd": "Revenue ($)",
    "order_qty_bu":    "Volume (units)",
}

# =============================================================================
# THEME
# =============================================================================
if "theme" not in st.session_state:
    st.session_state.theme = "Light"


# =============================================================================
# THEME — Design System v2
# =============================================================================
if "theme" not in st.session_state:
    st.session_state.theme = "Light"


def get_theme() -> dict:
    if st.session_state.theme == "Dark":
        return {
            "bg":            "#0a0e1a",
            "bg_grad_a":     "#0a0e1a",
            "bg_grad_b":     "#0f1729",
            "surface":       "#111827",
            "surface_2":     "#1f2937",
            "surface_glass": "rgba(17, 24, 39, 0.72)",
            "border":        "#1f2937",
            "border_strong": "#374151",
            "text":          "#f1f5f9",
            "text_muted":    "#94a3b8",
            "text_subtle":   "#64748b",
            "primary":       "#3b82f6",
            "primary_soft":  "rgba(59, 130, 246, 0.15)",
            "accent":        "#06b6d4",
            "success":       "#10b981",
            "success_soft":  "rgba(16, 185, 129, 0.15)",
            "warning":       "#f59e0b",
            "warning_soft":  "rgba(245, 158, 11, 0.15)",
            "danger":        "#ef4444",
            "danger_soft":   "rgba(239, 68, 68, 0.15)",
            "actual":        "#60a5fa",
            "ai":            "#10b981",
            "manual":        "#f59e0b",
            "plotly":        "plotly_dark",
            "warn_bg":       "#3a2e15",
            "shadow":        "0 8px 32px rgba(0, 0, 0, 0.4)",
            "shadow_sm":     "0 2px 8px rgba(0, 0, 0, 0.3)",
            "grid":          "rgba(148, 163, 184, 0.08)",
        }
    return {
        "bg":             "#f6f8fc",
        "bg_grad_a":      "#f6f8fc",
        "bg_grad_b":      "#eef2f7",
        "surface":        "#ffffff",
        "surface_2":      "#f8fafc",
        "surface_glass":  "rgba(255, 255, 255, 0.82)",
        "border":         "#e5e9f0",
        "border_strong":  "#cbd5e1",
        "text":           "#0b1220",
        "text_muted":     "#475569",
        "text_subtle":    "#94a3b8",
        "primary":        "#0088c2",      # algo8 brand blue
        "primary_soft":   "rgba(0, 136, 194, 0.10)",
        "accent":         "#0ea5e9",
        "success":        "#16a34a",
        "success_soft":   "rgba(22, 163, 74, 0.10)",
        "warning":        "#ef8a00",      # algo8 orange
        "warning_soft":   "rgba(239, 138, 0, 0.10)",
        "danger":         "#dc2626",
        "danger_soft":    "rgba(220, 38, 38, 0.10)",
        "actual":         "#0088c2",
        "ai":             "#16a34a",
        "manual":         "#ef8a00",
        "plotly":         "plotly_white",
        "warn_bg":        "#fff7ec",
        "shadow":         "0 8px 28px rgba(15, 23, 42, 0.06)",
        "shadow_sm":      "0 2px 8px rgba(15, 23, 42, 0.04)",
        "grid":           "rgba(15, 23, 42, 0.06)",
    }


def inject_css() -> None:
    c = get_theme()
    is_dark = st.session_state.theme == "Dark"
    css = f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
    <style>
      /* ============ GLOBAL RESET ============ */
      html, body, [class*="css"], .stApp, .stMarkdown, .stText {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
      }}
      .stApp {{
        background:
          radial-gradient(1200px 600px at 0% 0%, {c['primary_soft']} 0%, transparent 50%),
          radial-gradient(1000px 500px at 100% 100%, {c['warning_soft']} 0%, transparent 60%),
          linear-gradient(180deg, {c['bg_grad_a']} 0%, {c['bg_grad_b']} 100%);
        color: {c['text']};
        min-height: 100vh;
      }}
      .block-container {{
        padding-top: 1.1rem;
        padding-bottom: 2.5rem;
        max-width: 1500px;
      }}
      footer  {{ visibility: hidden; }}
      #MainMenu {{ visibility: hidden; }}
      header[data-testid="stHeader"] {{ background: transparent; }}

      /* ============ ANIMATIONS ============ */
      @keyframes cx-fade-up {{
        from {{ opacity: 0; transform: translateY(8px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
      }}
      @keyframes cx-shimmer {{
        0%   {{ background-position: -200% 0; }}
        100% {{ background-position: 200% 0; }}
      }}
      @keyframes cx-pulse-soft {{
        0%, 100% {{ box-shadow: 0 0 0 0 {c['primary_soft']}; }}
        50%      {{ box-shadow: 0 0 0 6px transparent; }}
      }}
      @keyframes cx-count-up {{
        from {{ opacity: 0.4; transform: scale(0.96); }}
        to   {{ opacity: 1;   transform: scale(1); }}
      }}

      /* ============ HEADER ============ */
      .cx-header {{
        background:
          linear-gradient(135deg, {c['primary']} 0%, {'#1e40af' if not is_dark else '#1e3a8a'} 100%);
        padding: 22px 28px;
        border-radius: 18px;
        margin-bottom: 18px;
        color: white;
        box-shadow: {c['shadow']};
        position: relative;
        overflow: hidden;
        animation: cx-fade-up 0.5s ease both;
      }}
      .cx-header::before {{
        content: "";
        position: absolute;
        inset: 0;
        background:
          radial-gradient(600px 200px at 100% 0%, rgba(255,255,255,0.18) 0%, transparent 60%),
          radial-gradient(400px 200px at 0% 100%, rgba(255,255,255,0.10) 0%, transparent 60%);
        pointer-events: none;
      }}
      .cx-header-row {{
        display: flex; justify-content: space-between; align-items: center;
        position: relative; z-index: 1; gap: 16px; flex-wrap: wrap;
      }}
      .cx-header-brand {{
        display: flex; align-items: center; gap: 14px;
      }}
      .cx-brand-mark {{
        width: 44px; height: 44px; border-radius: 12px;
        background: rgba(255,255,255,0.18);
        backdrop-filter: blur(10px);
        display: grid; place-items: center;
        font-size: 22px;
        border: 1px solid rgba(255,255,255,0.25);
      }}
      .cx-header h1 {{
        color: white; margin: 0;
        font-size: 22px; font-weight: 700;
        letter-spacing: -0.02em;
      }}
      .cx-header .cx-header-sub {{
        color: rgba(255,255,255,0.86); margin: 3px 0 0 0;
        font-size: 12.5px; font-weight: 400;
      }}
      .cx-header-pills {{
        display: flex; gap: 8px; align-items: center;
      }}
      .cx-pill {{
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(255,255,255,0.15);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.22);
        color: white;
        padding: 6px 12px; border-radius: 999px;
        font-size: 12px; font-weight: 500;
      }}
      .cx-pill .dot {{
        width: 6px; height: 6px; border-radius: 50%;
        background: #4ade80;
        box-shadow: 0 0 0 3px rgba(74, 222, 128, 0.25);
      }}

      /* ============ KPI CARDS ============ */
      .cx-card {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 14px;
        padding: 16px 18px;
        height: 100%;
        box-shadow: {c['shadow_sm']};
        transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
        animation: cx-fade-up 0.4s ease both;
        position: relative;
        overflow: hidden;
      }}
      .cx-card::after {{
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, {c['primary']} 0%, {c['accent']} 100%);
        opacity: 0;
        transition: opacity .2s ease;
      }}
      .cx-card:hover {{
        transform: translateY(-2px);
        box-shadow: {c['shadow']};
        border-color: {c['border_strong']};
      }}
      .cx-card:hover::after {{ opacity: 1; }}
      .cx-card-title {{
        color: {c['text_muted']};
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 8px;
        font-weight: 600;
        display: flex; align-items: center; gap: 6px;
      }}
      .cx-card-value {{
        color: {c['text']};
        font-size: 26px;
        font-weight: 700;
        letter-spacing: -0.02em;
        line-height: 1.1;
        animation: cx-count-up 0.5s ease both;
        font-variant-numeric: tabular-nums;
      }}
      .cx-card-delta {{
        font-size: 12px;
        margin-top: 6px;
        font-weight: 500;
        display: inline-flex; align-items: center; gap: 4px;
      }}
      .cx-delta-pos     {{ color: {c['success']}; }}
      .cx-delta-neg     {{ color: {c['danger']};  }}
      .cx-delta-neutral {{ color: {c['text_muted']}; }}
      .cx-delta-pos::before     {{ content: "▲"; font-size: 9px; }}
      .cx-delta-neg::before     {{ content: "▼"; font-size: 9px; }}

      /* ============ SECTION HEADER ============ */
      .cx-section {{
        color: {c['text']};
        font-size: 15px;
        font-weight: 700;
        letter-spacing: -0.01em;
        margin: 22px 0 10px 0;
        padding-bottom: 8px;
        border-bottom: 1px solid {c['border']};
        display: flex; align-items: center; gap: 8px;
      }}
      .cx-section::before {{
        content: "";
        width: 4px; height: 16px;
        background: linear-gradient(180deg, {c['primary']}, {c['accent']});
        border-radius: 2px;
      }}

      /* ============ INSIGHT GRADIENT CARDS ============ */
      .cx-insight {{
        border-radius: 14px;
        padding: 16px 20px;
        color: white;
        height: 100%;
        box-shadow: {c['shadow_sm']};
        position: relative; overflow: hidden;
        animation: cx-fade-up 0.5s ease both;
      }}
      .cx-insight::before {{
        content: "";
        position: absolute; inset: 0;
        background: radial-gradient(400px 200px at 100% 0%, rgba(255,255,255,0.15) 0%, transparent 60%);
        pointer-events: none;
      }}
      .cx-insight-blue   {{ background: linear-gradient(135deg, #0088c2 0%, #1e40af 100%); }}
      .cx-insight-green  {{ background: linear-gradient(135deg, #10b981 0%, #047857 100%); }}
      .cx-insight-orange {{ background: linear-gradient(135deg, #ef8a00 0%, #c2410c 100%); }}
      .cx-insight h3 {{
        color: white; margin: 0 0 8px 0;
        font-size: 13px; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.05em;
        position: relative; z-index: 1;
      }}
      .cx-insight .big {{
        font-size: 24px; font-weight: 700; margin: 6px 0;
        letter-spacing: -0.02em; position: relative; z-index: 1;
        font-variant-numeric: tabular-nums;
      }}
      .cx-insight p {{
        color: rgba(255,255,255,0.94); margin: 2px 0;
        font-size: 12.5px; position: relative; z-index: 1;
      }}

      /* ============ INFO STRIP ============ */
      .cx-info {{
        background: {c['warn_bg']};
        border-left: 4px solid {c['warning']};
        color: {c['text']};
        padding: 12px 16px;
        border-radius: 10px;
        font-size: 13px;
        margin: 10px 0 16px 0;
        box-shadow: {c['shadow_sm']};
      }}

      /* ============ CHART TITLES ============ */
      .cx-chart-title {{
        color: {c['text']};
        font-size: 14px; font-weight: 600;
        margin: 8px 0 4px 0;
        letter-spacing: -0.01em;
      }}
      .cx-chart-sub {{
        color: {c['text_muted']};
        font-size: 12px; margin-bottom: 6px;
      }}

      /* ============ TABS — pill style ============ */
      .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 14px;
        padding: 6px;
        box-shadow: {c['shadow_sm']};
      }}
      .stTabs [data-baseweb="tab"] {{
        height: 38px;
        padding: 0 18px;
        border-radius: 10px;
        color: {c['text_muted']};
        background: transparent;
        transition: all .15s ease;
        border: none;
      }}
      .stTabs [data-baseweb="tab"]:hover {{
        background: {c['surface_2']};
        color: {c['text']};
      }}
      .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        background: {c['primary']};
        color: white !important;
        box-shadow: 0 2px 10px {c['primary_soft']};
      }}
      .stTabs [data-baseweb="tab"][aria-selected="true"] p {{
        color: white !important;
      }}
      .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {{
        font-size: 13.5px; font-weight: 600;
      }}
      .stTabs [data-baseweb="tab-highlight"] {{ display: none; }}
      .stTabs [data-baseweb="tab-border"] {{ display: none; }}

      /* ============ STREAMLIT FORM CONTROLS ============ */
      [data-testid="stSelectbox"] > div > div,
      [data-testid="stMultiSelect"] > div > div,
      [data-testid="stTextInput"] > div > div {{
        border-radius: 10px !important;
        border-color: {c['border']} !important;
        background: {c['surface']} !important;
      }}
      [data-testid="stSelectbox"] > div > div:hover,
      [data-testid="stTextInput"] > div > div:hover {{
        border-color: {c['primary']} !important;
      }}
      .stButton button {{
        border-radius: 10px;
        font-weight: 500;
        transition: all .15s ease;
      }}
      .stButton button:hover {{
        transform: translateY(-1px);
        box-shadow: {c['shadow_sm']};
      }}

      /* ============ EXPANDER ============ */
      [data-testid="stExpander"] {{
        border: 1px solid {c['border']} !important;
        border-radius: 12px !important;
        background: {c['surface']} !important;
        box-shadow: {c['shadow_sm']};
        overflow: hidden;
      }}
      [data-testid="stExpander"] summary {{
        padding: 12px 16px !important;
        font-weight: 600;
      }}
      [data-testid="stExpander"] summary:hover {{
        background: {c['surface_2']};
      }}

      /* ============ DATAFRAME ============ */
      [data-testid="stDataFrame"] {{
        border-radius: 12px !important;
        overflow: hidden;
        border: 1px solid {c['border']};
        box-shadow: {c['shadow_sm']};
      }}

      /* ============ FILTER CONTAINER ============ */
      [data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 14px !important;
        border-color: {c['border']} !important;
        background: {c['surface_glass']} !important;
        backdrop-filter: blur(8px);
        box-shadow: {c['shadow_sm']};
      }}

      /* ============ FILE UPLOADER ============ */
      [data-testid="stFileUploader"] section {{
        border-radius: 12px;
        border: 2px dashed {c['border_strong']};
        background: {c['surface_2']};
        transition: all .15s ease;
      }}
      [data-testid="stFileUploader"] section:hover {{
        border-color: {c['primary']};
        background: {c['primary_soft']};
      }}

      /* ============ THEME TOGGLE PILL ============ */
      .cx-theme-toggle {{
        display: inline-flex;
        background: rgba(255,255,255,0.15);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.22);
        border-radius: 999px;
        padding: 3px;
        gap: 2px;
      }}

      /* ============ STATUS DOTS ============ */
      .cx-status {{
        display: inline-flex; align-items: center; gap: 6px;
        font-size: 11px; font-weight: 500;
        padding: 3px 10px; border-radius: 999px;
      }}
      .cx-status-good {{ color: {c['success']}; background: {c['success_soft']}; }}
      .cx-status-warn {{ color: {c['warning']}; background: {c['warning_soft']}; }}
      .cx-status-bad  {{ color: {c['danger']};  background: {c['danger_soft']}; }}

      /* ============ SCROLLBAR ============ */
      ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
      ::-webkit-scrollbar-track {{ background: transparent; }}
      ::-webkit-scrollbar-thumb {{
        background: {c['border_strong']};
        border-radius: 999px;
      }}
      ::-webkit-scrollbar-thumb:hover {{ background: {c['text_subtle']}; }}

      /* ============ MOBILE ============ */
      @media (max-width: 768px) {{
        .cx-header {{ padding: 16px 18px; border-radius: 14px; }}
        .cx-header h1 {{ font-size: 18px; }}
        .cx-card-value {{ font-size: 22px; }}
        .block-container {{ padding-left: 0.6rem; padding-right: 0.6rem; }}
      }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# =============================================================================
# DATA LOADING
# =============================================================================
@st.cache_data(show_spinner=False)
def _read_bytes(content: bytes, filename: str) -> pd.DataFrame:
    bio = io.BytesIO(content)
    if filename.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(bio)
    return pd.read_csv(bio, low_memory=False)


@st.cache_data(show_spinner=False)
def _read_path(path: str) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(p)
    return pd.read_csv(p, low_memory=False)


def normalize_main(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    for c in ("is_best", "is_forward"):
        if c in df.columns:
            df[c] = (df[c].astype(str).str.strip().str.lower()
                     .map({"true": 1, "false": 0, "1": 1, "0": 0, "1.0": 1, "0.0": 0})
                     .fillna(0).astype(int))

    numeric = ["actual", "forecast", "accuracy_pct", "error", "abs_error",
               "bias_pct", "wape_component_num", "wape_component_den",
               "year", "month", "ibp_forecast_cogs", "ibp_actual_cogs",
               "ibp_accuracy_pct"]
    for c in numeric:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        if "year" not in df.columns or df["year"].isna().all():
            df["year"] = df["date"].dt.year
        if "month" not in df.columns or df["month"].isna().all():
            df["month"] = df["date"].dt.month

    for c in ("level", "dimension_value", "codp_zone", "plant",
              "product_category_1", "target", "model", "split",
              "data_quality_flags"):
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
            df.loc[df[c].isin(["nan", "NaN", "None", ""]), c] = np.nan
    return df


def try_autoload():
    main_df = comp_df = recon_df = None
    msgs = []
    if Path(PRIMARY_FILE).exists():
        try:
            main_df = normalize_main(_read_path(PRIMARY_FILE))
            msgs.append(f"Loaded `{PRIMARY_FILE}` ({len(main_df):,} rows)")
        except Exception as e:
            msgs.append(f"Could not load `{PRIMARY_FILE}`: {e}")
    if Path(COMPARISON_FILE).exists():
        try:
            comp_df = _read_path(COMPARISON_FILE)
            comp_df.columns = [c.strip() for c in comp_df.columns]
            msgs.append(f"Loaded `{COMPARISON_FILE}` ({len(comp_df):,} rows)")
        except Exception as e:
            msgs.append(f"Could not load `{COMPARISON_FILE}`: {e}")
    if Path(RECON_FILE).exists():
        try:
            recon_df = _read_path(RECON_FILE)
            recon_df.columns = [c.strip() for c in recon_df.columns]
            msgs.append(f"Loaded `{RECON_FILE}` ({len(recon_df):,} rows)")
        except Exception as e:
            msgs.append(f"Could not load `{RECON_FILE}`: {e}")
    return main_df, comp_df, recon_df, msgs


# =============================================================================
# FORMATTING
# =============================================================================
def fmt_money(x, compact: bool = True) -> str:
    if pd.isna(x): return "—"
    a, sign = abs(x), "-" if x < 0 else ""
    if compact:
        if a >= 1e9: return f"{sign}${a/1e9:.2f}B"
        if a >= 1e6: return f"{sign}${a/1e6:.2f}M"
        if a >= 1e3: return f"{sign}${a/1e3:.1f}K"
    return f"{sign}${a:,.0f}"


def fmt_int(x) -> str:
    if pd.isna(x): return "—"
    return f"{int(x):,}"


def fmt_pct(x, decimals: int = 1) -> str:
    if pd.isna(x): return "—"
    return f"{x:.{decimals}f}%"


def fmt_pp(x, decimals: int = 1) -> str:
    if pd.isna(x): return "—"
    sign = "+" if x >= 0 else ""
    return f"{sign}{x:.{decimals}f} pts"


# =============================================================================
# ACCURACY HELPERS
# =============================================================================
def compute_signed_error_pct(actual: float, forecast: float) -> float:
    """Signed forecast error %:
        positive  → actual > forecast (under-forecasted, sold more than planned)
        negative  → actual < forecast (over-forecasted, sold less than planned)
        zero      → perfect
    Formula: (actual − forecast) / forecast × 100
    """
    if forecast is None or pd.isna(forecast) or forecast == 0:
        return np.nan
    if actual is None or pd.isna(actual):
        return np.nan
    return (actual - forecast) / forecast * 100


def compute_abs_error_pct(actual: float, forecast: float) -> float:
    """Absolute error % for "how big is the miss" framing."""
    e = compute_signed_error_pct(actual, forecast)
    return abs(e) if pd.notna(e) else np.nan


def fmt_signed_pct(x, decimals: int = 1) -> str:
    if pd.isna(x): return "—"
    sign = "+" if x >= 0 else ""
    return f"{sign}{x:.{decimals}f}%"


def compute_accuracy(actual_sum: float, abs_err_sum: float) -> float:
    if actual_sum is None or not actual_sum or actual_sum <= 0:
        return np.nan
    err_pct = abs_err_sum / actual_sum * 100
    return max(0.0, 100.0 - err_pct)


def compute_alignment(actual_sum: float, forecast_sum: float) -> float:
    if not forecast_sum or pd.isna(forecast_sum) or forecast_sum == 0:
        return np.nan
    return actual_sum / forecast_sum * 100


# =============================================================================
# KPI CARD
# =============================================================================
def kpi_card(title: str, value: str, sub: str = "",
             sub_class: str = "cx-delta-neutral", icon: str = "") -> None:
    icon_html = f'<span style="opacity:0.7">{icon}</span>' if icon else ""
    sub_html = f'<div class="cx-card-delta {sub_class}">{sub}</div>' if sub else ""
    st.markdown(
        f"""<div class="cx-card">
              <div class="cx-card-title">{icon_html}{title}</div>
              <div class="cx-card-value">{value}</div>
              {sub_html}
            </div>""",
        unsafe_allow_html=True,
    )


# =============================================================================
# CHART HELPERS
# =============================================================================
def _empty_fig(msg: str, height: int = 320) -> go.Figure:
    c = get_theme()
    fig = go.Figure()
    fig.add_annotation(text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
                       showarrow=False, font=dict(size=14, color=c["text_muted"]))
    fig.update_layout(template=c["plotly"], height=height,
                      margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


def _base_layout(fig: go.Figure, height: int = 360,
                 title: Optional[str] = None) -> go.Figure:
    """Apply base styling.

    title behaviour:
      - title=None (default): leave whatever title the chart already set untouched
      - title="..." (non-empty): set this as the chart title
      - title="" : explicitly clear the title (use dict-form so Plotly doesn't
        render 'undefined' on mobile)
    """
    c = get_theme()

    # Decide if a title will be visible on the final figure
    if title is None:
        existing = getattr(fig.layout.title, "text", None)
        has_title = bool(existing)
    else:
        has_title = bool(title)

    layout_kwargs = dict(
        template=c["plotly"], height=height,
        margin=dict(l=12, r=12, t=48 if has_title else 12, b=12),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(family="Inter, sans-serif", size=12, color=c["text"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        font=dict(family="Inter, sans-serif", size=12, color=c["text"]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(
            font=dict(family="Inter, sans-serif", size=12),
            bordercolor=c["border_strong"],
        ),
        xaxis=dict(
            gridcolor=c["grid"],
            linecolor=c["border"],
            zerolinecolor=c["border"],
            tickfont=dict(family="Inter, sans-serif", size=11),
        ),
        yaxis=dict(
            gridcolor=c["grid"],
            linecolor=c["border"],
            zerolinecolor=c["border"],
            tickfont=dict(family="Inter, sans-serif", size=11),
        ),
    )
    if title is not None:
        # Use dict form (not None) so Plotly never falls back to "undefined"
        layout_kwargs["title"] = (
            dict(text=title,
                 font=dict(family="Inter, sans-serif", size=14,
                           color=c["text"]))
            if title else dict(text="")
        )
    fig.update_layout(**layout_kwargs)
    return fig


def _add_no_data_shading(fig, df, value_col, c):
    """Shade months where the value column is NaN.

    Defensive against:
      - duplicate column names (e.g. two 'date' columns after set_index/reset_index)
      - pandas/Plotly Timestamp 'ambiguous truth value' errors
    """
    if df is None or value_col not in df.columns:
        return

    # Resolve the date column robustly (could be duplicated → DataFrame)
    if "date" not in df.columns:
        return
    date_obj = df["date"]
    if isinstance(date_obj, pd.DataFrame):
        date_obj = date_obj.iloc[:, 0]

    val_obj = df[value_col]
    if isinstance(val_obj, pd.DataFrame):
        val_obj = val_obj.iloc[:, 0]

    mask = val_obj.isna()
    dates_missing = pd.Series(pd.to_datetime(date_obj.values, errors="coerce"))[mask.values]
    dates_missing = dates_missing.dropna()
    if dates_missing.empty:
        return

    x0_ts = dates_missing.min()
    x1_ts = dates_missing.max()
    # Convert to native python datetimes
    x0 = x0_ts.to_pydatetime() if hasattr(x0_ts, "to_pydatetime") else x0_ts
    x1 = x1_ts.to_pydatetime() if hasattr(x1_ts, "to_pydatetime") else x1_ts

    # Widen a zero-width band so it's visible
    if x0 == x1:
        import datetime as _dt
        x0 = x0 - _dt.timedelta(days=15)
        x1 = x1 + _dt.timedelta(days=15)

    try:
        fig.add_vrect(
            x0=x0, x1=x1,
            fillcolor=c["text_muted"], opacity=0.10,
            layer="below", line_width=0,
            annotation_text="no data yet",
            annotation_position="top left",
            annotation=dict(font=dict(color=c["text_muted"], size=11)),
        )
    except Exception:
        try:
            fig.add_vrect(
                x0=x0, x1=x1,
                fillcolor=c["text_muted"], opacity=0.10,
                layer="below", line_width=0,
            )
        except Exception:
            pass


# =============================================================================
# HEADER & TOP CONTROLS
# =============================================================================
def render_header():
    is_dark = st.session_state.theme == "Dark"
    theme_label = "🌙 Dark" if is_dark else "☀️ Light"
    st.markdown(
        f"""<div class="cx-header">
             <div class="cx-header-row">
               <div class="cx-header-brand">
                 <div class="cx-brand-mark">📊</div>
                 <div>
                   <h1>Chemelex Demand Forecasting Cockpit</h1>
                   <div class="cx-header-sub">AI forecast accuracy · zone-level diagnostics · US region</div>
                 </div>
               </div>
               <div class="cx-header-pills">
                 <div class="cx-pill"><span class="dot"></span>Live data</div>
                 <div class="cx-pill">⚡ {theme_label}</div>
               </div>
             </div>
           </div>""",
        unsafe_allow_html=True,
    )


def render_top_controls():
    c1, c2 = st.columns([5, 2])
    with c1:
        upload = st.file_uploader(
            "📁 Upload / Replace Forecast File  (csv, xlsx)",
            type=["csv", "xlsx", "xls"],
            label_visibility="visible",
            key="uploader",
        )
    with c2:
        st.markdown(
            '<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.06em;'
            'color:var(--text-muted,#64748b);font-weight:600;margin:0 0 6px 2px;">Theme</div>',
            unsafe_allow_html=True,
        )
        choice = st.radio(
            "Theme",
            options=["☀️ Light", "🌙 Dark"],
            index=0 if st.session_state.theme == "Light" else 1,
            horizontal=True,
            key="theme_radio",
            label_visibility="collapsed",
        )
        new_theme = "Light" if choice == "☀️ Light" else "Dark"
        if new_theme != st.session_state.theme:
            st.session_state.theme = new_theme
            st.rerun()
    if upload is not None:
        return upload.getvalue(), upload.name
    return None, None


# =============================================================================
# FILTERS
# =============================================================================
def apply_filters(df, *, year, months, zones, plants, cats,
                  level, target, split, best_only, model, search_text):
    out = df.copy()
    if year is not None and "year" in out.columns:
        out = out[out["year"] == year]
    if months and "month" in out.columns:
        out = out[out["month"].isin(months)]
    if zones and "codp_zone" in out.columns:
        out = out[out["codp_zone"].isin(zones + ["All"])]
    if plants and "plant" in out.columns:
        out = out[out["plant"].isin(plants + ["All"])]
    if cats and "product_category_1" in out.columns:
        out = out[out["product_category_1"].isin(cats + ["All"])]
    if level and "level" in out.columns:
        out = out[out["level"] == level]
    if target and "target" in out.columns:
        out = out[out["target"] == target]
    if split and "split" in out.columns:
        out = out[out["split"] == split]
    if best_only and "is_best" in out.columns:
        out = out[out["is_best"] == 1]
    if model and "model" in out.columns:
        out = out[out["model"] == model]
    if search_text and "dimension_value" in out.columns:
        s = search_text.strip().lower()
        out = out[out["dimension_value"].astype(str).str.lower()
                  .str.contains(s, na=False)]
    return out


# =============================================================================
# CEO METRICS & BEST MODEL
# =============================================================================
def ceo_metrics(df):
    if df.empty:
        return {k: np.nan for k in
                ["actual", "forecast", "accuracy", "alignment", "gap",
                 "active_items", "off_track_items"]}

    total_actual   = df["actual"].sum()   if "actual"   in df.columns else np.nan
    total_forecast = df["forecast"].sum() if "forecast" in df.columns else np.nan
    abs_err = df["abs_error"].sum() if "abs_error" in df.columns else np.nan

    accuracy  = compute_accuracy(total_actual, abs_err) if not pd.isna(abs_err) else np.nan
    alignment = compute_alignment(total_actual, total_forecast)
    gap = (total_actual - total_forecast) if pd.notna(total_actual) and pd.notna(total_forecast) else np.nan

    active = df["dimension_value"].nunique() if "dimension_value" in df.columns else len(df)
    if {"actual", "forecast", "dimension_value"}.issubset(df.columns):
        per = df.groupby("dimension_value", dropna=False).agg(
            a=("actual", "sum"), f=("forecast", "sum"))
        per["align"] = per["a"] / per["f"] * 100
        off = int(((per["align"] < 80) | (per["align"] > 120)).sum())
    else:
        off = np.nan

    return {"actual": total_actual, "forecast": total_forecast,
            "accuracy": accuracy, "alignment": alignment, "gap": gap,
            "active_items": active, "off_track_items": off}


def best_ai_model(df, *, year=2025, target="order_value_usd",
                  level="Total", on_ibp_scope=True):
    pool = df[(df["year"] == year)
              & (df["split"] == "split2")
              & (df["target"] == target)
              & (df["level"] == level)
              & (df["model"] != "IBP_Manual")
              & (df["is_forward"] == 0)]
    if on_ibp_scope:
        pool = pool[pool["ibp_actual_cogs"].notna()]
    if pool.empty:
        return ("—", np.nan)

    results = []
    for m, sub in pool.groupby("model"):
        if on_ibp_scope:
            ratio = np.where(sub["actual"].abs() > 1e-6,
                             sub["ibp_actual_cogs"] / sub["actual"], np.nan)
            forecast_scaled = sub["forecast"] * ratio
            actual_used = sub["ibp_actual_cogs"]
            abs_err = (actual_used - forecast_scaled).abs().sum()
        else:
            actual_used = sub["actual"]
            abs_err = (sub["actual"] - sub["forecast"]).abs().sum()
        acc = compute_accuracy(float(actual_used.sum()), float(abs_err))
        results.append((m, acc))

    results = [(m, a) for m, a in results if not pd.isna(a)]
    if not results:
        return ("—", np.nan)
    results.sort(key=lambda t: t[1], reverse=True)
    return results[0]


def _best_in_filtered(fdf):
    if fdf.empty or "model" not in fdf.columns:
        return ("—", np.nan)
    g = (fdf.groupby("model")
         .agg(a=("actual", "sum"), ae=("abs_error", "sum"))
         .reset_index())
    g = g[g["a"] > 0]
    if g.empty:
        return ("—", np.nan)
    g["acc"] = 100 - (g["ae"] / g["a"] * 100)
    g["acc"] = g["acc"].clip(lower=0, upper=100)
    g = g.sort_values("acc", ascending=False)
    return (g.iloc[0]["model"], g.iloc[0]["acc"])


def _best_in_filtered_error(fdf):
    """Best AI model by smallest |signed error %| of (actual − forecast) / forecast."""
    if fdf.empty or "model" not in fdf.columns:
        return ("—", np.nan)
    g = (fdf.groupby("model")
         .agg(a=("actual", "sum"), f=("forecast", "sum"))
         .reset_index())
    g = g[g["f"] > 0]
    if g.empty:
        return ("—", np.nan)
    g["err"] = (g["a"] - g["f"]) / g["f"] * 100
    g["abs_err"] = g["err"].abs()
    g = g.sort_values("abs_err", ascending=True)
    return (g.iloc[0]["model"], float(g.iloc[0]["err"]))


# =============================================================================
# MAIN
# =============================================================================
def main():
    inject_css()
    render_header()

    upload_bytes, upload_name = render_top_controls()

    main_df = comp_df = recon_df = None
    if upload_bytes is not None:
        try:
            raw = _read_bytes(upload_bytes, upload_name)
            main_df = normalize_main(raw)
            st.success(f"Loaded `{upload_name}` ({len(main_df):,} rows)")
        except Exception as e:
            st.error(f"Could not read uploaded file: {e}")

    auto_main, comp_df, recon_df, msgs = try_autoload()
    if main_df is None:
        main_df = auto_main

    if main_df is None or main_df.empty:
        st.info(f"👋 **Welcome.** Place `{PRIMARY_FILE}` next to `app.py` "
                "or upload a forecast file above to begin.")
        for m in msgs:
            st.caption(m)
        st.stop()

    # ---- Filters ----
    with st.container(border=True):
        st.markdown("**🔎 Filters**")

        years = sorted([int(y) for y in main_df["year"].dropna().unique()])
        default_year = 2025 if 2025 in years else (years[-1] if years else None)

        zone_opts = [z for z in OFFICIAL_ZONES
                     if z in set(main_df["codp_zone"].dropna().unique())] or OFFICIAL_ZONES
        plant_opts = sorted([p for p in main_df["plant"].dropna().unique() if p != "All"])
        cat_opts   = sorted([c for c in main_df["product_category_1"].dropna().unique()
                             if c != "All"])

        r1 = st.columns([1.0, 2.2, 1.4, 1.6])
        with r1[0]:
            year_sel = st.selectbox(
                "Year", options=years,
                index=years.index(default_year) if default_year in years else 0)
        with r1[1]:
            mo_names = st.multiselect("Month", options=MONTH_NAMES,
                                      default=MONTH_NAMES,
                                      help="Leave all selected for full year")
            month_sel = [i + 1 for i, n in enumerate(MONTH_NAMES) if n in mo_names]
        with r1[2]:
            level_sel = st.selectbox("Forecast Level", options=LEVELS,
                                     index=LEVELS.index("Group"))
        with r1[3]:
            search_text = st.text_input("Search line items", value="",
                                        placeholder="Filter by name…")

        r2 = st.columns([2, 2, 2])
        with r2[0]:
            zone_sel = st.multiselect("Supply Chain Zone",
                                      options=zone_opts, default=zone_opts)
        with r2[1]:
            plant_sel = st.multiselect("Plant", options=plant_opts, default=plant_opts)
        with r2[2]:
            cat_sel = st.multiselect("Product Category",
                                     options=cat_opts, default=cat_opts)

        target_sel = "order_value_usd" if "order_value_usd" in (
            main_df.get("target", pd.Series([])).dropna().unique().tolist()) else None
        split_sel = "split2" if "split2" in (
            main_df.get("split", pd.Series([])).dropna().unique().tolist()) else None
        best_only = True
        model_sel = None

        with st.expander("⚙️ Advanced view (for analysts)"):
            adv = st.columns(3)
            with adv[0]:
                if "target" in main_df.columns:
                    targets = sorted(main_df["target"].dropna().unique().tolist())
                    target_sel = st.selectbox(
                        "Measure",
                        options=targets,
                        index=targets.index("order_value_usd")
                              if "order_value_usd" in targets else 0,
                        format_func=lambda t: TARGET_LABELS.get(t, t))
            with adv[1]:
                if "model" in main_df.columns:
                    model_opts = ["(all AI models)"] + sorted(
                        m for m in main_df["model"].dropna().unique() if m != "IBP_Manual")
                    pick = st.selectbox("Filter to one AI model",
                                        options=model_opts, index=0)
                    model_sel = None if pick == "(all AI models)" else pick
            with adv[2]:
                best_only = st.checkbox("Best model per line only", value=True)

    filtered = apply_filters(
        main_df[main_df.get("model", pd.Series(["x"] * len(main_df))) != "IBP_Manual"]
        if "model" in main_df.columns else main_df,
        year=year_sel, months=month_sel, zones=zone_sel, plants=plant_sel,
        cats=cat_sel, level=level_sel, target=target_sel, split=split_sel,
        best_only=best_only, model=model_sel, search_text=search_text,
    )

    tabs = st.tabs([
        "📈 Executive Overview",
        "🆚 AI vs Manual Plan",
        "🎯 Error by Line",
        "🔍 Drill Down",
        "📦 Forward Plan",
    ])

    with tabs[0]:
        render_overview(filtered, year_sel)
    with tabs[1]:
        render_ai_vs_manual(main_df, comp_df, zone_sel, plant_sel, cat_sel, year_sel)
    with tabs[2]:
        render_accuracy_table(filtered, level_sel, year_sel)
    with tabs[3]:
        render_drilldown(filtered)
    with tabs[4]:
        render_forward_plan(main_df, year_sel, zone_sel, plant_sel, cat_sel)


# =============================================================================
# TAB 1 — EXECUTIVE OVERVIEW
# =============================================================================
def render_overview(fdf, year_sel):
    c = get_theme()

    top_contributor = "—"
    top_contributor_pct = np.nan
    if "product_category_1" in fdf.columns:
        cat_sum = (fdf[fdf["product_category_1"] != "All"]
                   .groupby("product_category_1")["actual"].sum()
                   .sort_values(ascending=False))
        if len(cat_sum) and cat_sum.sum() > 0:
            top_contributor = cat_sum.index[0]
            top_contributor_pct = cat_sum.iloc[0] / cat_sum.sum() * 100

    best_zone = "—"
    best_zone_err = np.nan
    if {"codp_zone", "forecast", "actual"}.issubset(fdf.columns):
        z = (fdf[fdf["codp_zone"].isin(OFFICIAL_ZONES)]
             .groupby("codp_zone").agg(f=("forecast", "sum"), a=("actual", "sum"))
             .reset_index())
        z = z[z["f"] > 0]
        if len(z):
            z["err"] = (z["a"] - z["f"]) / z["f"] * 100
            z["abs_err"] = z["err"].abs()
            z = z.sort_values("abs_err", ascending=True)
            best_zone = z.iloc[0]["codp_zone"]
            best_zone_err = float(z.iloc[0]["err"])

    ins1, ins2 = st.columns(2)
    with ins1:
        st.markdown(
            f"""<div class="cx-insight cx-insight-blue">
                <h3>📈 Top revenue contributor</h3>
                <div class="big">{top_contributor}</div>
                <p>{fmt_pct(top_contributor_pct)} of business in current view</p>
                </div>""", unsafe_allow_html=True)
    with ins2:
        st.markdown(
            f"""<div class="cx-insight cx-insight-green">
                <h3>✅ Closest to plan</h3>
                <div class="big">{best_zone}</div>
                <p>{fmt_signed_pct(best_zone_err)} forecast error</p>
                </div>""", unsafe_allow_html=True)

    m = ceo_metrics(fdf)

    # Compute signed error % at portfolio level
    err_pct = compute_signed_error_pct(m["actual"], m["forecast"])

    k = st.columns(3)
    with k[0]:
        kpi_card("AI Forecast", fmt_money(m["forecast"]),
                 "What the AI model expected")
    with k[1]:
        gap = m["gap"]
        cls = "cx-delta-pos" if (not pd.isna(gap) and gap >= 0) else "cx-delta-neg"
        sub = (f"Sold {fmt_money(abs(gap))} more than AI forecast" if pd.notna(gap) and gap > 0
               else f"Sold {fmt_money(abs(gap))} less than AI forecast"
               if pd.notna(gap) else "")
        kpi_card("Total Actual", fmt_money(m["actual"]), sub, cls)
    with k[2]:
        if pd.isna(err_pct):
            sub, cls = "", "cx-delta-neutral"
        elif abs(err_pct) <= 5:
            sub, cls = "Close to AI forecast", "cx-delta-pos"
        elif err_pct > 0:
            sub, cls = "Sold more than AI forecast (under-forecast)", "cx-delta-pos"
        else:
            sub, cls = "Sold less than AI forecast (over-forecast)", "cx-delta-neg"
        kpi_card("Forecast Error", fmt_signed_pct(err_pct), sub, cls)

    k2 = st.columns(4)
    with k2[0]:
        kpi_card("Active Forecast Lines", fmt_int(m["active_items"]),
                 "Distinct product / plant lines")
    with k2[1]:
        off = m["off_track_items"]
        cls = "cx-delta-pos" if off == 0 else "cx-delta-neg"
        kpi_card("Off-track Lines", fmt_int(off),
                 "More than 20% off AI forecast", cls)
    with k2[2]:
        if "date" in fdf.columns and not fdf.empty:
            _dt_series = fdf["date"]
            if isinstance(_dt_series, pd.DataFrame):
                _dt_series = _dt_series.iloc[:, 0]
            _dt_vals = pd.to_datetime(_dt_series.values, errors="coerce")
            _dt_vals = pd.Series(_dt_vals).dropna()
            if len(_dt_vals):
                mn = _dt_vals.min()
                mx = _dt_vals.max()
                period = f"{mn:%b %Y} – {mx:%b %Y}"
            else:
                period = "—"
        else:
            period = "—"
        kpi_card("Period", period, f"Year: {year_sel}")
    with k2[3]:
        bm, be = _best_in_filtered_error(fdf)
        kpi_card("Top AI Model", bm if bm else "—",
                 (f"{fmt_signed_pct(be)} error" if pd.notna(be) else "—"),
                 "cx-delta-pos" if (pd.notna(be) and abs(be) <= 10) else "cx-delta-neutral")

    st.markdown('<div class="cx-section">Forecast vs Reality — by Month</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(chart_monthly_fa(fdf), use_container_width=True)
    with c2:
        st.plotly_chart(chart_accuracy_by_month(fdf), use_container_width=True)

    st.markdown('<div class="cx-section">Where the Business Is</div>',
                unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(chart_category_bars(fdf), use_container_width=True)
    with c4:
        st.plotly_chart(chart_accuracy_by_zone(fdf), use_container_width=True)

    # ------------------------------------------------------------------
    # SYNTHEFY PROMPT — diagnose why some strategies miss more than others
    # ------------------------------------------------------------------
    render_synthefy_prompt(fdf, year_sel)


def render_synthefy_prompt(fdf, year_sel):
    """Compute strategy-level diagnostics and craft a copyable prompt
    for the Synthefy multimodal AI platform, asking it to explain why
    Push/RM and BUFFER (at CODP) carry materially higher forecast error
    than Pull/Kanban, Pull/FG, and Push/MPS.
    """
    if fdf.empty or not {"codp_zone", "forecast", "actual"}.issubset(fdf.columns):
        return

    st.markdown(
        '<div class="cx-section">🤖 Ask Synthefy — Why are some strategies missing more?</div>',
        unsafe_allow_html=True)
    st.caption(
        "Synthefy is your multimodal AI analyst. Copy the prompt below and paste it "
        "into Synthefy to get a root-cause diagnosis and recommended actions for the "
        "strategies with the largest forecast error.")

    # ---- 1. Strategy-level error & share ----
    z = (fdf[fdf["codp_zone"].isin(OFFICIAL_ZONES)]
         .groupby("codp_zone")
         .agg(forecast=("forecast", "sum"),
              actual=("actual", "sum"),
              abs_error=("abs_error", "sum"))
         .reset_index())
    z = z[z["forecast"] > 0].copy()
    if z.empty:
        st.info("Not enough strategy-level data in the current filter to build a prompt.")
        return

    z["err_pct"]  = (z["actual"] - z["forecast"]) / z["forecast"] * 100
    z["abs_err_pct"] = z["err_pct"].abs()
    # MAPE-style on actuals (weighted)
    z["mape_on_actual"] = np.where(z["actual"] > 0,
                                   z["abs_error"] / z["actual"] * 100, np.nan)
    total_actual = z["actual"].sum()
    z["share_pct"] = z["actual"] / total_actual * 100 if total_actual > 0 else np.nan
    z = z.sort_values("abs_err_pct", ascending=False)

    # ---- 2. Identify the worst two strategies (by signed error magnitude) ----
    worst = z.head(2)["codp_zone"].tolist()

    # ---- 3. Worst monthly spikes within the worst strategies ----
    monthly_lines = []
    if "date" in fdf.columns:
        for strat in worst:
            m_df = (fdf[fdf["codp_zone"] == strat]
                    .groupby("date", as_index=False)
                    .agg(f=("forecast", "sum"), a=("actual", "sum")))
            m_df = m_df[m_df["f"] > 0]
            if m_df.empty:
                continue
            m_df["err"] = (m_df["a"] - m_df["f"]) / m_df["f"] * 100
            m_df["abs_err"] = m_df["err"].abs()
            top_months = m_df.sort_values("abs_err", ascending=False).head(3)
            for _, r in top_months.iterrows():
                d = pd.to_datetime(r["date"])
                monthly_lines.append(
                    f"  - {strat} · {d:%b %Y}: forecast {fmt_money(r['f'])}, "
                    f"actual {fmt_money(r['a'])}, error {r['err']:+.1f}%")

    # ---- 4. Worst SKUs / categories inside the worst strategies ----
    sku_lines = []
    if "product_category_1" in fdf.columns:
        for strat in worst:
            s_df = (fdf[(fdf["codp_zone"] == strat)
                        & (fdf["product_category_1"] != "All")]
                    .groupby("product_category_1", as_index=False)
                    .agg(f=("forecast", "sum"), a=("actual", "sum")))
            s_df = s_df[s_df["f"] > 0]
            if s_df.empty:
                continue
            s_df["err"] = (s_df["a"] - s_df["f"]) / s_df["f"] * 100
            s_df["abs_err"] = s_df["err"].abs()
            s_df["share"] = s_df["a"] / s_df["a"].sum() * 100 if s_df["a"].sum() > 0 else 0
            top_sku = s_df.sort_values("abs_err", ascending=False).head(3)
            for _, r in top_sku.iterrows():
                sku_lines.append(
                    f"  - {strat} · {r['product_category_1']}: "
                    f"error {r['err']:+.1f}%, share of strategy actual {r['share']:.1f}%")

    # ---- 5. Build the strategy table block ----
    table_lines = []
    for _, r in z.iterrows():
        table_lines.append(
            f"  - {r['codp_zone']:<22} "
            f"signed error {r['err_pct']:+6.1f}% · "
            f"|MAPE| {r['mape_on_actual']:5.1f}% · "
            f"volume share {r['share_pct']:5.1f}%"
        )

    # ---- 6. Find which is the top AI model in current view (for context) ----
    bm, be = _best_in_filtered_error(fdf)
    top_model_str = f"{bm} (signed error {fmt_signed_pct(be)})" if bm and bm != "—" else "(not available in current view)"

    # ---- 7. Assemble the prompt ----
    monthly_block = "\n".join(monthly_lines) if monthly_lines else "  (no monthly detail available)"
    sku_block = "\n".join(sku_lines) if sku_lines else "  (no SKU-level detail available)"
    worst_str = " and ".join(worst) if worst else "the highest-error strategies"

    prompt = f"""You are Synthefy, a multimodal demand-forecasting analyst for Chemelex's heat-tracing product line (US / NAM region).

CONTEXT
- Year analysed: {year_sel}
- Top performing AI model in current view: {top_model_str}
- Forecast error formula: (Actual − Forecast) / Forecast × 100
- Manufacturing strategies (CODP zones): Push/RM, BUFFER (at CODP), Pull/Kanban, Pull/FG, Push/MPS

STRATEGY-LEVEL FORECAST ACCURACY
{chr(10).join(table_lines)}

OBSERVATION
{worst_str} carry materially higher forecast error than the other strategies. We need to understand why.

WORST MONTHLY SPIKES (top 3 per problem strategy)
{monthly_block}

WORST PRODUCT CATEGORIES INSIDE THE PROBLEM STRATEGIES
{sku_block}

TASK
1. Diagnose the root causes of the elevated forecast error in {worst_str}. In your analysis, consider:
   - Demand-pattern mismatch: are these strategies dominated by lumpy, project-driven, or long-lead-time SKUs that the AI model cannot signal from history alone?
   - CODP positioning: is the buffer at the customer order decoupling point sized against the wrong demand distribution (e.g. assumed normal, actually intermittent)?
   - Raw-material-led push: for Push/RM, is the forecast anchored to RM availability rather than true downstream demand, causing a structural disconnect with actual sales?
   - Data sufficiency: do these SKUs have enough historical signal (≥ 24 months, low intermittency) for the chosen AI model class, or are they better served by Croston / SBA / intermittent-demand methods?
   - Seasonality and NPI: are spike months tied to new product introductions, project go-lives, or seasonal heat-tracing demand (winter onset, plant turnaround)?
   - Hierarchy & aggregation: would a different forecast level (Group vs Product Category vs SKU) reduce error for these strategies?

2. Recommend 3–5 concrete, prioritised actions to reduce forecast error in {worst_str}. For each action specify:
   - What to change (model, segmentation, buffer policy, planning cadence, data input)
   - Which strategy / category it applies to
   - Owner type (Demand Planner, Supply Planner, Data Science, S&OP lead)
   - Expected MAPE reduction (percentage points) with reasoning

3. Quantify the dollar-value error currently attributable to {worst_str} and the expected $ recovery if your top recommendation is adopted.

OUTPUT FORMAT
## Root Causes
(bullet list, grouped by strategy)

## Recommended Actions
(numbered list with the per-action fields above)

## Expected Impact
(table: action → MAPE Δ pp → $ recovery estimate → confidence H/M/L)

## Next 30 Days
(3 specific things the demand-planning team should run / build / decide)
"""

    # ---- 8. Display: a preview + a code block that's easy to copy ----
    with st.expander("📋 Open the Synthefy prompt (click to copy)", expanded=False):
        st.code(prompt, language="markdown")
        st.download_button(
            "⬇️ Download prompt as .txt",
            data=prompt.encode("utf-8"),
            file_name=f"synthefy_prompt_{year_sel}.txt",
            mime="text/plain",
            key="synthefy_dl",
        )


def chart_monthly_fa(fdf):
    c = get_theme()
    if fdf.empty or not {"date", "forecast", "actual"}.issubset(fdf.columns):
        return _empty_fig("No data")
    g = (fdf.groupby("date", as_index=False)[["forecast", "actual"]]
         .sum().sort_values("date"))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=g["date"], y=g["forecast"], mode="lines+markers",
                             name="AI Forecast",
                             line=dict(color=c["manual"], width=3)))
    fig.add_trace(go.Scatter(x=g["date"], y=g["actual"], mode="lines+markers",
                             name="Actual",
                             line=dict(color=c["actual"], width=3)))
    fig.update_yaxes(tickprefix="$", separatethousands=True)
    return _base_layout(fig, height=340,
                        title="Monthly AI Forecast vs Actual Revenue")


def chart_accuracy_by_month(fdf):
    """Signed forecast error % by month — positive = sold more than planned."""
    c = get_theme()
    if fdf.empty or not {"date", "actual", "forecast"}.issubset(fdf.columns):
        return _empty_fig("No data")
    g = (fdf.groupby("date", as_index=False)
         .agg(a=("actual", "sum"), f=("forecast", "sum"))
         .sort_values("date"))
    g = g[g["f"] > 0]
    if g.empty:
        return _empty_fig("No data")
    g["err"] = (g["a"] - g["f"]) / g["f"] * 100
    # Color bars: green near zero, orange for over-sold, red for under-sold
    colors = []
    for v in g["err"]:
        if abs(v) <= 5:
            colors.append(c["success"])
        elif v > 0:
            colors.append(c["primary"])    # sold more than planned
        else:
            colors.append(c["danger"])     # sold less than planned

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=g["date"], y=g["err"],
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in g["err"]],
        textposition="outside",
        name="Forecast Error %",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color=c["text_muted"],
                  annotation_text="0% (perfect)",
                  annotation_position="top right")
    fig.update_yaxes(ticksuffix="%")
    fig.update_layout(showlegend=False)
    return _base_layout(fig, height=340,
                        title="Monthly Forecast Error (Signed %)")


def chart_category_bars(fdf):
    c = get_theme()
    if fdf.empty or "product_category_1" not in fdf.columns:
        return _empty_fig("No category data")
    g = (fdf[fdf["product_category_1"] != "All"]
         .groupby("product_category_1")
         .agg(forecast=("forecast", "sum"), actual=("actual", "sum"))
         .reset_index()
         .sort_values("actual", ascending=False)
         .head(10))
    fig = go.Figure()
    fig.add_trace(go.Bar(name="AI Forecast", x=g["product_category_1"],
                         y=g["forecast"], marker_color=c["manual"]))
    fig.add_trace(go.Bar(name="Actual", x=g["product_category_1"],
                         y=g["actual"], marker_color=c["actual"]))
    fig.update_yaxes(tickprefix="$", separatethousands=True)
    fig.update_xaxes(tickangle=-25)
    fig.update_layout(barmode="group")
    return _base_layout(fig, height=380,
                        title="Top Product Categories — AI Forecast vs Actual")


def chart_accuracy_by_zone(fdf):
    c = get_theme()
    if fdf.empty or not {"codp_zone", "forecast", "actual"}.issubset(fdf.columns):
        return _empty_fig("No zone data")
    g = (fdf[fdf["codp_zone"].isin(OFFICIAL_ZONES)]
         .groupby("codp_zone").agg(f=("forecast", "sum"), a=("actual", "sum"))
         .reset_index())
    g = g[g["f"] > 0]
    if g.empty:
        return _empty_fig("No zone data")
    g["err"] = (g["a"] - g["f"]) / g["f"] * 100
    g["abs_err"] = g["err"].abs()
    g = g.sort_values("abs_err", ascending=True)

    cols = []
    for v in g["err"]:
        if abs(v) <= 5:
            cols.append(c["success"])
        elif abs(v) <= 15:
            cols.append(c["warning"])
        else:
            cols.append(c["danger"])
    fig = go.Figure(go.Bar(
        x=g["err"], y=g["codp_zone"], orientation="h",
        marker_color=cols,
        text=[f"{v:+.1f}%" for v in g["err"]],
        textposition="outside"))
    fig.update_xaxes(ticksuffix="%")
    fig.add_vline(x=0, line_dash="dash", line_color=c["text_muted"])
    return _base_layout(fig, height=380,
                        title="Forecast Error by Manufacturing Strategy")


# =============================================================================
# TAB 2 — AI vs MANUAL PLAN
# =============================================================================
def render_ai_vs_manual(main_df, comp_df, zone_sel, plant_sel, cat_sel, year_sel):
    c = get_theme()

    needed = {"model", "ibp_forecast_cogs", "ibp_actual_cogs",
              "is_forward", "data_quality_flags"}
    if not needed.issubset(main_df.columns):
        st.warning("This view needs a comparison-ready data file. "
                   "Please replace the file or contact the analytics team.")
        return
    if "IBP_Manual" not in set(main_df["model"].dropna().unique()):
        st.warning("Manual plan rows not found in the data.")
        return

    st.markdown(
        """<div class="cx-info">
             <b>How to read this page.</b>
             We compare the <b>manual demand plan</b> against our <b>AI forecast</b>
             on the same months and products. Accuracy is shown as
             "how close to 100%", so higher is better. Bigger AI improvement =
             stronger case for AI-led planning.
           </div>""", unsafe_allow_html=True)

    ml_models = sorted(m for m in main_df["model"].dropna().unique() if m != "IBP_Manual")

    best_name, best_acc = best_ai_model(
        main_df, year=year_sel, target="order_value_usd",
        level="Total", on_ibp_scope=True)

    control_options = ["🏆 Best AI Model (auto)"] + ml_models

    ctrl = st.columns([1.0, 1.6, 1.4])
    with ctrl[0]:
        years = sorted([int(y) for y in main_df["year"].dropna().unique()])
        ibp_year = st.selectbox(
            "Year", options=years,
            index=years.index(2025) if 2025 in years else 0,
            key="aim_year")
    with ctrl[1]:
        ai_pick = st.selectbox(
            "AI Model", options=control_options, index=0,
            key="aim_model",
            help=("Auto-pick chooses the AI model with the best accuracy "
                  "on the same months and products as the manual plan."))
    with ctrl[2]:
        targets = sorted(main_df["target"].dropna().unique())
        target = st.selectbox(
            "Measure", options=targets,
            index=targets.index("order_value_usd") if "order_value_usd" in targets else 0,
            format_func=lambda t: TARGET_LABELS.get(t, t),
            key="aim_target")

    # Recompute best for the selected year (best_acc was for default year)
    if ai_pick.startswith("🏆"):
        best_for_year, _ = best_ai_model(
            main_df, year=ibp_year, target=target,
            level="Total", on_ibp_scope=True)
        ai_model = best_for_year if best_for_year and best_for_year != "—" else (ml_models[0] if ml_models else None)
        ai_label = f"AI ({ai_model}) — auto-selected"
    else:
        ai_model = ai_pick
        ai_label = f"AI ({ai_model})"

    if ai_model is None:
        st.info("No AI models available in this data.")
        return

    base = main_df[
        (main_df["year"] == ibp_year)
        & (main_df["split"] == "split2")
        & (main_df["target"] == target)
        & (main_df["level"] == "Total")
    ].copy()

    if zone_sel and "codp_zone" in base.columns:
        base = base[base["codp_zone"].isin(zone_sel + ["All"])]
    if plant_sel and "plant" in base.columns:
        base = base[base["plant"].isin(plant_sel + ["All"])]
    if cat_sel and "product_category_1" in base.columns:
        base = base[base["product_category_1"].isin(cat_sel + ["All"])]

    if base.empty:
        st.info("No data for this selection.")
        return

    ibp_rows = base[base["model"] == "IBP_Manual"].copy()
    ai_rows  = base[base["model"] == ai_model].copy()

    ibp_monthly = (ibp_rows.groupby("date", as_index=False)
                   .agg(ibp_forecast=("ibp_forecast_cogs", "sum"),
                        ibp_actual=("ibp_actual_cogs", "sum"),
                        is_forward=("is_forward", "max"))
                   .sort_values("date"))
    ibp_monthly["date"] = pd.to_datetime(ibp_monthly["date"])
    ibp_monthly.loc[ibp_monthly["is_forward"] == 1, "ibp_actual"] = np.nan
    ibp_monthly.loc[ibp_monthly["ibp_actual"] == 0, "ibp_actual"] = np.nan

    all_dates = pd.to_datetime([f"{ibp_year}-{m:02d}-01" for m in range(1, 13)])
    # Build ibp_full WITHOUT duplicate 'date' columns: drop the original 'date'
    # column before set_index (set_index doesn't auto-drop a like-named index)
    _ibp_tmp = ibp_monthly.copy()
    _ibp_tmp.index = pd.DatetimeIndex(_ibp_tmp["date"])
    _ibp_tmp = _ibp_tmp.drop(columns=["date"])
    _ibp_tmp.index.name = "date"
    ibp_full = _ibp_tmp.reindex(all_dates).rename_axis("date").reset_index()

    ai_on_ibp = ai_rows[(ai_rows["ibp_actual_cogs"].notna())
                        & (ai_rows["is_forward"] == 0)].copy()
    if not ai_on_ibp.empty and (ai_on_ibp["actual"].abs() > 1e-6).any():
        ratio = np.where(ai_on_ibp["actual"].abs() > 1e-6,
                         ai_on_ibp["ibp_actual_cogs"] / ai_on_ibp["actual"], np.nan)
        ai_on_ibp["ai_forecast_scoped"] = ai_on_ibp["forecast"] * ratio

    # Aggregates restricted to the months we can verify (both IBP fc + IBP actual present)
    mask = ibp_full["ibp_forecast"].notna() & ibp_full["ibp_actual"].notna()
    ibp_sum_f = float(ibp_full.loc[mask, "ibp_forecast"].sum())
    ibp_sum_a = float(ibp_full.loc[mask, "ibp_actual"].sum())
    months_observed = int(mask.sum())

    # Signed error % for the manual plan
    ibp_err_pct = compute_signed_error_pct(ibp_sum_a, ibp_sum_f)

    # AI numbers — on the same scope
    if not ai_on_ibp.empty and "ai_forecast_scoped" in ai_on_ibp.columns:
        ai_sum_f = float(np.nansum(ai_on_ibp["ai_forecast_scoped"]))
        ai_sum_a = float(ai_on_ibp["ibp_actual_cogs"].sum())
    else:
        ai_sum_f = np.nan
        ai_sum_a = np.nan
    ai_err_pct = compute_signed_error_pct(ai_sum_a, ai_sum_f)

    # Improvement = how much smaller AI's absolute error is, in percentage points
    if pd.notna(ai_err_pct) and pd.notna(ibp_err_pct):
        improvement_pp = abs(ibp_err_pct) - abs(ai_err_pct)
    else:
        improvement_pp = np.nan

    # Build AI monthly frame, avoiding the duplicate-'date' column trap
    if not ai_on_ibp.empty and "ai_forecast_scoped" in ai_on_ibp.columns:
        ai_by_month = (ai_on_ibp.groupby("date", as_index=False)["ai_forecast_scoped"]
                       .sum())
        ai_by_month["date"] = pd.to_datetime(ai_by_month["date"])
        _ai_tmp = ai_by_month.copy()
        _ai_tmp.index = pd.DatetimeIndex(_ai_tmp["date"])
        _ai_tmp = _ai_tmp.drop(columns=["date"])
        _ai_tmp.index.name = "date"
        ai_full = _ai_tmp.reindex(all_dates).rename_axis("date").reset_index()
    else:
        ai_full = pd.DataFrame({"date": all_dates,
                                "ai_forecast_scoped": [np.nan] * len(all_dates)})

    # ============ KPI CARDS ============
    st.markdown('<div class="cx-section">Headline — AI vs Manual</div>',
                unsafe_allow_html=True)

    kc = st.columns(4)
    with kc[0]:
        if pd.isna(ibp_err_pct):
            sub, cls = "", "cx-delta-neutral"
        elif abs(ibp_err_pct) <= 5:
            sub, cls = f"Close to plan · {months_observed} months", "cx-delta-pos"
        elif ibp_err_pct > 0:
            sub, cls = f"Sold more than planned · {months_observed} months", "cx-delta-pos"
        else:
            sub, cls = f"Sold less than planned · {months_observed} months", "cx-delta-neg"
        kpi_card("Manual Plan Error",
                 fmt_signed_pct(ibp_err_pct), sub, cls)
    with kc[1]:
        if pd.isna(ai_err_pct):
            sub, cls = "", "cx-delta-neutral"
        elif abs(ai_err_pct) <= 5:
            sub, cls = f"Close to plan · Using {ai_model}", "cx-delta-pos"
        elif ai_err_pct > 0:
            sub, cls = f"Predicted low · Using {ai_model}", "cx-delta-pos"
        else:
            sub, cls = f"Predicted high · Using {ai_model}", "cx-delta-neg"
        kpi_card("AI Forecast Error",
                 fmt_signed_pct(ai_err_pct), sub, cls)
    with kc[2]:
        if pd.isna(improvement_pp):
            sub, cls = "", "cx-delta-neutral"
        elif improvement_pp > 0:
            sub, cls = "AI has smaller error", "cx-delta-pos"
        elif improvement_pp < 0:
            sub, cls = "Manual has smaller error", "cx-delta-neg"
        else:
            sub, cls = "Same error", "cx-delta-neutral"
        kpi_card("AI Improvement",
                 fmt_pp(improvement_pp), sub, cls)
    with kc[3]:
        # Dollar-value error reduction (|manual_err_$| − |ai_err_$|)
        ibp_err_usd = abs(ibp_sum_a - ibp_sum_f) if pd.notna(ibp_sum_f) and pd.notna(ibp_sum_a) else np.nan
        ai_err_usd  = abs(ai_sum_a - ai_sum_f)   if pd.notna(ai_sum_f)  and pd.notna(ai_sum_a)  else np.nan
        err_reduction_usd = (ibp_err_usd - ai_err_usd) if (pd.notna(ibp_err_usd) and pd.notna(ai_err_usd)) else np.nan
        cls = "cx-delta-pos" if (pd.notna(err_reduction_usd) and err_reduction_usd > 0) else "cx-delta-neg"
        sub = "Less forecast error" if (pd.notna(err_reduction_usd) and err_reduction_usd > 0) else "More forecast error"
        kpi_card("Error Reduction",
                 fmt_money(err_reduction_usd), sub, cls)

    # ============ TWO PAIRED CHARTS ============
    st.markdown('<div class="cx-section">AI Forecast vs Actual  &  Manual Forecast vs Actual</div>',
                unsafe_allow_html=True)

    # Shared y-axis so both pairs are visually comparable
    all_vals = []
    all_vals.extend(ibp_full["ibp_forecast"].dropna().tolist())
    all_vals.extend(ibp_full["ibp_actual"].dropna().tolist())
    all_vals.extend(ai_full["ai_forecast_scoped"].dropna().tolist())
    y_max = max(all_vals) * 1.12 if all_vals else None

    pair_l, pair_r = st.columns(2)

    # ---- LEFT: AI Forecast vs Actual ----
    with pair_l:
        st.markdown(
            f"""<div class="cx-chart-title" style="color:{c['ai']};">
                  🤖 AI Forecast vs Actual — {fmt_signed_pct(ai_err_pct)} error
                </div>
                <div class="cx-chart-sub">{ai_label}</div>""",
            unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=ai_full["date"], y=ai_full["ai_forecast_scoped"],
            name="AI Forecast", marker_color=c["ai"]))
        fig.add_trace(go.Bar(
            x=ibp_full["date"], y=ibp_full["ibp_actual"],
            name="Actual", marker_color=c["actual"]))
        fig.update_xaxes(tickformat="%b")
        fig.update_yaxes(tickprefix="$", separatethousands=True,
                         range=[0, y_max] if y_max else None)
        fig.update_layout(barmode="group")
        st.plotly_chart(_base_layout(fig, height=380), use_container_width=True)
        st.caption(
            f"Forecast: {fmt_money(ai_sum_f)}  ·  "
            f"Actual: {fmt_money(ai_sum_a)}  ·  "
            f"Error: {fmt_money(ai_err_usd) if pd.notna(ai_err_usd) else '—'}"
        )

    # ---- RIGHT: Manual Forecast vs Actual ----
    with pair_r:
        st.markdown(
            f"""<div class="cx-chart-title" style="color:{c['manual']};">
                  ✍️ Manual Forecast vs Actual — {fmt_signed_pct(ibp_err_pct)} error
                </div>
                <div class="cx-chart-sub">Today's demand consensus</div>""",
            unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=ibp_full["date"], y=ibp_full["ibp_forecast"],
            name="Manual Forecast", marker_color=c["manual"]))
        fig.add_trace(go.Bar(
            x=ibp_full["date"], y=ibp_full["ibp_actual"],
            name="Actual", marker_color=c["actual"]))
        fig.update_xaxes(tickformat="%b")
        fig.update_yaxes(tickprefix="$", separatethousands=True,
                         range=[0, y_max] if y_max else None)
        fig.update_layout(barmode="group")
        st.plotly_chart(_base_layout(fig, height=380), use_container_width=True)
        st.caption(
            f"Forecast: {fmt_money(ibp_sum_f)}  ·  "
            f"Actual: {fmt_money(ibp_sum_a)}  ·  "
            f"Error: {fmt_money(ibp_err_usd) if pd.notna(ibp_err_usd) else '—'}"
        )

    # ---- Headline summary line ----
    if pd.notna(improvement_pp) and pd.notna(err_reduction_usd):
        if improvement_pp > 0:
            verdict_line = (
                f"For the months we can verify, AI's forecast missed by "
                f"<b style='color:{c['success']};'>{fmt_signed_pct(ai_err_pct)}</b> "
                f"vs the manual plan's "
                f"<b style='color:{c['warning']};'>{fmt_signed_pct(ibp_err_pct)}</b> "
                f"— AI cut error by "
                f"<b style='color:{c['success']};'>{abs(improvement_pp):.1f} pts</b> "
                f"(≈ <b style='color:{c['success']};'>{fmt_money(err_reduction_usd)}</b> less error)."
            )
        elif improvement_pp < 0:
            verdict_line = (
                f"For the months we can verify, the manual plan missed by "
                f"<b>{fmt_signed_pct(ibp_err_pct)}</b> "
                f"vs AI's <b>{fmt_signed_pct(ai_err_pct)}</b> — "
                f"manual was {abs(improvement_pp):.1f} pts closer to actual."
            )
        else:
            verdict_line = "AI and manual plan have the same total error."
        st.markdown(
            f"""<div class="cx-info" style="font-size:14px; padding:14px 18px;">
                  {verdict_line}
                </div>""", unsafe_allow_html=True)

    if comp_df is not None and not comp_df.empty:
        st.markdown('<div class="cx-section">Detail by Product Category × Month</div>',
                    unsafe_allow_html=True)
        cmp_filt = comp_df.copy()
        if cat_sel:
            cmp_filt = cmp_filt[cmp_filt["product_category_1"].isin(cat_sel)]

        if cmp_filt.empty:
            st.caption("No comparison rows for selected categories.")
        else:
            disp = cmp_filt.copy()
            disp["Month"] = disp["month"].apply(
                lambda m: MONTH_NAMES[int(m) - 1] if 1 <= int(m) <= 12 else str(m))

            # Signed error %: (actual − forecast) / forecast × 100
            if {"model_actual_usd", "model_forecast_usd"}.issubset(disp.columns):
                disp["_ai_err_num"] = np.where(
                    disp["model_forecast_usd"].abs() > 1e-9,
                    (disp["model_actual_usd"] - disp["model_forecast_usd"])
                    / disp["model_forecast_usd"] * 100, np.nan)
            else:
                disp["_ai_err_num"] = np.nan
            if {"ibp_actual_cogs", "ibp_fc_cogs"}.issubset(disp.columns):
                disp["_man_err_num"] = np.where(
                    disp["ibp_fc_cogs"].abs() > 1e-9,
                    (disp["ibp_actual_cogs"] - disp["ibp_fc_cogs"])
                    / disp["ibp_fc_cogs"] * 100, np.nan)
            else:
                disp["_man_err_num"] = np.nan

            disp["Winner"] = np.where(
                disp["_ai_err_num"].abs() < disp["_man_err_num"].abs(),
                "🤖 AI", "✍️ Manual")
            # Tie / both NaN guard
            disp.loc[disp["_ai_err_num"].isna() | disp["_man_err_num"].isna(),
                     "Winner"] = "—"

            disp["AI Error"]     = disp["_ai_err_num"].apply(fmt_signed_pct)
            disp["Manual Error"] = disp["_man_err_num"].apply(fmt_signed_pct)

            for col in ("model_actual_usd", "model_forecast_usd",
                        "ibp_actual_cogs", "ibp_fc_cogs"):
                if col in disp.columns:
                    disp[col] = disp[col].apply(fmt_money)

            rename = {"product_category_1": "Product Category",
                      "ibp_actual_cogs": "Manual Actual",
                      "ibp_fc_cogs": "Manual Forecast",
                      "model_actual_usd": "AI Actual",
                      "model_forecast_usd": "AI Forecast"}
            disp = disp.rename(columns=rename)
            keep_cols = ["Product Category", "Month",
                         "Manual Forecast", "Manual Actual", "Manual Error",
                         "AI Forecast", "AI Actual", "AI Error", "Winner"]
            keep_cols = [col for col in keep_cols if col in disp.columns]
            st.dataframe(disp[keep_cols], use_container_width=True,
                         hide_index=True, height=420)

            ai_wins  = (disp["Winner"] == "🤖 AI").sum()
            man_wins = (disp["Winner"] == "✍️ Manual").sum()
            st.caption(f"AI had smaller error in **{ai_wins}** of {len(disp)} "
                       f"category × month comparisons; manual plan in **{man_wins}**.")

    with st.expander("📘 About this comparison (data scope & method)"):
        st.markdown(
            """
- **Region.** All numbers are US (NAM) only.
- **Manual plan coverage.** The manual plan covers about a tenth of total
  US revenue — the planned-production product set. The AI forecast covers
  the full US revenue surface, so for a fair head-to-head we rescale the AI
  forecast to the same products the manual plan covers.
- **Observed window.** Manual plan actuals are only available for the first
  five months of 2025. Later months in the charts show forecast only, with
  greyed-out actual bars.
- **Categories covered by manual plan (6):** Heat Tracing Components,
  Floor Heating, Control/Monitoring/Power Distribution,
  Polymer Pipe Heat Tracing – BIS, Polymer Pipe Heat Tracing – IND,
  Snow Melting & De-Icing.
            """
        )


# =============================================================================
# TAB 3 — ACCURACY BY LINE
# =============================================================================
def render_accuracy_table(fdf, level_sel, year_sel):
    st.markdown(
        f'<div class="cx-section">Error by Line — {level_sel} · {year_sel}</div>',
        unsafe_allow_html=True)
    st.caption("Forecast Error = (Actual − Forecast) ÷ Forecast. "
               "Positive = sold more than planned, negative = sold less. "
               "Status: ✅ within ±5% · 🟡 within ±15% · 🔴 beyond ±15%.")

    if fdf.empty:
        st.info("No rows for the current filter selection.")
        return

    group_cols = {
        "Total": [],
        "CODP Zone": ["codp_zone"],
        "Plant": ["plant"],
        "Product Category": ["product_category_1"],
        "Group": ["codp_zone", "plant", "product_category_1"],
    }.get(level_sel, [])
    group_cols = [c for c in group_cols if c in fdf.columns]

    if group_cols:
        agg = (fdf.groupby(group_cols, dropna=False)
               .agg(Forecast=("forecast", "sum"),
                    Actual=("actual", "sum"))
               .reset_index())
    else:
        agg = pd.DataFrame({
            "Forecast": [fdf["forecast"].sum()],
            "Actual":   [fdf["actual"].sum()]})

    agg["ErrorPct"] = np.where(
        agg["Forecast"].abs() > 1e-9,
        (agg["Actual"] - agg["Forecast"]) / agg["Forecast"] * 100, np.nan)
    agg["Gap"] = agg["Actual"] - agg["Forecast"]

    def _status(e):
        if pd.isna(e):           return "⚠️ Missing"
        a = abs(e)
        if a <= 5:               return "✅ On Track"
        if a <= 15:              return "🟡 Watch"
        return "🔴 Off Track"

    agg["Status"] = agg["ErrorPct"].apply(_status)
    if group_cols:
        agg["Line Item"] = agg[group_cols].astype(str).agg(" | ".join, axis=1)
    else:
        agg["Line Item"] = "Total"

    rename = {"codp_zone": "Supply Chain Zone", "plant": "Plant",
              "product_category_1": "Product Category"}
    agg = agg.rename(columns=rename)
    disp = pd.DataFrame()
    disp["Forecast Level"] = [level_sel] * len(agg)
    disp["Line Item"] = agg["Line Item"].values
    for opt in ("Supply Chain Zone", "Plant", "Product Category"):
        if opt in agg.columns:
            disp[opt] = agg[opt].values
    disp["Forecast"]      = agg["Forecast"].apply(lambda v: fmt_money(v, compact=False))
    disp["Actual"]        = agg["Actual"].apply(lambda v: fmt_money(v, compact=False))
    disp["Forecast Error"] = agg["ErrorPct"].apply(fmt_signed_pct)
    disp["Gap"]           = agg["Gap"].apply(lambda v: fmt_money(v, compact=False))
    disp["Status"]        = agg["Status"].values

    disp = disp.sort_values("Line Item").reset_index(drop=True)
    st.dataframe(disp, use_container_width=True, hide_index=True, height=520)

    csv = disp.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download as CSV", data=csv,
        file_name=f"forecast_error_{level_sel.lower().replace(' ', '_')}.csv",
        mime="text/csv")


# =============================================================================
# TAB 4 — DRILL DOWN
# =============================================================================
def render_drilldown(fdf):
    c = get_theme()
    st.markdown('<div class="cx-section">Drill Down by Dimension</div>',
                unsafe_allow_html=True)
    if fdf.empty:
        st.info("No rows for current filters.")
        return

    dim_opts = [d for d in ("codp_zone", "plant", "product_category_1")
                if d in fdf.columns]
    if not dim_opts:
        st.info("No drilldown dimensions available.")
        return

    nice = {"codp_zone": "Supply Chain Zone",
            "plant": "Plant",
            "product_category_1": "Product Category"}

    col1, col2 = st.columns([1.2, 4])
    with col1:
        dim = st.selectbox("View by", options=dim_opts,
                           format_func=lambda d: nice[d])

    agg = (fdf[fdf[dim] != "All"].groupby(dim)
           .agg(Forecast=("forecast", "sum"),
                Actual=("actual", "sum"))
           .reset_index())

    agg = agg[agg["Forecast"] > 0]
    agg["ErrorPct"] = (agg["Actual"] - agg["Forecast"]) / agg["Forecast"] * 100
    agg = agg.sort_values("Actual", ascending=False).head(15)

    fig = go.Figure()
    fig.add_trace(go.Bar(name="AI Forecast", x=agg[dim], y=agg["Forecast"],
                         marker_color=c["manual"]))
    fig.add_trace(go.Bar(name="Actual", x=agg[dim], y=agg["Actual"],
                         marker_color=c["actual"]))
    fig.update_yaxes(tickprefix="$", separatethousands=True)
    fig.update_xaxes(tickangle=-25)
    fig.update_layout(barmode="group")
    with col2:
        st.plotly_chart(_base_layout(fig, height=380,
                                     title=f"AI Forecast vs Actual by {nice[dim]}"),
                        use_container_width=True)

    disp = agg.copy()
    disp["Forecast"]       = disp["Forecast"].apply(fmt_money)
    disp["Actual"]         = disp["Actual"].apply(fmt_money)
    disp["Forecast Error"] = disp["ErrorPct"].apply(fmt_signed_pct)
    disp = disp.drop(columns=["ErrorPct"])
    disp = disp.rename(columns={dim: nice[dim]})
    st.dataframe(disp, use_container_width=True, hide_index=True)


# =============================================================================
# TAB 5 — FORWARD PLAN
# =============================================================================
def render_forward_plan(main_df, year_sel, zone_sel, plant_sel, cat_sel):
    c = get_theme()
    st.markdown('<div class="cx-section">Forward Plan — Looking Ahead</div>',
                unsafe_allow_html=True)
    st.caption("Forward months (no actuals yet). Shows what the AI forecast "
               "and the manual plan expect in the coming periods.")

    if "is_forward" not in main_df.columns:
        st.info("This file does not include forward-looking rows.")
        return

    best_name, _ = best_ai_model(main_df, year=year_sel,
                                 target="order_value_usd", level="Total",
                                 on_ibp_scope=True)

    fwd = main_df[(main_df["is_forward"] == 1)
                  & (main_df["target"] == "order_value_usd")
                  & (main_df["level"] == "Total")
                  & (main_df["split"] == "split2")]

    if zone_sel and "codp_zone" in fwd.columns:
        fwd = fwd[fwd["codp_zone"].isin(zone_sel + ["All"])]
    if plant_sel and "plant" in fwd.columns:
        fwd = fwd[fwd["plant"].isin(plant_sel + ["All"])]
    if cat_sel and "product_category_1" in fwd.columns:
        fwd = fwd[fwd["product_category_1"].isin(cat_sel + ["All"])]

    if fwd.empty:
        st.info("No forward-looking rows in current selection.")
        return

    ai_fwd  = (fwd[fwd["model"] == best_name].groupby("date", as_index=False)
               ["forecast"].sum().sort_values("date")) if best_name and best_name != "—" else pd.DataFrame()
    ibp_fwd = (fwd[fwd["model"] == "IBP_Manual"].groupby("date", as_index=False)
               ["ibp_forecast_cogs"].sum().sort_values("date"))

    fig = go.Figure()
    if not ai_fwd.empty:
        fig.add_trace(go.Scatter(
            x=ai_fwd["date"], y=ai_fwd["forecast"], mode="lines+markers",
            name=f"AI Forecast ({best_name})",
            line=dict(color=c["ai"], width=3)))
    if not ibp_fwd.empty:
        fig.add_trace(go.Scatter(
            x=ibp_fwd["date"], y=ibp_fwd["ibp_forecast_cogs"],
            mode="lines+markers", name="Manual Plan",
            line=dict(color=c["manual"], width=3)))
    fig.update_yaxes(tickprefix="$", separatethousands=True)
    fig.update_xaxes(tickformat="%b %Y")
    st.plotly_chart(_base_layout(fig, height=400, title="Forward forecasts"),
                    use_container_width=True)

    if not ai_fwd.empty or not ibp_fwd.empty:
        df_merge = pd.merge(
            ai_fwd.rename(columns={"forecast": "AI Forecast"}) if not ai_fwd.empty
                else pd.DataFrame(columns=["date", "AI Forecast"]),
            ibp_fwd.rename(columns={"ibp_forecast_cogs": "Manual Plan"})
                if not ibp_fwd.empty else pd.DataFrame(columns=["date", "Manual Plan"]),
            on="date", how="outer").sort_values("date")
        df_merge["Month"] = pd.to_datetime(df_merge["date"]).dt.strftime("%b %Y")
        for col in ("AI Forecast", "Manual Plan"):
            if col in df_merge.columns:
                df_merge[col] = df_merge[col].apply(fmt_money)
        cols = ["Month"] + [c for c in ("AI Forecast", "Manual Plan")
                            if c in df_merge.columns]
        st.dataframe(df_merge[cols], use_container_width=True, hide_index=True)


# =============================================================================
# RUN
# =============================================================================
if __name__ == "__main__":
    main()
    c = get_theme()
    st.markdown(
        f"""<div style="margin-top:32px;padding:18px 8px 4px 8px;
            border-top:1px solid {c['border']};
            display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;
            color:{c['text_muted']};font-size:12px;">
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="width:6px;height:6px;border-radius:50%;background:{c['success']};
                    box-shadow:0 0 0 3px {c['success_soft']};"></span>
              <span><b style="color:{c['text']};">Chemelex Demand Forecasting Cockpit</b></span>
              <span>·</span>
              <span>Theme: {st.session_state.theme}</span>
            </div>
            <div>Built for demand planning · powered by AI forecasts</div>
            </div>""",
        unsafe_allow_html=True,
    )
