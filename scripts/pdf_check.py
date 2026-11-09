from src.ingestion.pdf_reader import extract_pdf_text


pdf_path = input("Enter the invoice PDF path: ").strip().strip('"')

result = extract_pdf_text(pdf_path)

print("\n========== PDF DETAILS ==========")

print("File:", result["file_name"])
print("Pages:", result["page_count"])
print("Document type:", result["document_type"])
print("Total characters:", result["total_characters"])
print("SHA-256:", result["file_hash"])

print("\n========== EXTRACTED TEXT ==========")

for page in result["pages"]:
    print(f"\n--- PAGE {page['page_number']} ---")
    print(page["text"])