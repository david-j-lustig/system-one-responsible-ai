"""Case payloads and TypeSafe question types."""

from system_one.cases import CASES
from system_one.cases.financial import CASES as FINANCIAL
from system_one.cases.financial import LOAN_PROFILE_FIELDS, PRODUCTS, PROFILES


def test_every_case_has_noul_and_score() -> None:
    assert CASES
    for case in CASES:
        kinds = {question.type for question in case.questions.values()}
        assert "noul" in kinds
        assert "score" in kinds


def test_state_sends_profile_json_and_fills_name() -> None:
    for case in CASES:
        assert "{name}" in case.description
        state = case.state_for()
        assert case.person.name in state["description"]
        assert state["person"] == case.person.dumped()

        person = case.person.model_copy(update={"name": "Pat Lee", "race": "Asian"})
        updated = case.state_for(person)
        assert updated["person"]["name"] == "Pat Lee"
        assert updated["person"]["race"] == "Asian"


def test_financial_cases_cross_products_and_profiles() -> None:
    assert len(PRODUCTS) == 10
    assert len(PROFILES) == 10
    assert len(FINANCIAL) == 100
    assert {product.kind for product in PRODUCTS} == {"mortgage", "auto", "business"}
    for profile in PROFILES.values():
        for field in LOAN_PROFILE_FIELDS:
            assert getattr(profile, field) is not None
