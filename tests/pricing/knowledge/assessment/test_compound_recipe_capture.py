"""An omitted compound recipe cannot turn an incomplete capture into a price."""

import json
from pathlib import Path

import pytest

from pricing.knowledge.assessment.handlers.runeword import RunewordHandler
from pricing.knowledge.definition_store import DefinitionStore, definition_snapshot
from pricing.knowledge.definitions import build_definitions
from tests.pricing.knowledge.assessment.test_runeword_charges import harmony


@pytest.fixture(scope='module')
def rebuilt(tmp_path_factory):
    root = Path(__file__).resolve().parents[4]
    path = tmp_path_factory.mktemp('compiled-compound') / 'definitions.json'
    path.write_text(json.dumps(build_definitions(root)))
    return DefinitionStore(path).load()


def test_harmony_missing_elemental_damage_is_not_a_complete_comparison(rebuilt):
    with definition_snapshot(rebuilt):
        contract, gaps = RunewordHandler().contract(harmony(), 'weapon')
    assert contract is None
    assert any('elemental' in g.lower() for g in gaps)


@pytest.mark.parametrize(
    ('name', 'values'),
    [
        ('Harmony', {48: 55, 49: 160, 50: 55, 51: 160, 54: 55, 55: 160}),
        # Ort contributes1..50 lightning damage in addition to Famine's50..200.
        ('Famine', {48: 50, 49: 200, 50: 51, 51: 250, 54: 50, 55: 200}),
    ],
)
@pytest.mark.parametrize('changed_stat', [None, 48, 49, 50, 51, 54, 55])
@pytest.mark.parametrize('mutation', ['missing', 'raw', 'value'])
def test_rebuilt_recipe_verifies_all_endpoints_but_keeps_unknown_cold_duration(
    rebuilt, name, values, changed_stat, mutation
):
    from dataclasses import replace

    from pricing.knowledge.assessment.handlers.runeword import elemental_effects
    from pricing.knowledge.assessment.mechanics.compound_recipe import compound_recipe_gaps

    props = {48: '458', 49: '459', 50: '478', 51: '479', 54: '482', 55: '483'}
    stats = {f'{k}:0': {'status': 'decoded', 'raw': v, 'value': v} for k, v in values.items()}
    stats['56:0'] = {'status': 'decoded', 'raw': 100, 'value': 4, 'unit': 'seconds'}
    if changed_stat is not None:
        key = f'{changed_stat}:0'
        if mutation == 'missing':
            del stats[key]
        else:
            stats[key][mutation] += 1
    item = replace(harmony(), runeword=name, stats=stats, properties={props[k]: v for k, v in values.items()})
    definition = rebuilt.runewords[name]
    gaps = compound_recipe_gaps(item, definition, elemental_effects(definition, 'weapon'))
    assert any('cold duration' in gap for gap in gaps)
    assert any('endpoint' in gap for gap in gaps) is (changed_stat is not None)


def test_rebuilt_hellrack_contract_preserves_all_fixed_elemental_endpoints(rebuilt):
    from pricing.knowledge.assessment.adapters.capture import normalize
    from pricing.knowledge.assessment.handlers.named import NamedHandler
    from pricing.knowledge.assessment.registry import classify

    saved = json.loads((Path(__file__).parent / 'fixtures/named_cold_duration.json').read_text())
    observation = next(r['observation'] for r in saved['records'] if r['name'] == 'Hellrack')
    facts = normalize(observation)
    with definition_snapshot(rebuilt):
        contract, gaps = NamedHandler().contract(facts, classify(facts)[0])
    assert contract is not None, gaps
    for prop, expected in {'458': 63, '459': 324, '478': 63, '479': 324, '482': 63, '483': 324}.items():
        assert contract.properties[prop] == expected
        assert contract.intrinsic_properties[prop] == expected


def test_compound_guard_uses_only_published_recipe_evidence():
    from pricing.knowledge.publication import current_generation
    from pricing.knowledge.published_runtime import load_runtime, published_snapshot

    runtime = load_runtime(current_generation('pricing/data/generations'))
    with published_snapshot(runtime):
        contract, gaps = RunewordHandler().contract(harmony(), 'weapon')
    assert contract is None
    assert any('elemental' in gap.lower() for gap in gaps)
