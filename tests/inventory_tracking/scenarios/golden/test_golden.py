"""The decision goldens: every case of cases.py decides what decisions.json holds (framework-plan.md, Task 0.2)."""

import pytest

from tests.inventory_tracking.scenarios.golden.build_golden import recorded
from tests.inventory_tracking.scenarios.golden.cases import cases


CASES = {case.name: case for case in cases()}
RECORDED = recorded()


def test_case_names_are_unique():
    assert len(CASES) == len(cases())


def test_no_case_is_missing_or_stale():
    assert sorted(CASES) == sorted(RECORDED)


@pytest.mark.parametrize('name', sorted(CASES))
def test_every_case_reads_as_recorded(name):
    assert name in RECORDED, 'not in decisions.json: run build_golden for a case added on purpose'
    assert CASES[name].run() == RECORDED[name]
