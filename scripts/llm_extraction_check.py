
from src.ingestion.document_router import extract_document
from src.extraction.llm_extractor import extract_invoice_data


PDF_PATH = r"C:\Users\sansi\Downloads\Invoice_BioHue_Chemicals_102.pdf"


# Step 1: Extract text from the PDF
document = extract_document(PDF_PATH)

print("Document type:", document["document_type"])
print("Characters extracted:", document["total_characters"])


# Step 2: Extract structured invoice information
invoice_text = ""

for page in document["pages"]:
    invoice_text += (
        f"\n--- PAGE {page['page_number']} ---\n"
        f"{page['text']}\n"
    )

invoice = extract_invoice_data(invoice_text)


# Step 3: Display the extracted information
print("\n========== EXTRACTED INVOICE ==========")

print(invoice.model_dump_json(indent=4))
