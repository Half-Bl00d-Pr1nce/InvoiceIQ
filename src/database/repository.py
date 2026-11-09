
import csv
from collections import defaultdict
from decimal import Decimal
from src.database.db import get_connection
import json
from decimal import Decimal, ROUND_HALF_UP


def load_reference_data():
    """Load vendor and purchase order data safely from CSV files."""

    connection = get_connection()

    try:
        # ---------------------------------------
        # 1. Load vendor master
        # ---------------------------------------
        with open("data/vendors.csv", newline="", encoding="utf-8") as file:
            vendors = csv.DictReader(file)

            for vendor in vendors:
                connection.execute(
                    """
                    INSERT INTO vendors
                    (vendor_id, vendor_name, gstin, status, bank_ref)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(vendor_id) DO UPDATE SET
                        vendor_name = excluded.vendor_name,
                        gstin = excluded.gstin,
                        status = excluded.status,
                        bank_ref = excluded.bank_ref
                    """,
                    (
                        vendor["vendor_id"],
                        vendor["vendor_name"],
                        vendor["gstin"],
                        vendor["status"],
                        vendor["bank_ref"],
                    ),
                )

        # ---------------------------------------
        # 2. Load purchase orders and PO items
        # ---------------------------------------
        item_counters = defaultdict(int)
        expected_po_items = defaultdict(set)
        with open(
            "data/purchase_orders.csv",
            newline="",
            encoding="utf-8",
        ) as file:
            orders = csv.DictReader(file)

            for order in orders:
                po_id = order["po_id"]

                # Insert or update the PO header
                connection.execute(
                    """
                    INSERT INTO purchase_orders
                    (po_id, vendor_id, po_date, status, currency)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(po_id) DO UPDATE SET
                        vendor_id = excluded.vendor_id,
                        po_date = excluded.po_date,
                        status = excluded.status,
                        currency = excluded.currency
                    """,
                    (
                        po_id,
                        order["vendor_id"],
                        order["po_date"],
                        order["status"],
                        order["currency"],
                    ),
                )

                # Generate a distinct ID for each PO item row.
                # This supports repeated item codes within one PO.
                item_counters[po_id] += 1
                po_item_id = f"{po_id}-LINE-{item_counters[po_id]:04d}"
                expected_po_items[po_id].add(po_item_id)

                connection.execute(
                    """
                    INSERT INTO po_items
                    (
                        po_item_id, po_id, item_code, description,
                        quantity, unit_price_paise, tax_rate
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(po_item_id) DO UPDATE SET
                        item_code = excluded.item_code,
                        description = excluded.description,
                        quantity = excluded.quantity,
                        unit_price_paise = excluded.unit_price_paise,
                        tax_rate = excluded.tax_rate
                    """,
                    (
                        po_item_id,
                        po_id,
                        order["item_code"],
                        order["description"],
                        float(order["quantity"]),
                        int(order["unit_price_paise"]),
                        float(order["tax_rate"]) if order["tax_rate"] is not None else 0.0,
                    ),
                )
            for po_id, expected_ids in expected_po_items.items():
                placeholders = ",".join("?" for _ in expected_ids)

                connection.execute(
                    f"""
                    DELETE FROM po_items
                    WHERE po_id = ?
                    AND po_item_id NOT IN ({placeholders})
                    """,
                    (po_id, *expected_ids),
                )
        # Both reference files are loaded in one transaction.
        connection.commit()
        print("Vendor and PO reference data loaded successfully.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def get_reference_data():
    """Retrieve vendors, purchase orders and PO items for the dashboard."""

    connection = get_connection()

    try:
        vendors = connection.execute(
            """
            SELECT vendor_id, vendor_name, gstin, status, bank_ref
            FROM vendors
            ORDER BY vendor_id
            """
        ).fetchall()

        purchase_orders = connection.execute(
            """
            SELECT
                po.po_id,
                po.vendor_id,
                v.vendor_name,
                po.po_date,
                po.status,
                po.currency
            FROM purchase_orders po
            LEFT JOIN vendors v
                ON po.vendor_id = v.vendor_id
            ORDER BY po.po_id
            """
        ).fetchall()

        po_items = connection.execute(
            """
            SELECT
                po_item_id,
                po_id,
                item_code,
                description,
                quantity,
                unit_price_paise,
                tax_rate
            FROM po_items
            ORDER BY po_id, po_item_id
            """
        ).fetchall()

        return {
            "vendors": [dict(row) for row in vendors],
            "purchase_orders": [dict(row) for row in purchase_orders],
            "po_items": [dict(row) for row in po_items],
        }

    finally:
        connection.close()


def import_reference_data(vendor_rows, po_rows):
    """
    Insert or update uploaded vendor and PO reference records.

    Existing records and invoice history are preserved.
    """

    connection = get_connection()

    try:
        # 1. Insert or update vendors first.
        for vendor in vendor_rows:
            connection.execute(
                """
                INSERT INTO vendors
                (vendor_id, vendor_name, gstin, status, bank_ref)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(vendor_id) DO UPDATE SET
                    vendor_name = excluded.vendor_name,
                    gstin = excluded.gstin,
                    status = excluded.status,
                    bank_ref = excluded.bank_ref
                """,
                (
                    vendor["vendor_id"],
                    vendor["vendor_name"],
                    vendor["gstin"],
                    vendor["status"],
                    vendor["bank_ref"],
                ),
            )

        # 2. Insert or update purchase orders and their items.
        item_counters = {}

        for order in po_rows:
            po_id = order["po_id"]

            connection.execute(
                """
                INSERT INTO purchase_orders
                (po_id, vendor_id, po_date, status, currency)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(po_id) DO UPDATE SET
                    vendor_id = excluded.vendor_id,
                    po_date = excluded.po_date,
                    status = excluded.status,
                    currency = excluded.currency
                """,
                (
                    po_id,
                    order["vendor_id"],
                    order["po_date"],
                    order["status"],
                    order["currency"],
                ),
            )

            item_counters[po_id] = item_counters.get(po_id, 0) + 1

            po_item_id = (
                f"{po_id}-LINE-{item_counters[po_id]:04d}"
            )

            connection.execute(
                """
                INSERT INTO po_items
                (
                    po_item_id, po_id, item_code, description,
                    quantity, unit_price_paise, tax_rate
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(po_item_id) DO UPDATE SET
                    item_code = excluded.item_code,
                    description = excluded.description,
                    quantity = excluded.quantity,
                    unit_price_paise = excluded.unit_price_paise,
                    tax_rate = excluded.tax_rate
                """,
                (
                    po_item_id,
                    po_id,
                    order["item_code"],
                    order["description"],
                    float(order["quantity"]),
                    int(order["unit_price_paise"]),
                    float(order["tax_rate"]),
                ),
            )

        connection.commit()

        return {
            "vendors_imported": len(vendor_rows),
            "po_rows_imported": len(po_rows),
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def get_historical_po_billing(po_id, exclude_invoice_id=None):
    """
    Retrieve previously recorded invoice billing for a PO.

    APPROVED invoices contribute to confirmed billing.
    PENDING_REVIEW and PROCESSING invoices contribute to pending exposure.
    REJECTED invoices are excluded.
    """

    connection = get_connection()

    try:
        query = """
            SELECT
                i.invoice_id,
                i.status,
                ii.item_code,
                ii.quantity,
                ii.line_total_paise
            FROM invoices i
            JOIN invoice_items ii
                ON i.invoice_id = ii.invoice_id
            WHERE i.po_id = ?
              AND i.status IN (
                  'APPROVED',
                  'PENDING_REVIEW',
                  'PROCESSING'
              )
        """

        params = [po_id]

        if exclude_invoice_id is not None:
            query += " AND i.invoice_id != ?"
            params.append(exclude_invoice_id)

        rows = connection.execute(query, params).fetchall()

        billing = defaultdict(
            lambda: {
                "approved_quantity": Decimal("0"),
                "pending_quantity": Decimal("0"),
                "approved_amount_paise": Decimal("0"),
                "pending_amount_paise": Decimal("0"),
            }
        )

        for row in rows:
            if not row["item_code"]:
                continue

            item_code = row["item_code"].strip().upper()
            status = row["status"]

            quantity = Decimal(str(row["quantity"] or 0))
            amount = Decimal(str(row["line_total_paise"] or 0))

            if status == "APPROVED":
                billing[item_code]["approved_quantity"] += quantity
                billing[item_code]["approved_amount_paise"] += amount

            else:
                billing[item_code]["pending_quantity"] += quantity
                billing[item_code]["pending_amount_paise"] += amount

        return dict(billing)

    finally:
        connection.close()

def decimal_string(value):
    """Convert a monetary value to a precise decimal string."""

    if value is None:
        return None

    return str(Decimal(str(value)))


def amount_to_paise(value):
    """Convert an INR amount into integer paise."""

    if value is None:
        return None

    amount = Decimal(str(value)) * 100

    return int(
        amount.quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    )

def create_invoice_record(
    invoice,
    file_name,
    file_hash,
    vendor_id=None,
    po_id=None,
):
    """
    Create the main invoice record.
    Returns the generated invoice_id.
    """

    connection = get_connection()

    try:
        is_inr = (invoice.currency or "").upper() == "INR"

        cursor = connection.execute(
            """
            INSERT INTO invoices (
                vendor_id,
                extracted_vendor_name,
                invoice_number,
                invoice_date,
                po_id,
                subtotal_paise,
                tax_amount_paise,
                total_amount_paise,
                subtotal_amount,
                tax_amount,
                total_amount,
                shipping_amount,
                discount_amount,
                tax_treatment,
                currency,
                file_name,
                file_hash,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                vendor_id,
                invoice.vendor.vendor_name,
                invoice.invoice_number,
                invoice.invoice_date.isoformat()
                if invoice.invoice_date else None,
                po_id,

                amount_to_paise(invoice.subtotal) if is_inr else None,
                amount_to_paise(invoice.tax_amount) if is_inr else None,
                amount_to_paise(invoice.total_amount) if is_inr else None,

                decimal_string(invoice.subtotal),
                decimal_string(invoice.tax_amount),
                decimal_string(invoice.total_amount),
                decimal_string(invoice.shipping),
                decimal_string(invoice.discount),

                invoice.tax_treatment,
                invoice.currency,
                file_name,
                file_hash,
                "PROCESSING",
            ),
        )

        invoice_id = cursor.lastrowid

        connection.commit()

        return invoice_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def save_invoice_items(invoice_id, items, currency):
    """
    Save extracted invoice line items.

    Currency-independent decimal values are always preserved.
    Paise columns are populated only for INR invoices.
    """

    connection = get_connection()

    try:
        is_inr = (currency or "").upper() == "INR"

        for item in items:
            connection.execute(
                """
                INSERT INTO invoice_items (
                    invoice_id,
                    item_code,
                    description,
                    quantity,
                    unit_price_paise,
                    tax_rate,
                    line_total_paise,
                    unit_price_amount,
                    line_total_amount
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_id,
                    item.item_code,
                    item.description,
                    float(item.quantity),

                    amount_to_paise(item.unit_price) if is_inr else None,
                    float(item.tax_rate) if item.tax_rate is not None else None,
                    amount_to_paise(item.line_amount) if is_inr else None,

                    decimal_string(item.unit_price),
                    decimal_string(item.line_amount),
                ),
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def save_validation_results(invoice_id, validation_results):
    """Persist individual validation outcomes."""

    connection = get_connection()

    try:
        for check_name, result in validation_results.items():
            status = result.get("status", "NOT_CHECKED")

            explanation = result.get(
                "message",
                result.get("reason", "No explanation provided.")
            )

            connection.execute(
                """
                INSERT INTO validation_results (
                    invoice_id,
                    check_name,
                    status,
                    explanation
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    invoice_id,
                    check_name,
                    status,
                    str(explanation),
                ),
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def save_processing_log(invoice_id, stage, status, message):
    """Record a processing-stage event."""

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO processing_logs (
                invoice_id,
                stage,
                status,
                message
            )
            VALUES (?, ?, ?, ?)
            """,
            (invoice_id, stage, status, message),
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
        
def update_invoice_status(invoice_id, status):
    """Update the final processing status of an invoice."""

    allowed_statuses = {
        "PROCESSING",
        "APPROVED",
        "REJECTED",
        "PENDING_REVIEW",
    }

    if status not in allowed_statuses:
        raise ValueError(f"Invalid invoice status: {status}")

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE invoices
            SET status = ?
            WHERE invoice_id = ?
            """,
            (status, invoice_id),
        )

        if cursor.rowcount == 0:
            raise ValueError(f"Invoice ID {invoice_id} does not exist.")

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def get_dashboard_data():
    """Retrieve invoice statistics and recent invoice activity."""

    connection = get_connection()

    try:
        # 1. Overall invoice statistics
        stats_query = """
            SELECT
                COUNT(*) AS total_invoices,

                SUM(CASE
                    WHEN status = 'APPROVED' THEN 1
                    ELSE 0
                END) AS approved,

                SUM(CASE
                    WHEN status = 'PENDING_REVIEW' THEN 1
                    ELSE 0
                END) AS pending_review,

                SUM(CASE
                    WHEN status = 'REJECTED' THEN 1
                    ELSE 0
                END) AS rejected

            FROM invoices
        """

        stats = connection.execute(stats_query).fetchone()

        # 2. Recent invoice activity
        recent_query = """
            SELECT
                i.invoice_id,
                i.invoice_number,
                COALESCE(
                    v.vendor_name,
                    i.extracted_vendor_name,
                    'Unknown Vendor'
                ) AS vendor_name,
                i.total_amount,
                i.currency,
                i.status,
                i.created_at,
                i.file_name

            FROM invoices i

            LEFT JOIN vendors v
                ON i.vendor_id = v.vendor_id

            ORDER BY i.created_at DESC, i.invoice_id DESC

            LIMIT 8
        """

        recent_invoices = connection.execute(
            recent_query
        ).fetchall()

        return {
            "total_invoices": stats["total_invoices"] or 0,
            "approved": stats["approved"] or 0,
            "pending_review": stats["pending_review"] or 0,
            "rejected": stats["rejected"] or 0,
            "recent_invoices": [
                dict(row) for row in recent_invoices
            ],
        }

    finally:
        connection.close()


