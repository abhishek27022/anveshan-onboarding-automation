"""
=============================================================================
Anveshan Industries — HR Onboarding Automation · Executive Command Center
=============================================================================

Deploy:
  streamlit run app.py

Requirements:
  streamlit
  pandas
  plotly

What this app does:
  - Upload or auto-load the 3 CSV inputs
  - Apply onboarding task rules
  - Resolve named owners
  - Calculate due dates
  - Flag escalations
  - Render an executive HR command center + Joinee 360 + escalation tower
=============================================================================
"""

import io
import os
import re
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Anveshan HR Onboarding Command Center",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Fixed challenge baseline. Change to date.today() in production.
TODAY = date(2026, 4, 30)

POLICY = {
    "urgent_lead_days": 7,
    "critical_lead_days": 3,
    "full_onboarding_days": 14,
    "plant_keywords": ["plant", "factory", "works", "manufacturing site"],
    "dept_aliases": {
        "r&d": "r&d and innovation",
        "r & d": "r&d and innovation",
        "research and development": "r&d and innovation",
        "sales": "sales & marketing",
        "sales and marketing": "sales & marketing",
        "finance": "finance & accounts",
        "finance and accounts": "finance & accounts",
        "hr": "human resources",
        "human resource": "human resources",
        "mfg": "manufacturing",
        "production": "manufacturing",
    },
    "flagged_references": ["sameer joshi"],
    "senior_ctc_threshold": 15.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS — Executive cockpit style
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
.block-container {
    padding-top: 1.1rem;
    padding-bottom: 2.4rem;
    max-width: 1520px;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #111827 55%, #0b1020 100%);
    border-right: 1px solid rgba(255,255,255,0.08);
}

section[data-testid="stSidebar"] * {
    color: #e5e7eb;
}

div[data-testid="stMetric"] {
    background: linear-gradient(180deg, rgba(255,255,255,0.055), rgba(255,255,255,0.024));
    border: 1px solid rgba(255,255,255,0.10);
    padding: 16px 16px;
    border-radius: 18px;
    box-shadow: 0 16px 45px rgba(0,0,0,0.16);
}

div[data-testid="stMetric"] label {
    color: #94a3b8 !important;
}

div[data-testid="stMetricValue"] {
    font-size: 2.05rem;
    font-weight: 850;
}

[data-testid="stTabs"] button {
    font-weight: 800;
    letter-spacing: -0.01em;
}

.hero-card {
    background:
        radial-gradient(circle at top left, rgba(59,130,246,0.28), transparent 34%),
        radial-gradient(circle at bottom right, rgba(239,68,68,0.18), transparent 32%),
        linear-gradient(135deg, #0f172a 0%, #111827 45%, #020617 100%);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 28px;
    padding: 24px 26px;
    margin-bottom: 18px;
    box-shadow: 0 26px 75px rgba(2,6,23,0.34);
}

.hero-title {
    font-size: 2.15rem;
    line-height: 1.08;
    font-weight: 900;
    color: #f8fafc;
    margin-bottom: 8px;
}

.hero-subtitle {
    color: #cbd5e1;
    font-size: 0.98rem;
    line-height: 1.58;
    max-width: 1120px;
}

.command-strip {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
    margin-top: 18px;
}

.command-item {
    background: rgba(255,255,255,0.062);
    border: 1px solid rgba(255,255,255,0.105);
    border-radius: 18px;
    padding: 14px;
}

.command-label {
    color: #94a3b8;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.command-value {
    color: #ffffff;
    font-size: 1.28rem;
    font-weight: 850;
    margin-top: 4px;
}

.card-shell {
    background: rgba(255,255,255,0.035);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 22px;
    padding: 18px;
    margin-bottom: 18px;
}

.insight-box {
    background: linear-gradient(180deg, rgba(255,255,255,0.052), rgba(255,255,255,0.022));
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 20px;
    padding: 16px;
    min-height: 112px;
}

.insight-title {
    font-size: 0.82rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 800;
}

.insight-main {
    font-size: 1.3rem;
    color: #f8fafc;
    font-weight: 850;
    margin-top: 5px;
}

.insight-sub {
    font-size: 0.86rem;
    color: #cbd5e1;
    margin-top: 6px;
    line-height: 1.45;
}

.pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 850;
    border: 1px solid rgba(255,255,255,0.12);
}

.pill-red { background:#7f1d1d; color:#fff; }
.pill-amber { background:#92400e; color:#fff; }
.pill-green { background:#065f46; color:#fff; }
.pill-blue { background:#075985; color:#fff; }
.pill-violet { background:#581c87; color:#fff; }
.pill-slate { background:#334155; color:#fff; }

.small-muted {
    color: #94a3b8;
    font-size: 0.86rem;
}

.kicker {
    color: #38bdf8;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    font-weight: 900;
}

.hr-divider {
    height: 1px;
    background: rgba(255,255,255,0.08);
    margin: 12px 0 18px 0;
}

@media (max-width: 900px) {
    .command-strip {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def normalize(text):
    if pd.isna(text):
        return ""
    return re.sub(r"\s+", " ", str(text).strip().lower())


def normalize_dept(dept_raw):
    n = normalize(dept_raw)
    return POLICY["dept_aliases"].get(n, n)


def is_plant_location(location):
    loc = normalize(location)
    return any(kw in loc for kw in POLICY["plant_keywords"])


def to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")


def find_default_file(prefix, extensions=(".csv",)):
    candidates = []
    for f in os.listdir("."):
        fl = f.lower()
        if fl.startswith(prefix.lower()) and fl.endswith(extensions):
            candidates.append(f)
    if not candidates:
        return None
    return sorted(candidates, key=lambda x: (len(x), x))[0]


def safe_style_map(styler, func, subset):
    if isinstance(subset, str):
        subset_cols = [subset]
    else:
        subset_cols = list(subset)
    valid_cols = [c for c in subset_cols if c in styler.data.columns]
    if not valid_cols:
        return styler
    if hasattr(styler, "map"):
        return styler.map(func, subset=valid_cols)
    return styler.applymap(func, subset=valid_cols)


def pill(label, tone="slate"):
    return f'<span class="pill pill-{tone}">{label}</span>'

# ─────────────────────────────────────────────────────────────────────────────
# RULE ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def parse_applies_to(applies_to_raw):
    raw = str(applies_to_raw).strip()
    n = normalize(raw)

    if n == "all":
        return {"type": "ALL", "raw": raw}
    if n == "permanent":
        return {"type": "PERMANENT", "raw": raw}
    if n == "intern":
        return {"type": "INTERN", "raw": raw}
    if n in ("plant-based", "plant based", "plant"):
        return {"type": "PLANT", "raw": raw}

    ctc_match = re.match(r"ctc\s*>\s*(\d+(?:\.\d+)?)", n)
    if ctc_match:
        return {"type": "CTC_GT", "value": float(ctc_match.group(1)), "raw": raw}

    items = [x.strip() for x in raw.split(",")]
    normalized_items = [normalize(x) for x in items]

    designation_words = [
        "manager", "engineer", "director", "executive", "officer", "head",
        "analyst", "supervisor", "intern", "associate", "senior", "junior",
        "lead", "specialist", "coordinator",
    ]

    if any(any(dw in ni for dw in designation_words) for ni in normalized_items):
        return {"type": "DESIG_LIST", "values": normalized_items, "raw_values": items, "raw": raw}

    dept_fragments = [
        "manufacturing", "quality", "r&d", "sales", "finance", "hr",
        "human resources", "r&d and innovation", "sales & marketing",
        "finance & accounts", "administration", "logistics", "supply chain",
    ]

    if any(any(frag in ni for frag in dept_fragments) for ni in normalized_items):
        expanded = [POLICY["dept_aliases"].get(ni, ni) for ni in normalized_items]
        return {"type": "DEPT_LIST", "values": expanded, "raw_values": items, "raw": raw}

    return {"type": "DESIG_LIST", "values": normalized_items, "raw_values": items, "raw": raw}


def task_applies(joinee, rule):
    rtype = rule["type"]

    if rtype == "ALL":
        return True, "Applies to ALL employees"
    if rtype == "PERMANENT":
        return (True, "Employment type = Permanent") if joinee["employment_type_n"] == "permanent" else (False, "")
    if rtype == "INTERN":
        return (True, "Employment type = Intern") if joinee["employment_type_n"] == "intern" else (False, "")
    if rtype == "PLANT":
        return (True, f"Plant-based location ({joinee['location']})") if joinee["is_plant"] else (False, "")
    if rtype == "CTC_GT":
        threshold = rule["value"]
        return (True, f"CTC {joinee['ctc_lpa']} LPA > {threshold} LPA") if joinee["ctc_lpa"] > threshold else (False, "")
    if rtype == "DEPT_LIST":
        jdept = joinee["department_n"]
        for val in rule["values"]:
            val_expanded = POLICY["dept_aliases"].get(val, val)
            if jdept == val_expanded or val_expanded in jdept or jdept in val_expanded:
                return True, f"Department '{joinee['department']}' matches rule {rule['raw_values']}"
        return False, ""
    if rtype == "DESIG_LIST":
        jdesig = normalize(joinee["designation"])
        for val in rule["values"]:
            if val in jdesig or jdesig in val:
                return True, f"Designation '{joinee['designation']}' matches rule {rule['raw_values']}"
        return False, ""
    return False, ""


def build_contact_lookup(contacts_df):
    lookup = {}
    for _, row in contacts_df.iterrows():
        role_n = normalize(row.get("role", ""))
        entry = {
            "name": str(row.get("name", "")).strip(),
            "email": str(row.get("email", "")).strip(),
            "location": normalize(row.get("location", "")),
        }
        lookup.setdefault(role_n, []).append(entry)
    return lookup


def resolve_owner(owner_role_raw, joinee, contact_lookup):
    role_n = normalize(owner_role_raw)

    if role_n == "reporting manager":
        return joinee["reports_to"], joinee["reports_to_email"], True

    if role_n in ("plant hr", "plant admin"):
        loc_n = normalize(joinee["location"])
        loc_words = [w for w in loc_n.split() if len(w) > 3]
        for key, contacts in contact_lookup.items():
            if role_n in key and any(loc_word in key for loc_word in loc_words):
                return contacts[0]["name"], contacts[0]["email"], True
        if role_n in contact_lookup:
            return contact_lookup[role_n][0]["name"], contact_lookup[role_n][0]["email"], True
        return "MISSING OWNER", "N/A", False

    if role_n in contact_lookup:
        return contact_lookup[role_n][0]["name"], contact_lookup[role_n][0]["email"], True

    for key, contacts in contact_lookup.items():
        if role_n in key or key in role_n:
            return contacts[0]["name"], contacts[0]["email"], True

    return "MISSING OWNER", "N/A", False


def escalation_for_task(row, today):
    reasons = []
    priority = "Medium"
    due_date = row["due_date_dt"]
    joining_date = row["joining_date_dt"]
    lead_time = (joining_date - today).days

    if joining_date <= today:
        reasons.append(f"Joinee already joined on {joining_date} — all tasks OVERDUE")
        priority = "Critical"
    elif due_date < today:
        reasons.append(f"Due date {due_date} already passed")
        priority = "High"
    elif lead_time < POLICY["urgent_lead_days"]:
        reasons.append(f"Urgent joining: only {lead_time} days lead time")
        priority = "High"

    if row["owner_name"] == "MISSING OWNER":
        reasons.append("No owner mapped — manual assignment required")
        if priority == "Medium":
            priority = "High"

    if row["sensitivity"] == "Highly Confidential":
        reasons.append("Highly Confidential task — senior approval required")

    if row.get("reference_flag"):
        reasons.append("Reference employee on notice — HR Manager re-validation required")
        if priority == "Medium":
            priority = "High"

    if reasons:
        if joining_date <= today or due_date < today:
            status = "OVERDUE"
        elif lead_time < POLICY["urgent_lead_days"]:
            status = "AT RISK"
        elif row.get("reference_flag") and row["owner_name"] != "MISSING OWNER":
            status = "FLAGGED"
        else:
            status = "AT RISK"
        return True, "; ".join(reasons), priority, status

    return False, "", "", "Pending"


def validate_required_columns(df, required_cols, file_label):
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"{file_label} is missing required columns: {', '.join(missing)}")


def run_pipeline(joinees_df, tasks_df, contacts_df):
    required_joinee_cols = [
        "request_date", "name", "employee_id", "designation", "department",
        "reports_to", "reports_to_email", "location", "joining_date",
        "employment_type", "ctc_lpa", "systems_required", "reference_employee",
    ]
    required_task_cols = ["task_id", "task_name", "owner_role", "days_before_joining", "applies_to", "sensitivity"]
    required_contact_cols = ["role", "name", "email"]

    validate_required_columns(joinees_df, required_joinee_cols, "new_joinees.csv")
    validate_required_columns(tasks_df, required_task_cols, "onboarding_tasks_master.csv")
    validate_required_columns(contacts_df, required_contact_cols, "department_contacts.csv")

    df = joinees_df.copy()
    df["joining_date_dt"] = pd.to_datetime(df["joining_date"]).dt.date
    df["request_date_dt"] = pd.to_datetime(df["request_date"]).dt.date
    df["department_n"] = df["department"].apply(normalize_dept)
    df["designation_n"] = df["designation"].apply(normalize)
    df["employment_type_n"] = df["employment_type"].apply(normalize)
    df["location_n"] = df["location"].apply(normalize)
    df["is_plant"] = df["location"].apply(is_plant_location)
    df["ctc_lpa"] = pd.to_numeric(df["ctc_lpa"], errors="coerce").fillna(0)
    df["lead_time_days"] = df.apply(lambda r: (r["joining_date_dt"] - r["request_date_dt"]).days, axis=1)
    df["reference_flag"] = df["reference_employee"].apply(
        lambda x: normalize(x) in POLICY["flagged_references"] if not pd.isna(x) else False
    )

    contact_lookup = build_contact_lookup(contacts_df)
    rows = []

    for _, joinee in df.iterrows():
        j = joinee.to_dict()
        joining_date = j["joining_date_dt"]
        for _, task in tasks_df.iterrows():
            owner_roles_raw = [r.strip() for r in str(task["owner_role"]).split("+") if r.strip()]
            rule = parse_applies_to(str(task["applies_to"]).strip())
            applies, reason = task_applies(j, rule)
            if not applies:
                continue

            due_date = joining_date - timedelta(days=int(task["days_before_joining"]))
            for owner_role_raw in owner_roles_raw:
                owner_name, owner_email, _ = resolve_owner(owner_role_raw, j, contact_lookup)
                row = {
                    "employee_id": j["employee_id"],
                    "joinee_name": j["name"],
                    "designation": j["designation"],
                    "department": j["department"],
                    "location": j["location"],
                    "employment_type": j["employment_type"],
                    "ctc_lpa": j["ctc_lpa"],
                    "systems_required": j["systems_required"],
                    "reference_employee": j["reference_employee"],
                    "reports_to": j["reports_to"],
                    "reports_to_email": j["reports_to_email"],
                    "request_date": str(j["request_date_dt"]),
                    "joining_date": str(joining_date),
                    "task_id": task["task_id"],
                    "task_name": task["task_name"],
                    "applies_to": task["applies_to"],
                    "rule_type": rule["type"],
                    "rule_matched": reason,
                    "owner_role": owner_role_raw,
                    "owner_name": owner_name,
                    "owner_email": owner_email,
                    "days_before_joining": int(task["days_before_joining"]),
                    "due_date": str(due_date),
                    "sensitivity": task["sensitivity"],
                    "due_date_dt": due_date,
                    "joining_date_dt": joining_date,
                    "reference_flag": j["reference_flag"],
                }
                esc, esc_reason, esc_priority, status = escalation_for_task(row, TODAY)
                row["task_status_initial"] = status
                row["escalation_required"] = "Yes" if esc else "No"
                row["escalation_reason"] = esc_reason
                row["escalation_priority"] = esc_priority if esc else ""
                row["days_to_joining"] = (joining_date - TODAY).days
                row["due_in_days"] = (due_date - TODAY).days
                row["recommended_action"] = recommended_action(row)
                rows.append(row)

    action_df = pd.DataFrame(rows)
    if action_df.empty:
        return pd.DataFrame(), df

    priority_rank = {"Critical": 0, "High": 1, "Medium": 2, "": 3}
    status_rank = {"OVERDUE": 0, "AT RISK": 1, "FLAGGED": 2, "Pending": 3}
    action_df["priority_rank"] = action_df["escalation_priority"].map(priority_rank).fillna(3)
    action_df["status_rank"] = action_df["task_status_initial"].map(status_rank).fillna(3)
    action_df = action_df.sort_values(["priority_rank", "status_rank", "due_date", "joining_date"])
    return action_df, df


def recommended_action(row):
    if row["joining_date_dt"] <= TODAY:
        return "IMMEDIATE: Complete same-day; joinee already on-site"
    if row["task_status_initial"] == "OVERDUE":
        return "Escalate to owner today and close before EOD"
    if row["owner_name"] == "MISSING OWNER":
        return "Assign owner manually before workflow continues"
    if row.get("reference_flag"):
        return "HR Manager validation needed before proceeding"
    if row["sensitivity"] == "Highly Confidential":
        return "Route for senior approval and access validation"
    if row["task_status_initial"] == "AT RISK":
        return "Pull forward task and confirm owner commitment"
    return "Proceed as planned"

# ─────────────────────────────────────────────────────────────────────────────
# STYLING HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def color_priority(val):
    if val == "Critical":
        return "background-color:#7F1D1D;color:#FFFFFF;font-weight:800"
    if val == "High":
        return "background-color:#92400E;color:#FFFFFF;font-weight:800"
    if val == "Medium":
        return "background-color:#581C87;color:#FFFFFF;font-weight:700"
    return ""


def color_status(val):
    if val == "OVERDUE":
        return "background-color:#7F1D1D;color:#FFFFFF;font-weight:800"
    if val == "AT RISK":
        return "background-color:#92400E;color:#FFFFFF;font-weight:800"
    if val == "FLAGGED":
        return "background-color:#581C87;color:#FFFFFF;font-weight:700"
    if val == "Pending":
        return "background-color:#064E3B;color:#FFFFFF;font-weight:700"
    return ""


def color_esc(val):
    return "background-color:#7F1D1D;color:#FFFFFF;font-weight:800" if val == "Yes" else ""


def color_urgent(val):
    try:
        val = int(val)
    except Exception:
        return ""
    if val > 10:
        return "background-color:#7F1D1D;color:#FFFFFF;font-weight:800"
    if val > 0:
        return "background-color:#92400E;color:#FFFFFF;font-weight:800"
    return ""

# ─────────────────────────────────────────────────────────────────────────────
# PLOT HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def style_plotly(fig, height=360):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        margin=dict(l=20, r=20, t=52, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E5E7EB", size=12),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.08)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.08)")
    return fig


def status_donut(action_df):
    d = action_df["task_status_initial"].value_counts().reset_index()
    d.columns = ["Status", "Count"]
    color_map = {"OVERDUE": "#EF4444", "AT RISK": "#F59E0B", "FLAGGED": "#8B5CF6", "Pending": "#22C55E"}
    fig = px.pie(d, names="Status", values="Count", hole=0.62, color="Status", color_discrete_map=color_map, title="Task status mix")
    fig.update_traces(textinfo="percent+label", marker=dict(line=dict(color="#111827", width=2)))
    return style_plotly(fig, 350)


def owner_load_chart(action_df):
    d = (
        action_df[action_df["owner_name"] != "MISSING OWNER"]
        .groupby("owner_name")
        .agg(
            total_tasks=("task_id", "count"),
            urgent_tasks=("escalation_priority", lambda x: x.isin(["Critical", "High"]).sum()),
        )
        .reset_index()
        .sort_values("total_tasks", ascending=True)
        .tail(10)
    )
    fig = go.Figure()
    fig.add_trace(go.Bar(y=d["owner_name"], x=d["total_tasks"], orientation="h", name="Total", marker_color="#38BDF8"))
    fig.add_trace(go.Bar(y=d["owner_name"], x=d["urgent_tasks"], orientation="h", name="Urgent", marker_color="#EF4444"))
    fig.update_layout(title="Owner workload vs urgency", barmode="overlay")
    return style_plotly(fig, 390)


def due_timeline_chart(action_df):
    d = action_df.copy()
    d["due_date"] = pd.to_datetime(d["due_date"])
    d = d.groupby(["due_date", "task_status_initial"]).size().reset_index(name="tasks")
    color_map = {"OVERDUE": "#EF4444", "AT RISK": "#F59E0B", "FLAGGED": "#8B5CF6", "Pending": "#22C55E"}
    fig = px.bar(d, x="due_date", y="tasks", color="task_status_initial", color_discrete_map=color_map, title="Due-date workload timeline")
    fig.update_layout(barmode="stack")
    return style_plotly(fig, 380)


def department_treemap(action_df):
    d = action_df.groupby(["department", "location", "task_status_initial"]).size().reset_index(name="tasks")
    fig = px.treemap(d, path=["department", "location", "task_status_initial"], values="tasks", color="task_status_initial", title="Department × location risk map", color_discrete_map={"OVERDUE": "#EF4444", "AT RISK": "#F59E0B", "FLAGGED": "#8B5CF6", "Pending": "#22C55E"})
    return style_plotly(fig, 390)


def sensitivity_bar(action_df):
    d = action_df.groupby(["sensitivity", "task_status_initial"]).size().reset_index(name="tasks")
    fig = px.bar(d, x="sensitivity", y="tasks", color="task_status_initial", barmode="group", title="Sensitivity exposure by task status", color_discrete_map={"OVERDUE": "#EF4444", "AT RISK": "#F59E0B", "FLAGGED": "#8B5CF6", "Pending": "#22C55E"})
    return style_plotly(fig, 350)


def readiness_gauge(score, title="Readiness score"):
    if score >= 80:
        color = "#22C55E"
    elif score >= 50:
        color = "#F59E0B"
    else:
        color = "#EF4444"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "/100", "font": {"size": 40}},
        title={"text": title},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 50], "color": "rgba(239,68,68,0.20)"},
                {"range": [50, 80], "color": "rgba(245,158,11,0.20)"},
                {"range": [80, 100], "color": "rgba(34,197,94,0.20)"},
            ],
        },
    ))
    return style_plotly(fig, 300)

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOAD
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Running onboarding automation engine…")
def cached_pipeline(joinees_bytes, tasks_bytes, contacts_bytes):
    joinees_df = pd.read_csv(io.BytesIO(joinees_bytes))
    tasks_df = pd.read_csv(io.BytesIO(tasks_bytes))
    contacts_df = pd.read_csv(io.BytesIO(contacts_bytes))
    action_df, enriched_df = run_pipeline(joinees_df, tasks_df, contacts_df)
    return action_df, enriched_df, tasks_df, contacts_df


def load_default_bytes():
    joinee_file = find_default_file("new_joinees")
    task_file = find_default_file("onboarding_tasks_master")
    contact_file = find_default_file("department_contacts")
    missing = []
    if not joinee_file:
        missing.append("new_joinees*.csv")
    if not task_file:
        missing.append("onboarding_tasks_master*.csv")
    if not contact_file:
        missing.append("department_contacts*.csv")
    if missing:
        raise FileNotFoundError("Missing default files in repo root: " + ", ".join(missing))
    with open(joinee_file, "rb") as f:
        joinees_bytes = f.read()
    with open(task_file, "rb") as f:
        tasks_bytes = f.read()
    with open(contact_file, "rb") as f:
        contacts_bytes = f.read()
    return joinees_bytes, tasks_bytes, contacts_bytes, {"joinees": joinee_file, "tasks": task_file, "contacts": contact_file}

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏢 Anveshan Industries")
    st.caption("Executive HR Onboarding Command Center")
    st.markdown("---")
    st.markdown("### 📂 Input files")
    uploaded_joinees = st.file_uploader("1. new_joinees.csv", type="csv", key="joinees")
    uploaded_tasks = st.file_uploader("2. onboarding_tasks_master.csv", type="csv", key="tasks")
    uploaded_contacts = st.file_uploader("3. department_contacts.csv", type="csv", key="contacts")
    st.markdown("---")
    st.caption(f"Challenge baseline date: {TODAY.strftime('%d %b %Y')}")
    st.caption("Upload all 3 files to rerun the workflow. If any file is missing, repo defaults are used.")

try:
    if uploaded_joinees and uploaded_tasks and uploaded_contacts:
        action_df, joinees_df, tasks_df, contacts_df = cached_pipeline(uploaded_joinees.getvalue(), uploaded_tasks.getvalue(), uploaded_contacts.getvalue())
        source_note = "Using uploaded CSV files."
    else:
        jb, tb, cb, default_files = load_default_bytes()
        action_df, joinees_df, tasks_df, contacts_df = cached_pipeline(jb, tb, cb)
        source_note = f"Using repo defaults: {default_files['joinees']}, {default_files['tasks']}, {default_files['contacts']}"
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

if action_df.empty:
    st.warning("No tasks generated. Please check input rules and joinee data.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# DERIVED TABLES AND FILTERS
# ─────────────────────────────────────────────────────────────────────────────
esc_df = action_df[action_df["escalation_required"] == "Yes"].copy()
next7 = TODAY + timedelta(days=7)
action_df["_due_dt"] = pd.to_datetime(action_df["due_date"]).dt.date
next7_df = action_df[(action_df["_due_dt"] >= TODAY) & (action_df["_due_dt"] <= next7)].copy()

# Joinee-level summary with readiness
summary_rows = []
for _, j in joinees_df.iterrows():
    eid = j["employee_id"]
    subset = action_df[action_df["employee_id"] == eid]
    critical = int((subset["escalation_priority"] == "Critical").sum())
    high = int((subset["escalation_priority"] == "High").sum())
    missing = int((subset["owner_name"] == "MISSING OWNER").sum())
    overdue = int((subset["task_status_initial"] == "OVERDUE").sum())
    at_risk = int((subset["task_status_initial"] == "AT RISK").sum())
    score = max(0, 100 - critical * 25 - high * 15 - missing * 10 - overdue * 10 - at_risk * 5)
    if score >= 80:
        status_label = "On Track"
    elif score >= 50:
        status_label = "Needs Attention"
    else:
        status_label = "Critical Risk"
    if j["joining_date_dt"] <= TODAY:
        next_action = "IMMEDIATE: joinee is already on-site; close tasks retroactively today"
    elif j["lead_time_days"] < POLICY["urgent_lead_days"]:
        next_action = f"URGENT: only {j['lead_time_days']} days lead time; HR Manager escalation needed"
    elif j["reference_flag"]:
        next_action = "Reference on notice; HR Manager validation required"
    elif overdue + at_risk > 0:
        next_action = f"Expedite {overdue + at_risk} overdue/at-risk task(s)"
    else:
        next_action = "On track; monitor task closure"
    summary_rows.append({
        "employee_id": eid,
        "joinee_name": j["name"],
        "designation": j["designation"],
        "department": j["department"],
        "location": j["location"],
        "employment_type": j["employment_type"],
        "joining_date": str(j["joining_date_dt"]),
        "reports_to": j["reports_to"],
        "reports_to_email": j["reports_to_email"],
        "ctc_lpa": j["ctc_lpa"],
        "systems_required": j["systems_required"],
        "reference_employee": j["reference_employee"],
        "request_date": str(j["request_date_dt"]),
        "lead_time_days": int(j["lead_time_days"]),
        "total_tasks": int(len(subset)),
        "critical_tasks": critical,
        "high_tasks": high,
        "overdue_tasks": overdue,
        "at_risk_tasks": at_risk,
        "confidential_tasks": int(subset["sensitivity"].isin(["Confidential", "Highly Confidential"]).sum()),
        "missing_owner_tasks": missing,
        "readiness_score": int(score),
        "readiness_status": status_label,
        "escalation_required": "Yes" if (subset["escalation_required"] == "Yes").any() else "No",
        "next_action": next_action,
    })
summary_df = pd.DataFrame(summary_rows).sort_values(["readiness_score", "joining_date"])

# Sidebar filters after data exists
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🔎 Global filters")
    departments = ["All"] + sorted(action_df["department"].dropna().unique().tolist())
    locations = ["All"] + sorted(action_df["location"].dropna().unique().tolist())
    employments = ["All"] + sorted(action_df["employment_type"].dropna().unique().tolist())
    priorities = ["All"] + sorted([p for p in action_df["escalation_priority"].dropna().unique().tolist() if p])
    sensitivities = ["All"] + sorted(action_df["sensitivity"].dropna().unique().tolist())
    owner_roles = ["All"] + sorted(action_df["owner_role"].dropna().unique().tolist())
    f_dept = st.selectbox("Department", departments)
    f_location = st.selectbox("Location", locations)
    f_employment = st.selectbox("Employment Type", employments)
    f_priority = st.selectbox("Escalation Priority", priorities)
    f_sensitivity = st.selectbox("Sensitivity", sensitivities)
    f_owner_role = st.selectbox("Owner Role", owner_roles)
    f_search = st.text_input("Search joinee / task / owner")

filtered = action_df.copy()
if f_dept != "All":
    filtered = filtered[filtered["department"] == f_dept]
if f_location != "All":
    filtered = filtered[filtered["location"] == f_location]
if f_employment != "All":
    filtered = filtered[filtered["employment_type"] == f_employment]
if f_priority != "All":
    filtered = filtered[filtered["escalation_priority"] == f_priority]
if f_sensitivity != "All":
    filtered = filtered[filtered["sensitivity"] == f_sensitivity]
if f_owner_role != "All":
    filtered = filtered[filtered["owner_role"] == f_owner_role]
if f_search.strip():
    q = normalize(f_search)
    mask = (
        filtered["joinee_name"].apply(normalize).str.contains(q, na=False)
        | filtered["task_name"].apply(normalize).str.contains(q, na=False)
        | filtered["owner_name"].apply(normalize).str.contains(q, na=False)
        | filtered["employee_id"].apply(normalize).str.contains(q, na=False)
    )
    filtered = filtered[mask]

filtered_summary = summary_df[summary_df["employee_id"].isin(filtered["employee_id"].unique())].copy()
filtered_esc = filtered[filtered["escalation_required"] == "Yes"].copy()

# ─────────────────────────────────────────────────────────────────────────────
# HEADER HERO
# ─────────────────────────────────────────────────────────────────────────────
critical_count = int((action_df["escalation_priority"] == "Critical").sum())
high_count = int((action_df["escalation_priority"] == "High").sum())
missing_count = int((action_df["owner_name"] == "MISSING OWNER").sum())
confidential_count = int(action_df["sensitivity"].isin(["Confidential", "Highly Confidential"]).sum())
worst_joinee = summary_df.iloc[0]
top_owner = (
    action_df[action_df["owner_name"] != "MISSING OWNER"].groupby("owner_name").size().sort_values(ascending=False).index[0]
    if len(action_df[action_df["owner_name"] != "MISSING OWNER"]) else "N/A"
)

st.markdown(
    f"""
<div class="hero-card">
  <div class="kicker">Anveshan Industries · HR Onboarding Operations</div>
  <div class="hero-title">Onboarding Command Center</div>
  <div class="hero-subtitle">
    A decision-first dashboard that converts raw joinee intake into owner-wise actions, due-date risk, escalation triggers,
    and joinee-level readiness. Baseline date: <b>{TODAY.strftime('%d %b %Y')}</b>. {source_note}
  </div>
  <div class="command-strip">
    <div class="command-item"><div class="command-label">Worst readiness</div><div class="command-value risk-critical">{worst_joinee['joinee_name']} · {worst_joinee['readiness_score']}/100</div></div>
    <div class="command-item"><div class="command-label">Critical task load</div><div class="command-value risk-critical">{critical_count} critical</div></div>
    <div class="command-item"><div class="command-label">Top owner load</div><div class="command-value">{top_owner}</div></div>
    <div class="command-item"><div class="command-label">Sensitive exposure</div><div class="command-value">{confidential_count} tasks</div></div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# KPI row
k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
k1.metric("👥 Joinees", len(joinees_df))
k2.metric("✅ Total Tasks", len(action_df))
k3.metric("🚨 Escalations", int((action_df["escalation_required"] == "Yes").sum()), delta="need action", delta_color="inverse")
k4.metric("🔥 Critical", critical_count, delta="highest risk", delta_color="inverse")
k5.metric("⏱ Due Today", int((action_df["due_date"] == str(TODAY)).sum()))
k6.metric("📅 Due in 7 Days", len(next7_df))
k7.metric("👤 Missing Owners", missing_count, delta_color="inverse")

# Tabs
st.markdown("<div class='hr-divider'></div>", unsafe_allow_html=True)
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1. Command Center",
    "2. Joinee 360",
    "3. Escalation Tower",
    "4. Owner Digest",
    "5. Rule Audit",
    "6. Data Quality",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: COMMAND CENTER
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown("### Executive risk cockpit")
    a, b, c, d = st.columns(4)
    a.markdown(f"<div class='insight-box'><div class='insight-title'>Immediate HR focus</div><div class='insight-main'>{worst_joinee['joinee_name']}</div><div class='insight-sub'>{worst_joinee['next_action']}</div></div>", unsafe_allow_html=True)
    b.markdown(f"<div class='insight-box'><div class='insight-title'>Escalation pressure</div><div class='insight-main'>{critical_count + high_count} urgent tasks</div><div class='insight-sub'>{critical_count} Critical · {high_count} High · {missing_count} missing owner tasks</div></div>", unsafe_allow_html=True)
    c.markdown(f"<div class='insight-box'><div class='insight-title'>Owner bottleneck</div><div class='insight-main'>{top_owner}</div><div class='insight-sub'>Highest total task load. Check Owner Digest before sending reminders.</div></div>", unsafe_allow_html=True)
    d.markdown(f"<div class='insight-box'><div class='insight-title'>Sensitive controls</div><div class='insight-main'>{confidential_count} sensitive tasks</div><div class='insight-sub'>Confidential and highly confidential workflows require controlled tracking.</div></div>", unsafe_allow_html=True)

    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.plotly_chart(due_timeline_chart(filtered), use_container_width=True)
    with c2:
        st.plotly_chart(status_donut(filtered), use_container_width=True)

    c3, c4 = st.columns([1, 1])
    with c3:
        st.plotly_chart(owner_load_chart(filtered), use_container_width=True)
    with c4:
        st.plotly_chart(department_treemap(filtered), use_container_width=True)

    st.markdown("### Today’s highest-priority action list")
    action_cols = [
        "escalation_priority", "due_date", "task_status_initial", "joinee_name", "department", "location",
        "task_id", "task_name", "owner_role", "owner_name", "sensitivity", "recommended_action",
    ]
    action_view = filtered[action_cols].head(40).copy()
    styled = action_view.style
    styled = safe_style_map(styled, color_priority, "escalation_priority")
    styled = safe_style_map(styled, color_status, "task_status_initial")
    st.dataframe(styled, use_container_width=True, hide_index=True, height=520)

    dl1, dl2, dl3 = st.columns(3)
    dl1.download_button("⬇️ Full Action Plan CSV", to_csv_bytes(action_df.drop(columns=["_due_dt"], errors="ignore")), "01_onboarding_action_plan.csv", "text/csv")
    dl2.download_button("⬇️ Escalation List CSV", to_csv_bytes(esc_df.drop(columns=["_due_dt"], errors="ignore")), "03_escalation_list.csv", "text/csv")
    dl3.download_button("⬇️ Joinee Summary CSV", to_csv_bytes(summary_df), "02_joinee_summary.csv", "text/csv")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: JOINEE 360
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### Joinee 360 — readiness, timeline, task ownership")
    joinee_options = filtered_summary["joinee_name"].tolist() if not filtered_summary.empty else summary_df["joinee_name"].tolist()
    default_name = filtered_summary.iloc[0]["joinee_name"] if not filtered_summary.empty else summary_df.iloc[0]["joinee_name"]
    selected_name = st.selectbox("Select joinee", joinee_options, index=joinee_options.index(default_name) if default_name in joinee_options else 0)
    selected = summary_df[summary_df["joinee_name"] == selected_name].iloc[0]
    selected_tasks = action_df[action_df["employee_id"] == selected["employee_id"]].copy()

    j1, j2 = st.columns([0.9, 1.2])
    with j1:
        st.markdown(
            f"""
<div class="card-shell">
  <div class="kicker">Joinee profile</div>
  <h2 style="margin-bottom:4px;">{selected['joinee_name']}</h2>
  <div class="small-muted">{selected['designation']} · {selected['department']} · {selected['location']}</div>
  <div class="hr-divider"></div>
  <b>Employee ID:</b> {selected['employee_id']}<br>
  <b>Employment:</b> {selected['employment_type']}<br>
  <b>Joining:</b> {selected['joining_date']}<br>
  <b>Reports to:</b> {selected['reports_to']}<br>
  <b>Systems:</b> {selected['systems_required']}<br>
  <b>Reference employee:</b> {selected['reference_employee']}<br>
  <br>{pill(selected['readiness_status'], 'red' if selected['readiness_score'] < 50 else 'amber' if selected['readiness_score'] < 80 else 'green')}
</div>
""",
            unsafe_allow_html=True,
        )
    with j2:
        st.plotly_chart(readiness_gauge(int(selected["readiness_score"]), f"{selected['joinee_name']} readiness"), use_container_width=True)

    s1, s2, s3, s4, s5, s6 = st.columns(6)
    s1.metric("Total Tasks", int(selected["total_tasks"]))
    s2.metric("Critical", int(selected["critical_tasks"]))
    s3.metric("High", int(selected["high_tasks"]))
    s4.metric("Overdue", int(selected["overdue_tasks"]))
    s5.metric("Sensitive", int(selected["confidential_tasks"]))
    s6.metric("Missing Owner", int(selected["missing_owner_tasks"]))

    st.info(selected["next_action"])

    timeline = selected_tasks.copy()
    timeline["due_date"] = pd.to_datetime(timeline["due_date"])
    fig = px.timeline(
        timeline.sort_values("due_date"),
        x_start="due_date",
        x_end="joining_date",
        y="task_name",
        color="task_status_initial",
        hover_data=["owner_name", "owner_role", "sensitivity", "escalation_priority"],
        title="Task timeline against joining date",
        color_discrete_map={"OVERDUE": "#EF4444", "AT RISK": "#F59E0B", "FLAGGED": "#8B5CF6", "Pending": "#22C55E"},
    )
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(style_plotly(fig, 460), use_container_width=True)

    st.markdown("### All tasks for selected joinee")
    display_cols = [
        "task_id", "task_name", "rule_matched", "owner_role", "owner_name", "owner_email", "due_date",
        "days_before_joining", "sensitivity", "task_status_initial", "escalation_priority", "recommended_action",
    ]
    jstyled = selected_tasks[display_cols].style
    jstyled = safe_style_map(jstyled, color_priority, "escalation_priority")
    jstyled = safe_style_map(jstyled, color_status, "task_status_initial")
    st.dataframe(jstyled, use_container_width=True, hide_index=True, height=520)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: ESCALATION TOWER
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### Escalation Tower — task-level risk queue")
    if filtered_esc.empty:
        st.success("No escalation tasks under current filters.")
    else:
        e1, e2, e3 = st.columns([1, 1, 1])
        e1.metric("Critical", int((filtered_esc["escalation_priority"] == "Critical").sum()))
        e2.metric("High", int((filtered_esc["escalation_priority"] == "High").sum()))
        e3.metric("Flagged Joinees", filtered_esc["employee_id"].nunique())
        st.plotly_chart(status_donut(filtered_esc), use_container_width=True)
        esc_cols = [
            "escalation_priority", "task_status_initial", "due_date", "joining_date", "joinee_name", "employee_id",
            "task_id", "task_name", "owner_name", "owner_email", "sensitivity", "escalation_reason", "recommended_action",
        ]
        esc_view = filtered_esc[esc_cols].copy()
        estyled = esc_view.style
        estyled = safe_style_map(estyled, color_priority, "escalation_priority")
        estyled = safe_style_map(estyled, color_status, "task_status_initial")
        st.dataframe(estyled, use_container_width=True, hide_index=True, height=620)
        st.download_button("⬇️ Download Escalation List", to_csv_bytes(esc_view), "03_escalation_list.csv", "text/csv")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: OWNER DIGEST
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown("### Owner Digest — accountability and workload balance")
    owner_rows = []
    for (owner_name, owner_email, owner_role), grp in action_df.groupby(["owner_name", "owner_email", "owner_role"]):
        if owner_name == "MISSING OWNER":
            continue
        owner_rows.append({
            "owner_name": owner_name,
            "owner_email": owner_email,
            "owner_role": owner_role,
            "total_tasks": int(len(grp)),
            "urgent_tasks": int(grp["escalation_priority"].isin(["Critical", "High"]).sum()),
            "overdue_tasks": int((grp["task_status_initial"] == "OVERDUE").sum()),
            "due_today": int((grp["due_date"] == str(TODAY)).sum()),
            "sensitive_tasks": int(grp["sensitivity"].isin(["Confidential", "Highly Confidential"]).sum()),
            "joinees_covered": ", ".join(sorted(grp["joinee_name"].unique().tolist())),
        })
    owner_df = pd.DataFrame(owner_rows).sort_values(["urgent_tasks", "total_tasks"], ascending=False)
    st.plotly_chart(owner_load_chart(action_df), use_container_width=True)

    ostyled = owner_df.style
    ostyled = safe_style_map(ostyled, color_urgent, "urgent_tasks")
    ostyled = safe_style_map(ostyled, color_urgent, "overdue_tasks")
    st.dataframe(ostyled, use_container_width=True, hide_index=True, height=520)

    st.markdown("### Copy-ready daily digest")
    selected_owner = st.selectbox("Select owner for email draft", owner_df["owner_name"].unique().tolist())
    owner_tasks = action_df[action_df["owner_name"] == selected_owner]
    owner_email = owner_tasks["owner_email"].iloc[0]
    urgent_owner_tasks = owner_tasks[owner_tasks["escalation_priority"].isin(["Critical", "High"])]
    email_body = f"""Subject: Onboarding tasks requiring your action — {TODAY.strftime('%d %b %Y')}

Hi {selected_owner},

You have {len(owner_tasks)} onboarding task(s), out of which {len(urgent_owner_tasks)} are urgent/critical.

Top actions:
"""
    for _, r in urgent_owner_tasks.head(8).iterrows():
        email_body += f"- {r['joinee_name']} | {r['task_name']} | Due {r['due_date']} | {r['recommended_action']}\n"
    email_body += "\nPlease confirm closure/status by EOD.\n\nRegards,\nHR Onboarding Team"
    st.text_area("Email draft", value=email_body, height=260)
    st.download_button("⬇️ Download Owner Digest CSV", to_csv_bytes(owner_df), "04_owner_daily_digest.csv", "text/csv")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5: RULE AUDIT
# ─────────────────────────────────────────────────────────────────────────────
with tab5:
    st.markdown("### Rule Audit — why every task was applied")
    rule_rows = []
    for _, task in tasks_df.iterrows():
        rule = parse_applies_to(task["applies_to"])
        matched = action_df[action_df["task_id"] == task["task_id"]]
        rule_rows.append({
            "task_id": task["task_id"],
            "task_name": task["task_name"],
            "owner_role": task["owner_role"],
            "applies_to_raw": task["applies_to"],
            "interpreted_rule_type": rule["type"],
            "days_before_joining": task["days_before_joining"],
            "sensitivity": task["sensitivity"],
            "generated_rows": int(len(matched)),
            "matched_joinees": int(matched["employee_id"].nunique()) if not matched.empty else 0,
        })
    rule_df = pd.DataFrame(rule_rows)
    st.dataframe(rule_df, use_container_width=True, hide_index=True, height=420)

    st.markdown("### Explainability sample — generated action rows")
    explain_cols = ["joinee_name", "employee_id", "task_id", "task_name", "applies_to", "rule_type", "rule_matched", "owner_name", "due_date", "sensitivity"]
    st.dataframe(action_df[explain_cols].head(80), use_container_width=True, hide_index=True, height=480)
    st.download_button("⬇️ Download Rule Audit CSV", to_csv_bytes(rule_df), "rule_audit.csv", "text/csv")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 6: DATA QUALITY
# ─────────────────────────────────────────────────────────────────────────────
with tab6:
    st.markdown("### Data Quality — readiness for production rollout")
    dq_rows = []
    dq_rows.append({"check": "Required joinee columns", "status": "Pass", "issue_count": 0, "recommendation": "Input schema available"})
    dq_rows.append({"check": "Required task master columns", "status": "Pass", "issue_count": 0, "recommendation": "Task schema available"})
    dq_rows.append({"check": "Missing owner mappings", "status": "Pass" if missing_count == 0 else "Fail", "issue_count": missing_count, "recommendation": "Maintain role/location-aware contact master"})
    duplicate_rows = int(action_df.duplicated(subset=["employee_id", "task_id", "owner_role"]).sum())
    dq_rows.append({"check": "Duplicate employee-task-owner rows", "status": "Pass" if duplicate_rows == 0 else "Review", "issue_count": duplicate_rows, "recommendation": "T014 HR + Legal split is expected; other duplicates should be reviewed"})
    blank_emails = int((action_df["owner_email"].fillna("") == "").sum())
    dq_rows.append({"check": "Blank owner emails", "status": "Pass" if blank_emails == 0 else "Fail", "issue_count": blank_emails, "recommendation": "Fix contacts file before sending workflow emails"})
    restricted = int(action_df["systems_required"].fillna("").str.contains("ERP|MES|Finance|R&D|SAP", case=False, regex=True).sum())
    dq_rows.append({"check": "Restricted system exposure", "status": "Review", "issue_count": restricted, "recommendation": "Route restricted system access through approval workflow"})
    dq_df = pd.DataFrame(dq_rows)
    st.dataframe(dq_df, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(sensitivity_bar(action_df), use_container_width=True)
    with c2:
        st.plotly_chart(department_treemap(action_df), use_container_width=True)

    st.markdown("### Source data preview")
    p1, p2, p3 = st.tabs(["Joinees", "Task Master", "Contacts"])
    with p1:
        st.dataframe(joinees_df, use_container_width=True, hide_index=True, height=320)
    with p2:
        st.dataframe(tasks_df, use_container_width=True, hide_index=True, height=320)
    with p3:
        st.dataframe(contacts_df, use_container_width=True, hide_index=True, height=320)

# Footer
st.markdown("<div class='hr-divider'></div>", unsafe_allow_html=True)
st.caption(
    f"Anveshan Industries HR Onboarding Automation · Generated using baseline date {TODAY.strftime('%d %b %Y')} · "
    "Replace the three input files to rerun this workflow for next week's joinees."
)
