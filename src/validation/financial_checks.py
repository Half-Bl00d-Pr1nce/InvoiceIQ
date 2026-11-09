
from decimal import Decimal

from src.extraction.schemas import InvoiceData

from decimal import ROUND_HALF_UP

def validate_line_items(invoice: InvoiceData) -> dict:
    """
    Check whether quantity * unit price matches
    the extracted line amount for each item.
    """

    results = []

    for index, item in enumerate(invoice.items, start=1):

        # Cannot validate if a required value is missing
        if (
            item.quantity is None
            or item.unit_price is None
            or item.line_amount is None
        ):
            results.append({
                "item_number": index,
                "status": "NOT_CHECKED",
                "message": "Missing quantity, unit price or line amount."
            })
            continue

        expected_amount = item.quantity * item.unit_price

        difference = abs(expected_amount - item.line_amount)

        if difference == Decimal("0"):
            status = "PASS"
            message = "Line amount matches quantity * unit price."
        else:
            status = "FAIL"
            message = (
                f"Expected {expected_amount}, "
                f"but extracted {item.line_amount}."
            )

        results.append({
            "item_number": index,
            "status": status,
            "message": message
        })

    return {
        "check": "LINE_ITEM_ARITHMETIC",
        "results": results
    }


def validate_subtotal(invoice: InvoiceData) -> dict:
    """
    Compare the sum of line amounts against
    the invoice subtotal.
    """

    if invoice.subtotal is None:
        return {
            "check": "SUBTOTAL_RECONCILIATION",
            "status": "NOT_CHECKED",
            "message": "Invoice subtotal is missing."
        }

    if not invoice.items:
        return {
            "check": "SUBTOTAL_RECONCILIATION",
            "status": "NOT_CHECKED",
            "message": "No line items are available."
        }

    if any(item.line_amount is None for item in invoice.items):
        return {
            "check": "SUBTOTAL_RECONCILIATION",
            "status": "NOT_CHECKED",
            "message": "One or more line amounts are missing."
        }

    calculated_subtotal = sum(
        (item.line_amount for item in invoice.items),
        Decimal("0")
    )

    difference = abs(calculated_subtotal - invoice.subtotal)

    if difference == Decimal("0"):
        status = "PASS"
        message = "Sum of line amounts matches invoice subtotal."
    else:
        status = "FAIL"
        message = (
            f"Calculated subtotal is {calculated_subtotal}, "
            f"but extracted subtotal is {invoice.subtotal}."
        )

    return {
        "check": "SUBTOTAL_RECONCILIATION",
        "status": status,
        "calculated_amount": str(calculated_subtotal),
        "extracted_amount": str(invoice.subtotal),
        "message": message
    }



def validate_invoice_total(invoice: InvoiceData) -> dict:
    """
    Verify the invoice total using the appropriate tax treatment.
    """

    required_fields = {
        "subtotal": invoice.subtotal,
        "tax_amount": invoice.tax_amount,
        "total_amount": invoice.total_amount
    }

    missing_fields = [
        field
        for field, value in required_fields.items()
        if value is None
    ]

    if missing_fields:
        return {
            "check": "INVOICE_TOTAL_RECONCILIATION",
            "status": "NOT_CHECKED",
            "message": f"Missing fields: {', '.join(missing_fields)}."
        }

    shipping = invoice.shipping or Decimal("0")
    discount = invoice.discount or Decimal("0")

    if invoice.tax_treatment == "EXCLUSIVE":
        expected_total = (
            invoice.subtotal
            + shipping
            - discount
            + invoice.tax_amount
        )

    elif invoice.tax_treatment == "INCLUSIVE":
        # Tax is already included in the subtotal.
        expected_total = (
            invoice.subtotal
            + shipping
            - discount
        )

    else:
        return {
            "check": "INVOICE_TOTAL_RECONCILIATION",
            "status": "NOT_CHECKED",
            "message": (
                "Tax treatment is unknown. "
                "Human verification is required."
            )
        }

    difference = abs(expected_total - invoice.total_amount)

    if difference == Decimal("0"):
        status = "PASS"
        message = "Calculated total matches invoice total."
    else:
        status = "FAIL"
        message = (
            f"Calculated total is {expected_total}, "
            f"but extracted invoice total is {invoice.total_amount}."
        )

    return {
        "check": "INVOICE_TOTAL_RECONCILIATION",
        "status": status,
        "tax_treatment": invoice.tax_treatment,
        "calculated_amount": str(expected_total),
        "extracted_amount": str(invoice.total_amount),
        "message": message
    }



def validate_po_tax_amount(invoice: InvoiceData, po_items) -> dict:
    """Validate invoice tax against tax rates authorised by the matched PO."""

    if invoice.tax_amount is None:
        return {
            "check": "PO_TAX_RATE_RECONCILIATION",
            "status": "NOT_CHECKED",
            "message": "Invoice tax amount is missing."
        }

    if invoice.tax_treatment not in ("EXCLUSIVE", "INCLUSIVE"):
        return {
            "check": "PO_TAX_RATE_RECONCILIATION",
            "status": "NOT_CHECKED",
            "message": "Tax treatment is unknown; PO tax cannot be verified."
        }

    if invoice.shipping not in (None, Decimal("0")) or invoice.discount not in (None, Decimal("0")):
        return {
            "check": "PO_TAX_RATE_RECONCILIATION",
            "status": "NOT_CHECKED",
            "message": "Shipping or discount is present; its tax treatment needs human verification."
        }

    expected_tax = Decimal("0")
    issues = []

    for line_number, item in enumerate(invoice.items, start=1):
        if item.line_amount is None or not item.item_code:
            issues.append(
                f"Invoice line {line_number} has no line amount or item code."
            )
            continue

        matches = po_items[
            po_items["item_code"].astype(str).str.strip().str.upper()
            == str(item.item_code).strip().upper()
        ]

        if len(matches) != 1:
            issues.append(
                f"Invoice line {line_number} does not map to exactly one PO item."
            )
            continue

        raw_rate = matches.iloc[0]["tax_rate"]

        try:
            rate = Decimal(str(raw_rate))
            if rate < 0:
                raise ValueError
        except (ValueError, TypeError):
            issues.append(
                f"PO tax rate is missing or invalid for invoice line {line_number}."
            )
            continue

        if invoice.tax_treatment == "EXCLUSIVE":
            line_tax = item.line_amount * rate / Decimal("100")
        else:
            line_tax = (
                item.line_amount * rate / (Decimal("100") + rate)
            )

        expected_tax += line_tax.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    if issues:
        return {
            "check": "PO_TAX_RATE_RECONCILIATION",
            "status": "NOT_CHECKED",
            "expected_tax": f"{expected_tax:.2f}",
            "message": " ".join(issues)
        }

    if abs(expected_tax - invoice.tax_amount) <= Decimal("0.01"):
        status = "PASS"
        message = "Invoice tax matches the tax calculated using the PO tax rates."
    else:
        status = "FAIL"
        message = (
            f"Expected tax is {expected_tax:.2f} using the PO tax rate(s), "
            f"but the invoice reports {invoice.tax_amount:.2f}."
        )

    return {
        "check": "PO_TAX_RATE_RECONCILIATION",
        "status": status,
        "expected_tax": f"{expected_tax:.2f}",
        "extracted_tax": f"{invoice.tax_amount:.2f}",
        "message": message
    }

def validate_financials(invoice: InvoiceData) -> dict:
    """
    Run all financial checks and return
    a combined validation report.
    """

    line_check = validate_line_items(invoice)
    subtotal_check = validate_subtotal(invoice)
    total_check = validate_invoice_total(invoice)

    return {
        "line_items": line_check,
        "subtotal": subtotal_check,
        "total": total_check
    }

def validate_cumulative_po_amount(
    po_amount_paise,
    approved_amount_paise,
    pending_amount_paise,
    current_amount_paise,
    tolerance_percentage,
    tolerance_absolute_paise
):
    """
    Validate cumulative pre-tax invoice value against PO value.

    All monetary amounts are in paise.
    """

    po_amount = Decimal(str(po_amount_paise))
    approved_amount = Decimal(str(approved_amount_paise))
    pending_amount = Decimal(str(pending_amount_paise))
    current_amount = Decimal(str(current_amount_paise))

    percentage = Decimal(str(tolerance_percentage))
    absolute_tolerance = Decimal(str(tolerance_absolute_paise))

    tolerance_by_percentage = (
        po_amount * percentage / Decimal("100")
    )

    # Apply the stricter of the two configured limits.
    effective_tolerance = min(
        tolerance_by_percentage,
        absolute_tolerance
    )

    confirmed_total = approved_amount + current_amount

    projected_total = (
        approved_amount
        + pending_amount
        + current_amount
    )

    confirmed_excess = max(
        Decimal("0"),
        confirmed_total - po_amount
    )

    projected_excess = max(
        Decimal("0"),
        projected_total - po_amount
    )

    # Previously approved invoices alone already exceed tolerance.
    if approved_amount > po_amount + effective_tolerance:
        status = "FAIL"
        message = "Previously approved invoices already exceed the PO limit and tolerance."

    # Current invoice causes a confirmed overrun beyond tolerance.
    elif confirmed_excess > effective_tolerance:
        status = "REVIEW"
        message = "Current invoice causes cumulative billing to exceed the configured tolerance."

    # Pending invoices create a potential overrun.
    elif projected_excess > effective_tolerance:
        status = "REVIEW"
        message = "Pending invoices create a potential cumulative PO overrun."

    elif confirmed_excess > 0 or projected_excess > 0:
        status = "PASS"
        message = "Cumulative billing is within the configured tolerance."

    else:
        status = "PASS"
        message = "Cumulative billing is within the PO value."

    return {
        "check": "CUMULATIVE_PO_AMOUNT",
        "status": status,
        "po_amount_paise": str(po_amount),
        "approved_amount_paise": str(approved_amount),
        "pending_amount_paise": str(pending_amount),
        "current_amount_paise": str(current_amount),
        "confirmed_total_paise": str(confirmed_total),
        "projected_total_paise": str(projected_total),
        "effective_tolerance_paise": str(effective_tolerance),
        "confirmed_excess_paise": str(confirmed_excess),
        "projected_excess_paise": str(projected_excess),
        "message": message
    }
