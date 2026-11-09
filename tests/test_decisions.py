
from src.decision.rules_engine import make_decision
from src.decision.explanation import generate_explanation


def valid_results():
    return {
        "duplicate": {"status": "PASS"},
        "vendor": {"status": "PASS"},
        "po": {"status": "PASS"},
        "financial": {"status": "PASS"},
        "item_reconciliation": {"status": "PASS"},
        "extraction": {"status": "PASS"}
    }


def test_all_checks_pass():
    result = make_decision(valid_results())

    assert result["status"] == "APPROVED"


def test_duplicate_causes_rejection():
    results = valid_results()
    results["duplicate"] = {
        "status": "FAIL",
        "message": "Duplicate invoice detected."
    }

    result = make_decision(results)

    assert result["status"] == "REJECTED"


def test_unknown_vendor_causes_rejection():
    results = valid_results()
    results["vendor"] = {
        "status": "FAIL",
        "message": "Vendor is not registered."
    }

    result = make_decision(results)

    assert result["status"] == "REJECTED"


def test_ambiguous_po_requires_review():
    results = valid_results()
    results["po"] = {
        "status": "REVIEW",
        "message": "Multiple PO candidates found."
    }

    result = make_decision(results)

    assert result["status"] == "PENDING_REVIEW"


def test_financial_failure_requires_review():
    results = valid_results()
    results["financial"] = {
        "status": "FAIL",
        "message": "Invoice total does not match."
    }

    result = make_decision(results)

    assert result["status"] == "PENDING_REVIEW"


def test_missing_check_requires_review():
    results = valid_results()
    del results["duplicate"]

    result = make_decision(results)

    assert result["status"] == "PENDING_REVIEW"


def test_explanation_contains_reasons():
    results = valid_results()
    results["po"] = {
        "status": "REVIEW",
        "message": "PO match is ambiguous."
    }

    decision = make_decision(results)
    explanation = generate_explanation(decision)

    assert explanation["status"] == "PENDING_REVIEW"
    assert "PO match is ambiguous." in explanation["reasons"]
