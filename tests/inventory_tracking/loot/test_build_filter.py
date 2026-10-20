"""The one loot filter profile (Warlock Lean2): unique and set items shown by base, from the knowledge base's
evidence, rebuilt in place."""

import json
import re
from pathlib import Path

import pytest

from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot import build_filter
from inventory_tracking.loot.build_filter import build, evidence, load_sources


D2DATA = Path('third-parties/d2data/json/base')


@pytest.fixture(scope='module')
def sources():
    # without the Chronicle: what it lacks changes with every find
    return {**load_sources(), 'chronicle': None}


@pytest.fixture(scope='module')
def built(sources):
    return build(json.loads(build_filter.PROFILE.read_text()), sources)


def rule(profile, name):
    [found] = [r for r in profile['rules'] if r['name'] == name]
    return found


def test_only_the_generated_rules_are_rebuilt_and_the_name_fits_the_game(built):
    profile, _ = built
    source = json.loads(build_filter.PROFILE.read_text())
    assert profile['name'] == source['name'] == 'Warlock Lean2'  # the game's saved copy is found by this name
    assert len(profile['name']) <= 13
    assert {key: value for key, value in profile.items() if key != 'rules'} == {
        key: value for key, value in source.items() if key != 'rules'
    }
    assert [r for r in profile['rules'] if r['name'] not in build_filter.GENERATED] == [
        r for r in source['rules'] if r['name'] not in build_filter.GENERATED
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


def test_lootfilter_holds_the_one_profile():
    # the player's ruling, 2026-10-20: "retire other filters. and keep only one filter file at all"
    assert sorted(path.name for path in build_filter.PROFILE.parent.glob('*.json')) == [build_filter.PROFILE.name]


def test_a_rebuild_round_trips_the_profile_unchanged(built, sources, tmp_path, monkeypatch):
    profile, _ = built
    assert build(profile, sources)[0] == profile  # rebuilding a rebuilt profile changes nothing
    source = build_filter.PROFILE.read_text()
    assert source == json.dumps(json.loads(source), indent=2) + '\n'  # in the form main() writes
    target, names = tmp_path / build_filter.PROFILE.name, tmp_path / 'filter_names.json'
    target.write_text(json.dumps(profile, indent=2) + '\n')
    monkeypatch.setattr(build_filter, 'PROFILE', target)
    monkeypatch.setattr(build_filter, 'NAMES', names)
    monkeypatch.setattr(build_filter, 'load_sources', lambda: sources)
    monkeypatch.setattr(build_filter, 'copy', lambda text: False)
    written = target.read_bytes()
    assert build_filter.main() == 0
    assert target.read_bytes() == written
    assert json.loads(names.read_text())['unique']['shown']


def test_a_profile_without_the_generated_rules_is_refused(sources):
    with pytest.raises(ValueError, match='generated rules'):
        build({'name': 'Warlock Lean2', 'rules': [{'name': 'SHOW Unique Set'}]}, sources)


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
    assert names['unique']['hidden']['Bverrit Keep'].startswith('1 trades in 30 days, median 0.79 Ist')  # trade record
    assert names['trades']['items_covered'] > 500
    assert names['unique']['shown']["Blackhorn's Face"] == 'shares its base with a shown item'  # Hellwarden's Will
    assert 'trades in 30 days' in names['unique']['shown']['Harlequin Crest']
    assert 'uar' not in rule(profile, 'SHOW Set ARMOR')['equipmentItemCode']  # IK Soul Cage sells for two gems
    assert names['set']['hidden']["Immortal King's Soul Cage"].startswith('20 trades in 30 days, median 0.12 Ist')


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
        'elite base',
        'in a maxroll planner loadout',
    ]
    assert reasons['The Gnasher'] == []


def test_trade_record_replaces_asks_demand_and_elite_guarantee_but_not_self_use():
    sources = {
        'asks': {
            'date': '2026-09-18',
            'bases': {
                '1': {'code': 'urn', 'uniques': [{'id': 1, 'name': 'Crown of Ages', 'high': 1027.0}], 'sets': []}
            },
        },
        'demand': {'Crown of Ages': {'a'}, 'Stormlash': {'b'}},
        'builds': set(),
        'recommended': {'Tarnhelm', 'Bloodfist'},
        'owned': {'Bloodfist'},
        'trades': {
            'Crown of Ages': {'last_30d': 1, 'median_ist': 400.0, 'date': '2026-10-09'},  # too few sales
            'Stormlash': {'last_30d': 0, 'median_ist': None, 'date': '2026-10-09'},  # elite, never trades
            'Tarnhelm': {'last_30d': 0, 'median_ist': None, 'date': '2026-10-09'},
            'Bloodfist': {
                'last_30d': 20,
                'median_ist': 0.13,
                'date': '2026-10-09',
            },  # leveling piece, owned, sells for a gem
            'The Gnasher': {'last_30d': 4, 'median_ist': 0.12, 'date': '2026-10-09'},  # sells, for nothing
            'Nagelring': {'last_30d': 9, 'median_ist': 0.79, 'date': '2026-10-09'},
            'Cranebeak': {'last_30d': 1, 'last_90d': 3, 'median_ist': 3.66, 'date': '2026-10-09'},  # slow but dear
        },
    }
    reasons = evidence('unique', sources)
    assert reasons['Crown of Ages'] == []
    assert reasons['Stormlash'] == []
    assert reasons['Tarnhelm'] == ['leveling recommendation, not owned yet']
    assert reasons['Bloodfist'] == []
    assert reasons['The Gnasher'] == []
    assert reasons['Nagelring'] == ['9 trades in 30 days, median 0.79 Ist (Traderie Recent Trades 2026-10-09)']
    assert reasons['Cranebeak'] == [
        'slow but dear: 3 trades in 90 days, median 3.66 Ist (Traderie Recent Trades 2026-10-09)'
    ]
    assert reasons['Bverrit Keep'] == []  # not covered by the trade record: the old rules, which find nothing


def test_an_item_the_chronicle_lacks_is_shown_until_it_is_found():
    sources = {
        'asks': {'date': '2026-09-18', 'bases': {}},
        'demand': {},
        'builds': set(),
        'recommended': set(),
        'trades': {
            name: {'last_30d': 20, 'median_ist': 0.06, 'date': '2026-10-09'}
            for name in ('The Gnasher', 'Deathspade', 'Horadric Staff', 'Cold Rupture')
        },
        'chronicle': {'Deathspade'},
    }
    reasons = evidence('unique', sources)
    assert reasons['The Gnasher'] == ['not in the Chronicle yet']
    assert reasons['Deathspade'] == []  # found
    assert reasons['Horadric Staff'] == []  # a quest item: no monster drops it
    assert reasons['Cold Rupture'] == []  # the game keeps it out of the Chronicle
    assert evidence('unique', {**sources, 'chronicle': None})['The Gnasher'] == []  # no dump, no reason


def test_the_chronicle_is_read_by_name_and_is_absent_without_a_dump(tmp_path):
    dump = tmp_path / 'chronicle.json'
    assert build_filter.load_chronicle(dump) is None
    entries = {'unique': [{'name': 'Deathspade'}], 'set': [{'name': "Civerb's Ward"}], 'runeword': [{'name': None}]}
    dump.write_text(json.dumps({'entries': entries}))
    assert build_filter.load_chronicle(dump) == {'Deathspade', "Civerb's Ward"}


def test_the_profile_goes_to_the_clipboard_when_wl_copy_is_there(monkeypatch):
    sent = []

    def run(command, *, input, **_):
        sent.append((command, input))
        return type('Done', (), {'returncode': 0})()

    monkeypatch.setattr(build_filter.subprocess, 'run', run)
    monkeypatch.setattr(build_filter.shutil, 'which', lambda name: None)
    assert build_filter.copy('{}') is False
    assert sent == []
    monkeypatch.setattr(build_filter.shutil, 'which', lambda name: '/usr/bin/wl-copy')
    assert build_filter.copy('{}') is True
    assert sent == [(['wl-copy'], b'{}')]
