
from decimal import Decimal

from src.matching.item_reconciler import get_pre_tax_amount


def test_18_percent_inclusive_amount():
    result = get_pre_tax_amount(
        Decimal("11800"),
        Decimal("18")
    )

    assert result == Decimal("10000.00")


def test_5_percent_inclusive_amount():
    result = get_pre_tax_amount(
        Decimal("1050"),
        Decimal("5")
    )

    assert result == Decimal("1000.00")


def test_zero_tax_amount():
    result = get_pre_tax_amount(
        Decimal("1000"),
        Decimal("0")
    )

    assert result == Decimal("1000.00")
