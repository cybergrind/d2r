import json
from pathlib import Path

from inventory_tracking.items.decode import decode_items
from pricing.knowledge.assessment.engine import assess


ROOT = Path(__file__).parents[4]


def dread_edge():
    saved = json.loads((ROOT / 'tests/inventory_tracking/fixtures/dread_edge.json').read_text())
    row = saved['snapshot']['resources']['items'][0]
    return decode_items(
        saved['snapshot'], saved['report'], inventory_page=4, inventory_owner_id=row['details']['owner_id']
    )[0]


def test_dagger_role_assessment_is_not_a_runeword_base_or_endgame_claim():
    result = assess(dread_edge())
    assert result['family'] == 'weapon'
    assert result['quality_policy'] == 'affixed'
    assert result['facts']['item_type'] == 'knif'
    assert result['facts']['stats']['218:0']['per_level'] == {'numerator': 4, 'denominator': 8}
    assert result['facts']['stats']['218:0']['value_at_reference_level'] == 45
    roles = {r['id']: r for r in result['roles']}
    assert roles['echoing-starter-dagger']['status'] == 'partial'
    assert roles['abyss-starter-dagger']['status'] == 'failed'
    assert result['contract'] is not None  # Fully projected modifiers permit comparison, not a price claim.
    assert result['price_gaps'] == []


def test_sazabi_component_is_not_a_complete_mercenary_setup():
    saved = json.loads((ROOT / 'tests/inventory_tracking/fixtures/sazabi_mental_sheath.json').read_text())
    row = saved['snapshot']['resources']['items'][0]
    extraction = decode_items(
        saved['snapshot'],
        saved['report'],
        inventory_page=row['details']['inventory_page'],
        inventory_owner_id=row['details']['owner_id'],
    )[0]
    assert not extraction['unresolved_stats']
    result = assess(extraction)
    role = next(r for r in result['roles'] if r['id'] == 'echoing-ubers-sazabi-helm')
    assert role['status'] == 'partial'
    assert role['side'] == 'merc'
    assert any('Cham' in s for s in role['missing'])
    assert any('companions' in s for s in role['missing'])
    assert result['quality_policy'] == 'named'


def test_unknown_identification_and_socket_facets_do_not_default_to_normal():
    result = assess({'item': {'name': 'Cinquedeas', 'base_code': '9kr', 'rarity': 'rare'}, 'decoded_stats': []})
    assert result['contract'] is None
    assert result['facts']['ethereal'] is None
    assert result['facts']['sockets'] is None
    assert any('identified' in gap for gap in result['price_gaps'])


def test_per_level_comparison_is_independent_of_viewer():
    from inventory_tracking.items.metadata import decode_stats
    from pricing.knowledge.assessment.adapters.capture import normalize

    item = {'name': 'Cinquedeas', 'base_code': '9kr', 'rarity': 'rare'}
    values = []
    for level in (20, 99):
        decoded, _, _ = decode_stats([{'id': 218, 'raw': 4, 'layer': 0}], viewer_level=level)
        values.append(normalize({'item': item, 'decoded_stats': decoded}).stats['218:0'])
    assert values[0]['value'] == 10
    assert values[1]['value'] == 49
    assert values[0]['value_at_reference_level'] == values[1]['value_at_reference_level'] == 45


def test_ambiguous_family_rules_fail_explicitly():
    import pytest

    from pricing.knowledge.assessment.adapters.capture import normalize
    from pricing.knowledge.assessment.registry import Family, classify

    facts = normalize({'item': {'base_code': '9kr'}})
    with pytest.raises(ValueError, match='Ambiguous'):
        classify(facts, (Family('a', frozenset({'knif'})), Family('b', frozenset({'knif'}))))


def test_profile_publication_matches_reviewed_sources():
    from pricing.knowledge.assessment.build_profiles import OUTPUT, build
    from pricing.knowledge.assessment.profiles import validate_profiles

    document = build(ROOT)
    validate_profiles(document['profiles'])
    assert document == json.loads(OUTPUT.read_text())


def test_unknown_skill_identity_is_not_an_executable_profile():
    from copy import deepcopy

    import pytest

    from pricing.knowledge.assessment.profiles import load_profiles, validate_profiles

    profiles = deepcopy(load_profiles()[0])
    profiles[0]['required_any_stats'] = ['107:999999']
    with pytest.raises(ValueError, match='Unknown skill'):
        validate_profiles(profiles)


def test_repeated_appraisals_do_not_mutate_cached_coverage_or_previous_results(monkeypatch):
    from inventory_tracking.appraisal.text import assessment_lines
    from pricing.knowledge.assessment import engine

    cached = ([], ['Limited profile coverage.'])
    monkeypatch.setattr(engine, 'load_candidates', lambda facts: cached)
    extraction = {'item': {'name': 'Cinquedeas', 'base_code': '9kr', 'rarity': 'normal'}}
    results = [engine.assess(extraction) for _ in range(3)]
    expected = [
        'Limited profile coverage.',
        'No reviewed build-role profile applies; absence is not evidence of no demand.',
    ]
    assert cached[1] == ['Limited profile coverage.']
    for result in results:
        assert result['coverage_gaps'] == expected
        lines = assessment_lines({'assessment': result})
        assert not any('No reviewed build-role profile applies' in line for line in lines)
    results[0]['coverage_gaps'].append('A caller-specific note.')
    assert results[1]['coverage_gaps'] == expected
