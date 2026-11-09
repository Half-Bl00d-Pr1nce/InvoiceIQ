
from datetime import date
from decimal import Decimal
from typing import Optional, Literal
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_validator
)


class FieldEvidence(BaseModel):
    """
    Records where an extracted value came from.
    Helps explain and audit extraction results.
    """
    page_number: Optional[int] = None
    supporting_text: Optional[str] = None


class VendorDetails(BaseModel):
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    tax_id: Optional[str] = None
    vendor_id: Optional[str] = None

    @field_validator("vendor_name", "vendor_address", "tax_id", "vendor_id", mode="before")
    @classmethod
    def normalize_missing_strings(cls, value):
        if isinstance(value, str):
            if value.strip().lower() in {"null", "none", "n/a", ""}:
                return None

        return value


class InvoiceItem(BaseModel):
    item_code: Optional[str] = None
    description: Optional[str] = None

    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    line_amount: Optional[Decimal] = None

    tax_rate: Optional[Decimal] = None


class InvoiceData(BaseModel):
    # Allows optional fields and additional extracted fields
    model_config = ConfigDict(extra="allow")

    vendor: VendorDetails = Field(default_factory=VendorDetails)

    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None

    po_number: Optional[str] = None
    currency: Optional[str] = None

    items: list[InvoiceItem] = Field(default_factory=list)

    subtotal: Optional[Decimal] = None
    shipping: Optional[Decimal] = None
    discount: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None

    tax_treatment: Literal[
        "INCLUSIVE",
        "EXCLUSIVE",
        "UNKNOWN"
    ] = "UNKNOWN"

    # Evidence for important extracted fields
    evidence: dict[str, FieldEvidence] = Field(default_factory=dict)
