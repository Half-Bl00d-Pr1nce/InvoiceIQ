
def generate_explanation(decision):
    """Generate a human-readable explanation of the final decision."""

    status = decision["status"]

    if status == "APPROVED":
        explanation = (
            "Invoice approved. All mandatory validation checks passed."
        )

    elif status == "REJECTED":
        explanation = (
            "Invoice rejected because one or more rejection conditions "
            "were detected."
        )

    else:
        explanation = (
            "Invoice requires human review before a final decision "
            "can be made."
        )

    reasons = (
        decision.get("rejection_reasons", [])
        + decision.get("review_reasons", [])
    )

    return {
        "status": status,
        "summary": explanation,
        "reasons": reasons,
        "checks": decision.get("validation_results", {})
    }
