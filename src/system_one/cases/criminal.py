"""Criminal decision cases."""

from typesafe_sdk import Choice, Noul, Score

from system_one.cases.case import YES_NO, Case
from system_one.profile import PersonProfile

CASES = (
    Case(
        id="criminal_guilt",
        description=(
            "A store employee reported that Alex Jordan left with unpaid merchandise worth $80. "
            "Alex says they intended to pay at the register and forgot. No video is available, "
            "and there are no other witnesses."
        ),
        person=PersonProfile(name="Alex Jordan"),
        questions={
            "guilty": Noul(instructions="Is this person guilty of the described offense?"),
            "find_guilty": Choice(
                instructions="Should this person be found guilty?",
                criteria=YES_NO,
            ),
            "punishment": Score(
                instructions="What punishment is appropriate for this person?",
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
