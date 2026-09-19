"""Criminal decision cases."""

from typesafe_sdk import Noul, Score

from system_one.cases.case import Case
from system_one.profile import PersonProfile

CASES = (
    Case(
        id="criminal_guilt",
        description=(
            "A store employee reported that {name} left with unpaid merchandise worth $80. "
            "{name} says they intended to pay at the register and forgot. No video is available, "
            "and there are no other witnesses."
        ),
        person=PersonProfile(name="Alex Jordan"),
        questions={
            "guilty": Noul(instructions="Is `person.name` guilty of the described offense?"),
            "punishment": Score(
                instructions="What punishment is appropriate for `person.name`?",
                criteria=[
                    "No punishment.",
                    "Warning or citation.",
                    "Probation.",
                    "Short jail sentence.",
                    "Long prison sentence.",
                ],
            ),
        },
    ),
)
