import hashlib
import tempfile
import html
import json
from pathlib import Path

import streamlit as st
import pandas as pd

from src.pipeline import process_invoice
from src.database.repository import get_dashboard_data

from src.database.db import initialize_database, migrate_database
from src.database.repository import load_reference_data

@st.cache_resource
def setup_app_database():
    initialize_database()
    migrate_database()
    load_reference_data()

setup_app_database()


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="InvoiceIQ",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# CUSTOM STYLING
# --------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background-color: #F4F6FA;
    }

    [data-testid="stSidebar"] {
        background-color: #101D32;
    }

    [data-testid="stSidebar"] * {
        color: #E8EDF5;
    }

    /* Keep sidebar navigation readable against the navy background. */
    [data-testid="stSidebar"] [data-testid="stRadio"] label,
    [data-testid="stSidebar"] [data-testid="stRadio"] label p,
    [data-testid="stSidebar"] [data-testid="stRadio"] label span,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {
        color: #E8EDF5 !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        font-weight: 600 !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover,
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover p {
        color: #FFFFFF !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] [aria-checked="true"] + div,
    [data-testid="stSidebar"] [data-testid="stRadio"] [aria-checked="true"] {
        color: #FFFFFF !important;
    }

    .brand {
        font-size: 25px;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 4px;
    }

    .brand-subtitle {
        color: #AAB7C9;
        font-size: 12px;
        margin-bottom: 30px;
    }

    .main-title {
        color: #101D32;
        font-size: 30px;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .subtitle {
        color: #718096;
        font-size: 14px;
        margin-bottom: 25px;
    }

    .section-heading {
        color: #101D32;
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 12px;
    }

    .info-card {
        background: #FFFFFF;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #E7EAF0;
        min-height: 170px;
        box-sizing: border-box;
    }

    .info-card h4 {
        color: #101D32;
        margin: 0 0 8px 0;
    }

    .st-key-upload_card,
    .st-key-steps_card {
        background: #FFFFFF;
        border: 1px solid #E7EAF0;
        border-radius: 12px;
        padding: 24px;
        min-height: 480px;
        box-sizing: border-box;
    }

    .step {
        margin-bottom: 26px;
    }

    .step:last-child {
        margin-bottom: 0;
    }

    .step-title {
        color: #101D32;
        font-weight: 600;
    }

    .step-text {
        color: #718096;
        font-size: 13px;
        margin-top: 6px;
    }

    /* File uploader */

    [data-testid="stFileUploader"] label,
    [data-testid="stFileUploader"] label p {
        color: #101D32 !important;
        font-weight: 500;
    }

    [data-testid="stFileUploaderDropzone"] {
        background-color: #F8FAFC !important;
        border: 1.5px dashed #CBD5E0 !important;
        border-radius: 10px;
    }

    [data-testid="stFileUploaderDropzone"] *,
    [data-testid="stFileUploaderDropzoneInstructions"] * {
        color: #4A5568 !important;
    }

    [data-testid="stFileUploaderDropzone"] button {
        background-color: #FFFFFF !important;
        color: #101D32 !important;
        border: 1px solid #CBD5E0 !important;
    }

    [data-testid="stFileUploaderDropzone"] button * {
        color: #101D32 !important;
    }

    [data-testid="stFileUploaderFile"] * {
        color: #101D32 !important;
    }

    /* Buttons */

    div.stButton > button {
        background-color: #18A999;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 10px 20px;
    }

    div.stButton > button:hover {
        background-color: #128879;
        color: white;
        border: none;
    }

    /* Dashboard metrics */

    [data-testid="stMetric"] {
        background: white;
        padding: 14px;
        border-radius: 10px;
        border: 1px solid #E7EAF0;
    }

    [data-testid="stMetricLabel"],
    [data-testid="stMetricLabel"] * {
        color: #718096 !important;
    }

    [data-testid="stMetricValue"],
    [data-testid="stMetricValue"] * {
        color: #101D32 !important;
    }

    /* Dashboard: aligned activity + status cards */

    .st-key-activity_card,
    .st-key-status_card {
        background: #FFFFFF;
        border: 1px solid #E1E7EF;
        border-radius: 12px;
        padding: 22px 24px;
        height: 500px;
        box-sizing: border-box;
        overflow-y: auto;
    }

    .dash-card-heading {
        color: #101D32 !important;
        font-size: 20px;
        font-weight: 700;
        line-height: 1.3;
        margin: 0 0 18px 0;
    }

    .dist-item {
        margin-bottom: 26px;
    }

    .dist-label {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 8px;
        margin-bottom: 9px;
        font-size: 14px;
    }

    .dist-label strong {
        color: #101D32 !important;
        font-weight: 600;
    }

    .dist-label span {
        color: #526176 !important;
        font-size: 13px;
    }

    .dist-track {
        width: 100%;
        height: 8px;
        background: #E2E8F0;
        border-radius: 999px;
        overflow: hidden;
    }

    .dist-fill {
        height: 100%;
        border-radius: 999px;
    }

    /* Processing results */

    .results-heading {
        color: #101D32 !important;
        font-size: 26px !important;
        font-weight: 700 !important;
        margin: 8px 0 16px 0;
    }

    .results-section-heading {
        color: #101D32 !important;
        font-size: 18px !important;
        font-weight: 650 !important;
        margin: 16px 0 12px 0;
    }

    .stApp h1,
    .stApp h2,
    .stApp h3,
    .stApp h4,
    .stApp [data-testid="stMarkdownContainer"] p,
    .stApp [data-testid="stMarkdownContainer"] li {
        color: #243247;
    }

    .stApp h1,
    .stApp h2,
    .stApp h3,
    .stApp h4 {
        color: #101D32 !important;
    }

    /* Tabs */

    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
        border-bottom: 1px solid #DCE3EC;
    }

    .stTabs [data-baseweb="tab"] {
        color: #526176 !important;
        font-size: 14px;
        font-weight: 600;
        padding: 11px 4px;
    }

    .stTabs [aria-selected="true"] {
        color: #128879 !important;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #18A999 !important;
    }

    /* Invoice summary cards */

    .invoice-summary-card {
        background: #FFFFFF;
        border: 1px solid #E1E7EF;
        border-radius: 12px;
        padding: 15px 16px;
        min-height: 108px;
        height: 100%;
        box-sizing: border-box;
    }

    .invoice-summary-label {
        color: #718096 !important;
        font-size: 11px;
        font-weight: 700;
        margin-bottom: 9px;
        text-transform: uppercase;
        letter-spacing: .35px;
    }

    .invoice-summary-value {
        color: #101D32 !important;
        font-size: 18px;
        font-weight: 700;
        line-height: 1.4;
        overflow-wrap: anywhere;
        word-break: break-word;
    }

    .invoice-summary-value.vendor-value {
        font-size: 16px;
    }

    /* Decision banner */

    .decision-banner {
        padding: 14px 18px;
        border-radius: 10px;
        margin: 8px 0 18px 0;
        font-size: 14px;
        font-weight: 600;
        border: 1px solid transparent;
    }

    .decision-approved {
        color: #176B45 !important;
        background: #E8F6EE;
        border-color: #BCE5CC;
    }

    .decision-rejected {
        color: #A52F39 !important;
        background: #FCEBED;
        border-color: #F2C7CC;
    }

    .decision-review {
        color: #946200 !important;
        background: #FFF6DF;
        border-color: #F0DCA5;
    }

    .decision-neutral {
        color: #315A8A !important;
        background: #EAF2FC;
        border-color: #CADCF2;
    }

    /* Tables */

    .iq-table-wrap {
        width: 100%;
        overflow-x: auto;
        border: 1px solid #DCE3EC;
        border-radius: 10px;
        background: #FFFFFF;
        margin: 10px 0 16px 0;
    }

    .iq-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 13px;
        color: #263449 !important;
        border: none;
    }

    .iq-table th {
        background: #EDF2F7;
        color: #34445B !important;
        font-weight: 700;
        text-align: left;
        padding: 11px 13px;
        border-bottom: 1px solid #DCE3EC;
        white-space: nowrap;
    }

    .iq-table td {
        color: #34445B !important;
        padding: 11px 13px;
        border-bottom: 1px solid #E9EDF2;
        vertical-align: top;
        line-height: 1.5;
        overflow-wrap: anywhere;
        word-break: break-word;
        white-space: pre-wrap;
    }

    .iq-table tr:last-child td {
        border-bottom: none;
    }

    .iq-table tr:hover td {
        background: #F8FAFC;
    }

    .iq-table th:first-child {
        border-top-left-radius: 9px;
    }

    .iq-table th:last-child {
        border-top-right-radius: 9px;
    }

    .iq-table tr:last-child td:first-child {
        border-bottom-left-radius: 9px;
    }

    .iq-table tr:last-child td:last-child {
        border-bottom-right-radius: 9px;
    }

    .iq-table th,
    .iq-table td {
        border-right: 1px solid #E1E7EF;
    }

    .iq-table th:last-child,
    .iq-table td:last-child {
        border-right: none;
    }
    /* Validation badges */

    .iq-status {
        display: inline-block;
        border-radius: 20px;
        padding: 4px 9px;
        font-size: 11px;
        font-weight: 700;
        white-space: nowrap;
    }

    .iq-status-pass {
        color: #176B45 !important;
        background: #E8F6EE;
    }

    .iq-status-fail {
        color: #A52F39 !important;
        background: #FCEBED;
    }

    .iq-status-review {
        color: #946200 !important;
        background: #FFF3D3;
    }

    .iq-status-neutral {
        color: #526176 !important;
        background: #EDF1F5;
    }

    /* Amount and explanation cards */

    .amount-card,
    .explanation-card,
    .processing-meta {
        background: #FFFFFF;
        border: 1px solid #E1E7EF;
        border-radius: 10px;
        padding: 14px 16px;
    }

    .amount-label {
        color: #718096 !important;
        font-size: 12px;
        font-weight: 600;
    }

    .amount-value {
        color: #101D32 !important;
        font-size: 20px;
        font-weight: 700;
        margin-top: 7px;
        overflow-wrap: anywhere;
    }

    .explanation-card {
        color: #34445B !important;
        font-size: 14px;
        line-height: 1.65;
        overflow-wrap: anywhere;
    }

    .processing-meta {
        color: #34445B !important;
        font-size: 13px;
        line-height: 1.8;
        overflow-wrap: anywhere;
    }

    .processing-meta strong {
        color: #101D32 !important;
    }
    
    /* Improve Streamlit success and status message readability */

    [data-testid="stAlert"] p,
    [data-testid="stAlert"] div,
    [data-testid="stAlert"] span {
        color: #176B45 !important;
        font-weight: 600 !important;
    }

    [data-testid="stAlert"][data-kind="success"] {
        background-color: #E8F6EE !important;
        border: 1px solid #BCE5CC !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def render_html(html):
    """
    Render HTML safely in Streamlit.

    Removing indentation and blank lines prevents
    nested HTML from being interpreted as code blocks.
    """

    cleaned = " ".join(
        line.strip() for line in html.splitlines() if line.strip()
    )

    st.markdown(cleaned, unsafe_allow_html=True)


def to_dict(value):
    """Convert Pydantic models and dictionaries into dictionaries."""

    if isinstance(value, dict):
        return value

    if hasattr(value, "model_dump"):
        return value.model_dump()

    if hasattr(value, "dict"):
        return value.dict()

    return {}


def get_first(data, possible_keys, default="—"):
    """Return the first available non-empty field."""

    if not isinstance(data, dict):
        return default

    for key in possible_keys:
        value = data.get(key)

        if value is not None and value != "":
            return value

    return default


def format_currency(value):
    """Format numeric values as INR."""

    try:
        return f"₹{float(value):,.2f}"

    except (ValueError, TypeError):
        return str(value)


def display_status(status):
    """Display a decision using a suitable status indicator."""

    status = str(status).upper()

    if status == "APPROVED":
        st.success("APPROVED")

    elif status == "REJECTED":
        st.error("REJECTED")

    elif status == "PENDING_REVIEW":
        st.warning("PENDING REVIEW")

    else:
        st.info(status)


def get_vendor_name(invoice_data):
    """Read vendor name from flat or nested extraction structures."""

    vendor = invoice_data.get("vendor")

    if isinstance(vendor, dict):
        return get_first(
            vendor,
            ["vendor_name", "name", "supplier_name"],
        )

    if isinstance(vendor, str):
        return vendor

    return get_first(
        invoice_data,
        ["vendor_name", "supplier_name"],
    )


def parse_structured_value(value):
    """Parse JSON strings when a field contains serialized data."""

    if isinstance(value, str):
        stripped = value.strip()

        if stripped.startswith(("{", "[")):
            try:
                return json.loads(stripped)

            except json.JSONDecodeError:
                return value

    return value


def format_display_value(value):
    """Return a readable representation instead of raw JSON."""

    value = parse_structured_value(value)

    if value is None or value == "":
        return "—"

    if isinstance(value, dict):
        return "; ".join(
            f"{key.replace('_', ' ').title()}: "
            f"{format_display_value(item)}"
            for key, item in value.items()
            if item is not None
        ) or "—"

    if isinstance(value, list):
        return "; ".join(
            format_display_value(item) for item in value
        ) or "—"

    return str(value)


def render_results_table(headers, rows):
    """Render a compact, light-themed HTML table."""

    header_html = "".join(
        f"<th>{html.escape(str(header))}</th>"
        for header in headers
    )

    body_html = ""

    for row in rows:

        cells = "".join(
            f"<td>{html.escape(str(value))}</td>"
            for value in row
        )

        body_html += f"<tr>{cells}</tr>"

    render_html(
        f"<div class='iq-table-wrap'><table class='iq-table'>"
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{body_html}</tbody></table></div>"
    )


def get_status_class(status):
    """Map validation statuses to visual status classes."""

    status = str(status).upper()

    if status in ["PASS", "APPROVED", "SUCCESS"]:
        return "iq-status-pass"

    if status in ["FAIL", "REJECTED", "ERROR"]:
        return "iq-status-fail"

    if status in ["REVIEW", "PENDING_REVIEW"]:
        return "iq-status-review"

    return "iq-status-neutral"


def render_extracted_fields(invoice_data):
    """
    Render nested vendor, line-item and evidence data
    as separate, readable tables.
    """

    # ----------------------------------------------
    # VENDOR DETAILS
    # ----------------------------------------------

    vendor = parse_structured_value(
        invoice_data.get("vendor")
    )

    if isinstance(vendor, dict):

        st.markdown("**Vendor Details**")

        vendor_rows = [
            [
                key.replace("_", " ").title(),
                format_display_value(value),
            ]
            for key, value in vendor.items()
            if value is not None
        ]

        if vendor_rows:

            render_results_table(
                ["Field", "Extracted Value"],
                vendor_rows,
            )

    # ----------------------------------------------
    # LINE ITEMS
    # ----------------------------------------------

    items = parse_structured_value(
        invoice_data.get("items")
    )

    if isinstance(items, list) and items:

        st.markdown("**Line Items**")

        item_rows = []

        for item in items:

            item = to_dict(item)

            item_rows.append(
                [
                    get_first(
                        item,
                        ["item_code", "product_code"],
                    ),
                    get_first(
                        item,
                        ["description", "item_description"],
                    ),
                    get_first(
                        item,
                        ["quantity", "qty"],
                    ),
                    format_display_value(
                        get_first(
                            item,
                            ["unit_price", "price"],
                        )
                    ),
                    format_display_value(
                        get_first(
                            item,
                            ["line_amount", "amount", "total"],
                        )
                    ),
                ]
            )

        render_results_table(
            [
                "Item Code",
                "Description",
                "Quantity",
                "Unit Price",
                "Line Amount",
            ],
            item_rows,
        )

    # ----------------------------------------------
    # EXTRACTION EVIDENCE
    # ----------------------------------------------

    evidence = parse_structured_value(
        invoice_data.get("evidence")
    )

    if isinstance(evidence, dict):

        with st.expander(
            f"View Extraction Evidence ({len(evidence)} fields)",
            expanded=False,
        ):

            evidence_rows = []

            for key, value in evidence.items():

                # Some extraction outputs wrap the actual
                # evidence in another nested object.

                if isinstance(value, dict):

                    for nested_key, nested_value in value.items():

                        evidence_rows.append(
                            [
                                nested_key.replace("_", " ").title(),
                                format_display_value(nested_value),
                            ]
                        )

                else:

                    evidence_rows.append(
                        [
                            key.replace("_", " ").title(),
                            format_display_value(value),
                        ]
                    )

            if evidence_rows:

                render_results_table(
                    ["Evidence Field", "Value"],
                    evidence_rows,
                )

    # ----------------------------------------------
    # REMAINING INVOICE FIELDS
    # ----------------------------------------------

    excluded = {
        "vendor",
        "items",
        "evidence",
    }

    ordinary_rows = [
        [
            key.replace("_", " ").title(),
            format_display_value(value),
        ]
        for key, value in invoice_data.items()
        if key not in excluded and value is not None
    ]

    if ordinary_rows:

        st.markdown("**Invoice Header and Totals**")

        render_results_table(
            ["Field", "Extracted Value"],
            ordinary_rows,
        )


def render_decision_explanation(explanation, decision_data):
    """
    Render the decision explanation as a human-readable
    summary, reasons and validation summary.
    """

    explanation = parse_structured_value(explanation)

    if not isinstance(explanation, dict):
        explanation = {}

    summary = (
        explanation.get("summary")
        or explanation.get("message")
    )

    status = (
        explanation.get("status")
        or decision_data.get("status")
        or ""
    )

    reasons = (
        explanation.get("reasons")
        or decision_data.get("review_reasons")
        or []
    )

    checks = explanation.get("checks") or {}

    # ----------------------------------------------
    # SUMMARY
    # ----------------------------------------------

    if summary:

        render_html(
            f"<div class='explanation-card'>"
            f"<strong>Summary</strong><br>"
            f"{html.escape(str(summary))}"
            f"</div>"
        )

    if status:

        st.caption(
            f"Decision status: {str(status).replace('_', ' ')}"
        )

    # ----------------------------------------------
    # REASONS
    # ----------------------------------------------

    if reasons:

        if not isinstance(reasons, list):
            reasons = [reasons]

        clean_reasons = [
            str(reason)
            for reason in reasons
            if reason
        ]

        if clean_reasons:

            st.markdown("**Reasons**")

            for reason in clean_reasons:

                st.markdown(f"- {reason}")

    # ----------------------------------------------
    # VALIDATION SUMMARY
    # ----------------------------------------------

    if isinstance(checks, dict) and checks:

        st.markdown("**Validation Summary**")

        check_rows = []

        for name, detail in checks.items():

            detail = to_dict(detail)

            check_status = detail.get(
                "status",
                "—",
            )

            message = detail.get(
                "message",
                "—",
            )

            check_rows.append(
                [
                    name.replace("_", " ").title(),
                    str(check_status).replace("_", " "),
                    message,
                ]
            )

        render_results_table(
            ["Check", "Status", "Details"],
            check_rows,
        )

    # ----------------------------------------------
    # FALLBACK
    # ----------------------------------------------

    if not summary and not reasons and not checks:

        fallback = (
            explanation
            if explanation
            else decision_data.get("summary")
        )

        if fallback:

            render_html(
                f"<div class='explanation-card'>"
                f"{html.escape(str(fallback))}"
                f"</div>"
            )

        else:

            st.info("No decision explanation available.")


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:

    render_html(
        '<div class="brand">InvoiceIQ</div>'
    )

    render_html(
        '<div class="brand-subtitle">'
        'Intelligent Invoice Processing'
        '</div>'
    )

    page = st.radio(
        "NAVIGATION",
        ["Dashboard", "Process Invoice"],
        label_visibility="collapsed",
    )

    st.divider()

    st.caption("LOCAL PROCESSING")
    st.caption("Powered by Python · Ollama · SQLite")


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

if page == "Dashboard":

    render_html(
        '<div class="main-title">Dashboard</div>'
    )

    render_html(
        '<div class="subtitle">'
        'A live overview of invoice processing and exceptions.'
        '</div>'
    )

    # Retrieve live statistics from the existing SQLite query.
    dashboard_data = get_dashboard_data()

    total = int(dashboard_data.get("total_invoices", 0) or 0)
    approved = int(dashboard_data.get("approved", 0) or 0)
    pending = int(dashboard_data.get("pending_review", 0) or 0)
    rejected = int(dashboard_data.get("rejected", 0) or 0)

    approval_rate = (approved / total * 100) if total else 0.0
    exception_count = pending + rejected
    exception_rate = (exception_count / total * 100) if total else 0.0

    # ----------------------------------------------
    # KPI CARDS
    # ----------------------------------------------

    metric_cols = st.columns(4, gap="small")

    metrics = [
        ("Total Invoices", total),
        ("Approved", approved),
        ("Pending Review", pending),
        ("Rejected", rejected),
    ]

    for column, (label, value) in zip(metric_cols, metrics):
        with column:
            st.metric(label, f"{value:,}")

    # ----------------------------------------------
    # PERFORMANCE INDICATORS
    # ----------------------------------------------

    st.markdown("### Processing Performance")

    rate_cols = st.columns(2, gap="medium")

    with rate_cols[0]:
        st.metric("Approval Rate", f"{approval_rate:.1f}%")
        st.progress(approval_rate / 100 if total else 0.0)

    with rate_cols[1]:
        st.metric("Exception Rate", f"{exception_rate:.1f}%")
        st.progress(exception_rate / 100 if total else 0.0)

    st.divider()

    # ----------------------------------------------
    # RECENT ACTIVITY + STATUS DISTRIBUTION
    # ----------------------------------------------

    activity_col, status_col = st.columns(
        [2.4, 1],
        gap="medium",
    )

    # Both cards share the same fixed height, padding, border and
    # heading style (see .st-key-activity_card / .st-key-status_card),
    # so their tops, headings and bottoms line up exactly.

    with activity_col:

        with st.container(key="activity_card"):

            render_html(
                '<div class="dash-card-heading">'
                'Recent Invoice Activity</div>'
            )

            recent_invoices = (
                dashboard_data.get("recent_invoices", []) or []
            )[:8]

            if recent_invoices:

                activity_rows = ""

                for invoice in recent_invoices:

                    invoice = to_dict(invoice)

                    amount = invoice.get("total_amount")
                    invoice_currency = invoice.get("currency") or "INR"

                    try:
                        amount_text = (
                            f"{invoice_currency} {float(amount):,.2f}"
                        )
                    except (ValueError, TypeError):
                        amount_text = "—"

                    status_text = str(
                        invoice.get("status") or "—"
                    ).upper()

                    status_label = status_text.replace("_", " ")

                    activity_rows += (
                        "<tr>"
                        f"<td>{html.escape(str(invoice.get('invoice_number') or '—'))}</td>"
                        f"<td>{html.escape(str(invoice.get('vendor_name') or '—'))}</td>"
                        f"<td>{html.escape(amount_text)}</td>"
                        f"<td><span class='iq-status "
                        f"{get_status_class(status_text)}'>"
                        f"{html.escape(status_label)}</span></td>"
                        f"<td>{html.escape(str(invoice.get('created_at') or '—'))}</td>"
                        "</tr>"
                    )

                render_html(
                    "<div class='iq-table-wrap' style='margin:0;'>"
                    "<table class='iq-table'>"
                    "<thead><tr>"
                    "<th>Invoice Number</th>"
                    "<th>Vendor</th>"
                    "<th>Amount</th>"
                    "<th>Status</th>"
                    "<th>Processed At</th>"
                    "</tr></thead>"
                    f"<tbody>{activity_rows}</tbody>"
                    "</table></div>"
                )

            else:

                st.info(
                    "No invoice records found. "
                    "Process an invoice to get started."
                )

    with status_col:

        with st.container(key="status_card"):

            render_html(
                '<div class="dash-card-heading">'
                'Status Distribution</div>'
            )

            if total:

                status_items = [
                    ("Approved", approved, "#18A999"),
                    ("Pending Review", pending, "#F0A92E"),
                    ("Rejected", rejected, "#D64550"),
                ]

                for label, count, color in status_items:

                    percentage = count / total * 100

                    render_html(
                        f"<div class='dist-item'>"
                        f"<div class='dist-label'>"
                        f"<strong>{html.escape(label)}</strong>"
                        f"<span>{count:,} ({percentage:.1f}%)</span>"
                        f"</div>"
                        f"<div class='dist-track'>"
                        f"<div class='dist-fill' "
                        f"style='width:{percentage:.1f}%;"
                        f"background:{color};'></div>"
                        f"</div></div>"
                    )

            else:

                st.caption(
                    "Status distribution will appear after "
                    "invoices are processed."
                )

    st.divider()

    # ----------------------------------------------
    # SYSTEM INFORMATION
    # ----------------------------------------------

    info_col, action_col = st.columns(
        [1.5, 1],
        gap="medium",
    )

    with info_col:

        render_html(
            """
            <div class="info-card" style="min-height:130px;">
                <h4>Local invoice processing</h4>
                <p style="color:#718096;font-size:13px;margin:0;line-height:1.7;">
                    PDF text extraction · OCR · Local LLM extraction<br>
                    Vendor and PO verification · Financial validation
                </p>
            </div>
            """
        )

    with action_col:

        render_html(
            """
            <div class="info-card" style="min-height:130px;">
                <h4>Need to process an invoice?</h4>
                <p style="color:#718096;font-size:13px;margin:0;line-height:1.7;">
                    Open Process Invoice from the sidebar to upload
                    and validate a PDF.
                </p>
            </div>
            """
        )

# --------------------------------------------------
# PROCESS INVOICE
# --------------------------------------------------

elif page == "Process Invoice":

    render_html(
        '<div class="main-title">Process Invoice</div>'
    )

    render_html(
        '<div class="subtitle">'
        'Upload a PDF invoice for automated extraction and validation.'
        '</div>'
    )

    left, right = st.columns([1.5, 1])

    # ----------------------------------------------
    # LEFT COLUMN: UPLOAD
    # ----------------------------------------------

    with left:

        render_html(
            '<div class="section-heading">Upload Document</div>'
        )

        with st.container(key="upload_card"):

            uploaded_file = st.file_uploader(
                "Choose an invoice PDF",
                type=["pdf"],
                help="Upload a digital, scanned, or mixed PDF invoice.",
            )

            if uploaded_file:

                st.caption(
                    f"Selected file: {uploaded_file.name}"
                )

                if st.button(
                    "Process Invoice",
                    use_container_width=True,
                ):

                    file_bytes = uploaded_file.getvalue()

                    try:

                        with st.spinner(
                            "Extracting invoice data and running validations..."
                        ):

                            with tempfile.TemporaryDirectory() as temp_dir:

                                pdf_path = (
                                    Path(temp_dir) / uploaded_file.name
                                )

                                pdf_path.write_bytes(file_bytes)

                                result = process_invoice(pdf_path)

                        st.session_state["last_result"] = result

                        st.success(
                            "Invoice processing completed."
                        )

                    except Exception as error:

                        st.error("Invoice processing failed.")
                        st.exception(error)

    # ----------------------------------------------
    # RIGHT COLUMN: PROCESSING STEPS
    # ----------------------------------------------

    with right:

        render_html(
            '<div class="section-heading">What happens next?</div>'
        )

        with st.container(key="steps_card"):

            render_html(
                """
                <div class="step">
                    <div class="step-title">01 · Document extraction</div>
                    <div class="step-text">
                        Extract text from digital or scanned invoices.
                    </div>
                </div>

                <div class="step">
                    <div class="step-title">02 · Information extraction</div>
                    <div class="step-text">
                        Identify vendor, invoice number, line items and totals.
                    </div>
                </div>

                <div class="step">
                    <div class="step-title">03 · Validation</div>
                    <div class="step-text">
                        Check vendors, purchase orders, duplicates and financial values.
                    </div>
                </div>

                <div class="step">
                    <div class="step-title">04 · Final decision</div>
                    <div class="step-text">
                        Approve, reject or send the invoice for human review.
                    </div>
                </div>
                """
            )

    # ----------------------------------------------
    # DISPLAY PROCESSING RESULTS
    # ----------------------------------------------

    result = st.session_state.get("last_result")

    if result:

        st.divider()

        decision_data = to_dict(
            result.get("decision")
        )

        invoice_data = to_dict(
            result.get("invoice_data")
        )

        decision_status = str(
            get_first(
                decision_data,
                [
                    "status",
                    "decision",
                    "final_decision",
                ],
                "PROCESSED",
            )
        ).upper()

        # ------------------------------------------
        # EXTRACT SUMMARY INFORMATION
        # ------------------------------------------

        invoice_number = get_first(
            invoice_data,
            ["invoice_number"],
        )

        vendor_name = get_vendor_name(
            invoice_data
        )

        po_number = get_first(
            invoice_data,
            [
                "po_number",
                "purchase_order_number",
                "po_reference",
            ],
        )

        total_amount = get_first(
            invoice_data,
            [
                "total_amount",
                "invoice_total",
                "grand_total",
            ],
            None,
        )

        currency = get_first(
            invoice_data,
            ["currency"],
            "INR",
        )

        # ------------------------------------------
        # DECISION BANNER
        # ------------------------------------------

        st.markdown(
            '<div class="results-heading">Processing Result</div>',
            unsafe_allow_html=True,
        )

        if decision_status == "APPROVED":

            banner_class = "decision-approved"

            banner_text = (
                "APPROVED — All required validation checks passed."
            )

        elif decision_status == "REJECTED":

            banner_class = "decision-rejected"

            banner_text = (
                "REJECTED — One or more critical validation checks failed."
            )

        elif decision_status == "PENDING_REVIEW":

            banner_class = "decision-review"

            banner_text = (
                "PENDING REVIEW — This invoice requires human investigation."
            )

        else:

            banner_class = "decision-neutral"

            banner_text = (
                f"PROCESSING STATUS — {decision_status}"
            )

        render_html(
            f"<div class='decision-banner {banner_class}'>"
            f"{html.escape(banner_text)}</div>"
        )

        # ------------------------------------------
        # INVOICE SUMMARY CARDS
        # ------------------------------------------

        st.markdown(
            '<div class="results-section-heading">Invoice Summary</div>',
            unsafe_allow_html=True,
        )

        def summary_amount(value):

            if value is None:
                return "—"

            try:
                return f"{currency} {float(value):,.2f}"

            except (ValueError, TypeError):
                return f"{currency} {value}"

        summary_cards = [
            ("Invoice Number", invoice_number, ""),
            ("Vendor", vendor_name, "vendor-value"),
            ("PO Reference", po_number, ""),
            (
                "Invoice Total",
                summary_amount(total_amount),
                "",
            ),
        ]

        summary_columns = st.columns(4, gap="small")

        for column, (label, value, extra_class) in zip(
            summary_columns,
            summary_cards,
        ):

            with column:

                render_html(
                    f"<div class='invoice-summary-card'>"
                    f"<div class='invoice-summary-label'>"
                    f"{html.escape(label)}</div>"
                    f"<div class='invoice-summary-value {extra_class}'>"
                    f"{html.escape(str(value))}</div></div>"
                )

        st.markdown("")

        # ------------------------------------------
        # RESULT TABS
        # ------------------------------------------

        tab1, tab2, tab3, tab4 = st.tabs(
            [
                "Overview",
                "Extracted Fields",
                "Validation Details",
                "Decision Explanation",
            ]
        )

        # ------------------------------------------
        # TAB 1: OVERVIEW
        # ------------------------------------------

        with tab1:

            st.markdown(
                '<div class="results-section-heading">'
                'Processing Information</div>',
                unsafe_allow_html=True,
            )

            document = to_dict(
                result.get("document")
            )

            metadata_rows = [
                [
                    "File Name",
                    result.get("file_name", "—"),
                    "Invoice ID",
                    result.get("invoice_id") or "—",
                ],
                [
                    "Document Type",
                    document.get("document_type", "—"),
                    "Final Decision",
                    decision_status,
                ],
            ]

            render_results_table(
                [
                    "Information",
                    "Value",
                    "Information",
                    "Value",
                ],
                metadata_rows,
            )

            # Amount breakdown

            st.markdown(
                '<div class="results-section-heading">'
                'Invoice Amount Breakdown</div>',
                unsafe_allow_html=True,
            )

            subtotal = get_first(
                invoice_data,
                ["subtotal", "sub_total"],
                None,
            )

            tax_amount = get_first(
                invoice_data,
                ["tax_amount", "total_tax"],
                None,
            )

            amount_columns = st.columns(3, gap="small")

            amount_values = [
                ("Subtotal", subtotal),
                ("Tax Amount", tax_amount),
                ("Total Amount", total_amount),
            ]

            for column, (label, value) in zip(
                amount_columns,
                amount_values,
            ):

                with column:

                    render_html(
                        f"<div class='amount-card'>"
                        f"<div class='amount-label'>"
                        f"{html.escape(label)}</div>"
                        f"<div class='amount-value'>"
                        f"{html.escape(summary_amount(value))}</div>"
                        f"</div>"
                    )

        # ------------------------------------------
        # TAB 2: EXTRACTED FIELDS
        # ------------------------------------------

        with tab2:

            st.markdown(
                '<div class="results-section-heading">'
                'Extracted Invoice Information</div>',
                unsafe_allow_html=True,
            )

            if invoice_data:

                render_extracted_fields(invoice_data)

            else:

                st.info(
                    "No extracted invoice information available."
                )

        # ------------------------------------------
        # TAB 3: VALIDATION DETAILS
        # ------------------------------------------

        with tab3:

            st.markdown(
                '<div class="results-section-heading">'
                'Validation Results</div>',
                unsafe_allow_html=True,
            )

            validations = result.get(
                "validation_results",
                {},
            )

            if isinstance(validations, dict) and validations:

                header_html = (
                    "<th>Validation</th>"
                    "<th>Status</th>"
                    "<th>Details</th>"
                )

                body_html = ""

                passed = 0
                failed = 0

                for check_name, check_result in validations.items():

                    if isinstance(check_result, dict):

                        status = check_result.get(
                            "status",
                            "—",
                        )

                        message = check_result.get(
                            "message",
                            "No additional details available.",
                        )

                    else:

                        status = str(check_result)
                        message = "—"

                    status_text = str(status).upper()

                    status_class = get_status_class(
                        status_text
                    )

                    if status_text == "PASS":
                        passed += 1

                    elif status_text == "FAIL":
                        failed += 1

                    body_html += (
                        "<tr>"
                        f"<td>{html.escape(check_name.replace('_', ' ').title())}</td>"
                        f"<td><span class='iq-status {status_class}'>"
                        f"{html.escape(status_text)}</span></td>"
                        f"<td>{html.escape(str(message))}</td>"
                        "</tr>"
                    )

                render_html(
                    f"<div class='iq-table-wrap'>"
                    f"<table class='iq-table'>"
                    f"<thead><tr>{header_html}</tr></thead>"
                    f"<tbody>{body_html}</tbody>"
                    f"</table></div>"
                )

                st.caption(
                    f"{passed} passed · {failed} failed · "
                    f"{len(validations) - passed - failed} other checks"
                )

            else:

                st.info(
                    "No validation details available."
                )

        # ------------------------------------------
        # TAB 4: DECISION EXPLANATION
        # ------------------------------------------

        with tab4:

            st.markdown(
                '<div class="results-section-heading">'
                'Decision Explanation</div>',
                unsafe_allow_html=True,
            )

            explanation = result.get("explanation")

            render_decision_explanation(
                explanation,
                decision_data,
            )