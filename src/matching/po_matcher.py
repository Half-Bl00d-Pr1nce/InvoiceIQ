import pandas as pd
from src.matching.semantic_matcher import find_po_candidates

import pandas as pd
from src.matching.semantic_matcher import find_po_candidates


def match_purchase_order(
    po_number: str,
    vendor_id: str,
    purchase_orders_df: pd.DataFrame
) -> dict:

    if not po_number or not po_number.strip():
        return {
            "check": "PO_MATCHING",
            "status": "NOT_CHECKED",
            "po_id": None,
            "message": "Invoice does not contain a PO number."
        }

    matches = purchase_orders_df[
        purchase_orders_df["po_id"].astype(str).str.strip().str.upper()
        == po_number.strip().upper()
    ]

    if matches.empty:
        return {
            "check": "PO_MATCHING",
            "status": "FAIL",
            "po_id": None,
            "message": f"Purchase order '{po_number}' was not found."
        }

    # Multiple rows are allowed when they represent different items
    # belonging to the same purchase order.
    vendors = matches["vendor_id"].dropna().astype(str).str.strip().unique()

    if len(vendors) != 1:
        return {
            "check": "PO_MATCHING",
            "status": "REVIEW",
            "po_id": None,
            "message": "Purchase order has inconsistent vendor records."
        }

    if vendors[0] != str(vendor_id).strip():
        return {
            "check": "PO_MATCHING",
            "status": "FAIL",
            "po_id": None,
            "message": "Purchase order belongs to a different vendor."
        }

    statuses = (
        matches["status"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .unique()
    )

    if len(statuses) != 1:
        return {
            "check": "PO_MATCHING",
            "status": "REVIEW",
            "po_id": None,
            "message": "Purchase order has inconsistent status records."
        }

    if statuses[0] != "OPEN":
        return {
            "check": "PO_MATCHING",
            "status": "FAIL",
            "po_id": None,
            "message": f"Purchase order is not open. Current status: {statuses[0]}."
        }

    return {
        "check": "PO_MATCHING",
        "status": "PASS",
        "po_id": matches.iloc[0]["po_id"],
        "message": f"Purchase order '{po_number}' was verified."
    }


def find_implicit_po_candidates(
    vendor_id: str,
    invoice_items: list,
    purchase_orders_df: pd.DataFrame,
    top_k: int = 5
) -> dict:

    if not vendor_id:
        return {
            "check": "IMPLICIT_PO_MATCHING",
            "status": "NOT_CHECKED",
            "candidates": [],
            "message": "Vendor could not be identified."
        }

    # Restrict candidates to this vendor's open POs.
    vendor_pos = purchase_orders_df[
        (purchase_orders_df["vendor_id"] == vendor_id)
        & (purchase_orders_df["status"].str.strip().str.upper() == "OPEN")
    ].copy()

    if vendor_pos.empty:
        return {
            "check": "IMPLICIT_PO_MATCHING",
            "status": "NOT_CHECKED",
            "candidates": [],
            "message": "No open purchase orders found for this vendor."
        }

    # Collect the best matching PO item for each PO.
    po_candidates = {}

    for invoice_item in invoice_items:
        description = invoice_item.description or ""

        if not description.strip():
            continue

        matches = find_po_candidates(
            description,
            vendor_pos,
            top_k=len(vendor_pos)
        )

        for candidate in matches:
            po_id = candidate["po_id"]

            if not po_id:
                continue

            if (
                po_id not in po_candidates
                or candidate["similarity_score"]
                > po_candidates[po_id]["similarity_score"]
            ):
                po_candidates[po_id] = {
                    "po_id": po_id,
                    "vendor_id": vendor_id,
                    "item_code": candidate["item_code"],
                    "description": candidate["description"],
                    "similarity_score": candidate["similarity_score"]
                }

    ranked_candidates = sorted(
        po_candidates.values(),
        key=lambda item: item["similarity_score"],
        reverse=True
    )[:top_k]

    # Use the configured review threshold.
    plausible_candidates = [
        candidate for candidate in ranked_candidates
        if candidate["similarity_score"] >= 0.75
    ]

    if len(plausible_candidates) > 1:
        status = "REVIEW"
        message = (
            "Multiple plausible purchase orders were found. Human confirmation is required."
        )

    elif len(plausible_candidates) == 1:
        status = "REVIEW"
        message = (
            "One likely purchase order was found, but explicit "
            "confirmation is required because the invoice has no PO number."
        )

    else:
        status = "NOT_CHECKED"
        message = "No sufficiently similar PO candidates were found."

    return {
        "check": "IMPLICIT_PO_MATCHING",
        "status": status,
        "candidates": ranked_candidates,
        "message": message
    }