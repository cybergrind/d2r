"""The plain base gate (loot/base_floor.py BASE_FLOOR; the player, 2026-10-23: the junk Superior Flail, "we absolutely
MUST NOT trash good items") and its town rule (keep.py K9). Item codes by the bundled metadata's names, not from
memory."""

from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot import base_floor
from inventory_tracking.loot.api import town_verdicts
from inventory_tracking.loot.facts import (
    DAMAGE_PERCENT,
    DEFENSE_PERCENT,
    NORMAL,
    SOCKETS,
    SUPERIOR,
    ItemFacts,
    Owner,
    Where,
)
from inventory_tracking.loot.keep import Action, decide
from inventory_tracking.loot.value import assess


def code_of(name: str) -> str:
    [found] = [base['code'] for base in metadata()['bases'].values() if base['name'] == name]
    return found


# The good bases the player's ruling names (the coordinator's list, 2026-10-23), every quality and ED a sale wants
GOOD = [
    ('Flail', SUPERIOR, False, 4, 15),
    ('Flail', SUPERIOR, True, 0, 15),
    ('Monarch', NORMAL, False, 4, 0),
    ('Monarch', SUPERIOR, False, 4, 15),
    ('Crystal Sword', NORMAL, False, 4, 0),
    ('Crystal Sword', NORMAL, True, 4, 0),
    ('Corona', NORMAL, True, 3, 0),
    ('Archon Plate', NORMAL, False, 4, 0),
    ('Archon Plate', NORMAL, True, 4, 0),
    ('Archon Plate', SUPERIOR, False, 4, 15),
    ('Mage Plate', NORMAL, False, 4, 0),
    ('Mage Plate', SUPERIOR, False, 4, 15),
    ('Phase Blade', NORMAL, False, 5, 0),
    ('Phase Blade', SUPERIOR, False, 5, 15),
]


@pytest.mark.parametrize(('name', 'quality', 'ethereal', 'sockets', 'ed'), GOOD)
def test_the_good_bases_are_never_junk(name, quality, ethereal, sockets, ed):
    assert base_floor.junk(code_of(name), quality, ethereal=ethereal, sockets=sockets, ed=ed) is None


def test_the_junk_superior_flail_is_under_the_floor_by_its_dated_asks():
    why = base_floor.junk(code_of('Flail'), SUPERIOR, ethereal=False, sockets=0, ed=7)
    assert why is not None
    assert why.startswith('a plain base under the floor: asks ')
    assert 'under 1 Ist' in why
    assert '2026-' in why


@pytest.mark.parametrize(
    ('ethereal', 'sockets', 'ed'),
    [(None, 0, 7), (False, None, 7), (False, 0, None)],
    ids=['eth unread', 'sockets unread', 'ED unread'],
)
def test_a_fact_unread_keeps_it(ethereal, sockets, ed):
    assert base_floor.junk(code_of('Flail'), SUPERIOR, ethereal=ethereal, sockets=sockets, ed=ed) is None


def test_the_switch_off_or_no_table_keeps_every_base(monkeypatch):
    monkeypatch.setattr(base_floor, 'BASE_FLOOR', False)
    assert base_floor.junk(code_of('Flail'), SUPERIOR, ethereal=False, sockets=0, ed=7) is None
    monkeypatch.setattr(base_floor, 'BASE_FLOOR', True)
    monkeypatch.setattr(base_floor, 'table', dict)
    assert base_floor.junk(code_of('Flail'), SUPERIOR, ethereal=False, sockets=0, ed=7) is None


def test_the_table_holds_only_clear_fitting_bands_with_three_sellers():
    from inventory_tracking.loot.build_base_floor import CLEARLY, SELLERS

    junk = base_floor.table()['junk']
    assert junk, 'the built table is empty'
    for key, record in junk.items():
        assert record['median'] <= CLEARLY * base_floor.FLOOR_IST, key
        assert record['sellers'] >= SELLERS, key
        assert record['verdict'] in base_floor.SELLS_OVER, key
        assert record['observed'], key


def test_a_band_that_does_not_fit_or_names_demand_is_not_written():
    from inventory_tracking.loot.build_base_floor import junk_record

    fits = {
        'verdict': 'slow', 'decision_ist': 0.43, 'demand': [], 'own_use': None,
        'band': {'median_ist': 0.57, 'q1_ist': 0.43, 'sellers': 3, 'liquidity': 'thin', 'evidence_kind': 'asks',
                 'observed_at': '2026-10-04', 'relaxed_facets': ['base_ed'],
                 'bucket': '{"base_modifiers":{},"ethereal":false,"rarity":"superior","sockets":0}'},
    }  # fmt: skip
    facts = {'rarity': 'superior', 'ethereal': False, 'sockets': 0, 'perfect': False}
    assert junk_record(fits, **facts) is not None
    assert junk_record({**fits, 'demand': [{'runeword': 'Heart of the Oak'}]}, **facts) is None
    assert junk_record({**fits, 'verdict': 'check'}, **facts) is None
    assert junk_record({**fits, 'band': {**fits['band'], 'sellers': 2}}, **facts) is None
    assert junk_record({**fits, 'band': {**fits['band'], 'relaxed_facets': ['sockets']}}, **facts) is None
    assert junk_record(fits, **{**facts, 'perfect': True}) is None  # a 15 ED one priced by ordinary rolls
    assert junk_record(fits, **{**facts, 'sockets': 4}) is None  # the bucket is another socket count
    assert junk_record({**fits, 'band': {**fits['band'], 'median_ist': 0.95}}, **facts) is None  # not clearly under


def facts(
    name: str, quality: int, *, ethereal: bool | None, sockets: int, ed: int, unit: int = 1, **rolls
) -> ItemFacts:
    base = next(base for base in metadata()['bases'].values() if base['name'] == name)
    stat = DAMAGE_PERCENT if base['category'] == 'weapons' else DEFENSE_PERCENT
    return ItemFacts(
        unit_id=unit, code=base['code'], base_type=base['type'], size=(2, 3), quality=quality, identified=True,
        ethereal=ethereal, sockets=sockets, rolls={f'{SOCKETS}:0': sockets, f'{stat}:0': ed, **rolls},
        owner=Owner.LOOP, base_name=name,
    )  # fmt: skip


def test_k9_sells_a_plain_base_on_no_allowlist_entry_and_keeps_the_allowlisted(monkeypatch):
    monkeypatch.setattr(base_floor, 'TAKEN', {})
    monkeypatch.setattr(base_floor, '_taken_read', lambda: base_floor.TAKEN)
    junk = facts('Flail', SUPERIOR, ethereal=False, sockets=0, ed=7, unit=1)
    good = facts('Flail', SUPERIOR, ethereal=False, sockets=4, ed=15, unit=2)
    unread = facts('Flail', SUPERIOR, ethereal=None, sockets=0, ed=7, unit=3)
    taken = facts('Flail', SUPERIOR, ethereal=None, sockets=0, ed=7, unit=4)  # the town's read lacks its facts
    base_floor.seen(('game-1', 3))
    base_floor.remember(4, 'allowlisted: Superior 15 ED Flail 4os')
    decision = decide(junk, assess(junk, worth=None), [])
    assert (decision.action, decision.rule) == (Action.DROP, 'K9')
    assert decide(good, assess(good, worth=None), []).action == Action.KEEP
    assert decide(unread, assess(unread, worth=None), []).action == Action.DROP  # "never stashed"
    assert decide(taken, assess(taken, worth=None), []).action == Action.KEEP
    items = [(f, assess(f, worth=None)) for f in (junk, good, unread, taken)]
    verdicts = {v.facts.unit_id: v for v in town_verdicts(items, lambda _: [])}
    assert verdicts[1].sold
    assert verdicts[3].sold
    assert not verdicts[2].sold
    assert not verdicts[4].sold
    assert 'allowlist' in verdicts[1].said()


def test_k9_leaves_jewels_charms_runes_and_named_items_to_their_own_rules():
    for name in ('Jewel', 'Grand Charm', 'El Rune', 'Chipped Ruby'):
        found = ItemFacts(unit_id=9, code=code_of(name), base_type='', size=(1, 1), quality=NORMAL, identified=True,
                          ethereal=False, sockets=0, rolls={}, owner=Owner.LOOP)  # fmt: skip
        assert base_floor.town_junk(found) is None, name
    named = facts('Flail', SUPERIOR, ethereal=False, sockets=0, ed=7)
    assert base_floor.town_junk(replace(named, quality=7)) is None  # a unique Flail: not a plain base


def test_the_taken_record_goes_to_the_tests_own_file_never_the_live_one(tmp_path):
    live = base_floor.LIVE_TAKEN_FILE.read_text() if base_floor.LIVE_TAKEN_FILE.exists() else None
    assert base_floor.TAKEN_FILE != base_floor.LIVE_TAKEN_FILE  # tests/inventory_tracking/conftest.py
    base_floor.remember(7, 'allowlisted: a test')
    assert base_floor.remembered(7) == 'allowlisted: a test'
    after = base_floor.LIVE_TAKEN_FILE.read_text() if base_floor.LIVE_TAKEN_FILE.exists() else None
    assert after == live


# -- 2026-10-23: the allowlist verifier's findings (rca/2026-10-23/base-pickups-verify.md)


def test_a_better_copy_falls_back_to_the_lower_key(monkeypatch):
    """MISSED: a 15 ED superior matches its ordinary twin, a superior its normal twin, when its own key is missing;
    a key proved under the floor by its own split evidence stops the walk."""
    kb = {
        'p/superior/eth/6os/ordinary': {'facts': 'ordinary', 'median_ist': 119.9, 'n': 3, 'q1_ist': 100.0},
        'q/normal/noneth/4os/ordinary': {'facts': 'normal', 'median_ist': 22.8, 'n': 4, 'q1_ist': 20.0},
        'w/normal/noneth/4os/ordinary': {'facts': 'normal', 'median_ist': 5.0, 'n': 4, 'q1_ist': 4.0},
    }
    dropped = {'w/superior/noneth/4os/ordinary': 'wp-b split by ED: 0.25-0.895 Ist'}
    monkeypatch.setattr(base_floor, 'pickups', lambda: {'kb': kb, 'kb_dropped': dropped})
    assert base_floor.lower_keys('p', 'superior', ethereal=True, sockets=6, perfect=True) == [
        'p/superior/eth/6os/perfect', 'p/superior/eth/6os/ordinary', 'p/normal/eth/6os/ordinary',
    ]  # fmt: skip

    def matched(code: str, rarity: str, *, ethereal: bool, perfect: bool, sockets: int) -> str | None:
        found = base_floor.kb_match(code, rarity, ethereal=ethereal, sockets=sockets, perfect=perfect)
        return None if found is None else found['facts']

    assert matched('p', 'superior', ethereal=True, sockets=6, perfect=True) == 'ordinary'
    assert matched('q', 'superior', ethereal=False, sockets=4, perfect=True) == 'normal'
    assert matched('q', 'superior', ethereal=True, sockets=4, perfect=True) is None  # eth is its own
    assert matched('w', 'superior', ethereal=False, sockets=4, perfect=False) is None
    assert matched('w', 'normal', ethereal=False, sockets=4, perfect=False) == 'normal'


def test_the_real_list_takes_the_15_ed_twin_of_an_ordinary_key():
    # the verifier's examples: a 15 ED eth 6os War Pike (ordinary 119.9), a Superior eth 6os Archon Staff (normal 22.8)
    pike = facts('War Pike', SUPERIOR, ethereal=True, sockets=6, ed=15)
    staff = facts('Archon Staff', SUPERIOR, ethereal=True, sockets=6, ed=5)
    assert base_floor.allowed(pike) is not None
    assert base_floor.allowed(staff) is not None
    # Wire Fleece superior 4os under 15 ED: wp-b's split says 0.895 Ist, no lower key overrules it
    assert base_floor.allowed(facts('Wire Fleece', SUPERIOR, ethereal=False, sockets=4, ed=5)) is None
    assert base_floor.allowed(facts('Wire Fleece', SUPERIOR, ethereal=False, sockets=4, ed=15)) is not None


def test_no_ordinary_key_carries_its_15_ed_twins_numbers():
    """ED pooling: an ordinary superior key equal to its perfect twin's band is the twin's (the verifier)."""
    found = base_floor.pickups()
    kb = found['kb']
    for name, entry in kb.items():
        code, rarity, eth, sockets, grade = name.split('/')
        twin = kb.get(f'{code}/{rarity}/{eth}/{sockets}/perfect')
        if grade != 'ordinary' or rarity != 'superior' or twin is None or 'wp-b' in entry['source']:
            continue
        if entry['q1_ist'] >= 10:
            continue  # POOLED_KEEP_IST: a pool this dear is kept ("MUST NOT trash good items")
        assert (entry['q1_ist'], entry['median_ist'], entry['n']) != (twin['q1_ist'], twin['median_ist'], twin['n'])
    assert 'utu/superior/noneth/4os/ordinary' in found['kb_dropped']
    assert 'utu/superior/eth/0os/ordinary' in found['kb_dropped']
    assert '7h7/superior/noneth/6os/ordinary' not in kb


def test_the_evidence_says_fills_or_asks():
    said = base_floor._evidence({'q1_ist': 2.58, 'median_ist': 4.03, 'n': 16, 'kind': 'fills', 'observed': 'x'})
    assert said.startswith('fills 2.58-4.03 Ist')
    assert base_floor._evidence({'q1_ist': 1, 'median_ist': 5, 'n': 3, 'observed': 'x'}).startswith('asks')


def test_the_taken_bases_are_kept_by_game_and_unit():
    base_floor.remember(7, 'allowlisted: a', ('game-1', 3))
    assert base_floor.remembered(7, 'game-1') == 'allowlisted: a'
    assert base_floor.remembered(7, ('game-2', 4)) is None  # unit ids repeat across games
    base_floor.seen(('game-2', 4))
    assert base_floor.remembered(7) is None
    base_floor.seen(('game-1', 3))
    assert base_floor.remembered(7) == 'allowlisted: a'


def test_k8_never_sells_an_allowlisted_base_by_its_appraisal():
    """K8 ran before K9 without the allowlist: a base the field took (or the town's read matches) appraised
    worthless was sold (the verifier). Now kept by the K9 rule before K8."""
    from inventory_tracking.loot.value import Value

    taken = facts('Flail', SUPERIOR, ethereal=None, sockets=0, ed=7, unit=5)  # the town's read lacks its facts
    matched = facts('Flail', SUPERIOR, ethereal=False, sockets=4, ed=15, unit=6)
    junk = facts('Flail', SUPERIOR, ethereal=False, sockets=0, ed=7, unit=8)
    base_floor.seen(('game-1', 3))
    base_floor.remember(5, 'allowlisted: Superior 15 ED Flail 4os')
    worthless = Value(worth_ist=0.1, band=None, verdict='vendor', wants=(), matters=(), tier='worthless')
    for kept in (taken, matched):
        decision = decide(kept, worthless, [])
        assert (decision.action, decision.rule) == (Action.KEEP, 'K9'), kept.unit_id
        assert 'allowlist' in decision.reason
    assert decide(junk, worthless, []).action == Action.DROP
    base_floor.seen(('game-2', 1))  # another game: unit 5 is another item
    assert decide(taken, worthless, []).action == Action.DROP


# -- 2026-10-23 ~17:20, the player's base-price ruling ("Sales-backed now"; "Drop both" on the two conflicts): the
# allowlist by the sales-first rule per facet (loot/build_base_pickups.py, pricing/data/base-evidence.json)

RES_45 = {f'{stat}:0': 45 for stat in (39, 41, 43, 45)}
ABYSS, ELDRITCH_BLAST, HEX_PURGE = '107:402', '107:384', '107:389'  # items metadata skills (class 'war')


def _ground(found: ItemFacts) -> ItemFacts:
    return replace(found, where=Where.GROUND, owner=Owner.UNKNOWN)


def _picked_on_the_ground(found: ItemFacts) -> bool:
    from inventory_tracking.loot.assess import Assessor, FakeAppraiser, Outcome, Site

    return Assessor(FakeAppraiser({})).assess(_ground(found), Site.GROUND).outcome == Outcome.PICK


def test_the_sacred_rondache_3os_45_res_normal_is_picked():
    """Fills n33 median 8.23 Ist (08-16..10-23), the two Lo trades the player saw: left before the ruling."""
    rondache = facts('Sacred Rondache', NORMAL, ethereal=False, sockets=3, ed=0, **RES_45)
    assert base_floor.allowed(rondache) is not None
    assert _picked_on_the_ground(rondache)
    res_44 = {f'{stat}:0': 44 for stat in (39, 41, 43, 45)}  # 40-44 res 3os normal: fills n54 median 1.55
    assert base_floor.allowed(facts('Sacred Rondache', NORMAL, ethereal=False, sockets=3, ed=0, **res_44)) is None


@pytest.mark.parametrize(
    ('name', 'ethereal', 'sockets', 'rolls'),
    [
        ('Sacred Rondache', False, 0, RES_45),  # "Drop both": asks n11 4.05 against one fill of 2.0
        ('Archon Plate', True, 4, {}),  # eth normal 4os: fills n83 median 2.58 (asks n98 9.32)
        ('Archon Staff', False, 6, {}),  # "Drop both": 3 buyers at 4+, 3 fills median 1.0
        ('Sacred Armor', True, 4, {}),  # eth normal 4os: fills n34 median 2.58
    ],
    ids=['rondache-0os-45-normal', 'archon-eth-4os-normal', 'archon-staff-6os-normal', 'sacred-armor-eth-4os-normal'],
)
def test_the_ruled_out_bases_are_left(name, ethereal, sockets, rolls):
    found = facts(name, NORMAL, ethereal=ethereal, sockets=sockets, ed=0, **rolls)
    assert base_floor.allowed(found) is None
    assert not _picked_on_the_ground(found)


def test_the_superior_eth_4os_archon_stays_a_merc_base():
    assert base_floor.allowed(facts('Archon Plate', SUPERIOR, ethereal=True, sockets=4, ed=8)) is not None


def test_a_void_dagger_with_eldritch_blast_alone_is_left_and_with_a_second_mod_picked():
    """+3 EB alone fills n9 median 1.43 Ist; with a second staff mod >= +2 the facet fills median 11.4."""
    alone = facts('Kriss', NORMAL, ethereal=False, sockets=3, ed=0, **{ELDRITCH_BLAST: 3})
    paired = facts('Kriss', NORMAL, ethereal=False, sockets=3, ed=0, **{ELDRITCH_BLAST: 3, HEX_PURGE: 2})
    weak = facts('Kriss', NORMAL, ethereal=False, sockets=3, ed=0, **{ELDRITCH_BLAST: 3, HEX_PURGE: 1})
    assert base_floor.allowed(alone) is None
    assert not _picked_on_the_ground(alone)
    assert base_floor.allowed(paired) is not None
    assert _picked_on_the_ground(paired)
    assert base_floor.allowed(weak) is None


def test_a_denied_facet_beats_the_row_that_would_take_it():
    """The eth 4os Mancatcher superior under 15 ED fills n4 median 2.42: the merc polearm row (eth 4os superior) is
    overruled by the denied facet; the Thresher of the same row stays."""
    mancatcher = facts('Mancatcher', SUPERIOR, ethereal=True, sockets=4, ed=5)
    assert base_floor.denied(mancatcher) is not None
    assert base_floor.allowed(mancatcher) is None
    assert base_floor.allowed(facts('Thresher', SUPERIOR, ethereal=True, sockets=4, ed=5)) is not None


def test_a_denied_key_stops_the_lower_key_walk(monkeypatch):
    doc = {'kb': {'q/normal/noneth/4os/ordinary': {'facts': 'normal', 'median_ist': 9.0, 'n': 4, 'q1_ist': 5.0}},
           'denied': {'f': {'keys': ['q/superior/noneth/4os/ordinary']}}}  # fmt: skip
    monkeypatch.setattr(base_floor, 'pickups', lambda: doc)
    assert base_floor.kb_match('q', 'superior', ethereal=False, sockets=4, perfect=True) is None
    assert base_floor.kb_match('q', 'normal', ethereal=False, sockets=4, perfect=False) is not None
