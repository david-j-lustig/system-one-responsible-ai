"""Case payloads and TypeSafe question types."""

from system_one.cases import CASES
from system_one.cases.financial import BORROWER_NAME, LOAN_PROFILE_FIELDS, PRODUCTS, PROFILES
from system_one.cases.financial import CASES as FINANCIAL


def test_every_case_has_noul_and_score() -> None:
    assert CASES
    for case in CASES:
        kinds = {question.type for question in case.questions.values()}
        assert "noul" in kinds
        assert "score" in kinds


def test_description_templates_name_from_profile() -> None:
    for case in CASES:
        assert "{name}" in case.description
        assert case.person.name
        assert case.person.name not in case.description
        state = case.state_for()
        assert "case_id" not in state
        assert case.person.name in state["description"]
        assert state["person"] == case.person.dumped()

        renamed = case.person.model_copy(update={"name": "Pat Lee", "race": "Asian"})
        updated = case.state_for(renamed)
        assert "Pat Lee" in updated["description"]
        assert case.person.name not in updated["description"]
        assert updated["person"]["name"] == "Pat Lee"
        assert updated["person"]["race"] == "Asian"


def test_financial_cases_are_products_times_profiles() -> None:
    assert len(LOAN_PROFILE_FIELDS) == 10
    assert len(PRODUCTS) == 10
    assert len(PROFILES) == 10
    assert len(FINANCIAL) == 100
    assert [product.id for product in PRODUCTS] == [
        "mortgage_approval",
        "fha_mortgage",
        "jumbo_mortgage",
        "refinance_mortgage",
        "new_auto_loan",
        "used_auto_loan",
        "auto_refinance",
        "sba_working_capital",
        "equipment_loan",
        "startup_business_loan",
    ]
    assert {product.kind for product in PRODUCTS} == {"mortgage", "auto", "business"}
    assert sum(product.kind == "mortgage" for product in PRODUCTS) == 4
    assert sum(product.kind == "auto" for product in PRODUCTS) == 3
    assert sum(product.kind == "business" for product in PRODUCTS) == 3
    assert [case.id for case in FINANCIAL] == [
        f"{product.id}__{profile_id}" for product in PRODUCTS for profile_id in PROFILES
    ]
    assert len({case.id for case in FINANCIAL}) == 100


def test_loan_profiles_are_sent_as_json() -> None:
    average = next(case for case in FINANCIAL if case.id == "mortgage_approval__average")
    dumped = average.person.dumped()
    for field in LOAN_PROFILE_FIELDS:
        assert dumped.get(field) is not None
    assert dumped["name"] == BORROWER_NAME
    assert dumped["annual_income"] == 85_000
    assert dumped["credit_score"] == 700

    state = average.state_for()
    assert state["person"] == dumped
    assert "credit_score" not in average.description
    assert "annual_income" not in average.description
    assert "Credit score" not in state["description"]

    with_race = average.state_for(average.person.model_copy(update={"race": "White"}))
    assert with_race["person"] == {**dumped, "race": "White"}
    assert "White" not in with_race["description"]
