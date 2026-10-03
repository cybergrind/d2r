"""Allow red/green against staged artifacts and final checks against publication."""

from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.verification_scope import verification_inputs
from pricing.knowledge.refresh import atomic_json
from tests.pricing.knowledge.assessment.item_bank.receipts import RunReceipt
from tests.pricing.knowledge.assessment.item_bank.trade_checks import trade_case


RECEIPT = pytest.StashKey[RunReceipt]()
ROOT = Path(__file__).resolve().parents[5]


def pytest_addoption(parser):
    parser.addoption(
        '--item-bank-staged',
        action='store_true',
        default=False,
        help='Run item-bank appraisal against rebuilt working-tree artifacts instead of publication.',
    )
    parser.addoption('--item-bank-receipt', type=Path, help='Write source-bound executed-case evidence as JSON.')


def pytest_collection_finish(session):
    if not session.config.getoption('--item-bank-receipt'):
        return
    if session.config.getoption('numprocesses', default=0):
        raise pytest.UsageError('Item-bank receipts currently require a single pytest process.')
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    session.config.stash[RECEIPT] = RunReceipt(
        {
            case.id: {
                'covers': list(case.covers),
                'scenario': case.scenario,
                'evidence': list(case.evidence),
                **({'trade_case': trade_case(case)} if case.trade_checks is not None else {}),
                **(
                    {'quality': case.item.rarity, 'complete': case.item.complete, 'report_checks': case.report_checks}
                    if case.report_checks is not None
                    else {}
                ),
            }
            for case in CASES
        },
        verification_inputs(ROOT),
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    receipt = item.config.stash.get(RECEIPT, None)
    if receipt is None or item.originalname != 'test_constructed_item_through_published_appraisal':
        return
    case = item.callspec.params['case']
    runtime = item.funcargs.get('runtime')
    receipt.record(case.id, report.when, report.outcome, runtime.generation if runtime else None)


def pytest_sessionfinish(session, exitstatus):
    receipt = session.config.stash.get(RECEIPT, None)
    if receipt is not None:
        session.config.getoption('--item-bank-receipt').parent.mkdir(parents=True, exist_ok=True)
        atomic_json(
            session.config.getoption('--item-bank-receipt'), receipt.finish(exitstatus, verification_inputs(ROOT))
        )
