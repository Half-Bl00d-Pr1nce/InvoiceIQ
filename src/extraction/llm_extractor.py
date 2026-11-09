
import re
from src.extraction.llm_client import (
    generate_with_ollama,
    generate_with_groq
)

from src.extraction.schemas import InvoiceData
from src.extraction.prompts import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE
)


def clean_extracted_items(invoice: InvoiceData) -> InvoiceData:
    """
    Remove financial summary/tax rows mistakenly extracted
    as invoice items and normalize missing item codes.
    """

    summary_patterns = [
        r"^(?:cgst|sgst|igst|utgst)\b",
        r"^(?:total\s+tax|tax\s+total|total\s+gst)\b",
        r"^(?:invoice\s+total|grand\s+total|total\s+amount)\b",
        r"^(?:amount\s+payable|net\s+payable|balance\s+due)\b",
        r"^(?:sub\s*total|subtotal)\b"
    ]

    genuine_items = []

    for item in invoice.items:

        description = (item.description or "").strip()
        item_code = (item.item_code or "").strip()

        # Check both fields because the LLM may copy
        # a summary label into either one.
        combined_text = f"{description} {item_code}".lower()

        is_summary_row = any(
            re.search(pattern, combined_text, re.IGNORECASE)
            for pattern in summary_patterns
        )

        if is_summary_row:
            continue

        # If item_code is merely a copy of description,
        # treat the item code as missing.
        if (
            item_code
            and description
            and item_code.casefold() == description.casefold()
        ):
            item.item_code = None

        genuine_items.append(item)

    invoice.items = genuine_items

    return invoice


def extract_invoice_data_with_backend(invoice_text: str):
    if not invoice_text or not invoice_text.strip():
        raise ValueError("Invoice text is empty.")

    user_prompt = USER_PROMPT_TEMPLATE.format(
        invoice_text=invoice_text
    )

    schema = InvoiceData.model_json_schema()

    # First attempt: local Ollama
    try:
        extracted_json = generate_with_ollama(
            SYSTEM_PROMPT,
            user_prompt,
            schema
        )

        invoice = InvoiceData.model_validate_json(extracted_json)
        backend_used = "ollama"

    except Exception as ollama_error:
        # Second attempt: Groq
        try:
            extracted_json = generate_with_groq(
                SYSTEM_PROMPT,
                user_prompt,
                schema
            )

            invoice = InvoiceData.model_validate_json(extracted_json)
            backend_used = "groq"

        except Exception as groq_error:
            raise RuntimeError(
                f"Invoice extraction failed with both Ollama and Groq.\n"
                f"Ollama error: {ollama_error}\n"
                f"Groq error: {groq_error}"
            ) from groq_error

    invoice = clean_extracted_items(invoice)

    return invoice, backend_used


def extract_invoice_data(invoice_text: str) -> InvoiceData:
    """Backward-compatible function used by the existing pipeline."""

    invoice, _ = extract_invoice_data_with_backend(invoice_text)

    return invoice
