from src.database.db import get_connection


def detect_duplicate(
    file_hash=None,
    vendor_id=None,
    invoice_number=None,
    invoice_date=None,
    total_amount_paise=None,
    invoice_id=None,
):
    """
    Check whether an invoice has already been processed.

    Exact matches:
      1. Same PDF file hash
      2. Same vendor and invoice number

    Possible match:
      3. Same vendor, invoice date and total amount

    An exact match returns FAIL.
    A possible match returns REVIEW.
    """

    connection = get_connection()

    try:
        conditions = []
        parameters = []

        # Exclude the current invoice when rechecking an existing record.
        exclusion = ""
        if invoice_id is not None:
            exclusion = " AND invoice_id != ?"

        # Check 1: Exact PDF file match
        if file_hash:
            query = """
                SELECT invoice_id, invoice_number, file_name
                FROM invoices
                WHERE file_hash = ?
            """ + exclusion

            params = [file_hash]
            if invoice_id is not None:
                params.append(invoice_id)

            row = connection.execute(query, params).fetchone()

            if row:
                return {
                    "check": "duplicate_detection",
                    "status": "FAIL",
                    "reason": "An identical PDF file has already been processed.",
                    "matched_invoice_id": row["invoice_id"],
                    "match_type": "FILE_HASH",
                }

        # Check 2: Same vendor and invoice number
        if vendor_id and invoice_number:
            query = """
                SELECT invoice_id, invoice_number, file_name
                FROM invoices
                WHERE vendor_id = ?
                  AND LOWER(TRIM(invoice_number)) = LOWER(TRIM(?))
            """ + exclusion

            params = [vendor_id, invoice_number]
            if invoice_id is not None:
                params.append(invoice_id)

            row = connection.execute(query, params).fetchone()

            if row:
                return {
                    "check": "duplicate_detection",
                    "status": "FAIL",
                    "reason": (
                        "This vendor has previously submitted "
                        "an invoice with the same invoice number."
                    ),
                    "matched_invoice_id": row["invoice_id"],
                    "match_type": "VENDOR_INVOICE_NUMBER",
                }

        # Check 3: Same vendor, date and amount.
        # This is a possible duplicate, not definitive proof.
        if (
            vendor_id
            and invoice_date
            and total_amount_paise is not None
        ):
            query = """
                SELECT invoice_id, invoice_number, file_name
                FROM invoices
                WHERE vendor_id = ?
                  AND invoice_date = ?
                  AND total_amount_paise = ?
            """ + exclusion

            params = [
                vendor_id,
                invoice_date,
                total_amount_paise,
            ]
            if invoice_id is not None:
                params.append(invoice_id)

            row = connection.execute(query, params).fetchone()

            if row:
                return {
                    "check": "duplicate_detection",
                    "status": "REVIEW",
                    "reason": (
                        "Another invoice from this vendor has "
                        "the same date and total amount. "
                        "Manual verification is required."
                    ),
                    "matched_invoice_id": row["invoice_id"],
                    "match_type": "VENDOR_DATE_AMOUNT",
                }

        return {
            "check": "duplicate_detection",
            "status": "PASS",
            "reason": "No duplicate invoice was found.",
            "matched_invoice_id": None,
            "match_type": None,
        }

    finally:
        connection.close()