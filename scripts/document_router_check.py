from src.ingestion.document_router import extract_document


pdf_path = input("Enter PDF path: ").strip().strip('"')

result = extract_document(pdf_path)

print("\n========== DOCUMENT DETAILS ==========")

print("File:", result["file_name"])
print("Pages:", result["page_count"])
print("Document type:", result["document_type"])
print("Total characters:", result["total_characters"])
print("SHA-256:", result["file_hash"])

print("\n========== PAGE EXTRACTION ==========")

for page in result["pages"]:

    print(f"\n--- PAGE {page['page_number']} ---")

    print("Extraction method:", page["source"])
    print("Characters:", page["character_count"])
    print(page["text"])