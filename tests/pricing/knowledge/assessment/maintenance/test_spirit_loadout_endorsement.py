"""Spirit source examples retain actual active FCR and named companions."""

import hashlib
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.assessment.maintenance.planner_fcr import SOURCE_PATHS
from tests.pricing.knowledge.assessment.maintenance.test_swap_planner_links import read


def pin(path):
    return {'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}


def example(index=1):
    roles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    profile_id = 'hammer-standard-spirit-shield' if index == 1 else 'hammer-mf-spirit-shield'
    role = deepcopy(next(r for r in roles if r['id'] == profile_id))
    evidence = {
        'spirit_loadout': 'hammer_active',
        'coverage': 'player_runeword_component',
        'ethereal_scope': 'unrestricted_reviewed_role',
        'slot': 'larm',
        'profile_index': index,
        'planner': pin('pricing/raw/mr/planners/f80206a8.json'),
        'fcr_sources': {k: pin(p) for k, p in SOURCE_PATHS.items()},
    }
    return evidence, role


def validate(evidence, role, read_json=lambda pin: read(pin['path'])):
    from pricing.knowledge.assessment.maintenance.spirit_loadout_endorsement import spirit_loadout_role

    return spirit_loadout_role(evidence, role, {'class': 'Paladin'}, read_json)


@pytest.mark.parametrize('index', [1, 2])
def test_spirit_loadout_preserves_original_rule_and_adds_native_recipe_evidence(index):
    evidence, role = example(index)
    original = deepcopy(role)
    result = validate(evidence, role)
    assert role == original
    assert result['must'] == original['must']
    assert result['depends_on'] == original['depends_on']
    assert result['source']['corroborating'][-1]['locator'] == '/Spirit'


@pytest.mark.parametrize(
    'change', ['optional', 'missing', 'lower-target', 'wrong-companion', 'eth-constraint', 'swap', 'missing-source']
)
def test_spirit_review_rejects_weakened_or_changed_scope(change):
    evidence, role = example()
    if change == 'optional':
        role['depends_on'][0]['required'] = False
    elif change == 'missing':
        role['depends_on'].pop()
    elif change == 'lower-target':
        role['depends_on'][0]['when']['value'] = 75
    elif change == 'wrong-companion':
        role['depends_on'][1]['when']['value'] = 'Unreviewed companion'
    elif change == 'eth-constraint':
        role['must']['all'].append({'op': 'fact_eq', 'field': 'ethereal', 'value': False})
    elif change == 'swap':
        evidence['slot'] = 'larm2'
    else:
        evidence['fcr_sources'].pop('properties')
    with pytest.raises(ValueError, match='Spirit'):
        validate(evidence, role)


def test_spirit_loadout_rejects_actual_fcr_shortfall():
    from pricing.knowledge.builds import decode_planner

    evidence, role = example()
    planner = deepcopy(decode_planner(read(evidence['planner']['path'])))
    profile = planner['profiles'][1]
    planner['items'][str(profile['items']['larm'])]['stats']['item_fastercastrate'] = 25
    # The source reader supplies the actual changed planner, not a claimed total.
    from unittest.mock import patch

    import pricing.knowledge.assessment.maintenance.spirit_loadout_endorsement as module

    with patch.object(module, 'decode_planner', return_value=planner), pytest.raises(ValueError, match=r'Spirit.*125'):
        validate(evidence, role)


@pytest.mark.parametrize('index', [1, 2])
def test_spirit_selected_guide_and_native_recipe_endorsement(index):
    from pricing.knowledge.assessment.maintenance.planner_endorsement import validate_endorsement
    from pricing.knowledge.assessment.maintenance.planner_runeword_endorsement import SOURCES
    from pricing.knowledge.builds import decode_planner

    evidence, role = example(index)
    planner = decode_planner(read(evidence['planner']['path']))
    profile = planner['profiles'][index]
    item_id = str(profile['items']['larm'])
    builds = read(role['source']['path'])
    labels = builds[role['build']]['variants'][index]['player']['Off-Hand']
    quote_index = labels.index('Spirit Sacred Targe')
    evidence.update(
        guide={'path': 'pricing/data/appraisal-guide-sections.json'},
        guide_source=f'pricing/raw/mr/guides__{role["build"]}.html',
        quote=labels[quote_index],
        equipment_quote={
            **role['source'],
            'locator': f'/{role["build"]}/variants/{index}/player/Off-Hand/{quote_index}',
        },
        variant_alias=role['variant'],
        guide_tab=role['variant'],
        profile_uid=profile['uid'],
        profile_name=profile['name'],
        player_class_code=profile['class'],
        item_id=item_id,
        expected_item=planner['items'][item_id],
        recipe_sources={k: pin(p) for k, p in SOURCES.items()},
    )
    validate_endorsement(
        {'planner_endorsement': evidence}, role, builds[role['build']], ROOT, lambda p: read(p['path'])
    )
