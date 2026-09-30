"""Repeated structured sources reuse one reviewed rule, not another gear variant."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


def inputs(slot='armor'):
    def read(path):
        return json.loads(Path(path).read_text())

    inventory = read('pricing/data/appraisal-guide-inventory.json')['occurrences']
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    uses = read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
    role = next(r for r in profiles if r['id'] == 'berserk-barbarian-starter-topaz-' + slot)
    occurrence = next(
        o
        for o in inventory
        if o['source_id'] == 'pricing/data/wp-a-variants/berserk-barbarian.json'
        and o['variant'] == 'Starter'
        and o['slot'] == role['slot']
        and o['side'] == 'player'
    )
    use = next(u for u in uses if u['profile_id'] == role['id'])
    pin = {
        'path': occurrence['source_id'],
        'sha256': hashlib.sha256(Path(occurrence['source_id']).read_bytes()).hexdigest(),
    }
    review = {
        'pattern_kind': 'structured_player_variant_mirror',
        'occurrence_id': occurrence['id'],
        'profile_id': role['id'],
        'occurrence_fingerprint': fingerprint(occurrence),
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'mirror': pin,
        'review_date': '2026-09-28',
        'reason': 'Exact duplicate Starter equipment context; preserve the existing item predicates.',
    }
    return review, occurrence, role, use


def compile_one(args):
    review, occurrence, role, use = args
    return compile_table_equivalence({'schema_version': 1, 'rows': [review]}, [occurrence], [role], [use], Path.cwd())


@pytest.mark.parametrize('slot', ['armor', 'helmet'])
def test_exact_starter_source_mirror_reuses_the_existing_rule(slot):
    args = inputs(slot)
    rows = compile_one(args)
    assert rows[0]['state'] == 'reviewed'
    assert rows[0]['profile_id'] == args[2]['id']
    assert rows[0]['occurrence_id'] == args[1]['id']


@pytest.mark.parametrize(
    'change', ['variant', 'slot', 'side', 'label', 'class', 'recommendation', 'locator', 'source', 'hash', 'role']
)
def test_changed_occurrence_does_not_borrow_a_reviewed_configuration(change):
    review, occurrence, role, use = inputs()
    if change == 'hash':
        review['mirror']['sha256'] = '0' * 64
    elif change == 'role':
        role['must'] = {}
    else:
        key, value = {
            'variant': ('variant', 'Ubers'),
            'slot': ('slot', 'Helmet'),
            'side': ('side', 'merc'),
            'label': ('original_label', 'Gemmed Dusk Shroud (4x Perfect Ruby)'),
            'class': ('class', 'Warlock'),
            'locator': ('source_locator', '/variants/1/player/Body Armor/0'),
            'source': ('source_id', 'pricing/data/wp-a-variants/fissure-druid.json'),
            'recommendation': ('details', {'recommended': False}),
        }[change]
        occurrence[key] = value
        review['occurrence_fingerprint'] = fingerprint(occurrence)
    with pytest.raises(ValueError, match=r'[Mm]irror|Stale guide-use|Stale table equivalence'):
        compile_one((review, occurrence, role, use))


@pytest.mark.parametrize('change', ['mercenary', 'player-gear', 'variant-name', 'planner-only', 'class', 'label'])
def test_equal_labels_do_not_hide_a_changed_variant_document(change):
    from pricing.knowledge.assessment.maintenance.structured_variant_mirrors import validate_mirror

    review, occurrence, role, use = inputs()

    def read(pin):
        doc = deepcopy(json.loads(Path(pin['path']).read_text()))
        if pin['path'] == review['mirror']['path']:
            variant = doc['variants'][0]
            if change == 'mercenary':
                variant['merc']['type'] = 'Act 3 Fire'
            elif change == 'player-gear':
                variant['player']['Weapon'] = ['Other weapon']
            elif change == 'variant-name':
                variant['name'] = 'Ubers'
            elif change == 'planner-only':
                variant['planner_only'] = True
            elif change == 'class':
                doc['class'] = 'Warlock'
            else:
                variant['player']['Body Armor'][0] = 'Gemmed Dusk Shroud (4x Perfect Ruby)'
        return doc

    with pytest.raises(ValueError, match='Structured mirror changed'):
        validate_mirror(review, occurrence, role, [use], Path.cwd(), read)


def test_both_starter_mirrors_are_registered():
    doc = json.loads(Path('pricing/knowledge/assessment/rules/table_equivalence_reviews.json').read_text())
    expected = {inputs(slot)[1]['id'] for slot in ('armor', 'helmet')}
    assert expected <= {
        r['occurrence_id'] for r in doc['rows'] if r.get('pattern_kind') == 'structured_player_variant_mirror'
    }
