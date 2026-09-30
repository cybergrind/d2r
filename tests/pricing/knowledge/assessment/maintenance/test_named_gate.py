import pytest

from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.maintenance.named_gate import audit, native_cases
from pricing.knowledge.assessment.policies import named_baselines
from pricing.knowledge.definition_store import catalog


@pytest.mark.parametrize('name', ['Bane Ash', "Blinkbat's Form"])
def test_ethereal_census_specimen_retains_definition_stats(name):
    identity = 'unique', name
    for definition in catalog().named_variants[identity]:
        cases = dict(native_cases(identity, definition))
        ethereal = cases['ethereal']
        assert ethereal.stats == cases['min'].stats
        resolved, errors = resolve_named_definition(ethereal)
        assert not errors
        assert resolved['roll_ranges'] == definition['roll_ranges']


def test_runtime_gate_detects_lost_baseline_even_when_variant_policy_exists(monkeypatch):
    original = named_baselines.baselines

    def without_guardian(raw):
        return {key: row for key, row in original(raw).items() if key != ('unique', 'Guardian Angel')}

    monkeypatch.setattr(named_baselines, 'baselines', without_guardian)
    result = audit()
    assert not result['complete']
    assert result['gates']['uniques_missing_baseline'] == 1
    assert result['gates']['rendered_tier_failures'] > 0
    assert {row['name'] for row in result['rendering_failures']} == {'Guardian Angel'}
