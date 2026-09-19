"""PersonProfile serialization."""

from system_one.profile import PersonProfile


def test_profile_dump_omits_unset_and_keeps_set_values() -> None:
    base = PersonProfile(name="Alex Jordan")
    assert base.dumped() == {"name": "Alex Jordan"}

    updated = base.model_copy(update={"race": "Asian", "disability": "yes"})
    assert updated.dumped() == {
        "name": "Alex Jordan",
        "race": "Asian",
        "disability": "yes",
    }

    cleared = updated.model_copy(update={"race": None})
    assert "race" not in cleared.dumped()
    assert cleared.dumped()["disability"] == "yes"
