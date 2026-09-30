"""Planner runewords require native recipe, base and exact bearer evidence."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.builds import decode_planner
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import pin, read, validate


PID = 'fist-of-the-heavens-paladin-4-merc-fortitude'
OID = 'b9ef4cdcef149b5f9128e9a9'


def records():
    role = next(r for r in read('pricing/data/appraisal-build-profiles.json')['profiles'] if r['id'] == PID)
    use = next(
        r for r in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'] if r['profile_id'] == PID
    )
    occurrence = next(r for r in read('pricing/data/appraisal-guide-inventory.json')['occurrences'] if r['id'] == OID)
    exemplar = next(
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['occurrence_id'] == '3db1f4eb689b273071b6d59f'
    )
    evidence = deepcopy(exemplar['planner_endorsement'])
    evidence.pop('ethereal_scope')
    evidence.pop('rune_definitions')
    evidence.update(
        coverage='merc_runeword_component',
        slot='tors',
        item_id='29',
        mercenary_id='10',
        mercenary_type='Act 2 Holy Freeze',
        expected_item=decode_planner(read(evidence['planner']['path']))['items']['29'],
    )
    evidence['recipe_sources'] = {
        key: pin(path)
        for key, path in {
            'planner': 'pricing/raw/mr/planners/game-data.json',
            'runes': 'third-parties/d2data/json/runes.json',
            'armor': 'third-parties/d2data/json/armor.json',
            'types': 'third-parties/d2data/json/itemtypes.json',
        }.items()
    }
    review = {
        'pattern_kind': 'structured_named_variant',
        'occurrence_id': OID,
        'occurrence_fingerprint': fingerprint(occurrence),
        'profile_id': PID,
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'canonical_name': 'Fortitude',
        'review_date': '2026-09-29',
        'reason': (
            'Explicit Holy Bolt support endorsement; exact ethereal Sacred Armor Fortitude on the Holy Freeze '
            'mercenary, with native recipe validation. Physical damage and survival component only; '
            'no player spell damage or full-loadout claim.'
        ),
        'required_predicates': deepcopy(role['must']['all']),
        'required_conditions': deepcopy(role['conditions']),
        'planner_endorsement': evidence,
    }
    return review, occurrence, role, use


def test_completed_runeword_can_bind_to_explicitly_endorsed_mercenary():
    assert validate(records())['state'] == 'reviewed'


@pytest.mark.parametrize('field', ['runeword', 'sockets', 'socket_contents', 'base_code', 'ethereal', 'mercenary_type'])
def test_recipe_review_rejects_removed_guard_even_with_refreshed_fingerprints(field):
    review, occurrence, role, use = records()
    role['must']['all'] = [p for p in role['must']['all'] if p.get('field') != field]
    review['required_predicates'] = deepcopy(role['must']['all'])
    use['profile_fingerprint'] = review['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match=r'[Pp]lanner|predicate|[Ee]ndorsed'):
        validate((review, occurrence, role, use))


@pytest.mark.parametrize(
    'change',
    [
        'wrong-rune',
        'rune-order',
        'socket-count',
        'identity',
        'weapon-recipe',
        'excluded-base',
        'capacity',
        'missing-pin',
        'stale-native',
        'missing-corroboration',
    ],
)
def test_native_recipe_validation_rejects_inconsistent_evidence(change):
    from pricing.knowledge.assessment.maintenance.planner_runeword_endorsement import validate_runeword

    review, _, role, _ = records()
    evidence = review['planner_endorsement']
    item = deepcopy(evidence['expected_item'])
    tables = {key: read(value['path']) for key, value in evidence['recipe_sources'].items()}
    recipe = tables['runes']['Fortitude']
    if change == 'wrong-rune':
        item['socketedItems'][-1] = 'r01'
    elif change == 'rune-order':
        item['socketedItems'].reverse()
    elif change == 'socket-count':
        item['sockets'] = 3
    elif change == 'identity':
        tables['planner']['runes']['runeword067']['name'] = 'AnotherRecipe'
    elif change == 'weapon-recipe':
        recipe.pop('itype2')
    elif change == 'excluded-base':
        recipe['etype1'] = 'tors'
    elif change == 'capacity':
        tables['armor']['uar']['gemsockets'] = 3
    elif change == 'missing-pin':
        evidence['recipe_sources'].pop('types')
    elif change == 'stale-native':
        evidence['recipe_sources']['runes']['sha256'] = '0' * 64
    else:
        role['source']['corroborating'] = []
    by_path = {value['path']: tables[key] for key, value in evidence['recipe_sources'].items()}
    with pytest.raises(ValueError, match='Planner runeword'):
        validate_runeword(evidence, role, item, lambda ref: by_path[ref['path']])


def test_registered_holy_bolt_fortitude_keeps_recipe_and_wearer_proof():
    _, occurrence, role, use = records()
    matches = [
        row
        for row in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if row['occurrence_id'] == OID
    ]
    assert len(matches) == 1
    assert matches[0]['required_predicates'] == role['must']['all']
    assert matches[0]['required_conditions'] == role['conditions']
    assert matches[0]['planner_endorsement']['coverage'] == 'merc_runeword_component'
    assert validate((matches[0], occurrence, role, use))['state'] == 'reviewed'


def weapon_records(profile_id):
    candidate = next(
        r
        for r in read('pricing/data/appraisal-planner-candidate-tab-audit.json')['rows']
        if r['profile_id'] == profile_id and r['state'] == 'exact_tab_reference'
    )
    role = next(r for r in read('pricing/data/appraisal-build-profiles.json')['profiles'] if r['id'] == profile_id)
    planner = decode_planner(read(candidate['planner_path']))
    profile = planner['profiles'][candidate['planner_profile_index']]
    slot = 'rarm2' if role['slot'] == 'Weapon-Swap' else 'rarm'
    container = 'items' if role['side'] == 'player' else 'mercItems'
    item = planner['items'][str(profile[container][slot])]
    evidence = {
        'recipe_sources': {
            key: pin(path)
            for key, path in {
                'planner': 'pricing/raw/mr/planners/game-data.json',
                'runes': 'third-parties/d2data/json/runes.json',
                'weapons': 'third-parties/d2data/json/weapons.json',
                'types': 'third-parties/d2data/json/itemtypes.json',
            }.items()
        }
    }
    role['source']['corroborating'] = [
        {**evidence['recipe_sources']['runes'], 'locator': '/' + role['names'][0]},
    ]
    return evidence, role, item


@pytest.mark.parametrize(
    'profile_id',
    [
        'echoing-standard-cta-prebuff',
        'echoing-mf-cta-prebuff',
        'echoing-ubers-cta-prebuff',
        'fire-standard-cta-prebuff',
        'fire-mf-cta-prebuff',
        'abyss-standard-cta-prebuff',
        'abyss-mf-cta-prebuff',
        'mirrored-standard-cta-prebuff',
        'mirrored-ubers-cta-prebuff',
        'hammer-standard-insight-merc',
        'hammer-mf-insight-merc',
        'dream-paladin-hand-of-justice-hybrid-source-recipe',
    ],
)
def test_native_weapon_recipe_matches_selected_planner_configuration(profile_id):
    from pricing.knowledge.assessment.maintenance.planner_runeword_endorsement import validate_runeword

    evidence, role, item = weapon_records(profile_id)
    validate_runeword(evidence, role, item, lambda ref: read(ref['path']))


@pytest.mark.parametrize(
    'change', ['rune-order', 'count', 'illegal-base', 'wrong-slot', 'wrong-table', 'missing-source']
)
def test_weapon_recipe_rejects_wrong_payload_base_or_slot(change):
    from pricing.knowledge.assessment.maintenance.planner_runeword_endorsement import validate_runeword

    evidence, role, item = weapon_records('hammer-standard-insight-merc')
    if change == 'rune-order':
        item['socketedItems'].reverse()
    elif change == 'count':
        item['sockets'] = 3
    elif change == 'illegal-base':
        item['base'] = weapon_records('echoing-standard-cta-prebuff')[2]['base']
    elif change == 'wrong-slot':
        role['slot'] = 'Body Armor'
    elif change == 'wrong-table':
        evidence['recipe_sources']['weapons'] = pin('third-parties/d2data/json/armor.json')
    else:
        evidence['recipe_sources'].pop('weapons')
    with pytest.raises(ValueError, match='Planner runeword'):
        validate_runeword(evidence, role, item, lambda ref: read(ref['path']))
