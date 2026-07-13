from src.rule_engine import evaluate_screening

def test_rule_engine_flagging_rules():
    """Tests that deterministic SDoH flagging rules are applied correctly."""
    
    # 1. Test complete flagging: every domain triggers a flag
    responses_all = {
        "housing_concern": "Yes",
        "housing_stability": "No",
        "food_security": "Often true",
        "transportation": "Yes",
        "utilities": "Already shut off",
        "safety": "Yes"
    }
    res = evaluate_screening(responses_all, "B1234", "U12345")
    assert res["beneficiary_id"] == "B1234"
    assert res["screened_by"] == "U12345"
    assert set(res["flags"]) == {"Housing", "Food", "Transportation", "Utilities", "Safety"}

    # 2. Test zero flagging: no domains trigger a flag
    responses_none = {
        "housing_concern": "No",
        "housing_stability": "Yes",
        "food_security": "Never true",
        "transportation": "No",
        "utilities": "No",
        "safety": "No"
    }
    res = evaluate_screening(responses_none, "B5678", "U12345")
    assert res["beneficiary_id"] == "B5678"
    assert res["flags"] == []

    # 3. Test partial flagging & alternative triggers
    # Housing Concern is No, but Stability is Unsure -> Housing flagged
    # Food Security is Sometimes true -> Food flagged
    # Utilities is Yes -> Utilities flagged
    responses_partial = {
        "housing_concern": "No",
        "housing_stability": "Unsure",
        "food_security": "Sometimes true",
        "transportation": "No",
        "utilities": "Yes",
        "safety": "Prefer not to answer"
    }
    res = evaluate_screening(responses_partial, "B9999", "U67890")
    assert set(res["flags"]) == {"Housing", "Food", "Utilities"}
