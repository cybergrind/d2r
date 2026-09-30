from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.completion import compile_completion
from pricing.knowledge.assessment.maintenance.guide_inventory import compile_inventory
from pricing.knowledge.assessment.maintenance.source_matching import occurrence_quality_matches
from tests.pricing.knowledge.assessment.maintenance.test_inline_source_links import inline_review
from tests.pricing.knowledge.assessment.maintenance.test_review_dossiers import reviewed


def sample(variant, quality='normal'):
    role, occurrence = inline_review()
    name = f'Hustle ({variant})'
    slot = 'Body Armors' if variant == 'armor' else 'Weapon'
    role.update(names=[name], types=['tors'] if variant == 'armor' else ['swor'], qualities=[quality], slot=slot)
    role['must'] = {'op': 'fact_eq', 'field': 'runeword', 'value': name}
    occurrence.update(
        name='Hustle',
        original_label='Hustle',
        category='runeword',
        slot=slot,
        details={'recommended': True, 'resolution_status': 'resolved'},
    )
    return role, occurrence


@pytest.mark.parametrize('variant', ['armor', 'weapon'])
@pytest.mark.parametrize('quality', ['normal', 'superior', 'low_quality'])
def test_reviewed_hustle_variant_closes_only_exact_source_and_setup(variant, quality):
    role, occurrence = sample(variant, quality)
    other = {**occurrence, 'id': 'other', 'variant': 'Other setup'}
    inventory = compile_inventory([occurrence, other], [role], {'hustle': {'category': 'runeword', 'name': 'Hustle'}})
    use = reviewed(role, item=role['names'][0])
    result = compile_completion({'rows': []}, inventory, {'complete': True}, profiles=[role], uses=[use])
    pending = {row['id'] for row in result['queue']}
    assert 'occurrence:' + occurrence['id'] not in pending
    assert 'occurrence:other' in pending
    assert not result['complete']


@pytest.mark.parametrize('variant', ['armor', 'weapon'])
@pytest.mark.parametrize(
    'change', ['wrong-slot', 'missing-slot', 'wrong-recipe', 'optional-recipe', 'wrong-type', 'magic']
)
def test_hustle_alias_requires_unambiguous_reviewed_recipe_slot_and_quality(variant, change):
    role, occurrence = sample(variant)
    if change == 'wrong-slot':
        occurrence['slot'] = 'Weapon' if variant == 'armor' else 'Body Armors'
    elif change == 'missing-slot':
        occurrence.pop('slot')
    elif change == 'wrong-recipe':
        role['must']['value'] = 'Hustle (weapon)' if variant == 'armor' else 'Hustle (armor)'
    elif change == 'optional-recipe':
        role['must'] = {'any': [deepcopy(role['must']), {'op': 'fact_eq', 'field': 'identified', 'value': True}]}
    elif change == 'wrong-type':
        role['types'] = ['swor'] if variant == 'armor' else ['tors']
    else:
        role['qualities'] = ['magic']
    assert not occurrence_quality_matches(occurrence, role)
