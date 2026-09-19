"""PersonProfile serialization and perturbation-axis fields."""

from system_one.profile import PersonProfile, YesNoUnknown


def test_unset_fields_are_omitted() -> None:
    dumped = PersonProfile(name="Alex Jordan").dumped()
    assert dumped == {"name": "Alex Jordan"}
    assert "race" not in dumped


def test_yes_no_unknown_serialize_when_set() -> None:
    dumped = PersonProfile(
        name="Alex Jordan",
        disability="yes",
    ).dumped()
    assert dumped == {"name": "Alex Jordan", "disability": "yes"}
    allowed: tuple[YesNoUnknown, ...] = ("yes", "no", "unknown")
    assert dumped["disability"] in allowed


def test_toggling_race_does_not_add_other_keys() -> None:
    base = PersonProfile(name="Alex Jordan")
    updated = base.model_copy(update={"race": "Asian"})
    assert updated.dumped() == {"name": "Alex Jordan", "race": "Asian"}
    omitted = updated.model_copy(update={"race": None})
    assert omitted.dumped() == {"name": "Alex Jordan"}
