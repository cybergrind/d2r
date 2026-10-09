"""The Warlock Lean v2 profile: unique and set items shown by base, from the knowledge base's evidence."""

import json
import re
from pathlib import Path

import pytest

from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot import build_filter
from inventory_tracking.loot.build_filter import build, evidence, load_sources


D2DATA = Path('third-parties/d2data/json/base')


@pytest.fixture(scope='module')
def built():
    return build(json.loads(build_filter.TEMPLATE.read_text()), load_sources())


def rule(profile, name):
    [found] = [r for r in profile['rules'] if r['name'] == name]
    return found


def test_only_the_unique_set_rule_is_replaced_and_the_name_fits_the_game(built):
    profile, _ = built
    template = json.loads(build_filter.TEMPLATE.read_text())
    assert len(profile['name']) <= 13
    assert [r['name'] for r in profile['rules'] if not r['name'].startswith(('SHOW Unique', 'SHOW Set'))] == [
        r['name'] for r in template['rules'] if r['name'] != 'SHOW Unique Set'
    ]
    assert [r['name'] for r in profile['rules'][3:7]] == [
        'SHOW Unique ARMOR',
        'SHOW Unique WEAPONS',
        'SHOW Set ARMOR',
        'SHOW Set WEAPONS',
    ]
    for r in profile['rules']:
        assert len(r['name']) <= 32
        assert re.fullmatch(r'[A-Za-z0-9 _\-/.,]+', r['name'])


def test_every_code_is_a_real_base_of_the_rule_kind_and_categories_are_absent(built):
    profile, _ = built
    dumps = {
        label: set(json.loads((D2DATA / file).read_text()))
        for label, file in (('ARMOR', 'armor.json'), ('WEAPONS', 'weapons.json'))
    }
    for r in profile['rules'][3:7]:
        assert 'equipmentCategory' not in r  # a category would OR away the code list
        assert r['equipmentItemCode']
        assert set(r['equipmentItemCode']) <= dumps[r['name'].split()[-1]]


def test_worthwhile_bases_are_shown_and_evidence_free_low_bases_are_hidden(built):
    profile, names = built
    unique_armor, unique_weapons = rule(profile, 'SHOW Unique ARMOR'), rule(profile, 'SHOW Unique WEAPONS')
    assert {'uap', 'urn', 'xea'} <= set(unique_armor['equipmentItemCode'])  # Shako, Crown of Ages, Vipermagi: asks
    assert '7cr' in unique_weapons['equipmentItemCode']  # Azurewrath / Lightsabre: elite base, no ask pulled
    [bverrit] = [r['base_codes'] for r in metadata()['identities']['unique'].values() if r['name'] == 'Bverrit Keep']
    assert not set(bverrit) & set(unique_armor['equipmentItemCode'])  # Tower Shield: nothing in the KB wants it
    assert 'rin' not in unique_armor['equipmentItemCode']  # accessories stay with the accessories rule
    assert names['unique']['hidden']['Bverrit Keep'].startswith('Normal base')
    assert names['unique']['shown']["Blackhorn's Face"] == 'shares its base with a shown item'  # Hellwarden's Will
    assert 'asks' in names['unique']['shown']['Harlequin Crest']
    assert 'uar' in rule(profile, 'SHOW Set ARMOR')['equipmentItemCode']  # Sacred Armor: IK Soul Cage, elite


def test_evidence_names_every_reason():
    sources = {
        'asks': {
            'date': '2026-09-18',
            'bases': {
                '1': {'code': 'uap', 'uniques': [{'id': 1, 'name': 'Harlequin Crest', 'high': 2.58}], 'sets': []}
            },
        },
        'demand': {'Harlequin Crest': {'a', 'b'}},
        'builds': {'Harlequin Crest'},
        'recommended': set(),
    }
    reasons = evidence('unique', sources)
    assert reasons['Harlequin Crest'] == [
        'asks 2.58 Ist (2026-09-18)',
        'named by 2 maxroll build guide(s)',
        'in a maxroll planner loadout',
        'elite base',
    ]
    assert reasons['The Gnasher'] == []
