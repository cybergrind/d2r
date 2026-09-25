from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_dependencies_distinguish_item_fit_from_unconfirmed_loadout():
    profile = {
        'id': 'test',
        'types': ['tors'],
        'qualities': ['normal'],
        'build': 'test',
        'variant': 'Standard',
        'side': 'merc',
        'slot': 'Body Armor',
        'role': 'shared armor',
        'review_status': 'reviewed_setup',
        'source': {},
        'depends_on': [
            {
                'label': 'Act 2 Might mercenary',
                'when': {'op': 'context_eq', 'field': 'mercenary_type', 'value': 'Act 2 Might'},
            }
        ],
    }
    item = facts('Mage Plate')
    unknown = assess_roles(item, [profile])[0]
    assert unknown['status'] == 'partial'
    assert unknown['dependencies'][0]['status'] == 'unknown'
    wrong = assess_roles(item, [profile], {'mercenary_type': 'Act 5 Frenzy'})[0]
    assert wrong['dependencies'][0]['status'] == 'false'
    assert 'Act 2 Might' in wrong['missing'][0]
    assert assess_roles(item, [profile], {'mercenary_type': 'Act 2 Might'})[0]['status'] == 'matched'


def test_smite_shared_treachery_requires_nonethereal_and_preserves_prebuff_reason():
    item = replace(facts('Mage Plate', name='Treachery'), runeword='Treachery', sockets=3, socket_contents='filled')
    profiles = build()['profiles']
    role = next(r for r in assess_roles(item, profiles) if r['id'] == 'smite-shared-treachery')
    assert role['status'] == 'partial'
    assert role['ethereal_preference']['preference'] == 'avoid'
    assert 'Fade' in role['ethereal_preference']['reason']
    wrong = next(r for r in assess_roles(replace(item, ethereal=True), profiles) if r['id'] == 'smite-shared-treachery')
    assert wrong['status'] == 'failed'


def test_dependency_predicates_are_validated_before_publication():
    import pytest

    from pricing.knowledge.assessment.profiles import validate_profiles

    profile = next(p for p in build()['profiles'] if p['id'] == 'smite-shared-treachery')
    profile['depends_on'][0]['when']['field'] = 'invented_context'
    with pytest.raises(ValueError, match='Invalid fact/context predicate'):
        validate_profiles([profile])
