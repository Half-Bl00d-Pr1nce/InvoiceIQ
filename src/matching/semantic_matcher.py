
import re
from difflib import SequenceMatcher


STOP_WORDS = {
    "the", "and", "for", "with", "of", "to",
    "a", "an", "in", "on", "set", "assembly",
    "pack", "product", "item"
}


def tokenize(text):
    """Normalize text and extract meaningful tokens."""

    if not text:
        return set()

    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())

    return {
        token for token in tokens
        if token not in STOP_WORDS and len(token) > 1
    }



def calculate_similarity(invoice_description, po_description):
    """
    Calculate directional lexical similarity using:
    1. Invoice token coverage
    2. Sequence similarity

    Token coverage measures how much of the invoice
    description is represented in the PO description.
    """

    invoice_tokens = tokenize(invoice_description)
    po_tokens = tokenize(po_description)

    if not invoice_tokens or not po_tokens:
        return 0.0

    intersection = invoice_tokens.intersection(po_tokens)

    # How much of the invoice description is covered?
    coverage_score = len(intersection) / len(invoice_tokens)

    sequence_score = SequenceMatcher(
        None,
        invoice_description.lower(),
        po_description.lower()
    ).ratio()

    return round(
        0.7 * coverage_score + 0.3 * sequence_score,
        4
    )



def find_po_candidates(invoice_description, po_items, top_k=5):
    """
    Rank PO items against an invoice description.

    This function suggests candidates only.
    It does not approve or allocate bundled items.
    """

    candidates = []

    for _, po_item in po_items.iterrows():

        po_description = str(po_item["description"])

        score = calculate_similarity(
            invoice_description,
            po_description
        )

        if score > 0:
            candidates.append({
                "po_id": po_item.get("po_id"),
                "po_item_id": po_item.get("po_item_id"),
                "item_code": po_item.get("item_code"),
                "description": po_description,
                "similarity_score": score
            })

    candidates.sort(
        key=lambda item: item["similarity_score"],
        reverse=True
    )

    return candidates[:top_k]


def find_bundle_component_candidates(bundle_description, po_items, top_k=10):
    """
    Identify PO items that may be components of a bundled
    invoice line.

    This generates suggestions only. It does not allocate
    quantities or approve the invoice.
    """
    bundle_tokens = tokenize(bundle_description)

    if not bundle_tokens:
        return []

    candidates = []

    for _, po_item in po_items.iterrows():
        po_description = str(po_item["description"])
        po_tokens = tokenize(po_description)

        if not po_tokens:
            continue

        common_tokens = bundle_tokens.intersection(po_tokens)

        if not common_tokens:
            continue

        # Measures how much of the PO description is
        # represented in the bundled invoice description.
        score = len(common_tokens) / len(po_tokens)

        candidates.append({
            "po_id": po_item.get("po_id"),
            "po_item_id": po_item.get("po_item_id"),
            "item_code": po_item.get("item_code"),
            "description": po_description,
            "matched_terms": sorted(common_tokens),
            "similarity_score": round(score, 4)
        })

    candidates.sort(
        key=lambda item: item["similarity_score"],
        reverse=True
    )

    return candidates[:top_k]

