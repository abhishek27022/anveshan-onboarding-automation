"""
=============================================================================
Anveshan Industries — HR Onboarding Automation · Streamlit Web App
=============================================================================
Deploy to Streamlit Cloud (free, public URL, no login required):
  1. Push this repo to GitHub
  2. Go to share.streamlit.io → New app → point to app.py
  3. Share the URL with anyone

Local run:
  streamlit run app.py
=============================================================================
"""

import streamlit as st
import pandas as pd
import io
import re
import os
from datetime import date, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Anveshan HR Onboarding",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# POLICY CONSTANTS  (edit here if policy changes)
# ─────────────────────────────────────────────────────────────────────────────
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

TODAY = date.today()

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS  (same logic as onboarding_automation.py)
# ─────────────────────────────────────────────────────────────────────────────

def normalize(text):
    if pd.isna(text):
        return ""
    return re.sub(r'\s+', ' ', str(text).strip().lower())

def normalize_dept(dept_raw):
    n = normalize(dept_raw)
    return POLICY["dept_aliases"].get(n, n)

def is_plant_location(location):
    loc = normalize(location)
    return any(kw in loc for kw in POLICY["plant_keywords"])

def parse_applies_to(applies_to_raw):
    raw = str(applies_to_raw).strip()
    n = normalize(raw)
    if n == "all":
        return {"type": "ALL"}
    if n == "permanent":
        return {"type": "PERMANENT"}
    if n == "intern":
        return {"type": "INTERN"}
    if n in ("plant-based", "plant based", "plant"):
        return {"type": "PLANT"}
    ctc_match = re.match(r'ctc\s*>\s*(\d+(?:\.\d+)?)', n)
    if ctc_match:
        return {"type": "CTC_GT", "value": float(ctc_match.group(1))}

    items = [x.strip() for x in raw.split(",")]
    normalized_items = [normalize(x) for x in items]

    designation_words = [
        "manager", "engineer", "director", "executive", "officer",
        "head", "analyst", "supervisor", "intern", "associate",
        "senior", "junior", "lead", "specialist", "coordinator"
    ]
    if any(any(dw in ni for dw in designation_words) for ni in normalized_items):
        return {"type": "DESIG_LIST", "values": normalized_items, "raw_values": items}

    dept_fragments = [
        "manufacturing", "quality", "r&d", "sales", "finance", "hr",
        "human resources", "r&d and innovation", "sales & marketing",
        "finance & accounts", "administration", "logistics", "supply chain"
    ]
    if any(any(frag in ni for frag in dept_fragments) for ni in normalized_items):
        expanded = [POLICY["dept_aliases"].get(ni, ni) for ni in normalized_items]
        return {"type": "DEPT_LIST", "values": expanded, "raw_values": items}
    return {"type": "DESIG_LIST", "values": normalized_items, "raw_values": items}


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
        return (True, f"CTC {joinee['ctc_lpa']} LPA > {threshold} LPA (senior hire)") if joinee["ctc_lpa"] > threshold else (False, "")
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
        role_n = normalize(row["role"])
        entry = {
            "name": str(row["name"]).strip(),
            "email": str(row["email"]).strip(),
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
        for key in contact_lookup:
            if role_n in key and any(loc_word in key for loc_word in loc_n.split() if len(loc_word) > 3):
                return contact_lookup[key][0]["name"], contact_lookup[key][0]["email"], True
        if role_n in contact_lookup:
            return contact_lookup[role_n][0]["name"], contact_lookup[role_n][0]["email"], True
        return "MISSING OWNER", "N/A", False
    if role_n in contact_lookup:
        return contact_lookup[role_n][0]["name"], contact_lookup[role_n][0]["email"], True
    for key in contact_lookup:
        if role_n in key or key in role_n:
            return contact_lookup[key][0]["name"], contact_lookup[key][0]["email"], True
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
        reasons.append(f"Due date {due_date} already passed (today {today})")
        if priority != "Critical":
            priority = "High"
    elif lead_time < POLICY["urgent_lead_days"]:
        reasons.append(f"Urgent joining: only {lead_time} days lead time (min = {POLICY['urgent_lead_days']} days)")
        if priority != "Critical":
            priority = "High"
    if row["owner_name"] == "MISSING OWNER":
        reasons.append("No owner mapped — manual assignment required")
        if priority == "Medium":
            priority = "High"
    if row["sensitivity"] == "Highly Confidential":
        reasons.append("Highly Confidential task — CFO/R&D Head sign-off required")
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


def run_pipeline(joinees_df, tasks_df, contacts_df):
    """Core pipeline — same logic as onboarding_automation.py main()."""
    df = joinees_df.copy()
    df["joining_date_dt"]   = pd.to_datetime(df["joining_date"]).dt.date
    df["request_date_dt"]   = pd.to_datetime(df["request_date"]).dt.date
    df["department_n"]      = df["department"].apply(normalize_dept)
    df["designation_n"]     = df["designation"].apply(normalize)
    df["employment_type_n"] = df["employment_type"].apply(normalize)
    df["location_n"]        = df["location"].apply(normalize)
    df["is_plant"]          = df["location"].apply(is_plant_location)
    df["ctc_lpa"]           = pd.to_numeric(df["ctc_lpa"], errors="coerce").fillna(0)
    df["lead_time_days"]    = df.apply(lambda r: (r["joining_date_dt"] - r["request_date_dt"]).days, axis=1)
    df["reference_flag"]    = df["reference_employee"].apply(
        lambda x: normalize(x) in POLICY["flagged_references"] if not pd.isna(x) else False
    )
    contact_lookup = build_contact_lookup(contacts_df)

    rows = []
    for _, joinee in df.iterrows():
        j = joinee.to_dict()
        joining_date = j["joining_date_dt"]
        for _, task in tasks_df.iterrows():
            owner_roles_raw = [r.strip() for r in str(task["owner_role"]).split("+")]
            rule = parse_applies_to(str(task["applies_to"]).strip())
            applies, reason = task_applies(j, rule)
            if not applies:
                continue
            due_date = joining_date - timedelta(days=int(task["days_before_joining"]))
            for owner_role_raw in owner_roles_raw:
                owner_name, owner_email, _ = resolve_owner(owner_role_raw, j, contact_lookup)
                row = {
                    "employee_id": j["employee_id"], "joinee_name": j["name"],
                    "designation": j["designation"], "department": j["department"],
                    "location": j["location"], "employment_type": j["employment_type"],
                    "joining_date": str(joining_date),
                    "task_id": task["task_id"], "task_name": task["task_name"],
                    "rule_matched": reason, "owner_role": owner_role_raw,
                    "owner_name": owner_name, "owner_email": owner_email,
                    "days_before_joining": int(task["days_before_joining"]),
                    "due_date": str(due_date), "sensitivity": task["sensitivity"],
                    "due_date_dt": due_date, "joining_date_dt": joining_date,
                    "reference_flag": j["reference_flag"],
                }
                esc, esc_reason, esc_priority, status = escalation_for_task(row, TODAY)
                row["task_status_initial"] = status
                row["escalation_required"] = "Yes" if esc else "No"
                row["escalation_reason"]   = esc_reason
                row["escalation_priority"] = esc_priority if esc else ""
                rows.append(row)

    keep_cols = [
        "employee_id","joinee_name","designation","department","location",
        "employment_type","joining_date","task_id","task_name","rule_matched",
        "owner_role","owner_name","owner_email","due_date","days_before_joining",
        "sensitivity","task_status_initial","escalation_required",
        "escalation_reason","escalation_priority",
    ]
    action_df = pd.DataFrame(rows)[keep_cols]
    return action_df, df


def to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — FILE UPLOADS
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/company.png", width=60)
    st.title("Anveshan Industries")
    st.caption("HR Onboarding Automation v1.0")
    st.divider()

    st.subheader("📂 Upload Input Files")
    uploaded_joinees  = st.file_uploader("1. new_joinees.csv *", type="csv", key="joinees")
    uploaded_tasks    = st.file_uploader("2. onboarding_tasks_master.csv *", type="csv", key="tasks")
    uploaded_contacts = st.file_uploader("3. department_contacts.csv *", type="csv", key="contacts")

    st.divider()
    st.caption(f"🗓 Today: {TODAY}")
    st.caption("Replace new_joinees.csv and re-run for fresh outputs.")

    use_defaults = not (uploaded_joinees and uploaded_tasks and uploaded_contacts)
    if use_defaults:
        st.info("No files uploaded — showing results from the pre-loaded April 2026 batch.", icon="ℹ️")

# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Running onboarding automation engine…")
def cached_pipeline(joinees_bytes, tasks_bytes, contacts_bytes):
    joinees_df  = pd.read_csv(io.BytesIO(joinees_bytes))
    tasks_df    = pd.read_csv(io.BytesIO(tasks_bytes))
    contacts_df = pd.read_csv(io.BytesIO(contacts_bytes))
    return run_pipeline(joinees_df, tasks_df, contacts_df)

try:
    if uploaded_joinees and uploaded_tasks and uploaded_contacts:
        action_df, joinees_df = cached_pipeline(
            uploaded_joinees.getvalue(),
            uploaded_tasks.getvalue(),
            uploaded_contacts.getvalue(),
        )
    else:
        _j = open("new_joinees (1).csv","rb").read()
        _t = open("onboarding_tasks_master.csv","rb").read()
        _c = open("department_contacts.csv","rb").read()
        action_df, joinees_df = cached_pipeline(_j, _t, _c)
    data_ok = True
except Exception as e:
    st.error(f"Error loading data: {e}")
    data_ok = False

if not data_ok:
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# DERIVED TABLES
# ─────────────────────────────────────────────────────────────────────────────
esc_df = action_df[action_df["escalation_required"] == "Yes"].copy()
priority_order = {"Critical": 0, "High": 1, "Medium": 2}
esc_df["_sort"] = esc_df["escalation_priority"].map(priority_order).fillna(3)
esc_df = esc_df.sort_values(["_sort","joining_date"]).drop(columns=["_sort"])

next7 = TODAY + timedelta(days=7)
action_df["_due_dt"] = pd.to_datetime(action_df["due_date"]).dt.date
next7_df = action_df[(action_df["_due_dt"] >= TODAY) & (action_df["_due_dt"] <= next7)]

# ─────────────────────────────────────────────────────────────────────────────
# KPI TILES
# ─────────────────────────────────────────────────────────────────────────────
st.title("🏢 Anveshan Industries — HR Onboarding Dashboard")
st.caption(f"Batch: {joinees_df['joining_date'].min()} → {joinees_df['joining_date'].max()} · Generated: {TODAY}")
st.divider()

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("👥 Joinees", len(joinees_df))
col2.metric("✅ Tasks Generated", len(action_df))
col3.metric("🚨 Escalation Flags", (action_df["escalation_required"] == "Yes").sum(),
            delta="need action", delta_color="inverse")
col4.metric("👤 Missing Owners", (action_df["owner_name"] == "MISSING OWNER").sum(),
            delta_color="inverse")
col5.metric("📅 Due in 7 Days", len(next7_df))
col6.metric("⚠️ Joinees Flagged",
            joinees_df["employee_id"].isin(esc_df["employee_id"].unique()).sum(),
            delta_color="inverse")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚨 Escalations",
    "📋 Action Plan",
    "👥 Joinee Summary",
    "👤 Owner Digest",
    "📅 Due in 7 Days",
])

# ── TAB 1: Escalations ────────────────────────────────────────────────────
with tab1:
    st.subheader(f"🚨 Urgent Escalations — {len(esc_df)} flagged tasks")

    def color_priority(val):
        colors = {"Critical": "background-color:#fee2e2;color:#991b1b;font-weight:bold",
                  "High":     "background-color:#ffedd5;color:#9a3412;font-weight:bold",
                  "Medium":   "background-color:#fef9c3;color:#854d0e"}
        return colors.get(val, "")

    def color_status(val):
        colors = {"OVERDUE": "background-color:#fecaca;color:#991b1b;font-weight:bold",
                  "AT RISK": "background-color:#fed7aa;color:#9a3412",
                  "FLAGGED": "background-color:#e9d5ff;color:#6b21a8"}
        return colors.get(val, "")

    show_cols = ["escalation_priority","joinee_name","employee_id","joining_date",
                 "task_id","task_name","owner_name","owner_email",
                 "escalation_reason","task_status_initial"]
    styled = (
        esc_df[show_cols]
        .style
        def style_priority_table(df):     """     Safely style priority column for Streamlit across different pandas versions.     Works even if the priority column has been renamed.     """     if df is None or df.empty:         return df      possible_priority_cols = [         "escalation_priority",         "Priority",         "priority",         "Escalation Priority",         "ESCALATION_PRIORITY",     ]      priority_col = None     for col in possible_priority_cols:         if col in df.columns:             priority_col = col             break      if priority_col is None:         return df      styler = df.style      # pandas newer versions prefer Styler.map; older versions use applymap     if hasattr(styler, "map"):         return styler.map(color_priority, subset=[priority_col])     else:         return styler.applymap(color_priority, subset=[priority_col])
        .applymap(color_status,   subset=["task_status_initial"])
    )
    st.dataframe(styled, use_container_width=True, height=500)
    st.download_button("⬇️ Download Escalation List CSV",
                       to_csv_bytes(esc_df[show_cols]),
                       "03_escalation_list.csv", "text/csv")

# ── TAB 2: Full Action Plan ───────────────────────────────────────────────
with tab2:
    st.subheader(f"📋 Complete Onboarding Action Plan — {len(action_df)} task rows")

    fc1, fc2, fc3 = st.columns(3)
    filter_joinee = fc1.multiselect("Filter by Joinee", options=sorted(action_df["joinee_name"].unique()))
    filter_status = fc2.multiselect("Filter by Status", options=sorted(action_df["task_status_initial"].unique()))
    filter_sens   = fc3.multiselect("Filter by Sensitivity", options=sorted(action_df["sensitivity"].unique()))

    filtered = action_df.copy()
    if filter_joinee: filtered = filtered[filtered["joinee_name"].isin(filter_joinee)]
    if filter_status: filtered = filtered[filtered["task_status_initial"].isin(filter_status)]
    if filter_sens:   filtered = filtered[filtered["sensitivity"].isin(filter_sens)]

    st.caption(f"Showing {len(filtered)} of {len(action_df)} rows")

    def color_esc(val):
        return "background-color:#fee2e2;font-weight:bold" if val == "Yes" else ""

    display_cols = ["employee_id","joinee_name","task_id","task_name","rule_matched",
                    "owner_name","owner_email","due_date","sensitivity",
                    "task_status_initial","escalation_required","escalation_priority"]
    styled2 = (
        filtered[display_cols]
        .style
        .applymap(color_esc, subset=["escalation_required"])
        .applymap(color_status, subset=["task_status_initial"])
    )
    st.dataframe(styled2, use_container_width=True, height=500)
    st.download_button("⬇️ Download Full Action Plan CSV",
                       to_csv_bytes(action_df),
                       "01_onboarding_action_plan.csv", "text/csv")

# ── TAB 3: Joinee Summary ─────────────────────────────────────────────────
with tab3:
    st.subheader("👥 Joinee-Level Summary")

    summary_rows = []
    for _, j in joinees_df.iterrows():
        eid = j["employee_id"]
        subset = action_df[action_df["employee_id"] == eid]
        lead = j["lead_time_days"]
        joining = j["joining_date_dt"]
        esc_req = "Yes" if (subset["escalation_required"] == "Yes").any() else "No"
        if joining <= TODAY:
            nba = "🔴 IMMEDIATE: Joinee on-site — complete all tasks retroactively + HR Manager sign-off"
        elif lead < POLICY["urgent_lead_days"]:
            nba = f"🟠 URGENT: {lead} days lead time — escalate to HR Manager now"
        elif (subset["owner_name"] == "MISSING OWNER").sum() > 0:
            nba = f"🟡 Resolve {(subset['owner_name']=='MISSING OWNER').sum()} missing owner(s)"
        elif (subset["task_status_initial"].isin(["OVERDUE","AT RISK"])).sum() > 0:
            nba = f"🟠 {(subset['task_status_initial'].isin(['OVERDUE','AT RISK'])).sum()} tasks overdue/at-risk — expedite"
        elif j["reference_flag"]:
            nba = "🟡 Reference on notice — HR Manager re-validation required"
        else:
            nba = "🟢 On track — monitor completion"

        summary_rows.append({
            "Employee ID": eid,
            "Name": j["name"],
            "Department": j["department"],
            "Location": j["location"],
            "Employment Type": j["employment_type"],
            "Joining Date": str(joining),
            "Total Tasks": len(subset),
            "Confidential Tasks": subset["sensitivity"].isin(["Confidential","Highly Confidential"]).sum(),
            "At Risk / Overdue": subset["task_status_initial"].isin(["OVERDUE","AT RISK","FLAGGED"]).sum(),
            "Escalation": esc_req,
            "Next Action for HR": nba,
        })

    summary_df_display = pd.DataFrame(summary_rows)

    def color_esc_cell(val):
        return "background-color:#fee2e2;font-weight:bold" if val == "Yes" else "background-color:#dcfce7"

    styled3 = summary_df_display.style.applymap(color_esc_cell, subset=["Escalation"])
    st.dataframe(styled3, use_container_width=True, height=400)
    st.download_button("⬇️ Download Joinee Summary CSV",
                       to_csv_bytes(summary_df_display),
                       "02_joinee_summary.csv", "text/csv")

# ── TAB 4: Owner Digest ───────────────────────────────────────────────────
with tab4:
    st.subheader("👤 Owner-Wise Task Digest")

    digest_rows = []
    for (owner_name, owner_email), grp in action_df.groupby(["owner_name","owner_email"]):
        if owner_name == "MISSING OWNER":
            continue
        urgent = grp["escalation_priority"].isin(["Critical","High"]).sum()
        due_today = (grp["due_date"] == str(TODAY)).sum()
        joinees_list = ", ".join(
            f"{r['joinee_name']} ({r['employee_id']})"
            for _, r in grp[["joinee_name","employee_id"]].drop_duplicates().iterrows()
        )
        task_ids = ", ".join(sorted(grp["task_id"].unique()))
        digest_rows.append({
            "Owner Name": owner_name,
            "Owner Email": owner_email,
            "Total Tasks": len(grp),
            "Urgent Tasks": int(urgent),
            "Due Today": int(due_today),
            "Joinees Covered": joinees_list,
            "Task IDs": task_ids,
        })

    owner_df_display = pd.DataFrame(digest_rows).sort_values("Urgent Tasks", ascending=False)

    def color_urgent(val):
        if val > 5:  return "background-color:#fee2e2;font-weight:bold"
        if val > 0:  return "background-color:#ffedd5"
        return ""

    styled4 = owner_df_display.style.applymap(color_urgent, subset=["Urgent Tasks"])
    st.dataframe(styled4, use_container_width=True, height=450)
    st.download_button("⬇️ Download Owner Digest CSV",
                       to_csv_bytes(owner_df_display),
                       "04_owner_daily_digest.csv", "text/csv")

# ── TAB 5: Due in 7 Days ──────────────────────────────────────────────────
with tab5:
    st.subheader(f"📅 Tasks Due Between {TODAY} and {next7}")
    if len(next7_df) == 0:
        st.info("No tasks due in the next 7 days.")
    else:
        show_cols5 = ["due_date","joinee_name","employee_id","task_id","task_name",
                      "owner_name","owner_email","sensitivity","task_status_initial"]
        styled5 = (
            next7_df[show_cols5].sort_values("due_date")
            .style.applymap(color_status, subset=["task_status_initial"])
        )
        st.dataframe(styled5, use_container_width=True, height=450)
        st.download_button("⬇️ Download 7-Day Tasks CSV",
                           to_csv_bytes(next7_df[show_cols5].sort_values("due_date")),
                           "next_7_days_tasks.csv", "text/csv")

# ─────────────────────────────────────────────────────────────────────────────
# CHARTS ROW
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.subheader("📊 Summary Charts")

ch1, ch2, ch3 = st.columns(3)

with ch1:
    st.caption("Tasks by Sensitivity")
    sens_data = action_df["sensitivity"].value_counts().reset_index()
    sens_data.columns = ["Sensitivity", "Count"]
    st.bar_chart(sens_data.set_index("Sensitivity"), color="#7c3aed")

with ch2:
    st.caption("Tasks by Status")
    status_data = action_df["task_status_initial"].value_counts().reset_index()
    status_data.columns = ["Status", "Count"]
    st.bar_chart(status_data.set_index("Status"), color="#0ea5e9")

with ch3:
    st.caption("Top 8 Owners by Task Load")
    owner_chart = action_df[action_df["owner_name"] != "MISSING OWNER"] \
        .groupby("owner_name").size().nlargest(8).reset_index()
    owner_chart.columns = ["Owner", "Tasks"]
    st.bar_chart(owner_chart.set_index("Owner"), color="#16a34a")

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"Anveshan Industries Onboarding Automation Engine v1.0 · "
    f"Generated {TODAY} · "
    "Replace new_joinees.csv via the sidebar to process a new batch."
)
