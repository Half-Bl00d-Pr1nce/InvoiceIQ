
import pandas as pd
from decimal import Decimal
from pathlib import Path
import yaml
from decimal import ROUND_HALF_UP
from src.database.repository import get_historical_po_billing
from src.validation.financial_checks import (
    validate_cumulative_po_amount
)
from src.matching.semantic_matcher import (
    find_po_candidates,
    find_bundle_component_candidates
)


def load_tolerance_settings():
    """Read monetary tolerance settings from rules.yaml."""

    config_path = Path("config/rules.yaml")

    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    tolerance = config["tolerance"]

    return (
        tolerance["amount_percentage"],
        tolerance["amount_absolute_paise"]
    )


def to_paise(amount):
    """Convert a currency amount into integer paise."""

    return int(
        (
            Decimal(str(amount)) * Decimal("100")
        ).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    )
    
def get_pre_tax_amount(amount, tax_rate):
    """Convert a tax-inclusive amount into its pre-tax value."""

    amount = Decimal(str(amount))
    tax_rate = Decimal(str(tax_rate))

    divisor = Decimal("1") + tax_rate / Decimal("100")

    return (amount / divisor).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

def normalize_tax_rate(rate):
    """Convert decimal fractions to percentage points."""

    if rate is None:
        return None

    rate = Decimal(str(rate))

    if Decimal("0") < rate <= Decimal("1"):
        rate *= Decimal("100")

    return rate

def resolve_tax_rate(invoice_item, po_item):
    """
    Use the invoice tax rate when available, otherwise use
    the PO tax rate. Flag conflicting rates.
    """

    invoice_rate = normalize_tax_rate(invoice_item.tax_rate)

    po_rate = (
        Decimal(str(po_item["tax_rate"]))
        if pd.notna(po_item["tax_rate"])
        else None
    )
    
    if invoice_rate is not None:
        invoice_rate = Decimal(str(invoice_rate))

    if (
        invoice_rate is not None
        and po_rate is not None
        and invoice_rate != po_rate
    ):
        return None, "Invoice tax rate differs from PO tax rate."

    tax_rate = invoice_rate if invoice_rate is not None else po_rate

    if tax_rate is None:
        return None, "Tax rate is unavailable."

    if tax_rate < 0:
        return None, "Tax rate cannot be negative."

    return tax_rate, None

def reconcile_invoice_items(
    invoice_items: list,
    po_id: str,
    purchase_orders_df: pd.DataFrame,
    invoice_id=None,
    tax_treatment="EXCLUSIVE"
) -> dict:
    """
    Reconcile invoice items against a PO, considering
    previously approved and pending invoices.
    """

    po_items = purchase_orders_df[
        purchase_orders_df["po_id"].str.strip().str.upper()
        == po_id.strip().upper()
    ]

    if po_items.empty:
        return {
            "check": "PO_ITEM_RECONCILIATION",
            "status": "FAIL",
            "results": [],
            "message": f"No items found for PO {po_id}."
        }

    # Retrieve historical billing, excluding the current invoice
    # if it has already been stored.
    historical_billing = get_historical_po_billing(
        po_id,
        exclude_invoice_id=invoice_id
    )

    # Group current invoice lines by item code.
    grouped_items = {}

    for index, invoice_item in enumerate(invoice_items, start=1):
        item_code = invoice_item.item_code

        
        if not item_code:
            description = invoice_item.description or ""

            # First, check whether the description may represent
            # multiple PO components.
            bundle_candidates = find_bundle_component_candidates(
                description,
                po_items,
                top_k=10
            )

            # If multiple components are identified, treat this
            # as a possible bundled invoice line.
            if len(bundle_candidates) > 1:
                grouped_items[f"__BUNDLE_{index}"] = {
                    "item_code": None,
                    "items": [(index, invoice_item)],
                    "candidates": bundle_candidates,
                    "is_bundle": True
                }

            else:
                # Otherwise, use the normal missing-code matcher.
                candidates = find_po_candidates(
                    description,
                    po_items,
                    top_k=5
                )

                grouped_items[f"__MISSING_{index}"] = {
                    "item_code": None,
                    "items": [(index, invoice_item)],
                    "candidates": candidates,
                    "is_bundle": False
                }

            continue


        normalized_code = item_code.strip().upper()

        if normalized_code not in grouped_items:
            grouped_items[normalized_code] = {
                "item_code": item_code,
                "items": []
            }

        grouped_items[normalized_code]["items"].append(
            (index, invoice_item)
        )

    results = []

    for normalized_code, group in grouped_items.items():

        item_code = group["item_code"]
        current_lines = group["items"]

        
        if item_code is None:

            is_bundle = group.get("is_bundle", False)

            if is_bundle:
                results.append({
                    "item_code": None,
                    "description": current_lines[0][1].description,
                    "status": "REVIEW",
                    "message": (
                        "This invoice line may represent multiple "
                        "purchase order components. Component mapping "
                        "and quantity allocation require human confirmation."
                    ),
                    "is_bundle": True,
                    "suggested_components": group.get("candidates", [])
                })

            else:
                results.append({
                    "item_code": None,
                    "description": current_lines[0][1].description,
                    "status": "REVIEW",
                    "message": (
                        "Invoice item code is missing. Possible PO item "
                        "matches have been suggested using description "
                        "similarity. Human confirmation is required "
                        "before allocation."
                    ),
                    "suggested_matches": group.get("candidates", [])
                })

            continue


        matches = po_items[
            po_items["item_code"].str.strip().str.upper()
            == normalized_code
        ]

        if matches.empty:
            results.append({
                "item_code": item_code,
                "status": "FAIL",
                "message": "Item does not exist in the selected PO."
            })
            continue

        if len(matches) > 1:
            results.append({
                "item_code": item_code,
                "status": "REVIEW",
                "message": (
                    "Multiple PO item records match this item code. "
                    "Automatic reconciliation is ambiguous."
                )
            })
            continue

        po_item = matches.iloc[0]

        po_quantity = Decimal(str(po_item["quantity"]))
        po_price = (
            Decimal(str(po_item["unit_price_paise"]))
            / Decimal("100")
        )

        # Aggregate all current invoice lines for this item.
        current_quantity = sum(
            (
                Decimal(str(item.quantity))
                for _, item in current_lines
            ),
            Decimal("0")
        )
        
        # Check every invoice line against the PO unit price.
        price_mismatches = []
        tax_review_messages = []

        for line_number, item in current_lines:

            invoice_price = Decimal(str(item.unit_price))
            comparison_price = invoice_price

            if tax_treatment == "INCLUSIVE":

                tax_rate, tax_error = resolve_tax_rate(item, po_item)

                if tax_error:
                    tax_review_messages.append(tax_error)
                    continue

                comparison_price = get_pre_tax_amount(
                    invoice_price,
                    tax_rate
                )

            elif tax_treatment == "UNKNOWN":
                tax_review_messages.append(
                    "Tax treatment is unknown; unit price cannot "
                    "be safely normalised."
                )
                continue

            if comparison_price != po_price:
                price_mismatches.append({
                    "invoice_line": line_number,
                    "original_invoice_price": str(invoice_price),
                    "comparison_price": str(comparison_price),
                    "po_price": str(po_price)
                })

        if tax_review_messages:
            price_status = "REVIEW"
            price_message = "; ".join(sorted(set(tax_review_messages)))

        elif price_mismatches:
            price_status = "FAIL"
            price_message = (
                "One or more invoice unit prices differ from "
                "the PO unit price after tax normalisation."
            )

        else:
            price_status = "PASS"
            price_message = (
                "All invoice unit prices match the PO on a pre-tax basis."
            )


        # Retrieve historical approved and pending quantities.
        history = historical_billing.get(
            normalized_code,
            {
                "approved_quantity": Decimal("0"),
                "pending_quantity": Decimal("0")
            }
        )

        approved_quantity = history["approved_quantity"]
        pending_quantity = history["pending_quantity"]

        confirmed_quantity = (
            approved_quantity + current_quantity
        )

        projected_quantity = (
            approved_quantity
            + pending_quantity
            + current_quantity
        )

        # Cumulative quantity validation.
        if confirmed_quantity > po_quantity:
            quantity_status = "FAIL"
            quantity_message = (
                f"Confirmed cumulative quantity "
                f"{confirmed_quantity} exceeds PO quantity "
                f"{po_quantity}."
            )

        elif projected_quantity > po_quantity:
            quantity_status = "REVIEW"
            quantity_message = (
                f"Projected cumulative quantity "
                f"{projected_quantity} exceeds PO quantity "
                f"{po_quantity} when pending invoices are included. "
                f"Confirmed quantity is {confirmed_quantity}."
            )

        else:
            quantity_status = "PASS"
            quantity_message = (
                f"Confirmed cumulative quantity is "
                f"{confirmed_quantity} of {po_quantity}. "
                f"Projected quantity including pending invoices is "
                f"{projected_quantity}."
            )

        # Determine item-level outcome.
        if "FAIL" in [quantity_status, price_status]:
            overall_status = "FAIL"
        elif "REVIEW" in [quantity_status, price_status]:
            overall_status = "REVIEW"
        else:
            overall_status = "PASS"

        results.append({
            "item_code": item_code,
            "status": overall_status,
            "invoice_lines": [
                line_number for line_number, _ in current_lines
            ],
            "quantity": {
                "status": quantity_status,
                "po_quantity": str(po_quantity),
                "previously_approved": str(approved_quantity),
                "previously_pending": str(pending_quantity),
                "current_invoice": str(current_quantity),
                "confirmed_cumulative": str(confirmed_quantity),
                "projected_cumulative": str(projected_quantity),
                "message": quantity_message
            },
            "unit_price": {
                "status": price_status,
                "message": price_message,
                "mismatches": price_mismatches
            }
        })

    # ---------------------------------------
    # Cumulative monetary reconciliation 
    # (Moved outside the item loop)
    # ---------------------------------------
    current_amounts = [
        getattr(item, "line_amount", None)
        for item in invoice_items
    ]
    amount_result = {
    "check": "CUMULATIVE_PO_AMOUNT",
    "status": "NOT_CHECKED",
    "message": "Cumulative monetary validation could not be performed because one or more line amounts are missing."
}

    if all(amount is not None for amount in current_amounts):

        # Calculate original PO value before tax.
        po_amount_paise = sum(
            (
                Decimal(str(row["quantity"]))
                * Decimal(str(row["unit_price_paise"]))
                for _, row in po_items.iterrows()
            ),
            Decimal("0")
        )

        po_amount_paise = int(
            po_amount_paise.quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP
            )
        )

        # Retrieve historical amounts across all PO items.
        approved_amount_paise = sum(
            (
                value["approved_amount_paise"]
                for value in historical_billing.values()
            ),
            Decimal("0")
        )

        pending_amount_paise = sum(
            (
                value["pending_amount_paise"]
                for value in historical_billing.values()
            ),
            Decimal("0")
        )

        # Convert current invoice amounts to the pre-tax basis.
        normalised_amounts = []
        amount_errors = []

        for item in invoice_items:

            if item.line_amount is None:
                amount_errors.append("A line amount is missing.")
                continue

            if tax_treatment == "EXCLUSIVE":
                normalised_amounts.append(item.line_amount)

            elif tax_treatment == "INCLUSIVE":

                matches = po_items[
                    po_items["item_code"].str.strip().str.upper()
                    == str(item.item_code).strip().upper()
                ] if item.item_code else pd.DataFrame()

                if len(matches) != 1:
                    amount_errors.append(
                        "Cannot identify a unique PO item for tax normalisation."
                    )
                    continue

                po_item = matches.iloc[0]

                tax_rate, tax_error = resolve_tax_rate(item, po_item)

                if tax_error:
                    amount_errors.append(tax_error)
                    continue

                normalised_amounts.append(
                    get_pre_tax_amount(item.line_amount, tax_rate)
                )

            else:
                amount_errors.append(
                    "Tax treatment is unknown; pre-tax amount cannot be determined."
                )

        if amount_errors:
            amount_result = {
                "check": "CUMULATIVE_PO_AMOUNT",
                "status": "REVIEW",
                "message": "; ".join(sorted(set(amount_errors)))
            }

        else:
            current_amount_paise = sum(
                to_paise(amount)
                for amount in normalised_amounts
            )

            percentage, absolute_tolerance = load_tolerance_settings()

            amount_result = validate_cumulative_po_amount(
                po_amount_paise=po_amount_paise,
                approved_amount_paise=approved_amount_paise,
                pending_amount_paise=pending_amount_paise,
                current_amount_paise=current_amount_paise,
                tolerance_percentage=percentage,
                tolerance_absolute_paise=absolute_tolerance
            )

    overall_statuses = [
        item["status"] for item in results
    ]

    overall_statuses.append(amount_result["status"])

    if "FAIL" in overall_statuses:
        overall_status = "FAIL"
    elif any(status != "PASS" for status in overall_statuses):
        overall_status = "REVIEW"
    else:
        overall_status = "PASS"

    return {
        "check": "PO_ITEM_RECONCILIATION",
        "status": overall_status,
        "results": results,
        "amount_validation": amount_result
    }