from pathlib import Path

from src.database import db
from src.database.db import initialize_database, migrate_database
from src.database.repository import load_reference_data
from src.pipeline import process_invoice


# --------------------------------------------------
# 1. USE AN ISOLATED TEST DATABASE
# --------------------------------------------------

test_db_path = Path("data/invoiceiq_edge4_test.db")
test_db_path.parent.mkdir(parents=True, exist_ok=True)

# Delete only the dedicated test database from an earlier run.
if test_db_path.exists():
    test_db_path.unlink()

db.DB_PATH = test_db_path

# Initialise schema and reference data.
initialize_database()
migrate_database()
load_reference_data()


# --------------------------------------------------
# 2. RUN THE BUNDLED INVOICE
# --------------------------------------------------

pdf_path = (
    Path(__file__).resolve().parent
    / "sample_invoices"
    / "InvoiceIQ_Bundled_Test_INV-BUNDLE-001.pdf"
)

result = process_invoice(pdf_path)


# --------------------------------------------------
# 3. DISPLAY RESULTS
# --------------------------------------------------

print("\n--- DOCUMENT DETAILS ---")
print("File:", result["file_name"])
print("Type:", result["document"]["document_type"])

print("\n--- EXTRACTED INVOICE ---")
print(result["invoice_data"].model_dump())

print("\n--- VENDOR VALIDATION ---")
print(result["vendor_validation"])

print("\n--- PO VALIDATION ---")
print(result["po_validation"])

print("\n--- FINANCIAL VALIDATION ---")
print(result["financial_validation"])

print("\n--- ITEM RECONCILIATION ---")
print(result["item_reconciliation"])

print("\n--- DUPLICATE VALIDATION ---")
print(result["duplicate_validation"])

print("\n--- NORMALISED VALIDATION RESULTS ---")
print(result["validation_results"])

print("\n--- FINAL DECISION ---")
print(result["decision"])

print("\n--- DECISION EXPLANATION ---")
print(result["explanation"])

print("\n--- DATABASE PERSISTENCE ---")
print("Invoice ID:", result["invoice_id"])
print("Final status:", result["decision"]["status"])
print("Test database:", test_db_path)