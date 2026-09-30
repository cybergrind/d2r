"""Selected CTA/Spirit swaps require native skill, companion and source evidence."""

import hashlib
import json
from copy import deepcopy
from functools import lru_cache

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.inventory import ROOT


PROFILES = 'pricing/data/appraisal-build-profiles.json'
USES = 'pricing/knowledge/assessment/rules/guide_use_reviews.json'
GUIDE = 'pricing/data/appraisal-guide-sections.json'


@lru_cache
def read(path):
    return json.loads((ROOT / path).read_bytes())


def example(profile_id='echoing-standard-cta-prebuff'):
    audit = read('pricing/data/appraisal-weapon-recipe-candidate-audit.json')
    prepared = next(r for r in audit['rows'] if r['profile_id'] == profile_id)
    role = deepcopy(next(r for r in read(PROFILES)['profiles'] if r['id'] == profile_id))
    use = deepcopy(next(r for r in read(USES)['uses'] if r['profile_id'] == profile_id))
    guide_path = f'pricing/raw/mr/guides__{role["build"]}.html'
    variant_index = int(role['source']['locator'].split('/')[3])
    labels = read(role['source']['path'])[role['build']]['variants'][variant_index]['player']['Weapon-Swap']
    quote_index, quote = next((i, q) for i, q in enumerate(labels) if q in role['source']['quotes'])

    def pin(path):
        return {'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}

    evidence = {
        'prebuff_swap': 'cta_spirit',
        'ethereal_scope': 'unrestricted_reviewed_role',
        'coverage': 'player_runeword_component',
        'guide': pin(GUIDE),
        'guide_source': guide_path,
        'equipment_quote': {
            **pin(role['source']['path']),
            'locator': role['source']['locator'] + f'/player/Weapon-Swap/{quote_index}',
        },
        'quote': quote,
        'variant_alias': role['variant'],
        'guide_tab': role['variant'],
        'planner': prepared['planner'],
        'profile_index': prepared['profile_index'],
        'profile_uid': prepared['profile_uid'],
        'profile_name': role['variant'],
        'player_class_code': 'war',
        'slot': prepared['slot'],
        'item_id': prepared['item_id'],
        'expected_item': prepared['item'],
        'recipe_sources': prepared['recipe_sources'],
        'stat_definitions': pin('third-parties/d2data/json/itemstatcost.json'),
        'companion': prepared['swap_companion'],
    }
    inventory = read('pricing/data/appraisal-guide-inventory.json')
    parent = next(r for r in inventory['occurrences'] if r['id'] == prepared['parent_occurrence_id'])
    children = sorted(
        [
            r
            for r in inventory['occurrences']
            if r['source_id'] == parent['source_id']
            and r['source_locator'].startswith(parent['source_locator'] + '/socketedItems/')
        ],
        key=lambda r: r['source_locator'],
    )
    occurrences = [parent, *children]
    identities = {r['identity_id'] for r in occurrences}
    subset = {
        'occurrences': occurrences,
        'identities': [r for r in inventory['identities'] if r['id'] in identities],
        'sources': [r for r in inventory['sources'] if r['id'] == parent['source_id']],
    }

    def ref(row):
        return {'occurrence_id': row['id'], 'sha256': fingerprint(row)}

    row = {
        'id': profile_id + ':planner:' + parent['id'],
        'profile_id': profile_id,
        'profile_sha256': fingerprint(role),
        'use_sha256': fingerprint(use),
        'parent': ref(parent),
        'children': [ref(r) for r in children],
        'planner_endorsement': evidence,
        'reviewed_at': '2026-09-30',
        'reason': 'Exact CTA swap and native skills with Spirit in the selected swap offhand.',
    }
    paths = {
        PROFILES,
        USES,
        GUIDE,
        guide_path,
        role['source']['path'],
        prepared['planner']['path'],
        'third-parties/d2data/json/itemstatcost.json',
        'third-parties/d2data/json/misc.json',
    }
    paths.update(p['path'] for p in prepared['recipe_sources'].values())
    paths.update(p['path'] for p in prepared['swap_companion']['recipe_sources'].values())
    document = {
        'schema_version': 1,
        'scope': 'reviewed_cta_spirit_swaps',
        'inputs': {path: pin(path)['sha256'] for path in paths},
        'rows': [row],
    }
    return deepcopy(document), deepcopy(subset), [role], [use]


def compile_example(document, inventory, profiles, uses):
    from pricing.knowledge.assessment.maintenance.swap_planner_links import compile_swap_planner_links

    return compile_swap_planner_links(document, inventory, profiles, uses, ROOT)


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
    ],
)
def test_exact_cta_swap_links_only_its_six_occurrences_and_preserves_runtime_rule(profile_id):
    document, inventory, profiles, uses = example(profile_id)
    original = deepcopy((document, profiles))
    result = compile_example(document, inventory, profiles, uses)
    assert {r['occurrence_id'] for r in result} == {r['id'] for r in inventory['occurrences']}
    assert len(result) == 6
    assert all(r['profile_id'] == profile_id for r in result)
    assert (document, profiles) == original


@pytest.mark.parametrize(
    'change',
    [
        'missing-use',
        'wrong-tab',
        'wrong-companion-slot',
        'wrong-companion-id',
        'companion-runes',
        'missing-companion',
        'bo-low',
        'bo-high',
        'bc-missing',
        'bool-skill',
        'stat-source',
        'ethereal-scope',
        'invented-ethereal',
        'rune-order',
        'missing-rune-link',
        'wrong-class',
        'stale-guide',
        'scope',
    ],
)
def test_swap_rejects_incomplete_or_changed_proof(change):
    document, inventory, profiles, uses = example()
    row = document['rows'][0]
    e = row['planner_endorsement']
    if change == 'missing-use':
        uses = []
    elif change == 'wrong-tab':
        e['guide_tab'] = 'Starter'
    elif change == 'wrong-companion-slot':
        e['companion']['locator'] = e['companion']['locator'].replace('/larm2', '/larm')
    elif change == 'wrong-companion-id':
        e['companion']['item_id'] = e['item_id']
    elif change == 'companion-runes':
        e['companion']['item']['socketedItems'].reverse()
    elif change == 'missing-companion':
        e.pop('companion')
    elif change in ('bo-low', 'bo-high', 'bc-missing', 'bool-skill'):
        stats = e['expected_item']['stats']
        if change == 'bc-missing':
            stats.pop('item_nonclassskill#155')
        else:
            stats['item_nonclassskill#149'] = {'bo-low': 0, 'bo-high': 7, 'bool-skill': True}[change]
    elif change == 'stat-source':
        e['stat_definitions']['path'] = 'arbitrary.json'
    elif change == 'ethereal-scope':
        e.pop('ethereal_scope')
    elif change == 'invented-ethereal':
        e['expected_item']['ethereal'] = False
    elif change == 'rune-order':
        e['expected_item']['socketedItems'].reverse()
    elif change == 'missing-rune-link':
        row['children'].pop()
    elif change == 'wrong-class':
        e['player_class_code'] = 'pal'
    elif change == 'stale-guide':
        e['guide']['sha256'] = '0' * 64
    else:
        document['scope'] = 'any_swap'
    with pytest.raises(ValueError, match=r'CTA|[Ss]wap|[Pp]lanner|[Ee]ndorsed|[Gg]uide|[Ee]quipment'):
        compile_example(document, inventory, profiles, uses)


@pytest.mark.parametrize('change', ['optional-spirit', 'missing-spirit', 'ethereal-restriction', 'changed-skill-guard'])
def test_cta_proof_preserves_original_unrestricted_role_and_required_companion(change):
    from pricing.knowledge.assessment.maintenance.cta_swap_endorsement import cta_swap_role

    document, _, profiles, _ = example()
    e, role = document['rows'][0]['planner_endorsement'], profiles[0]
    if change == 'optional-spirit':
        role['depends_on'][0]['required'] = False
    elif change == 'missing-spirit':
        role['depends_on'] = []
    elif change == 'ethereal-restriction':
        role['must']['all'].append({'op': 'fact_eq', 'field': 'ethereal', 'value': True})
    else:
        role['must']['all'][-1]['value'] = 5
    with pytest.raises(ValueError, match='preserve'):
        cta_swap_role(e, role, read(role['source']['path'])[role['build']], lambda ref: read(ref['path']))


@pytest.mark.parametrize('change', ['sibling-slot', 'wrong-build', 'stale-pin', 'invented-quote', 'both-sources'])
def test_equipment_quote_is_exactly_bound_to_primary_swap_entry(change):
    document, inventory, profiles, uses = example()
    e = document['rows'][0]['planner_endorsement']
    if change == 'sibling-slot':
        e['equipment_quote']['locator'] = e['equipment_quote']['locator'].replace('Weapon-Swap', 'Weapon')
    elif change == 'wrong-build':
        e['equipment_quote']['path'] = 'pricing/data/wp-a-variants/smite-paladin.json'
    elif change == 'stale-pin':
        e['equipment_quote']['sha256'] = '0' * 64
    elif change == 'invented-quote':
        e['quote'] = 'Call to Arms in any slot'
    else:
        e['section_index'] = 0
    with pytest.raises(ValueError, match=r'CTA|[Ss]wap|[Pp]lanner|[Ee]ndorsed|[Gg]uide|[Ee]quipment'):
        compile_example(document, inventory, profiles, uses)


@pytest.mark.parametrize('value', [0, 7, True, None])
def test_skill_bounds_are_checked_independently_of_snapshot_equality(value):
    from pricing.knowledge.assessment.maintenance.cta_swap_endorsement import skill_requirements

    document, _, _, _ = example()
    e = document['rows'][0]['planner_endorsement']
    item = e['expected_item']
    item['stats']['item_nonclassskill#149'] = value
    tables = {key: read(pin['path']) for key, pin in e['recipe_sources'].items()}
    with pytest.raises(ValueError, match='native skill roll'):
        skill_requirements(item, tables, read(e['stat_definitions']['path']))
