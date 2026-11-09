
import pandas as pd

from src.matching.semantic_matcher import (
    find_bundle_component_candidates
)


def test_explicit_bundle_identifies_components():

    po_items = pd.DataFrame([
        {
            "po_id": "PO-2001",
            "po_item_id": "LINE-1",
            "item_code": "BOLT-M10",
            "description": "Steel Bolt M10"
        },
        {
            "po_id": "PO-2001",
            "po_item_id": "LINE-2",
            "item_code": "NUT-M10",
            "description": "Steel Nut M10"
        },
        {
            "po_id": "PO-2001",
            "po_item_id": "LINE-3",
            "item_code": "WASHER-M10",
            "description": "Steel Washer M10"
        }
    ])

    candidates = find_bundle_component_candidates(
        "Bolt, Nut and Washer Kit",
        po_items
    )

    matched_codes = {
        candidate["item_code"]
        for candidate in candidates
    }

    assert "BOLT-M10" in matched_codes
    assert "NUT-M10" in matched_codes
    assert "WASHER-M10" in matched_codes


def test_generic_bundle_does_not_force_component_mapping():

    po_items = pd.DataFrame([
        {
            "po_id": "PO-2001",
            "po_item_id": "LINE-1",
            "item_code": "BOLT-M10",
            "description": "Steel Bolt M10"
        },
        {
            "po_id": "PO-2001",
            "po_item_id": "LINE-2",
            "item_code": "NUT-M10",
            "description": "Steel Nut M10"
        }
    ])

    candidates = find_bundle_component_candidates(
        "Industrial Assembly Kit",
        po_items
    )

    assert candidates == []
