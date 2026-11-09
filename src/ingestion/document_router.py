from pathlib import Path

import pymupdf

from src.ingestion.pdf_reader import (
    calculate_file_hash
)

from src.ingestion.ocr_engine import (
    extract_page_with_ocr
)


MIN_DIGITAL_CHARACTERS = 30


def extract_document(file_path: str) -> dict:
    """
    Extract text from every PDF page.

    Pages with sufficient embedded text use PyMuPDF.
    Pages with insufficient embedded text use Tesseract OCR.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    document = pymupdf.open(path)

    if document.is_encrypted:
        document.close()
        raise ValueError("Encrypted PDFs are not supported.")

    extracted_pages = []

    for index, page in enumerate(document):
        digital_text = page.get_text("text").strip()

        if len(digital_text) >= MIN_DIGITAL_CHARACTERS:
            extracted_pages.append({
                "page_number": index + 1,
                "text": digital_text,
                "character_count": len(digital_text),
                "source": "DIGITAL"
            })

        else:
            # Fall back to OCR for this individual page.
            extracted_pages.append(
                extract_page_with_ocr(
                    file_path=str(path),
                    page_number=index
                )
            )

    document.close()

    full_text = "\n\n".join(
        page["text"] for page in extracted_pages
    )

    sources = {
        page["source"] for page in extracted_pages
    }

    if sources == {"DIGITAL"}:
        document_type = "DIGITAL"

    elif sources == {"OCR"}:
        document_type = "SCANNED"

    else:
        document_type = "MIXED"

    return {
        "file_name": path.name,
        "file_hash": calculate_file_hash(str(path)),
        "page_count": len(extracted_pages),
        "pages": extracted_pages,
        "full_text": full_text,
        "total_characters": len(full_text),
        "document_type": document_type
    }