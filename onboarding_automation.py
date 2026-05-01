"""
=============================================================================
Anveshan Industries — HR Onboarding Automation Engine
=============================================================================
Author  : Automation Architect
Version : 1.0
Date    : April 2026

Description:
    Reads 4 input files (new_joinees.csv, onboarding_tasks_master.csv,
    onboarding_policy.txt, department_contacts.csv), applies all onboarding
    rules deterministically, and produces 6 output files:

    Output 1: outputs/01_onboarding_action_plan.csv
    Output 2: outputs/02_joinee_summary.csv
    Output 3: outputs/03_escalation_list.csv
    Output 4: outputs/04_owner_daily_digest.csv
    Output 5: outputs/05_hr_dashboard.html
    Output 6: onboarding_automation.py  (this file = re-runnable workflow)

Usage:
    python onboarding_automation.py
    Replace new_joinees.csv with any file of the same schema and re-run.
=============================================================================
"""

import pandas as pd
import numpy as np
import os
import re
from datetime import datetime, date, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# File paths (relative to script location)
JOINEES_FILE   = "new_joinees (1).csv"
TASKS_FILE     = "onboarding_tasks_master.csv"
CONTACTS_FILE  = "department_contacts.csv"
POLICY_FILE    = "onboarding_policy.txt"
OUTPUT_DIR     = "outputs"

# Today's date — change this to date.today() in production
TODAY = date(2026, 4, 30)

# Policy-derived constants (sourced from onboarding_policy.txt)
POLICY = {
    # A joining is URGENT if lead time (joining_date - request_date) < 7 days
    "urgent_lead_days": 7,
    # A joining is CRITICAL if lead time < 3 days (already joining / joined)
    "critical_lead_days": 3,
    # Standard full onboarding window required
    "full_onboarding_days": 14,
    # Plant keywords — any location containing these words is plant-based
    "plant_keywords": ["plant", "factory", "works", "manufacturing site"],
    # Department aliases that map to canonical names
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
    # Reference employee on notice — any reference from this person triggers flag
    "flagged_references": ["sameer joshi"],
    # Minimum CTC threshold for senior hire flag
    "senior_ctc_threshold": 15.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# HELPER: TEXT NORMALISATION
# ─────────────────────────────────────────────────────────────────────────────

def normalize(text):
    """Lowercase, strip, collapse whitespace."""
    if pd.isna(text):
        return ""
    return re.sub(r'\s+', ' ', str(text).strip().lower())


def normalize_dept(dept_raw):
    """Normalize a department name to its canonical form."""
    n = normalize(dept_raw)
    return POLICY["dept_aliases"].get(n, n)


def normalize_designation(desig_raw):
    """Lowercase and strip designation for fuzzy matching."""
    return normalize(desig_raw)


def is_plant_location(location):
    """Return True if the location is a plant / manufacturing site."""
    loc = normalize(location)
    return any(kw in loc for kw in POLICY["plant_keywords"])


def parse_applies_to(applies_to_raw):
    """
    Parse the applies_to field from the task master and return a dict
    describing the rule type and its value(s).

    Supported rule types:
      ALL, PERMANENT, INTERN, PLANT, DEPT_LIST, DESIG_LIST, CTC_GT
    """
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

    # CTC condition: CTC>15 etc.
    ctc_match = re.match(r'ctc\s*>\s*(\d+(?:\.\d+)?)', n)
    if ctc_match:
        return {"type": "CTC_GT", "value": float(ctc_match.group(1))}

    # Otherwise it is a comma-separated list of department names OR designation names
    # We detect which kind it is by checking whether any token looks like a known dept
    items = [x.strip() for x in raw.split(",")]
    normalized_items = [normalize(x) for x in items]

    # Designation indicator words — if any item contains these, it's a designation list
    designation_words = [
        "manager", "engineer", "director", "executive", "officer",
        "head", "analyst", "supervisor", "intern", "associate",
        "senior", "junior", "lead", "specialist", "coordinator"
    ]

    # If any token contains a designation word → DESIG_LIST (takes priority)
    if any(
        any(dw in ni for dw in designation_words)
        for ni in normalized_items
    ):
        return {"type": "DESIG_LIST", "values": normalized_items, "raw_values": items}

    # Known department fragments (canonical + common aliases)
    dept_fragments = [
        "manufacturing", "quality", "r&d", "sales", "finance", "hr",
        "human resources", "r&d and innovation", "sales & marketing",
        "finance & accounts", "administration", "logistics", "supply chain"
    ]

    # If any token matches a dept fragment → DEPT_LIST
    if any(any(frag in ni for frag in dept_fragments) for ni in normalized_items):
        # Expand aliases in each item
        expanded = []
        for ni in normalized_items:
            expanded.append(POLICY["dept_aliases"].get(ni, ni))
        return {"type": "DEPT_LIST", "values": expanded, "raw_values": items}
    else:
        # Treat as designation list
        return {"type": "DESIG_LIST", "values": normalized_items, "raw_values": items}


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: RULE MATCHING
# ─────────────────────────────────────────────────────────────────────────────

def task_applies(joinee, rule):
    """
    Return (applies: bool, reason: str).
    joinee  — dict with normalized joinee fields
    rule    — dict returned by parse_applies_to()
    """
    rtype = rule["type"]

    if rtype == "ALL":
        return True, "Applies to ALL employees"

    if rtype == "PERMANENT":
        if joinee["employment_type_n"] == "permanent":
            return True, "Employment type = Permanent"
        return False, "Not Permanent"

    if rtype == "INTERN":
        if joinee["employment_type_n"] == "intern":
            return True, "Employment type = Intern"
        return False, "Not Intern"

    if rtype == "PLANT":
        if joinee["is_plant"]:
            return True, f"Plant-based location ({joinee['location']})"
        return False, "Not a plant location"

    if rtype == "CTC_GT":
        threshold = rule["value"]
        if joinee["ctc_lpa"] > threshold:
            return True, f"CTC {joinee['ctc_lpa']} LPA > {threshold} LPA (senior hire)"
        return False, f"CTC {joinee['ctc_lpa']} LPA ≤ {threshold} LPA"

    if rtype == "DEPT_LIST":
        jdept = joinee["department_n"]
        for val in rule["values"]:
            # Expand aliases for the rule value too
            val_expanded = POLICY["dept_aliases"].get(val, val)
            if jdept == val_expanded or val_expanded in jdept or jdept in val_expanded:
                return True, f"Department '{joinee['department']}' matches rule '{rule['raw_values']}'"
        return False, "Department not in rule list"

    if rtype == "DESIG_LIST":
        jdesig = joinee["designation_n"]
        for val in rule["values"]:
            # Substring match (e.g. "senior r&d engineer" in "senior r&d engineer - manesar")
            if val in jdesig or jdesig in val:
                return True, f"Designation '{joinee['designation']}' matches rule '{rule['raw_values']}'"
        return False, "Designation not in rule list"

    return False, "Unknown rule type"


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: OWNER MAPPING
# ─────────────────────────────────────────────────────────────────────────────

def build_contact_lookup(contacts_df):
    """
    Build a lookup dict: normalized_role → list of contact dicts.
    Plant HR / Plant Admin entries are stored with location key.
    """
    lookup = {}
    for _, row in contacts_df.iterrows():
        role_n = normalize(row["role"])
        entry = {
            "name": row["name"].strip(),
            "email": row["email"].strip(),
            "location": normalize(row.get("location", "")),
        }
        lookup.setdefault(role_n, []).append(entry)
    return lookup


def resolve_owner(owner_role_raw, joinee, contact_lookup):
    """
    Map owner_role + joinee location → (name, email, found: bool).
    Handles:
      - 'Reporting Manager' → joinee's reports_to / reports_to_email
      - 'Plant HR' / 'Plant Admin' → location-specific contact
      - Generic role → first match in lookup
    """
    role_n = normalize(owner_role_raw)

    # Special: Reporting Manager
    if role_n == "reporting manager":
        return joinee["reports_to"], joinee["reports_to_email"], True

    # Plant-specific roles
    if role_n in ("plant hr", "plant admin"):
        loc_n = normalize(joinee["location"])
        # Try location-qualified keys first: "plant hr - manesar"
        for key in contact_lookup:
            if role_n in key and any(
                loc_word in key for loc_word in loc_n.split()
                if len(loc_word) > 3
            ):
                contacts = contact_lookup[key]
                return contacts[0]["name"], contacts[0]["email"], True
        # Fallback: unqualified key
        if role_n in contact_lookup:
            return contact_lookup[role_n][0]["name"], contact_lookup[role_n][0]["email"], True
        return "MISSING OWNER", "N/A", False

    # Generic lookup
    if role_n in contact_lookup:
        contacts = contact_lookup[role_n]
        return contacts[0]["name"], contacts[0]["email"], True

    # Try partial match
    for key in contact_lookup:
        if role_n in key or key in role_n:
            return contact_lookup[key][0]["name"], contact_lookup[key][0]["email"], True

    return "MISSING OWNER", "N/A", False


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: ESCALATION & STATUS
# ─────────────────────────────────────────────────────────────────────────────

def compute_due_date(joining_date, days_before):
    """due_date = joining_date - days_before_joining"""
    return joining_date - timedelta(days=int(days_before))


def escalation_for_task(row, today):
    """
    Return (escalation_required: bool, reason: str, priority: str,
             status: str)
    """
    reasons = []
    priority = "Medium"

    due_date = row["due_date_dt"]
    joining_date = row["joining_date_dt"]
    lead_time = (joining_date - today).days

    # Already joined or joining today
    if joining_date <= today:
        reasons.append(f"Joinee already joined on {joining_date} — all tasks OVERDUE")
        priority = "Critical"

    # Due date already past
    elif due_date < today:
        reasons.append(f"Due date {due_date} already passed (today {today})")
        if priority != "Critical":
            priority = "High"

    # Urgent joining (< 7 days lead time)
    elif lead_time < POLICY["urgent_lead_days"]:
        reasons.append(
            f"Urgent joining: only {lead_time} days lead time "
            f"(policy minimum = {POLICY['urgent_lead_days']} days)"
        )
        if priority != "Critical":
            priority = "High"

    # Missing owner
    if row["owner_name"] == "MISSING OWNER":
        reasons.append("No owner mapped — manual assignment required")
        if priority == "Medium":
            priority = "High"

    # Highly confidential tasks
    if row["sensitivity"] == "Highly Confidential":
        reasons.append("Highly Confidential task — CFO/R&D Head sign-off required")

    # Reference flag
    if row.get("reference_flag"):
        reasons.append(
            "Reference employee (Sameer Joshi) is on notice — HR Manager re-validation required"
        )
        if priority == "Medium":
            priority = "High"

    if reasons:
        if joining_date <= today or due_date < today:
            status = "OVERDUE"
        elif lead_time < POLICY["urgent_lead_days"]:
            status = "AT RISK"
        elif row.get("reference_flag") and not row["owner_name"] == "MISSING OWNER":
            # Joinee-level flag (reference check) — task execution not blocked,
            # but HR must re-validate before proceeding with this joinee
            status = "FLAGGED"
        else:
            status = "AT RISK"
        return True, "; ".join(reasons), priority, status
    else:
        return False, "", "", "Pending"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def load_data():
    joinees  = pd.read_csv(JOINEES_FILE)
    tasks    = pd.read_csv(TASKS_FILE)
    contacts = pd.read_csv(CONTACTS_FILE)
    return joinees, tasks, contacts


def enrich_joinees(joinees_df):
    """Add normalized and derived columns to joinees dataframe."""
    df = joinees_df.copy()
    df["joining_date_dt"]    = pd.to_datetime(df["joining_date"]).dt.date
    df["request_date_dt"]    = pd.to_datetime(df["request_date"]).dt.date
    df["department_n"]       = df["department"].apply(normalize_dept)
    df["designation_n"]      = df["designation"].apply(normalize_designation)
    df["employment_type_n"]  = df["employment_type"].apply(normalize)
    df["location_n"]         = df["location"].apply(normalize)
    df["is_plant"]           = df["location"].apply(is_plant_location)
    df["ctc_lpa"]            = pd.to_numeric(df["ctc_lpa"], errors="coerce").fillna(0)
    df["lead_time_days"]     = df.apply(
        lambda r: (r["joining_date_dt"] - r["request_date_dt"]).days, axis=1
    )
    df["reference_flag"] = df["reference_employee"].apply(
        lambda x: normalize(x) in POLICY["flagged_references"]
        if not pd.isna(x) else False
    )
    return df


def build_action_plan(joinees_df, tasks_df, contact_lookup):
    """
    Core engine: for each joinee × task, evaluate whether the task applies.
    Returns a list of task-row dicts.
    """
    rows = []

    for _, joinee in joinees_df.iterrows():
        j = joinee.to_dict()
        joining_date = j["joining_date_dt"]

        for _, task in tasks_df.iterrows():
            applies_to_raw = str(task["applies_to"]).strip()

            # T014 has compound owner: "HR Manager + Legal" — generate 2 rows
            owner_roles_raw = [r.strip() for r in str(task["owner_role"]).split("+")]

            rule = parse_applies_to(applies_to_raw)
            applies, reason = task_applies(j, rule)

            if not applies:
                continue

            due_date = compute_due_date(joining_date, task["days_before_joining"])

            for owner_role_raw in owner_roles_raw:
                owner_name, owner_email, owner_found = resolve_owner(
                    owner_role_raw, j, contact_lookup
                )

                row = {
                    # Joinee identity
                    "employee_id":       j["employee_id"],
                    "joinee_name":       j["name"],
                    "designation":       j["designation"],
                    "department":        j["department"],
                    "location":          j["location"],
                    "employment_type":   j["employment_type"],
                    "joining_date":      str(joining_date),
                    # Task
                    "task_id":           task["task_id"],
                    "task_name":         task["task_name"],
                    "rule_matched":      reason,
                    "applies_to_rule":   applies_to_raw,
                    "owner_role":        owner_role_raw,
                    "owner_name":        owner_name,
                    "owner_email":       owner_email,
                    "days_before_joining": int(task["days_before_joining"]),
                    "due_date":          str(due_date),
                    "sensitivity":       task["sensitivity"],
                    # Internal date objects for computation
                    "due_date_dt":       due_date,
                    "joining_date_dt":   joining_date,
                    "reference_flag":    j["reference_flag"],
                    "lead_time_days":    j["lead_time_days"],
                }

                # Compute escalation
                esc, esc_reason, esc_priority, status = escalation_for_task(row, TODAY)
                row["task_status_initial"] = status
                row["escalation_required"] = "Yes" if esc else "No"
                row["escalation_reason"]   = esc_reason
                row["escalation_priority"] = esc_priority if esc else ""

                rows.append(row)

    return rows


def make_action_plan_df(rows):
    """Convert raw rows list to clean output dataframe (Output 1)."""
    keep_cols = [
        "employee_id", "joinee_name", "designation", "department",
        "location", "employment_type", "joining_date",
        "task_id", "task_name", "rule_matched",
        "owner_role", "owner_name", "owner_email",
        "due_date", "days_before_joining", "sensitivity",
        "task_status_initial", "escalation_required",
        "escalation_reason", "escalation_priority",
    ]
    df = pd.DataFrame(rows)[keep_cols]
    return df


def make_joinee_summary(rows_df, joinees_df):
    """Output 2: one row per joinee with aggregated metrics."""
    summary_rows = []
    for _, j in joinees_df.iterrows():
        eid = j["employee_id"]
        subset = rows_df[rows_df["employee_id"] == eid]

        total_tasks           = len(subset)
        high_sens             = (subset["sensitivity"] == "High Sensitivity").sum()
        confidential          = subset["sensitivity"].isin(
            ["Confidential", "Highly Confidential"]
        ).sum()
        missing_owner         = (subset["owner_name"] == "MISSING OWNER").sum()
        overdue_at_risk       = subset["task_status_initial"].isin(
            ["OVERDUE", "AT RISK", "FLAGGED"]
        ).sum()
        esc_required          = "Yes" if (subset["escalation_required"] == "Yes").any() else "No"
        esc_reasons           = "; ".join(
            subset[subset["escalation_required"] == "Yes"]["escalation_reason"]
            .unique().tolist()
        )

        # Next best action heuristic
        lead = j["lead_time_days"]
        if j["joining_date_dt"] <= TODAY:
            nba = "IMMEDIATE: Joinee already on-site — complete all pending tasks retroactively and get HR Manager sign-off."
        elif lead < POLICY["urgent_lead_days"]:
            nba = (
                f"URGENT: Only {lead} days lead time. Escalate to HR Manager immediately. "
                "Prioritise: offer letter, ID card, system access."
            )
        elif missing_owner > 0:
            nba = f"Resolve {missing_owner} missing owner(s) before tasks can be actioned."
        elif overdue_at_risk > 0:
            nba = f"{overdue_at_risk} tasks overdue/at-risk — review and expedite with respective owners."
        elif j["reference_flag"]:
            nba = "Sameer Joshi reference detected — escalate to HR Manager for re-validation before proceeding."
        else:
            # Nearest due task
            upcoming = subset[subset["task_status_initial"] == "Pending"].copy()
            if not upcoming.empty:
                upcoming["due_date_dt"] = pd.to_datetime(upcoming["due_date"]).dt.date
                nearest = upcoming.sort_values("due_date_dt").iloc[0]
                nba = (
                    f"Next action: '{nearest['task_name']}' "
                    f"(due {nearest['due_date']}, owner: {nearest['owner_name']})"
                )
            else:
                nba = "All tasks scheduled — monitor for completion."

        summary_rows.append({
            "employee_id":              eid,
            "joinee_name":              j["name"],
            "department":               j["department"],
            "location":                 j["location"],
            "employment_type":          j["employment_type"],
            "joining_date":             str(j["joining_date_dt"]),
            "total_tasks":              total_tasks,
            "high_sensitivity_tasks":   int(high_sens),
            "confidential_tasks":       int(confidential),
            "missing_owner_count":      int(missing_owner),
            "overdue_or_at_risk_count": int(overdue_at_risk),
            "escalation_required":      esc_required,
            "escalation_reason":        esc_reasons,
            "next_best_action_for_HR":  nba,
        })

    return pd.DataFrame(summary_rows)


def make_escalation_list(rows_df):
    """Output 3: only escalation rows."""
    esc = rows_df[rows_df["escalation_required"] == "Yes"].copy()

    # Sort by priority
    priority_order = {"Critical": 0, "High": 1, "Medium": 2}
    esc["priority_sort"] = esc["escalation_priority"].map(priority_order).fillna(3)
    esc = esc.sort_values(["priority_sort", "joining_date"])

    # Recommended action per priority
    def recommended_action(row):
        if row["escalation_priority"] == "Critical":
            return (
                "IMMEDIATE: Contact HR Manager and reporting manager now. "
                "Execute all pending tasks same-day. Document all deviations."
            )
        elif row["escalation_priority"] == "High":
            return (
                "Within 24h: Coordinate with task owner to expedite. "
                "HR Manager must approve any compressed timelines."
            )
        else:
            return "Monitor and ensure task is completed before due date."

    esc["recommended_action"] = esc.apply(recommended_action, axis=1)

    keep = [
        "joinee_name", "employee_id", "joining_date",
        "task_id", "task_name",
        "owner_name", "owner_email",
        "escalation_reason", "recommended_action", "escalation_priority",
    ]
    return esc[keep].reset_index(drop=True)


def make_owner_digest(rows_df):
    """Output 4: owner-wise daily digest."""
    digest_rows = []
    today_str = str(TODAY)
    next_7 = str(TODAY + timedelta(days=7))

    grouped = rows_df.groupby(["owner_name", "owner_email"])
    for (owner_name, owner_email), grp in grouped:
        if owner_name == "MISSING OWNER":
            continue

        # Tasks due today
        due_today = grp[grp["due_date"] == today_str]
        # Urgent tasks
        urgent = grp[grp["escalation_priority"].isin(["Critical", "High"])]
        # Due before joining (all rows have due_date ≤ joining_date by definition)
        due_before_joining = grp[grp["due_date"] <= grp["joining_date"]]

        # Build task list
        task_list = []
        for _, tr in grp.iterrows():
            task_list.append(
                f"[{tr['task_id']}] {tr['task_name']} | "
                f"{tr['joinee_name']} ({tr['employee_id']}) | "
                f"Due: {tr['due_date']} | Status: {tr['task_status_initial']}"
            )

        # Joinees this owner is responsible for
        joinees_list = grp[["joinee_name","employee_id"]].drop_duplicates()
        joinee_str = ", ".join(
            f"{r['joinee_name']} ({r['employee_id']})"
            for _, r in joinees_list.iterrows()
        )

        digest_rows.append({
            "owner_name":           owner_name,
            "owner_email":          owner_email,
            "total_tasks_assigned": len(grp),
            "urgent_tasks":         len(urgent),
            "tasks_due_today":      len(due_today),
            "tasks_due_before_joining": len(due_before_joining),
            "joinees_covered":      joinee_str,
            "task_list":            " || ".join(task_list),
        })

    return pd.DataFrame(digest_rows).sort_values("urgent_tasks", ascending=False)


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT 5: HTML DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

def make_html_dashboard(action_df, summary_df, escalation_df, owner_df):
    """Generate a self-contained HTML dashboard."""

    today_str = str(TODAY)
    next7_dt  = TODAY + timedelta(days=7)
    next7_str = str(next7_dt)

    total_joinees  = len(summary_df)
    total_tasks    = len(action_df)
    esc_count      = (action_df["escalation_required"] == "Yes").sum()
    missing_owners = (action_df["owner_name"] == "MISSING OWNER").sum()
    hr_attention   = (summary_df["escalation_required"] == "Yes").shape[0]

    # Tasks due in next 7 days
    action_df["due_date_dt_temp"] = pd.to_datetime(action_df["due_date"]).dt.date
    next7_tasks = action_df[
        (action_df["due_date_dt_temp"] >= TODAY) &
        (action_df["due_date_dt_temp"] <= next7_dt)
    ]

    # Sensitivity breakdown
    sens_counts = action_df["sensitivity"].value_counts().to_dict()

    # Owner task counts (top 10)
    owner_counts = action_df.groupby("owner_name").size().sort_values(ascending=False).head(10)

    def badge(text, color):
        return f'<span class="badge" style="background:{color}">{text}</span>'

    def priority_badge(p):
        colors = {"Critical": "#dc2626", "High": "#ea580c", "Medium": "#ca8a04", "": "#6b7280"}
        return badge(p or "—", colors.get(p, "#6b7280"))

    def sens_badge(s):
        colors = {
            "Standard": "#3b82f6",
            "Confidential": "#7c3aed",
            "Highly Confidential": "#dc2626",
        }
        return badge(s, colors.get(s, "#6b7280"))

    def status_badge(s):
        colors = {
            "OVERDUE": "#dc2626",
            "AT RISK": "#ea580c",
            "Pending": "#16a34a",
        }
        return badge(s, colors.get(s, "#6b7280"))

    # ── Next-7-days table rows ─────────────────────────────────────
    n7_rows = ""
    for _, r in next7_tasks.sort_values("due_date").head(30).iterrows():
        n7_rows += f"""
        <tr>
          <td>{r['due_date']}</td>
          <td>{r['joinee_name']}</td>
          <td>{r['task_id']}: {r['task_name']}</td>
          <td>{r['owner_name']}</td>
          <td>{sens_badge(r['sensitivity'])}</td>
          <td>{status_badge(r['task_status_initial'])}</td>
        </tr>"""

    # ── Escalation table rows ──────────────────────────────────────
    esc_rows = ""
    for _, r in escalation_df.head(20).iterrows():
        esc_rows += f"""
        <tr>
          <td>{priority_badge(r['escalation_priority'])}</td>
          <td>{r['joinee_name']} ({r['employee_id']})</td>
          <td>{r['joining_date']}</td>
          <td>{r['task_name']}</td>
          <td>{r['owner_name']}</td>
          <td>{r['escalation_reason']}</td>
          <td>{r['recommended_action']}</td>
        </tr>"""

    # ── Joinee summary table rows ─────────────────────────────────
    js_rows = ""
    for _, r in summary_df.iterrows():
        esc_class = 'style="background:#fff1f0"' if r["escalation_required"] == "Yes" else ""
        js_rows += f"""
        <tr {esc_class}>
          <td>{r['employee_id']}</td>
          <td><b>{r['joinee_name']}</b></td>
          <td>{r['department']}</td>
          <td>{r['location']}</td>
          <td>{r['joining_date']}</td>
          <td>{r['total_tasks']}</td>
          <td>{r['confidential_tasks']}</td>
          <td>{r['overdue_or_at_risk_count']}</td>
          <td>{badge('Yes','#dc2626') if r['escalation_required']=='Yes' else badge('No','#16a34a')}</td>
          <td style="font-size:12px">{r['next_best_action_for_HR']}</td>
        </tr>"""

    # ── Owner digest rows ─────────────────────────────────────────
    od_rows = ""
    for _, r in owner_df.iterrows():
        od_rows += f"""
        <tr>
          <td><b>{r['owner_name']}</b></td>
          <td>{r['owner_email']}</td>
          <td style="text-align:center">{r['total_tasks_assigned']}</td>
          <td style="text-align:center">{badge(str(r['urgent_tasks']),'#dc2626') if r['urgent_tasks']>0 else '0'}</td>
          <td style="text-align:center">{r['tasks_due_today']}</td>
          <td style="font-size:11px">{r['joinees_covered']}</td>
        </tr>"""

    # ── Sensitivity bar chart (pure CSS) ─────────────────────────
    sens_bars = ""
    total_tasks_nonzero = max(total_tasks, 1)
    sens_color = {
        "Standard": "#3b82f6",
        "Confidential": "#7c3aed",
        "Highly Confidential": "#dc2626",
    }
    for sname, scount in sorted(sens_counts.items(), key=lambda x: -x[1]):
        pct = round(scount / total_tasks_nonzero * 100)
        color = sens_color.get(sname, "#6b7280")
        sens_bars += f"""
        <div class="bar-row">
          <span class="bar-label">{sname}</span>
          <div class="bar-track">
            <div class="bar-fill" style="width:{pct}%;background:{color}"></div>
          </div>
          <span class="bar-val">{scount} ({pct}%)</span>
        </div>"""

    # ── Owner bar chart ───────────────────────────────────────────
    owner_bars = ""
    max_oc = owner_counts.max() if len(owner_counts) > 0 else 1
    for oname, ocount in owner_counts.items():
        pct = round(ocount / max_oc * 100)
        owner_bars += f"""
        <div class="bar-row">
          <span class="bar-label">{oname}</span>
          <div class="bar-track">
            <div class="bar-fill" style="width:{pct}%;background:#0ea5e9"></div>
          </div>
          <span class="bar-val">{ocount}</span>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Anveshan Industries — HR Onboarding Dashboard</title>
<style>
  :root {{
    --brand: #1e3a5f;
    --accent: #0ea5e9;
    --danger: #dc2626;
    --warn:   #ea580c;
    --ok:     #16a34a;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f0f4f8; color: #1a202c; }}
  header {{
    background: var(--brand); color: #fff;
    padding: 18px 32px; display: flex; justify-content: space-between; align-items: center;
  }}
  header h1 {{ font-size: 22px; font-weight: 700; }}
  header p  {{ font-size: 13px; opacity: .8; }}
  .kpi-grid {{
    display: grid; grid-template-columns: repeat(auto-fit,minmax(160px,1fr));
    gap: 16px; padding: 24px 32px;
  }}
  .kpi {{
    background:#fff; border-radius:10px; padding:20px;
    box-shadow:0 1px 3px rgba(0,0,0,.1); text-align:center;
  }}
  .kpi .val {{ font-size:36px; font-weight:800; color:var(--brand); }}
  .kpi .lbl {{ font-size:13px; color:#64748b; margin-top:4px; }}
  .kpi.danger .val {{ color:var(--danger); }}
  .kpi.warn   .val {{ color:var(--warn); }}
  .section {{
    margin: 0 32px 24px; background:#fff; border-radius:10px;
    box-shadow:0 1px 3px rgba(0,0,0,.1); overflow:hidden;
  }}
  .section h2 {{
    background:var(--brand); color:#fff; padding:14px 20px;
    font-size:16px; font-weight:600;
  }}
  .section-body {{ padding:20px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ background:#f1f5f9; text-align:left; padding:8px 10px; color:#475569; font-weight:600; }}
  td {{ padding:8px 10px; border-bottom:1px solid #f1f5f9; vertical-align:top; }}
  tr:hover td {{ background:#f8fafc; }}
  .badge {{
    display:inline-block; padding:2px 9px; border-radius:12px;
    font-size:11px; font-weight:700; color:#fff; white-space:nowrap;
  }}
  .bar-row {{ display:flex; align-items:center; margin:8px 0; gap:10px; }}
  .bar-label {{ width:200px; font-size:13px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .bar-track {{ flex:1; background:#e2e8f0; border-radius:4px; height:18px; }}
  .bar-fill  {{ height:18px; border-radius:4px; transition:width .3s; }}
  .bar-val   {{ width:80px; font-size:12px; color:#64748b; text-align:right; }}
  .charts-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:24px; padding:20px; }}
  .chart-box {{ background:#f8fafc; border-radius:8px; padding:16px; }}
  .chart-box h3 {{ font-size:14px; color:var(--brand); margin-bottom:12px; font-weight:600; }}
  .gen-note {{ text-align:center; font-size:12px; color:#94a3b8; padding:16px 32px 24px; }}
  @media(max-width:768px) {{
    .kpi-grid {{ padding:16px; }}
    .section  {{ margin:0 16px 16px; }}
    .charts-grid {{ grid-template-columns:1fr; }}
    .bar-label {{ width:120px; }}
  }}
</style>
</head>
<body>

<header>
  <div>
    <h1>🏢 Anveshan Industries — HR Onboarding Dashboard</h1>
    <p>Auto-generated | As of {today_str} | Batch: April 2026 Joinee Cohort</p>
  </div>
  <div style="text-align:right;font-size:12px;opacity:.8;">
    Source: new_joinees.csv<br>
    Powered by Onboarding Automation Engine v1.0
  </div>
</header>

<!-- KPI Row -->
<div class="kpi-grid">
  <div class="kpi">
    <div class="val">{total_joinees}</div>
    <div class="lbl">Total Joinees</div>
  </div>
  <div class="kpi">
    <div class="val">{total_tasks}</div>
    <div class="lbl">Tasks Generated</div>
  </div>
  <div class="kpi danger">
    <div class="val">{esc_count}</div>
    <div class="lbl">Escalation Flags</div>
  </div>
  <div class="kpi warn">
    <div class="val">{missing_owners}</div>
    <div class="lbl">Missing Owners</div>
  </div>
  <div class="kpi warn">
    <div class="val">{len(next7_tasks)}</div>
    <div class="lbl">Tasks Due in 7 Days</div>
  </div>
  <div class="kpi danger">
    <div class="val">{hr_attention}</div>
    <div class="lbl">Joinees Needing HR Attention</div>
  </div>
</div>

<!-- Charts -->
<div class="section">
  <h2>📊 Task Breakdown</h2>
  <div class="charts-grid">
    <div class="chart-box">
      <h3>Tasks by Sensitivity</h3>
      {sens_bars}
    </div>
    <div class="chart-box">
      <h3>Tasks by Owner (Top 10)</h3>
      {owner_bars}
    </div>
  </div>
</div>

<!-- Joinee Summary -->
<div class="section">
  <h2>👥 Joinee Summary (All {total_joinees} Joinees)</h2>
  <div class="section-body">
    <table>
      <tr>
        <th>Emp ID</th><th>Name</th><th>Department</th><th>Location</th>
        <th>Joining Date</th><th>Tasks</th><th>Confidential</th>
        <th>At Risk</th><th>Escalation</th><th>Next Action for HR</th>
      </tr>
      {js_rows}
    </table>
  </div>
</div>

<!-- Escalation List -->
<div class="section">
  <h2>🚨 Urgent Escalations</h2>
  <div class="section-body">
    <table>
      <tr>
        <th>Priority</th><th>Joinee</th><th>Joining Date</th>
        <th>Task</th><th>Owner</th><th>Reason</th><th>Recommended Action</th>
      </tr>
      {esc_rows}
    </table>
  </div>
</div>

<!-- Next 7 Days -->
<div class="section">
  <h2>📅 Tasks Due in Next 7 Days ({today_str} → {next7_str})</h2>
  <div class="section-body">
    <table>
      <tr>
        <th>Due Date</th><th>Joinee</th><th>Task</th>
        <th>Owner</th><th>Sensitivity</th><th>Status</th>
      </tr>
      {n7_rows if n7_rows else '<tr><td colspan="6" style="text-align:center;color:#94a3b8">No tasks due in the next 7 days</td></tr>'}
    </table>
  </div>
</div>

<!-- Owner Digest -->
<div class="section">
  <h2>📋 Owner-Wise Digest</h2>
  <div class="section-body">
    <table>
      <tr>
        <th>Owner</th><th>Email</th><th>Total Tasks</th>
        <th>Urgent</th><th>Due Today</th><th>Joinees Covered</th>
      </tr>
      {od_rows}
    </table>
  </div>
</div>

<p class="gen-note">
  Generated by Anveshan Industries Onboarding Automation Engine v1.0 |
  {today_str} |
  All rules sourced from onboarding_policy.txt v4.2 |
  Replace new_joinees.csv and re-run onboarding_automation.py to refresh.
</p>

</body>
</html>"""
    return html


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"[INFO] Today = {TODAY}")
    print("[INFO] Loading input files …")

    joinees_raw, tasks_df, contacts_df = load_data()

    print(f"[INFO] Joinees: {len(joinees_raw)}  |  Tasks: {len(tasks_df)}  |  Contacts: {len(contacts_df)}")

    # Enrich joinees
    joinees_df = enrich_joinees(joinees_raw)

    # Build contact lookup
    contact_lookup = build_contact_lookup(contacts_df)
    print(f"[INFO] Contact lookup keys: {list(contact_lookup.keys())}")

    # Build action plan
    print("[INFO] Applying task rules to each joinee …")
    rows = build_action_plan(joinees_df, tasks_df, contact_lookup)
    print(f"[INFO] Total task-rows generated: {len(rows)}")

    action_df = make_action_plan_df(rows)

    # ── OUTPUT 1 ──────────────────────────────────────────────────
    out1 = os.path.join(OUTPUT_DIR, "01_onboarding_action_plan.csv")
    action_df.to_csv(out1, index=False)
    print(f"[OUT 1] {out1}  ({len(action_df)} rows)")

    # ── OUTPUT 2 ──────────────────────────────────────────────────
    summary_df = make_joinee_summary(action_df, joinees_df)
    out2 = os.path.join(OUTPUT_DIR, "02_joinee_summary.csv")
    summary_df.to_csv(out2, index=False)
    print(f"[OUT 2] {out2}  ({len(summary_df)} rows)")

    # ── OUTPUT 3 ──────────────────────────────────────────────────
    escalation_df = make_escalation_list(action_df)
    out3 = os.path.join(OUTPUT_DIR, "03_escalation_list.csv")
    escalation_df.to_csv(out3, index=False)
    print(f"[OUT 3] {out3}  ({len(escalation_df)} rows)")

    # ── OUTPUT 4 ──────────────────────────────────────────────────
    owner_df = make_owner_digest(action_df)
    out4 = os.path.join(OUTPUT_DIR, "04_owner_daily_digest.csv")
    owner_df.to_csv(out4, index=False)
    print(f"[OUT 4] {out4}  ({len(owner_df)} rows)")

    # ── OUTPUT 5 ──────────────────────────────────────────────────
    html = make_html_dashboard(action_df, summary_df, escalation_df, owner_df)
    out5 = os.path.join(OUTPUT_DIR, "05_hr_dashboard.html")
    with open(out5, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OUT 5] {out5}")

    # ── SUMMARY PRINTOUT ──────────────────────────────────────────
    print("\n" + "="*60)
    print("ONBOARDING AUTOMATION COMPLETE")
    print("="*60)
    print(f"  Joinees processed   : {len(joinees_df)}")
    print(f"  Task rows generated : {len(action_df)}")
    print(f"  Escalation flags    : {(action_df['escalation_required']=='Yes').sum()}")
    print(f"  Missing owners      : {(action_df['owner_name']=='MISSING OWNER').sum()}")
    print(f"  Outputs in          : ./{OUTPUT_DIR}/")
    print("="*60)

    return action_df, summary_df, escalation_df, owner_df


if __name__ == "__main__":
    main()
