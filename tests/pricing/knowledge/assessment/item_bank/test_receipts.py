"""A selected test pass must never masquerade as a complete item-bank run."""

from tests.pricing.knowledge.assessment.item_bank.receipts import RunReceipt


def receipt():
    return RunReceipt({'a': {'scenario': 'positive'}, 'b': {'scenario': 'negative'}}, {'tests/example.py': 'sha'})


def pass_case(run, case, generation='g'):
    for phase in ('setup', 'call', 'teardown'):
        run.record(case, phase, 'passed', generation)


def test_partial_run_retains_exact_cases_without_claiming_full_bank():
    run = receipt()
    pass_case(run, 'a')
    result = run.finish(0, {'tests/example.py': 'sha'})
    assert result['passed_cases'] == ['a']
    assert result['full_bank_passed'] is False
    assert result['generation'] == 'g'


def test_full_run_requires_every_case_and_phase():
    run = receipt()
    pass_case(run, 'a')
    run.record('b', 'call', 'passed', 'g')
    assert run.finish(0, {'tests/example.py': 'sha'})['full_bank_passed'] is False
    run.record('b', 'setup', 'passed', 'g')
    run.record('b', 'teardown', 'passed', 'g')
    assert run.finish(0, {'tests/example.py': 'sha'})['full_bank_passed'] is True


def test_teardown_failure_and_nonzero_exit_invalidate_success():
    run = receipt()
    pass_case(run, 'a')
    pass_case(run, 'b')
    run.record('a', 'teardown', 'failed', 'g')
    assert run.finish(1, {'tests/example.py': 'sha'})['passed_cases'] == ['b']
    assert run.finish(1, {'tests/example.py': 'sha'})['full_bank_passed'] is False


def test_changed_sources_mixed_generations_and_staging_are_not_attestable():
    for second in ('other-generation', None):
        run = receipt()
        pass_case(run, 'a')
        pass_case(run, 'b', second)
        assert run.finish(0, {'tests/example.py': 'sha'})['full_bank_passed'] is False
    run = receipt()
    pass_case(run, 'a')
    pass_case(run, 'b')
    result = run.finish(0, {'tests/example.py': 'new'})
    assert result['sources_unchanged'] is False
    assert result['full_bank_passed'] is False


def test_skip_or_failed_attempt_cannot_be_overwritten_by_a_later_pass():
    for outcome in ('failed', 'skipped', 'rerun'):
        run = receipt()
        run.record('a', 'call', outcome, 'g')
        pass_case(run, 'a')
        pass_case(run, 'b')
        result = run.finish(0, {'tests/example.py': 'sha'})
        assert result['passed_cases'] == ['b']
        assert result['full_bank_passed'] is False
