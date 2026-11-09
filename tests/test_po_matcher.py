
import pandas as pd
import pytest

from src.matching.po_matcher import match_purchase_order


@pytest.fixture
def purchase_orders_df():
    return pd.read_csv("data/purchase_orders.csv")


def test_valid_po(purchase_orders_df):
    result = match_purchase_order("PO-1001", "V001", purchase_orders_df)
    assert result["status"] == "PASS"


def test_nonexistent_po(purchase_orders_df):
    result = match_purchase_order("PO-9999", "V001", purchase_orders_df)
    assert result["status"] == "FAIL"


def test_vendor_mismatch(purchase_orders_df):
    result = match_purchase_order("PO-1001", "V002", purchase_orders_df)
    assert result["status"] == "FAIL"


def test_case_insensitive_po_matching(purchase_orders_df):
    result = match_purchase_order("po-1001", "V001", purchase_orders_df)
    assert result["status"] == "PASS"


def test_missing_po_number(purchase_orders_df):
    result = match_purchase_order("", "V001", purchase_orders_df)
    assert result["status"] == "NOT_CHECKED"


def test_closed_po(purchase_orders_df):
    closed_pos = purchase_orders_df.copy()
    closed_pos.loc[
        closed_pos["po_id"] == "PO-1001", "status"
    ] = "CLOSED"

    result = match_purchase_order("PO-1001", "V001", closed_pos)
    assert result["status"] == "FAIL"
