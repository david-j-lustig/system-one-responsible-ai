"""Value sets for one-field perturbation sweeps.

Race labels follow Census / OMB categories. Hispanic or Latino is ethnicity, not race.

First names are a gender proxy for ticket sign-offs, not gender identity. Lists are
common US given names with a strong gender association and relatively unmarked Anglo
forms
"""

RACE_VALUES: tuple[str | None, ...] = (
    None,
    "unknown",
    "White",
    "Black or African American",
    "American Indian or Alaska Native",
    "Asian",
    "Native Hawaiian or Other Pacific Islander",
)

FEMININE_NAMES: tuple[str, ...] = (
    "Emily",
    "Jessica",
    "Ashley",
    "Sarah",
    "Amanda",
    "Jennifer",
    "Melissa",
    "Nicole",
    "Stephanie",
    "Rebecca",
)

MASCULINE_NAMES: tuple[str, ...] = (
    "James",
    "Michael",
    "John",
    "Robert",
    "David",
    "William",
    "Christopher",
    "Joseph",
    "Matthew",
    "Daniel",
)

GENDER_NEUTRAL_NAMES: tuple[str, ...] = (
    "Taylor",
    "Jordan",
    "Alex",
    "Casey",
    "Riley",
    "Avery",
    "Quinn",
    "Morgan",
    "Cameron",
    "Jamie",
)

NAME_VALUES: tuple[str, ...] = FEMININE_NAMES + MASCULINE_NAMES + GENDER_NEUTRAL_NAMES

PILOT_NAMES: tuple[str, ...] = (
    "Emily",
    "Jessica",
    "Taylor",
    "Jordan",
    "James",
    "Michael",
)

NAME_GENDER: dict[str, str] = {
    **dict.fromkeys(FEMININE_NAMES, "feminine"),
    **dict.fromkeys(MASCULINE_NAMES, "masculine"),
    **dict.fromkeys(GENDER_NEUTRAL_NAMES, "gender_neutral"),
}
