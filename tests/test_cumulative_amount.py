
from src.validation.financial_checks import (
    validate_cumulative_po_amount
)


def validate(
    approved=0,
    pending=0,
    current=0
):
    return validate_cumulative_po_amount(
        po_amount_paise=10_000_000,  # ₹1,00,000
        approved_amount_paise=approved,
        pending_amount_paise=pending,
        current_amount_paise=current,
        tolerance_percentage=2.0,
        tolerance_absolute_paise=10_000  # ₹100
    )


def test_amount_within_po():
    result = validate(current=9_900_000)
    assert result["status"] == "PASS"


def test_amount_within_absolute_tolerance():
    result = validate(current=10_005_000)
    assert result["status"] == "PASS"


def test_amount_at_tolerance_boundary():
    result = validate(current=10_010_000)
    assert result["status"] == "PASS"


def test_amount_exceeds_tolerance():
    result = validate(current=10_050_000)
    assert result["status"] == "REVIEW"


def test_pending_amount_creates_review():
    result = validate(
        approved=9_500_000,
        pending=100_000,
        current=500_000
    )
    assert result["status"] == "REVIEW"


def test_previous_approved_amount_already_exceeds_limit():
    result = validate(
        approved=10_020_000,
        current=100_000
    )
    assert result["status"] == "FAIL"
