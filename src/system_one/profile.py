"""Typed person record for explainability perturbations."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

YesNoUnknown = Literal["yes", "no", "unknown"]


class PersonProfile(BaseModel):
    """Optional person fields. Unset (`None`) values are omitted from the payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str | None = None
    sex: str | None = None
    gender: str | None = None
    age: int | None = None
    race: str | None = None
    ethnicity: str | None = None
    religion: str | None = None
    sexuality: str | None = None
    disability: YesNoUnknown | None = None
    political_affiliation: str | None = None
    annual_income: int | None = None
    credit_score: int | None = None
    employment_status: str | None = None
    occupation: str | None = None
    years_employed: int | None = None
    monthly_debt: int | None = None
    liquid_assets: int | None = None
    housing_status: str | None = None
    dependents: int | None = None

    def dumped(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)
