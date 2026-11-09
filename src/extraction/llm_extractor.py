
import re
import ollama

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


def extract_invoice_data(invoice_text: str) -> InvoiceData:

    if not invoice_text or not invoice_text.strip():
        raise ValueError("Invoice text is empty.")

    response = ollama.chat(
        model="qwen2.5:1.5b",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(
                    invoice_text=invoice_text
                )
            }
        ],
        format=InvoiceData.model_json_schema(),
        options={
            "temperature": 0
        }
    )

    extracted_json = response.message.content

    # Validate the LLM response using Pydantic
    invoice = InvoiceData.model_validate_json(extracted_json)

    # Clean common extraction mistakes deterministically
    invoice = clean_extracted_items(invoice)

    return invoice
