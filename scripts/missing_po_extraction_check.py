from src.ingestion.pdf_reader import extract_pdf_text
from src.extraction.llm_extractor import extract_invoice_data

pdf_path = r"C:\Users\sansi\Downloads\InvoiceIQ_missing_PO_ambiguous_match_test.pdf"

# Extract text from the PDF
document = extract_pdf_text(pdf_path)

# Run LLM extraction using 'full_text'
invoice = extract_invoice_data(document["full_text"])

print("\n========== EXTRACTION RESULTS ==========")

print("Vendor Name:", invoice.vendor.vendor_name)
print("Vendor ID:", invoice.vendor.vendor_id)
print("GSTIN:", invoice.vendor.tax_id)
print("PO Number:", invoice.po_number)
print("Invoice Number:", invoice.invoice_number)
print("Tax Rate:", invoice.items[0].tax_rate)
print("Tax Treatment:", invoice.tax_treatment)

print("========================================")