"""Completed armor source links retain reviewed use, recipe and wearer boundaries."""

import hashlib
import json
from copy import deepcopy
from functools import lru_cache

import pytest

from pricing.knowledge.assessment.maintenance.armor_planner_links import (
    compile_armor_planner_links,
    validate_armor_mercenary,
)
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.inventory import ROOT


PROFILES = 'pricing/data/appraisal-build-profiles.json'
USES = 'pricing/knowledge/assessment/rules/guide_use_reviews.json'
NATIVE = 'third-parties/d2data/json/misc.json'


@lru_cache
def read(path):
    return json.loads((ROOT / path).read_bytes())


def example(profile_id='fire-warlock-guide-1-merc-fortitude'):
    audit = read('pricing/data/appraisal-selected-armor-endorsement-audit.json')
    if not any(r['profile_id'] == profile_id for r in audit['rows']):
        audit = read('pricing/data/appraisal-remaining-armor-endorsement-audit.json')
    prepared = next(r for r in audit['rows'] if r['profile_id'] == profile_id)
    role = deepcopy(next(r for r in read(PROFILES)['profiles'] if r['id'] == profile_id))
    use = deepcopy(next(r for r in read(USES)['uses'] if r['profile_id'] == profile_id))
    inv = read('pricing/data/appraisal-guide-inventory.json')
    parent = next(r for r in inv['occurrences'] if r['id'] == prepared['parent_occurrence_id'])
    children = sorted(
        [
            r
            for r in inv['occurrences']
            if r['source_id'] == parent['source_id']
            and r['source_locator'].startswith(parent['source_locator'] + '/socketedItems/')
        ],
        key=lambda r: r['source_locator'],
    )
    occurrences = [parent, *children]
    identities = {r['identity_id'] for r in occurrences}
    inventory = deepcopy(
        {
            'occurrences': occurrences,
            'identities': [r for r in inv['identities'] if r['id'] in identities],
            'sources': [r for r in inv['sources'] if r['id'] == parent['source_id']],
        }
    )

    def ref(row):
        return {'occurrence_id': row['id'], 'sha256': fingerprint(row)}

    link = {
        'id': profile_id + ':planner',
        'profile_id': profile_id,
        'profile_sha256': fingerprint(role),
        'use_sha256': fingerprint(use),
        'planner_endorsement': deepcopy(prepared['planner_endorsement']),
        'parent': ref(parent),
        'children': [ref(r) for r in children],
        'reviewed_at': '2026-09-30',
        'reason': 'Exact selected armor recipe bound to its existing reviewed build use.',
    }
    paths = set(audit['inputs']) | {PROFILES, USES, NATIVE, role['source']['path']}
    document = {
        'schema_version': 1,
        'scope': 'reviewed_completed_armor_recipes',
        'inputs': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        'rows': [link],
    }
    return document, inventory, [role], [use]


@pytest.mark.parametrize(
    'profile_id',
    [
        'fire-warlock-guide-1-merc-fortitude',
        'blessed-hammer-paladin-1-merc-fortitude',
        'echoing-strike-warlock-guide-1-player-enigma',
        'smite-paladin-1-player-chains-honor',
        'echoing-strike-warlock-guide-1-merc-chains-honor',
        'echoing-strike-warlock-guide-2-merc-chains-honor',
        'dream-paladin-0-merc-treachery-native',
        'mirrored-blades-warlock-guide-1-merc-chains-honor',
        'lightning-fury-amazon-guide-3-player-chains-honor',
        'lightning-fury-amazon-guide-3-merc-treachery-native',
    ],
)
def test_completed_armor_links_exact_parent_and_payload(profile_id):
    document, inventory, profiles, uses = example(profile_id)
    result = compile_armor_planner_links(document, inventory, profiles, uses, ROOT)
    assert {r['occurrence_id'] for r in result} == {r['id'] for r in inventory['occurrences']}
    assert all(r['profile_id'] == profile_id and r['state'] == 'reviewed' for r in result)


@pytest.mark.parametrize(
    'failure',
    [
        'missing-use',
        'historical',
        'hardcore',
        'unreviewed',
        'partial',
        'changed-role',
        'wrong-merc',
        'wrong-slot',
        'wrong-recipe',
        'missing-rune',
        'duplicate',
        'wrong-tab',
        'unknown-scope',
    ],
)
def test_armor_link_rejects_incomplete_or_incompatible_proof(failure):
    document, inventory, profiles, uses = example()
    row = document['rows'][0]
    if failure == 'missing-use':
        uses = []
    elif failure in {'historical', 'hardcore', 'unreviewed', 'partial'}:
        key, value = {
            'historical': ('historical', True),
            'hardcore': ('scope', 'hardcore'),
            'unreviewed': ('review_state', 'pending'),
            'partial': ('source_coverage', {'kind': 'preparation_only'}),
        }[failure]
        uses[0][key] = value
        row['use_sha256'] = fingerprint(uses[0])
    elif failure == 'changed-role':
        profiles[0]['variant'] = 'Other'
        row['profile_sha256'] = fingerprint(profiles[0])
    elif failure == 'wrong-merc':
        row['planner_endorsement']['mercenary_type'] = 'Act 2 Prayer'
    elif failure == 'wrong-slot':
        row['planner_endorsement']['slot'] = 'head'
    elif failure == 'wrong-recipe':
        row['planner_endorsement']['expected_item']['socketedItems'].reverse()
    elif failure == 'missing-rune':
        row['children'].pop()
    elif failure == 'duplicate':
        document['rows'].append(deepcopy(row))
    elif failure == 'unknown-scope':
        document['scope'] = 'any_planner'
    else:
        row['planner_endorsement']['guide_tab'] = 'Magic Find'
    with pytest.raises(ValueError, match=r'[Aa]rmor|[Pp]lanner|[Ee]ndorsed|[Gg]uide|[Pp]rofile'):
        compile_armor_planner_links(document, inventory, profiles, uses, ROOT)


@pytest.mark.parametrize(
    ('mercenary_type', 'mercenary_id'),
    [('Act 2 Might', '11'), ('Act 2 Holy Freeze', '10'), ('Act 2 Prayer', '6'), ('Act 5 Frenzy', '36')],
)
def test_native_armor_wearer_requires_matching_act_and_skill(mercenary_type, mercenary_id):
    game = read('pricing/raw/mr/planners/game-data.json')
    evidence = {'mercenary_type': mercenary_type, 'mercenary_id': mercenary_id}
    validate_armor_mercenary(evidence, game)
    for wrong_id in {'11', '10', '6', '36', 'missing'} - {mercenary_id}:
        with pytest.raises(ValueError, match='native mercenary'):
            validate_armor_mercenary({**evidence, 'mercenary_id': wrong_id}, game)


def test_selected_base_branch_preserves_full_runtime_rule():
    document, inventory, profiles, uses = example('blessed-hammer-paladin-2-merc-chains-honor')
    original = deepcopy(profiles)
    document['rows'][0]['planner_endorsement']['equipment_branches'] = {'/all/6': 0}
    result = compile_armor_planner_links(document, inventory, profiles, uses, ROOT)
    assert len(result) == 5
    assert profiles == original


@pytest.mark.parametrize(
    'branches',
    [
        {'/all/6': 1},
        {'/all/6': 2},
        {'/all/6': -1},
        {'/all/6': True},
        {'/all/6': '0'},
        {'/all/0': 0},
        {'/all/06': 0},
        {'/all/6': 0, '/all/6/any/1/all/1': 0},
        {},
        [],
    ],
)
def test_equipment_branch_cannot_borrow_another_base_or_drop_requirements(branches):
    document, inventory, profiles, uses = example('blessed-hammer-paladin-2-merc-chains-honor')
    document['rows'][0]['planner_endorsement']['equipment_branches'] = branches
    with pytest.raises(ValueError, match=r'[Bb]ranch|[Ee]ndorsed'):
        compile_armor_planner_links(document, inventory, profiles, uses, ROOT)


def shared_example():
    document, inventory, profiles, uses = example('smite-shared-treachery')
    evidence = document['rows'][0]['planner_endorsement']
    quote = next(q for q in profiles[0]['source']['quotes'] if 'Mercenary can hold Treachery' in q)
    guide = read(evidence['guide']['path'])['sources'][evidence['guide_source']]
    evidence.update(
        shared_armor='mercenary_player_fade',
        mercenary_id='11',
        mercenary_type='Act 2 Might',
        ethereal_scope='nonethereal_only',
        quote=quote,
        section_index=next(i for i, section in enumerate(guide['sections']) if quote in section['text']),
    )
    return document, inventory, profiles, uses


def test_shared_armor_links_example_without_requiring_its_base_or_mutating_role():
    document, inventory, profiles, uses = shared_example()
    original = deepcopy(profiles)
    result = compile_armor_planner_links(document, inventory, profiles, uses, ROOT)
    assert len(result) == 4
    assert profiles == original


@pytest.mark.parametrize('change', ['scope', 'mercenary', 'quote', 'ethereal_scope', 'recipe', 'ethereal'])
def test_shared_armor_keeps_wearer_nonethereal_recipe_and_guide_requirements(change):
    document, inventory, profiles, uses = shared_example()
    evidence = document['rows'][0]['planner_endorsement']
    if change == 'scope':
        evidence['shared_armor'] = 'any_armor'
    elif change == 'mercenary':
        evidence['mercenary_type'] = 'Act 2 Prayer'
    elif change == 'quote':
        evidence['quote'] = profiles[0]['source']['quotes'][0]
    elif change == 'ethereal_scope':
        evidence.pop('ethereal_scope')
    elif change == 'recipe':
        evidence['expected_item']['socketedItems'].reverse()
    else:
        evidence['expected_item']['ethereal'] = True
    with pytest.raises(ValueError, match=r'[Ss]hared|[Pp]lanner|[Ee]ndorsed'):
        compile_armor_planner_links(document, inventory, profiles, uses, ROOT)
