
import pandas as pd

from src.matching.po_matcher import find_implicit_po_candidates
from src.extraction.llm_extractor import extract_invoice_data
from src.ingestion.document_router import extract_document

pdf_path = (
    r"C:\Users\sansi\Downloads\InvoiceIQ_missing_PO_ambiguous_match_fresh_051.pdf"
)

document = extract_document(pdf_path)
invoice = extract_invoice_data(document["full_text"])

purchase_orders_df = pd.read_csv("data/purchase_orders.csv")

result = find_implicit_po_candidates(
    vendor_id="V002",
    invoice_items=invoice.items,
    purchase_orders_df=purchase_orders_df
)

print("\n========== IMPLICIT PO MATCHING DIAGNOSTIC ==========")

print("\nInvoice description:")
for item in invoice.items:
    print(item.description)

print("\nCandidates:")
for candidate in result["candidates"]:
    print(candidate)

print("\nMatching status:", result["status"])
print("Message:", result["message"])

print("\n=====================================================")

assert result["candidates"], "No PO candidates were found."

po_ids = {
    candidate["po_id"]
    for candidate in result["candidates"]
}

print("\nPO IDs found:", po_ids)
