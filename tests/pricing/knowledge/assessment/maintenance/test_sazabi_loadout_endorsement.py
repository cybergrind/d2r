"""Mercenary Sazabi source proof preserves complete set and native rune effects."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from pricing.knowledge.builds import decode_planner
from tests.pricing.knowledge.assessment.maintenance.test_spirit_loadout_endorsement import pin
from tests.pricing.knowledge.assessment.maintenance.test_swap_planner_links import read


PATHS = {
    'profiles': 'pricing/data/appraisal-build-profiles.json',
    'game': 'pricing/raw/mr/planners/game-data.json',
    'sets': 'third-parties/d2data/json/setitems.json',
    'armor': 'third-parties/d2data/json/armor.json',
    'weapons': 'third-parties/d2data/json/weapons.json',
    'gems': 'third-parties/d2data/json/gems.json',
}
SLOTS = {'helm': 'head', 'armor': 'tors', 'sword': 'rarm'}


def example(suffix='helm'):
    tables = {key: deepcopy(read(path)) for key, path in PATHS.items()}
    role = deepcopy(next(r for r in tables['profiles']['profiles'] if r['id'] == 'echoing-ubers-sazabi-' + suffix))
    planner = deepcopy(decode_planner(read('pricing/raw/mr/planners/ucgz20le.json')))
    evidence = {
        'set_loadout': 'sazabi_frenzy',
        'coverage': 'merc_set_component',
        'ethereal_scope': 'legal_nonethereal_set',
        'slot': SLOTS[suffix],
        'profile_index': 3,
        'planner': pin('pricing/raw/mr/planners/ucgz20le.json'),
        'set_sources': {key: pin(path) for key, path in PATHS.items()},
        'ethereal_mechanics': pin('third-parties/D2MOO/source/D2Game/src/ITEMS/Items.cpp'),
    }
    return evidence, role, planner, tables


def validate(args):
    from pricing.knowledge.assessment.maintenance import sazabi_loadout_endorsement as module
    from pricing.knowledge.assessment.maintenance.inventory import ROOT

    evidence, role, planner, tables = args
    by_path = {PATHS[key]: value for key, value in tables.items()}
    by_path[evidence['planner']['path']] = read(evidence['planner']['path'])
    with patch.object(module, 'decode_planner', return_value=planner):
        return module.sazabi_loadout_role(evidence, role, {'class': 'Warlock'}, lambda p: by_path[p['path']], ROOT)


@pytest.mark.parametrize('suffix', SLOTS)
def test_sazabi_source_checks_actual_set_and_retains_runtime_companions(suffix):
    args = example(suffix)
    before = deepcopy(args)
    proof = validate(args)
    assert args == before
    assert proof['companions'] == args[1]['companions']
    assert proof['required_rune'] == args[1]['required_rune']
    assert proof['must']['all'][0] == args[1]['must']
    assert any(r['locator'].startswith('/r') for r in proof['source']['corroborating'])


@pytest.mark.parametrize(
    'change',
    [
        'missing-piece',
        'player-piece',
        'wrong-base',
        'wrong-rune',
        'empty-socket',
        'ethereal',
        'unknown-flag',
        'wrong-merc',
        'missing-companion-guard',
        'wrong-rune-guard',
        'wrong-quality',
        'changed-native-effect',
        'missing-mechanics',
    ],
)
def test_sazabi_source_rejects_incomplete_or_changed_setup(change):
    args = example()
    e, role, planner, tables = args
    merc = planner['profiles'][3]['mercItems']
    armor = planner['items'][str(merc['tors'])]
    if change == 'missing-piece':
        merc.pop('tors')
    elif change == 'player-piece':
        planner['profiles'][3]['items']['tors'] = merc.pop('tors')
    elif change == 'wrong-base':
        armor['base'] = planner['items'][str(merc['head'])]['base']
    elif change == 'wrong-rune':
        armor['socketedItems'] = planner['items'][str(merc['head'])]['socketedItems']
    elif change == 'empty-socket':
        armor['socketedItems'] = []
    elif change == 'ethereal':
        armor['ethereal'] = True
    elif change == 'unknown-flag':
        armor['ethereal'] = None
    elif change == 'wrong-merc':
        planner['profiles'][3]['merc'] = 11
    elif change == 'missing-companion-guard':
        role['companions'].pop()
    elif change == 'wrong-rune-guard':
        role['required_rune'] = 'Ber Rune'
    elif change == 'wrong-quality':
        armor['quality'] = 6
    elif change == 'changed-native-effect':
        tables['gems'][armor['socketedItems'][0]]['helmMod1Min'] = 0
    else:
        e.pop('ethereal_mechanics')
    with pytest.raises(ValueError, match=r'Sazabi|Planner set|mercenary'):
        validate(args)


def endorsement(suffix):
    e, role, planner, _ = example(suffix)
    profile = planner['profiles'][3]
    guide_path = f'pricing/raw/mr/guides__{role["build"]}.html'
    guide_index = 'pricing/data/appraisal-guide-sections.json'
    quote = next(q for q in role['source']['quotes'] if q.startswith('Act 5 Frenzy Mercenary'))
    sections = read(guide_index)['sources'][guide_path]['sections']
    index = next(i for i, section in enumerate(sections) if quote in section['text'])
    item_id = str(profile['mercItems'][e['slot']])
    e.update(
        guide=pin(guide_index),
        guide_source=guide_path,
        quote=quote,
        section_index=index,
        variant_alias=role['variant'],
        guide_tab=role['variant'],
        profile_uid=profile['uid'],
        profile_name=profile['name'],
        player_class_code=profile['class'],
        item_id=item_id,
        expected_item=planner['items'][item_id],
        mercenary_id=str(profile['merc']),
        mercenary_type='Act 5 Frenzy',
        rune_definitions=pin(PATHS['gems']),
    )
    build = read(role['source']['path'])[role['build']]
    return e, role, build


@pytest.mark.parametrize('suffix', SLOTS)
def test_sazabi_selected_guide_endorses_mercenary_piece_with_native_socket(suffix):
    from pricing.knowledge.assessment.maintenance.inventory import ROOT
    from pricing.knowledge.assessment.maintenance.planner_endorsement import validate_endorsement

    e, role, build = endorsement(suffix)
    validate_endorsement({'planner_endorsement': e}, role, build, ROOT, lambda p: read(p['path']))
