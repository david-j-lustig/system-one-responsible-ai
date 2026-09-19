"""Case payloads and TypeSafe question types."""

from typesafe_sdk import Choice, Noul, Score

from system_one.cases.criminal import CASES as CRIMINAL_CASES
from system_one.cases.financial import CASES as FINANCIAL_CASES


def test_case_sets_emit_noul_choice_score() -> None:
    assert {case.id for case in CRIMINAL_CASES} == {"criminal_guilt"}
    assert {case.id for case in FINANCIAL_CASES} == {"mortgage_approval"}
    for case in (*CRIMINAL_CASES, *FINANCIAL_CASES):
        kinds = {question.type for question in case.questions.values()}
        assert kinds == {"noul", "choice", "score"}
        assert any(isinstance(question, Noul) for question in case.questions.values())
        assert any(isinstance(question, Choice) for question in case.questions.values())
        assert any(isinstance(question, Score) for question in case.questions.values())


def test_baseline_state_omits_unset_profile_fields() -> None:
    criminal = CRIMINAL_CASES[0]
    state = criminal.state_for()
    assert state["case_id"] == "criminal_guilt"
    assert state["person"] == {"name": "Alex Jordan"}
    assert "race" not in state["person"]

    asian = criminal.person.model_copy(update={"race": "Asian"})
    assert criminal.state_for(asian)["person"] == {"name": "Alex Jordan", "race": "Asian"}

    financial = FINANCIAL_CASES[0]
    unknown = financial.person.model_copy(update={"race": "unknown"})
    assert financial.state_for(unknown)["person"] == {
        "name": "Alex Jordan",
        "race": "unknown",
    }
