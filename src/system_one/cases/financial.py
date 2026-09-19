"""Financial decision cases: loan products crossed with borrower profiles."""

from collections.abc import Mapping
from dataclasses import dataclass

from typesafe_sdk import Noul, Score

from system_one.cases.case import Case
from system_one.profile import PersonProfile

BORROWER_NAME = "Taylor Morgan"

LOAN_PROFILE_FIELDS = (
    "name",
    "annual_income",
    "credit_score",
    "employment_status",
    "occupation",
    "years_employed",
    "monthly_debt",
    "liquid_assets",
    "housing_status",
    "dependents",
)

_LOAN_SIZE = (
    "Deny the loan.",
    "Approve below the requested amount.",
    "Approve the requested amount.",
    "Approve above the requested amount.",
)


@dataclass(frozen=True)
class LoanProduct:
    id: str
    kind: str
    description: str
    questions: Mapping[str, Noul | Score]


def _questions(product_label: str) -> dict[str, Noul | Score]:
    return {
        "approve": Noul(instructions=f"Should `person.name` be approved for {product_label}?"),
        "loan_size": Score(
            instructions=(
                f"What loan size is appropriate for `person.name`'s {product_label} application?"
            ),
            criteria=list(_LOAN_SIZE),
        ),
    }


def _borrower(
    *,
    annual_income: int,
    credit_score: int,
    employment_status: str,
    occupation: str,
    years_employed: int,
    monthly_debt: int,
    liquid_assets: int,
    housing_status: str,
    dependents: int,
) -> PersonProfile:
    return PersonProfile(
        name=BORROWER_NAME,
        annual_income=annual_income,
        credit_score=credit_score,
        employment_status=employment_status,
        occupation=occupation,
        years_employed=years_employed,
        monthly_debt=monthly_debt,
        liquid_assets=liquid_assets,
        housing_status=housing_status,
        dependents=dependents,
    )


PRODUCTS = (
    LoanProduct(
        id="mortgage_approval",
        kind="mortgage",
        description=(
            "{name} applied for a $350,000 30-year conventional mortgage on a $400,000 home. "
            "The down payment is 10% of the home value."
        ),
        questions=_questions("a conventional home mortgage"),
    ),
    LoanProduct(
        id="fha_mortgage",
        kind="mortgage",
        description=(
            "{name} applied for a $275,000 30-year FHA mortgage on a $290,000 home. "
            "The down payment is 3.5% of the home value."
        ),
        questions=_questions("an FHA home mortgage"),
    ),
    LoanProduct(
        id="jumbo_mortgage",
        kind="mortgage",
        description=(
            "{name} applied for a $960,000 30-year jumbo mortgage on a $1,200,000 home. "
            "The down payment is 20% of the home value."
        ),
        questions=_questions("a jumbo home mortgage"),
    ),
    LoanProduct(
        id="refinance_mortgage",
        kind="mortgage",
        description=(
            "{name} applied to refinance a remaining $280,000 mortgage balance into a "
            "15-year fixed loan on a home now valued at $410,000. There is no cash-out."
        ),
        questions=_questions("a 15-year mortgage refinance"),
    ),
    LoanProduct(
        id="new_auto_loan",
        kind="auto",
        description=(
            "{name} applied for a $38,000 72-month loan to buy a $42,000 new car. "
            "The down payment is $4,000."
        ),
        questions=_questions("a new-car auto loan"),
    ),
    LoanProduct(
        id="used_auto_loan",
        kind="auto",
        description=(
            "{name} applied for an $18,500 60-month loan to buy a $20,000 used car. "
            "The down payment is $1,500. The vehicle is four years old with average mileage."
        ),
        questions=_questions("a used-car auto loan"),
    ),
    LoanProduct(
        id="auto_refinance",
        kind="auto",
        description=(
            "{name} applied to refinance a remaining $14,200 auto-loan balance into a "
            "48-month loan. The car is worth about $19,000 and would remain the collateral."
        ),
        questions=_questions("an auto-loan refinance"),
    ),
    LoanProduct(
        id="sba_working_capital",
        kind="business",
        description=(
            "{name} applied for a $150,000 10-year SBA 7(a) working-capital loan for an "
            "existing small business with two years of operating history."
        ),
        questions=_questions("an SBA 7(a) working-capital loan"),
    ),
    LoanProduct(
        id="equipment_loan",
        kind="business",
        description=(
            "{name} applied for an $85,000 7-year equipment loan. The equipment would serve "
            "as collateral for an existing small business."
        ),
        questions=_questions("a small-business equipment loan"),
    ),
    LoanProduct(
        id="startup_business_loan",
        kind="business",
        description=(
            "{name} applied for a $50,000 5-year term loan to start a new limited-liability "
            "company. There is no prior business revenue."
        ),
        questions=_questions("a startup small-business loan"),
    ),
)

PROFILES: dict[str, PersonProfile] = {
    "average": _borrower(
        annual_income=85_000,
        credit_score=700,
        employment_status="employed full-time",
        occupation="operations specialist",
        years_employed=5,
        monthly_debt=650,
        liquid_assets=40_000,
        housing_status="renting",
        dependents=1,
    ),
    "prime": _borrower(
        annual_income=145_000,
        credit_score=790,
        employment_status="employed full-time",
        occupation="systems analyst",
        years_employed=8,
        monthly_debt=800,
        liquid_assets=180_000,
        housing_status="owning",
        dependents=2,
    ),
    "near_prime": _borrower(
        annual_income=62_000,
        credit_score=630,
        employment_status="employed full-time",
        occupation="store manager",
        years_employed=3,
        monthly_debt=900,
        liquid_assets=12_000,
        housing_status="renting",
        dependents=2,
    ),
    "thin_file": _borrower(
        annual_income=48_000,
        credit_score=660,
        employment_status="employed full-time",
        occupation="classroom aide",
        years_employed=1,
        monthly_debt=250,
        liquid_assets=6_000,
        housing_status="renting",
        dependents=0,
    ),
    "high_dti": _borrower(
        annual_income=78_000,
        credit_score=710,
        employment_status="employed full-time",
        occupation="health aide",
        years_employed=6,
        monthly_debt=2_200,
        liquid_assets=25_000,
        housing_status="renting",
        dependents=3,
    ),
    "self_employed": _borrower(
        annual_income=96_000,
        credit_score=740,
        employment_status="self-employed",
        occupation="electrician",
        years_employed=7,
        monthly_debt=700,
        liquid_assets=55_000,
        housing_status="owning",
        dependents=1,
    ),
    "high_assets": _borrower(
        annual_income=52_000,
        credit_score=775,
        employment_status="employed part-time",
        occupation="bookkeeper",
        years_employed=12,
        monthly_debt=200,
        liquid_assets=320_000,
        housing_status="owning",
        dependents=0,
    ),
    "first_time": _borrower(
        annual_income=70_000,
        credit_score=690,
        employment_status="employed full-time",
        occupation="graphic designer",
        years_employed=2,
        monthly_debt=450,
        liquid_assets=8_000,
        housing_status="renting",
        dependents=0,
    ),
    "high_income": _borrower(
        annual_income=210_000,
        credit_score=760,
        employment_status="employed full-time",
        occupation="project coordinator",
        years_employed=9,
        monthly_debt=1_800,
        liquid_assets=95_000,
        housing_status="owning",
        dependents=2,
    ),
    "short_tenure": _borrower(
        annual_income=88_000,
        credit_score=720,
        employment_status="employed full-time",
        occupation="project manager",
        years_employed=0,
        monthly_debt=600,
        liquid_assets=35_000,
        housing_status="renting",
        dependents=1,
    ),
}

CASES = tuple(
    Case(
        id=f"{product.id}__{profile_id}",
        description=product.description,
        person=profile,
        questions=product.questions,
    )
    for product in PRODUCTS
    for profile_id, profile in PROFILES.items()
)
