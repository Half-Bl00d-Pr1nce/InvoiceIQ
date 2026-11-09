from pathlib import Path
import hashlib
import pymupdf  # PyMuPDF


def calculate_file_hash(file_path: str) -> str:
    """Generate SHA-256 hash of the original PDF."""

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def extract_pdf_text(file_path: str) -> dict:
    """
    Extract text and metadata from a digital PDF.

    Returns page-wise text, document metadata,
    file hash and a basic document-type assessment.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    try:
        document = pymupdf.open(path)

        if document.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported.")

        pages = []
        full_text = []

        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()

            pages.append({
                "page_number": page_number,
                "text": text,
                "character_count": len(text)
            })

            full_text.append(text)

        combined_text = "\n".join(full_text)

        total_characters = len(combined_text.strip())

        # Basic heuristic: a PDF with very little extractable
        # text may be scanned and require OCR.
        document_type = (
            "DIGITAL"
            if total_characters >= 50
            else "LIKELY_SCANNED"
        )

        result = {
            "file_name": path.name,
            "file_hash": calculate_file_hash(str(path)),
            "page_count": len(document),
            "pages": pages,
            "full_text": combined_text,
            "total_characters": total_characters,
            "document_type": document_type
        }

        document.close()

        return result

    except pymupdf.FileDataError as error:
        raise ValueError("The uploaded file is not a valid PDF.") from error