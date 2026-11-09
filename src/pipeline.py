from pathlib import Path
import pandas as pd
from src.validation.vendor_checks import validate_vendor
from src.ingestion.document_router import extract_document
from src.extraction.llm_extractor import extract_invoice_data
from src.matching.po_matcher import (
    match_purchase_order,
    find_implicit_po_candidates
)
from src.validation.financial_checks import (
    validate_financials,
    validate_po_tax_amount
)
from src.matching.item_reconciler import reconcile_invoice_items
from src.validation.duplicate_detector import detect_duplicate
from src.decision.rules_engine import make_decision
from src.decision.explanation import generate_explanation
from src.database.repository import (
    create_invoice_record,
    save_invoice_items,
    save_validation_results,
    save_processing_log,
    update_invoice_status,
    get_reference_data,
)

def aggregate_financial_status(financial_validation):
    statuses = []

    # Line-item arithmetic
    line_items = financial_validation.get("line_items", {})
    statuses.extend(
        item.get("status", "NOT_CHECKED")
        for item in line_items.get("results", [])
    )

    # Subtotal, total and PO tax checks
    for check_name in ["subtotal", "total", "po_tax"]:
        check = financial_validation.get(check_name, {})
        statuses.append(check.get("status", "NOT_CHECKED"))

    if "FAIL" in statuses:
        return "FAIL"

    if any(status != "PASS" for status in statuses):
        return "REVIEW"

    return "PASS"



def validate_extraction(invoice_data):
    required_fields = {
        "vendor": invoice_data.vendor.vendor_name,
        "invoice_number": invoice_data.invoice_number,
        "invoice_date": invoice_data.invoice_date,
        "currency": invoice_data.currency,
        "total_amount": invoice_data.total_amount,
    }

    missing_fields = [
        field for field, value in required_fields.items()
        if value is None or value == ""
    ]

    if missing_fields:
        return {
            "status": "REVIEW",
            "message": f"Missing fields: {', '.join(missing_fields)}"
        }

    return {
        "status": "PASS",
        "message": "All required invoice fields were extracted."
    }
    
def process_invoice(pdf_path):
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"Invoice not found: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF invoices are supported.")

    # --------------------------------------------------
    # 1. DOCUMENT INGESTION
    # --------------------------------------------------

    document = extract_document(str(pdf_path))
    extracted_text = document["full_text"]

    if not extracted_text.strip():
        raise ValueError("No readable text could be extracted.")

    # --------------------------------------------------
    # 2. STRUCTURED EXTRACTION
    # --------------------------------------------------

    invoice_data = extract_invoice_data(extracted_text)

    # --------------------------------------------------
    # 3. LOAD REFERENCE DATA FROM SQLITE
    # --------------------------------------------------

    reference_data = get_reference_data()

    vendors_df = pd.DataFrame(reference_data["vendors"])

    purchase_orders_df = pd.DataFrame(
        reference_data["purchase_orders"]
    )

    po_items_df = pd.DataFrame(
        reference_data["po_items"]
    )

    # Add PO header information to each PO line item.
    # This is needed for implicit PO matching.
    po_items_df = po_items_df.merge(
        purchase_orders_df[
            ["po_id", "vendor_id", "status", "currency"]
        ],
        on="po_id",
        how="left",
    )

    # --------------------------------------------------
    # 4. VENDOR VALIDATION AND RESOLUTION
    # --------------------------------------------------

    vendor_name = invoice_data.vendor.vendor_name
    extracted_vendor_id = invoice_data.vendor.vendor_id
    tax_id = invoice_data.vendor.tax_id

    vendor_validation = validate_vendor(
        vendor_name=vendor_name,
        vendors_df=vendors_df,
        vendor_id=extracted_vendor_id,
        tax_id=tax_id
    )

    # Only a successfully verified vendor can proceed
    # to duplicate detection and PO matching.
    vendor_id = (
        vendor_validation["vendor_id"]
        if vendor_validation["status"] == "PASS"
        else None
    )

    # --------------------------------------------------
    # 5. DUPLICATE DETECTION
    # --------------------------------------------------

    from decimal import Decimal

    total_amount_paise = None

    if (
        invoice_data.total_amount is not None
        and invoice_data.currency
        and invoice_data.currency.upper() == "INR"
    ):
        total_amount_paise = int(
            (Decimal(str(invoice_data.total_amount)) * 100)
            .quantize(Decimal("1"))
        )

    duplicate_validation = detect_duplicate(
        file_hash=document["file_hash"],
        vendor_id=vendor_id,
        invoice_number=invoice_data.invoice_number,
        invoice_date=(
            invoice_data.invoice_date.isoformat()
            if invoice_data.invoice_date
            else None
        ),
        total_amount_paise=total_amount_paise,
    )

    
    # --------------------------------------------------
    # 6. PO MATCHING
    # --------------------------------------------------

    implicit_po_validation = None

    if invoice_data.po_number and vendor_id:

        # Explicit PO reference: validate it directly.
        po_validation = match_purchase_order(
            invoice_data.po_number,
            vendor_id,
            purchase_orders_df
        )

    elif not invoice_data.po_number and vendor_id:

        # No explicit PO: discover possible candidates.
        implicit_po_validation = find_implicit_po_candidates(
            vendor_id,
            invoice_data.items,
            po_items_df,
        )

        # A candidate is not a confirmed PO.
        po_validation = {
            "check": "PO_MATCHING",
            "status": (
                "REVIEW"
                if implicit_po_validation["candidates"]
                else "NOT_CHECKED"
            ),
            "po_id": None,
            "message": implicit_po_validation["message"]
        }

    else:

        po_validation = {
            "check": "PO_MATCHING",
            "status": "NOT_CHECKED",
            "po_id": None,
            "message": (
                "PO matching could not be performed because "
                "the vendor could not be resolved."
            )
        }

    # Verify currency compatibility only for an explicitly
    # identified and validated PO.
    if (
        po_validation["status"] == "PASS"
        and po_validation.get("po_id")
    ):
        matched_po = purchase_orders_df[
            purchase_orders_df["po_id"]
            == po_validation["po_id"]
        ].iloc[0]

        if (
            invoice_data.currency.upper() != "INR"
            or str(matched_po["currency"]).upper() != "INR"
        ):
            po_validation["status"] = "REVIEW"
            po_validation["message"] = (
                "PO reconciliation currently supports INR only."
            )


    
    # --------------------------------------------------
    # 7. FINANCIAL VALIDATION
    # --------------------------------------------------

    financial_validation = validate_financials(invoice_data)

    # Verify invoice tax against the tax rate authorised by the matched PO.
    if po_validation["status"] == "PASS" and po_validation.get("po_id"):
        matched_po_items = po_items_df[
            po_items_df["po_id"].astype(str).str.strip().str.upper()
            == str(po_validation["po_id"]).strip().upper()
        ]

        financial_validation["po_tax"] = validate_po_tax_amount(
            invoice_data, matched_po_items
        )
    else:
        financial_validation["po_tax"] = {
            "check": "PO_TAX_RATE_RECONCILIATION",
            "status": "NOT_CHECKED",
            "message": "PO tax validation requires a uniquely validated purchase order."
        }


    # --------------------------------------------------
    # 8. CREATE INVOICE RECORD
    # --------------------------------------------------

    invoice_id = None

    # An exact duplicate is not inserted again.
    if duplicate_validation["status"] != "FAIL":

        invoice_id = create_invoice_record(
            invoice=invoice_data,
            file_name=document["file_name"],
            file_hash=document["file_hash"],
            vendor_id=vendor_id,
            po_id=(
                po_validation["po_id"]
                if po_validation["status"] == "PASS"
                else None
            ),
        )

        save_invoice_items(
            invoice_id,
            invoice_data.items,
            invoice_data.currency,
        )

        save_processing_log(
            invoice_id,
            "INGESTION",
            "PASS",
            "PDF text extraction completed."
        )

        save_processing_log(
            invoice_id,
            "EXTRACTION",
            "PASS",
            "Structured invoice extraction completed."
        )

    # --------------------------------------------------
    # 9. ITEM RECONCILIATION
    # --------------------------------------------------

    if (
        duplicate_validation["status"] != "FAIL"
        and po_validation["status"] == "PASS"
        and po_validation.get("po_id") is not None
    ):
        item_reconciliation = reconcile_invoice_items(
        invoice_data.items,
        po_validation["po_id"],
        po_items_df,
        invoice_id=invoice_id,
        tax_treatment=invoice_data.tax_treatment
    )
    else:
        item_reconciliation = {
            "check": "ITEM_RECONCILIATION",
            "status": "NOT_CHECKED",
            "message": (
                "Item reconciliation skipped because the invoice "
                "is a duplicate or no valid PO was identified."
            )
        }

    # --------------------------------------------------
    # 10. NORMALISE VALIDATION RESULTS
    # --------------------------------------------------

    financial_status = aggregate_financial_status(
        financial_validation
    )

    validation_results = {
        "duplicate": {
            "status": duplicate_validation["status"],
            "message": duplicate_validation.get(
                "reason",
                "Duplicate check completed."
            )
        },

        "vendor": {
            "status": vendor_validation["status"],
            "message": vendor_validation.get(
                "message",
                "Vendor validation completed."
            )
        },

        "po": {
            "status": po_validation["status"],
            "message": po_validation.get(
                "message",
                "PO validation completed."
            )
        },

        "financial": {
            "status": financial_status,
            "message": (
                "Financial checks passed."
                if financial_status == "PASS"
                else "One or more financial checks failed "
                     "or could not be completed."
            )
        },

        
        "item_reconciliation": {
            "status": item_reconciliation["status"],
            "message": item_reconciliation.get(
                "message",
                "; ".join(
                    message
                    for result in item_reconciliation.get("results", [])
                    for message in [
                        result.get("quantity", {}).get("message")
                        if result.get("quantity", {}).get("status")
                        in ("FAIL", "REVIEW")
                        else None,

                        result.get("unit_price", {}).get("message")
                        if result.get("unit_price", {}).get("status")
                        in ("FAIL", "REVIEW")
                        else None,
                    ]
                    if message
                ) or item_reconciliation.get(
                    "amount_validation", {}
                ).get(
                    "message",
                    "Item reconciliation completed."
                )
            )
        },


        "extraction": validate_extraction(invoice_data),
    }

    # --------------------------------------------------
    # 11. FINAL DECISION
    # --------------------------------------------------

    decision = make_decision(validation_results)

    explanation = generate_explanation(decision)

    # --------------------------------------------------
    # 12. DATABASE PERSISTENCE
    # --------------------------------------------------

    if invoice_id is not None:

        save_validation_results(
            invoice_id,
            validation_results
        )

        save_processing_log(
            invoice_id,
            "VALIDATION",
            "COMPLETED",
            "All configured validation stages were executed."
        )

        save_processing_log(
            invoice_id,
            "DECISION",
            decision["status"],
            explanation["summary"]
        )

        update_invoice_status(
            invoice_id,
            decision["status"]
        )

    # --------------------------------------------------
    # 13. RETURN COMPLETE RESULT
    # --------------------------------------------------

    return {
        "invoice_id": invoice_id,
        "file_name": pdf_path.name,
        "document": document,
        "invoice_data": invoice_data,
        "vendor_id": vendor_id,
        "vendor_validation": vendor_validation,
        "duplicate_validation": duplicate_validation,
        "po_validation": po_validation,
        "implicit_po_validation": implicit_po_validation,
        "financial_validation": financial_validation,
        "item_reconciliation": item_reconciliation,
        "validation_results": validation_results,
        "decision": decision,
        "explanation": explanation,
    }