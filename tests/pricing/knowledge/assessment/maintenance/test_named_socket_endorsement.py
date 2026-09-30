"""Named source examples need native stats, correct rune and original wearer guards."""

from copy import deepcopy

import pytest

from pricing.knowledge.builds import decode_planner
from tests.pricing.knowledge.assessment.maintenance.test_spirit_loadout_endorsement import pin
from tests.pricing.knowledge.assessment.maintenance.test_swap_planner_links import PROFILES, read


IDS = (
    'hammer-mf-stealskull-merc',
    'lightning-fury-ubers-gaze-merc',
    'fire-warlock-standard-ars-diabolos',
    'fire-warlock-mf-ars-diabolos',
)
PATHS = {
    'metadata': 'inventory_tracking/items/data/item_metadata.json',
    'uniques': 'third-parties/d2data/json/uniqueitems.json',
    'properties': 'third-parties/d2data/json/properties.json',
    'stats': 'third-parties/d2data/json/itemstatcost.json',
    'armor': 'third-parties/d2data/json/armor.json',
    'gems': 'third-parties/d2data/json/gems.json',
    'game': 'pricing/raw/mr/planners/game-data.json',
}


def example(pid=IDS[0]):
    role = deepcopy(next(r for r in read(PROFILES)['profiles'] if r['id'] == pid))
    row = next(
        r
        for r in read('pricing/data/appraisal-planner-candidate-tab-audit.json')['rows']
        if r['profile_id'] == pid and r['state'] == 'exact_tab_reference'
    )
    planner = decode_planner(read(row['planner_path']))
    profile = planner['profiles'][row['planner_profile_index']]
    slot = 'head' if role['side'] == 'merc' else 'larm'
    item = deepcopy(planner['items'][str(profile['mercItems' if role['side'] == 'merc' else 'items'][slot])])
    source = role['source']
    document = read(source['path'])
    aggregate = source['path'].endswith('wp-a-builds.json')
    index = row['planner_profile_index']
    variant = document[role['build']]['variants'][index] if aggregate else document['variants'][index]
    prefix = f'/{role["build"]}/variants' if aggregate else '/variants'
    quote = variant[role['side']][role['slot']][0]
    evidence = {
        'named_socket': 'native_unique',
        'coverage': 'merc_rune_socket_component' if role['side'] == 'merc' else 'player_rune_socket_component',
        'slot': slot,
        'expected_item': item,
        'guide_tab': role['variant'],
        'quote': quote,
        'equipment_quote': {**source, 'locator': f'{prefix}/{index}/{role["side"]}/{role["slot"]}/0'},
        'native_sources': {k: pin(p) for k, p in PATHS.items()},
        'mercenary_id': str(profile.get('merc')),
    }
    build = read('pricing/data/wp-a-builds.json')[role['build']]
    return evidence, role, build


def validate(e, role, build):
    from pricing.knowledge.assessment.maintenance.named_socket_endorsement import named_socket_role

    return named_socket_role(e, role, build, lambda p: read(p['path']))


@pytest.mark.parametrize('pid', IDS)
def test_named_socket_proof_keeps_original_runtime_guards(pid):
    args = example(pid)
    before = deepcopy(args)
    proof = validate(*args)
    assert args == before
    assert proof['must']['all'][0] == args[1]['must']
    assert proof.get('depends_on') == args[1].get('depends_on')
    assert proof['source']['quotes'][-1] == args[0]['quote']


@pytest.mark.parametrize(
    'change',
    [
        'stat-missing',
        'stat-low',
        'stat-high',
        'stat-bool',
        'wrong-base',
        'wrong-rune',
        'missing-rune',
        'wrong-merc',
        'optional-merc',
        'missing-guard',
        'perfect-minimum',
        'wrong-tab',
        'eth-bool',
    ],
)
def test_named_socket_rejects_invalid_native_or_role_evidence(change):
    e, role, build = example()
    item = e['expected_item']
    if change.startswith('stat-'):
        if change == 'stat-missing':
            item['stats'].pop('lifedrainmindam')
        else:
            item['stats']['lifedrainmindam'] = {'stat-low': 4, 'stat-high': 6, 'stat-bool': True}[change]
    elif change == 'wrong-base':
        item['base'] = 'invalid-base'
    elif change == 'wrong-rune':
        item['socketedItems'] = ['invalid-rune']
    elif change == 'missing-rune':
        item['socketedItems'] = []
    elif change == 'wrong-merc':
        e['mercenary_id'] = '11'
    elif change == 'optional-merc':
        role['depends_on'][0]['required'] = False
    elif change == 'missing-guard':
        role['must']['all'].pop()
    elif change == 'perfect-minimum':
        role['must']['all'][1]['value'] = 50
    elif change == 'wrong-tab':
        e['guide_tab'] = 'Starter'
    else:
        item['ethereal'] = 1
    with pytest.raises(ValueError, match=r'Named|Equipment|mercenary'):
        validate(e, role, build)


def endorsement(pid=IDS[0]):
    e, role, build = example(pid)
    row = next(
        r
        for r in read('pricing/data/appraisal-planner-candidate-tab-audit.json')['rows']
        if r['profile_id'] == pid and r['state'] == 'exact_tab_reference'
    )
    planner = decode_planner(read(row['planner_path']))
    profile = planner['profiles'][row['planner_profile_index']]
    container = 'mercItems' if role['side'] == 'merc' else 'items'
    item_id = str(profile[container][e['slot']])
    e.update(
        guide=pin('pricing/data/appraisal-guide-sections.json'),
        guide_source=f'pricing/raw/mr/guides__{role["build"]}.html',
        variant_alias=role['variant'],
        planner=pin(row['planner_path']),
        profile_index=row['planner_profile_index'],
        profile_uid=profile['uid'],
        profile_name=profile['name'],
        player_class_code=profile['class'],
        item_id=item_id,
        rune_definitions=pin(PATHS['gems']),
        ethereal_scope='nonethereal_only' if role['side'] == 'player' else 'reviewed_native_variant',
    )
    if role['side'] == 'merc':
        e['mercenary_type'] = role['depends_on'][0]['when']['value']
    return e, role, build


@pytest.mark.parametrize('pid', IDS)
def test_selected_named_socket_guide_and_native_endorsement(pid):
    from pricing.knowledge.assessment.maintenance.inventory import ROOT
    from pricing.knowledge.assessment.maintenance.planner_endorsement import validate_endorsement

    e, role, build = endorsement(pid)
    validate_endorsement({'planner_endorsement': e}, role, build, ROOT, lambda p: read(p['path']))
