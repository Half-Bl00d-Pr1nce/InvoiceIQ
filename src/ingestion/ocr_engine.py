import os
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image


# Optional explicit path for Windows installations.
# Set TESSERACT_CMD if tesseract.exe is not available on PATH.
tesseract_path = os.getenv("TESSERACT_CMD")

if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path


def extract_page_with_ocr(
    file_path: str,
    page_number: int,
    dpi: int = 300
) -> dict:
    """
    Render a PDF page as an image and extract text using Tesseract.

    page_number is zero-indexed internally.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    document = pymupdf.open(path)

    if page_number < 0 or page_number >= len(document):
        document.close()
        raise IndexError("Invalid PDF page number.")

    page = document.load_page(page_number)

    # Convert the PDF page into a high-resolution image.
    zoom = dpi / 72
    matrix = pymupdf.Matrix(zoom, zoom)

    pixmap = page.get_pixmap(
        matrix=matrix,
        colorspace=pymupdf.csRGB,
        alpha=False
    )

    image = Image.frombytes(
        "RGB",
        [pixmap.width, pixmap.height],
        pixmap.samples
    )

    # OCR using Tesseract.
    text = pytesseract.image_to_string(
        image,
        config="--psm 6"
    ).strip()

    document.close()

    return {
        "page_number": page_number + 1,
        "text": text,
        "character_count": len(text),
        "source": "OCR"
    }