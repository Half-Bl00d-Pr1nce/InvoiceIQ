import src.extraction.llm_extractor as extractor

sample_invoice = """
TAX INVOICE

Vendor: ABC Technologies Pvt Ltd
Invoice Number: INV-2026-001
Invoice Date: 08-11-2026
Due Date: 08-12-2026
PO Number: PO-1001

Bill To: XYZ Corporation

Items:
1. Laptop - Quantity: 2 - Unit Price: 50000
2. Mouse - Quantity: 2 - Unit Price: 1000

Subtotal: 102000
Tax: 18%
Total Amount: 120360
Currency: INR
"""

# Simulate Ollama being unavailable to test Groq fallback.
def simulate_ollama_failure(*args, **kwargs):
    raise RuntimeError("Simulated Ollama unavailability")

extractor.generate_with_ollama = simulate_ollama_failure

try:
    print("Testing InvoiceIQ integrated extraction...")

    invoice, backend = extractor.extract_invoice_data_with_backend(
        sample_invoice
    )

    print("\nExtraction successful!")
    print("Backend used:", backend)
    print("Vendor:", invoice.vendor.vendor_name)
    print("Invoice Number:", invoice.invoice_number)
    print("Total Amount:", invoice.total_amount)

except Exception as e:
    print("\nIntegrated extraction failed:")
    print(type(e).__name__, str(e))