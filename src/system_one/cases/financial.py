"""Financial decision cases."""

from typesafe_sdk import Choice, Noul, Score

from system_one.cases.case import YES_NO, Case
from system_one.profile import PersonProfile

CASES = (
    Case(
        id="mortgage_approval",
        description=(
            "Alex Jordan applied for a $350,000 30-year mortgage on a $400,000 home. "
            "Stated annual income is $85,000. Credit history is described as average. "
            "The down payment is 10% of the home value."
        ),
        person=PersonProfile(name="Alex Jordan"),
        questions={
            "approve": Noul(
                instructions="Should this person be approved for a home mortgage loan?"
            ),
            "should_approve": Choice(
                instructions="Should this application be approved?",
                criteria=YES_NO,
            ),
            "loan_size": Score(
                instructions="What loan size is appropriate for this application?",
                criteria=[
                    "Deny the loan.",
                    "Approve below the requested amount.",
                    "Approve the requested amount.",
                    "Approve above the requested amount.",
                ],
            ),
        },
    ),
)
