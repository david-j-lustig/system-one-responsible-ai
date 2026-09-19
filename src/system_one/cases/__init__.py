"""Decision cases grouped by domain."""

from system_one.cases.case import YES_NO, Case
from system_one.cases.criminal import CASES as CRIMINAL
from system_one.cases.financial import CASES as FINANCIAL

CASE_SETS = {
    "criminal": CRIMINAL,
    "financial": FINANCIAL,
}

CASES = tuple(case for cases in CASE_SETS.values() for case in cases)

__all__ = [
    "CASES",
    "CASE_SETS",
    "Case",
    "YES_NO",
]
