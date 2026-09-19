"""Case payloads and TypeSafe question types."""

from system_one.cases import CASES


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
        assert state["person"] == {"name": case.person.name}

        renamed = case.person.model_copy(update={"name": "Pat Lee", "race": "Asian"})
        updated = case.state_for(renamed)
        assert "Pat Lee" in updated["description"]
        assert case.person.name not in updated["description"]
        assert updated["person"] == {"name": "Pat Lee", "race": "Asian"}
