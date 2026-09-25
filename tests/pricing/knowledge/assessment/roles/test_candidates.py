from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_index_agrees_with_selectors_and_retains_roles_with_unknown_stats():
    from pricing.knowledge.assessment.roles.candidates import CandidateIndex

    profiles = build()['profiles']
    index = CandidateIndex(profiles)
    for item in [
        facts('Diadem', 'rare'),
        facts('Cinquedeas', 'rare'),
        replace(facts('Scythe', name='Infinity'), runeword='Infinity'),
    ]:
        expected = [
            p['id']
            for p in profiles
            if item.rarity in p['qualities']
            and (not p.get('types') or item.item_type in p['types'])
            and (not p.get('names') or item.name in p['names'])
        ]
        assert [p['id'] for p in index.select(item)] == expected
    # Unknown identity/type cannot establish a mismatch.
    partial = replace(facts('Cinquedeas', 'rare'), name=None, item_type=None)
    assert {p['id'] for p in index.select(partial)} == {p['id'] for p in profiles if 'rare' in p['qualities']}


def test_index_does_not_leak_mutable_source_or_selected_profiles():
    from pricing.knowledge.assessment.roles.candidates import CandidateIndex

    profiles = build()['profiles']
    index = CandidateIndex(profiles)
    item = facts('Cinquedeas', 'rare')
    profiles[0]['conditions'].append('mutation')
    selected = index.select(item)
    assert 'mutation' not in selected[0]['conditions']
    selected[0]['conditions'].append('caller mutation')
    assert 'caller mutation' not in index.select(item)[0]['conditions']
