"""Native weapon source examples retain base alternatives and wearer requirements."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.builds import decode_planner
from tests.pricing.knowledge.assessment.maintenance.test_swap_planner_links import GUIDE, PROFILES, USES, read


def example(profile_id='hammer-standard-insight-merc'):
    import hashlib

    prepared = next(
        r
        for r in read('pricing/data/appraisal-weapon-recipe-candidate-audit.json')['rows']
        if r['profile_id'] == profile_id
    )
    role = deepcopy(next(r for r in read(PROFILES)['profiles'] if r['id'] == profile_id))
    use = deepcopy(next(r for r in read(USES)['uses'] if r['profile_id'] == profile_id))
    source = role['source']
    variant_index = int(source['locator'].split('/')[3])
    variant = read(source['path'])[role['build']]['variants'][variant_index]
    quote_index, quote = next((i, q) for i, q in enumerate(variant[role['side']]['Weapon']) if q in source['quotes'])

    def pin(path):
        return {'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}

    planner = decode_planner(read(prepared['planner']['path']))
    profile = planner['profiles'][prepared['profile_index']]
    guide_path = f'pricing/raw/mr/guides__{role["build"]}.html'
    insight = role['names'] == ['Insight']
    evidence = {
        'weapon_component': 'insight_mercenary' if insight else 'hand_of_justice_player',
        'coverage': 'merc_runeword_component' if insight else 'player_runeword_component',
        'ethereal_scope': 'known_status_example' if insight else 'nonethereal_only',
        'guide': pin(GUIDE),
        'guide_source': guide_path,
        'quote': quote,
        'equipment_quote': {
            **pin(source['path']),
            'locator': f'/{role["build"]}/variants/{variant_index}/{role["side"]}/Weapon/{quote_index}',
        },
        'variant_alias': role['variant'],
        'guide_tab': role['variant'],
        'planner': prepared['planner'],
        'profile_index': prepared['profile_index'],
        'profile_uid': prepared['profile_uid'],
        'profile_name': role['variant'],
        'player_class_code': profile['class'],
        'slot': prepared['slot'],
        'item_id': prepared['item_id'],
        'expected_item': prepared['item'],
        'recipe_sources': prepared['recipe_sources'],
        'stat_definitions': pin('third-parties/d2data/json/itemstatcost.json'),
    }
    if insight:
        choice = next(
            i for i, child in enumerate(role['must']['all'][4]['any']) if child['value'] == prepared['item']['base']
        )
        evidence.update(
            equipment_branches={'/all/4': choice}, mercenary_type='Act 2 Holy Freeze', mercenary_id=str(profile['merc'])
        )
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
        'reason': 'Selected native weapon recipe and aura with required bearer; no complete loadout claim.',
    }
    paths = {
        PROFILES,
        USES,
        GUIDE,
        guide_path,
        source['path'],
        prepared['planner']['path'],
        'third-parties/d2data/json/itemstatcost.json',
        'third-parties/d2data/json/misc.json',
    }
    paths.update(ref['path'] for ref in evidence['recipe_sources'].values())
    document = {
        'schema_version': 1,
        'scope': 'reviewed_weapon_components',
        'inputs': {p: pin(p)['sha256'] for p in paths},
        'rows': [row],
    }
    subset = {
        'occurrences': occurrences,
        'identities': [r for r in inventory['identities'] if r['id'] in identities],
        'sources': [r for r in inventory['sources'] if r['id'] == parent['source_id']],
    }
    return deepcopy(document), deepcopy(subset), [role], [use]


def compile_example(document, inventory, profiles, uses):
    from pricing.knowledge.assessment.maintenance.weapon_planner_links import compile_weapon_planner_links

    return compile_weapon_planner_links(document, inventory, profiles, uses, ROOT)


@pytest.mark.parametrize(
    'profile_id',
    [
        'hammer-standard-insight-merc',
        'hammer-mf-insight-merc',
        'dream-paladin-hand-of-justice-hybrid-source-recipe',
    ],
)
def test_weapon_links_exact_five_occurrences_without_changing_runtime_role(profile_id):
    document, inventory, roles, uses = example(profile_id)
    original = deepcopy((document, roles))
    result = compile_example(document, inventory, roles, uses)
    assert len(result) == 5
    assert {r['occurrence_id'] for r in result} == {r['id'] for r in inventory['occurrences']}
    assert (document, roles) == original


@pytest.mark.parametrize(
    'change',
    [
        'wrong-branch',
        'wrong-merc',
        'unknown-ethereal',
        'aura-low',
        'aura-high',
        'missing-aura',
        'bool-aura',
        'wrong-class',
        'quote-slot',
        'quote-value',
        'rune-order',
        'missing-child',
        'missing-use',
        'wrong-tab',
    ],
)
def test_weapon_review_rejects_conflicting_source_mechanics_or_wearer(change):
    document, inventory, roles, uses = example()
    e = document['rows'][0]['planner_endorsement']
    if change == 'wrong-branch':
        e['equipment_branches']['/all/4'] = 0
    elif change == 'wrong-merc':
        e['mercenary_id'] = '11'
    elif change == 'unknown-ethereal':
        e['expected_item'].pop('ethereal')
    elif change in ('aura-low', 'aura-high', 'bool-aura'):
        e['expected_item']['stats']['item_aura#120'] = {'aura-low': 11, 'aura-high': 18, 'bool-aura': True}[change]
    elif change == 'missing-aura':
        e['expected_item']['stats'].pop('item_aura#120')
    elif change == 'wrong-class':
        e['player_class_code'] = 'war'
    elif change == 'quote-slot':
        e['equipment_quote']['locator'] = e['equipment_quote']['locator'].replace('/merc/', '/player/')
    elif change == 'quote-value':
        e['quote'] = 'Insight in any base'
    elif change == 'rune-order':
        e['expected_item']['socketedItems'].reverse()
    elif change == 'missing-child':
        document['rows'][0]['children'].pop()
    elif change == 'missing-use':
        uses = []
    else:
        e['guide_tab'] = 'Starter'
    with pytest.raises(ValueError, match=r'[Ww]eapon|[Pp]lanner|[Ee]ndorsed|[Gg]uide|[Ee]quipment'):
        compile_example(document, inventory, roles, uses)


@pytest.mark.parametrize(
    'change', ['optional-wearer', 'missing-wearer', 'wrong-wearer', 'aura-guard', 'ethereal-guard']
)
def test_insight_proof_cannot_drop_dependencies_or_narrow_runtime_ethereal_scope(change):
    from pricing.knowledge.assessment.maintenance.planner_equipment_branch import equipment_branch
    from pricing.knowledge.assessment.maintenance.weapon_component_endorsement import weapon_component_role

    document, _, roles, _ = example()
    e, role = document['rows'][0]['planner_endorsement'], roles[0]
    role['must'] = equipment_branch(role['must'], e['equipment_branches'])
    if change == 'optional-wearer':
        role['depends_on'][0]['required'] = False
    elif change == 'missing-wearer':
        role['depends_on'] = []
    elif change == 'wrong-wearer':
        role['depends_on'][0]['when']['any'][0]['value'] = 'Act 2 Might'
    elif change == 'aura-guard':
        role['must']['all'][3]['value'] = 1
    else:
        role['must']['all'].append({'op': 'fact_eq', 'field': 'ethereal', 'value': True})
    with pytest.raises(ValueError, match='preserve'):
        weapon_component_role(e, role, read(role['source']['path'])[role['build']], lambda ref: read(ref['path']))


@pytest.mark.parametrize(
    ('profile_id', 'value'),
    [
        ('hammer-standard-insight-merc', 11),
        ('hammer-standard-insight-merc', 18),
        ('hammer-standard-insight-merc', True),
        ('dream-paladin-hand-of-justice-hybrid-source-recipe', 15),
        ('dream-paladin-hand-of-justice-hybrid-source-recipe', 17),
    ],
)
def test_native_aura_bounds_independent_of_snapshot_equality(profile_id, value):
    from pricing.knowledge.assessment.maintenance.weapon_component_endorsement import native_aura

    document, _, roles, _ = example(profile_id)
    e, role = document['rows'][0]['planner_endorsement'], roles[0]
    item = e['expected_item']
    aura_key = next(key for key in item['stats'] if key.startswith('item_aura#'))
    item['stats'][aura_key] = value
    tables = {key: read(pin['path']) for key, pin in e['recipe_sources'].items()}
    with pytest.raises(ValueError, match='native aura'):
        native_aura(item, role['names'][0], tables, read(e['stat_definitions']['path']))


def test_hand_of_justice_ethereal_example_is_rejected():
    args = example('dream-paladin-hand-of-justice-hybrid-source-recipe')
    args[0]['rows'][0]['planner_endorsement']['expected_item']['ethereal'] = True
    with pytest.raises(ValueError, match='requirements'):
        compile_example(*args)
