
import pandas as pd

from src.matching.semantic_matcher import (
    calculate_similarity,
    find_po_candidates
)


def test_identical_descriptions():
    score = calculate_similarity(
        "Industrial Steel Bolt M10",
        "Industrial Steel Bolt M10"
    )

    assert score == 1.0


def test_similar_descriptions():
    score = calculate_similarity(
        "Steel Bolt M10",
        "Industrial Steel Bolt M10"
    )

    assert score > 0


def test_unrelated_descriptions():
    score = calculate_similarity(
        "Electrical Copper Cable",
        "Industrial Steel Bolt"
    )

    assert score < 0.5


def test_candidate_ranking():
    po_items = pd.DataFrame([
        {
            "po_item_id": "PO-1",
            "item_code": "BOLT",
            "description": "Industrial Steel Bolt M10"
        },
        {
            "po_item_id": "PO-2",
            "item_code": "CABLE",
            "description": "Electrical Copper Cable"
        }
    ])

    candidates = find_po_candidates(
        "Steel Bolt M10",
        po_items
    )

    assert len(candidates) == 2
    assert candidates[0]["item_code"] == "BOLT"
