"""The keep bar for magic, rare and crafted finds (loot/wants.py KEEP_BAR, loot/build_wants.py BAR_ROWS, loot/keep.py
`junk_unwanted` / `junk_magic`; rca/2026-10-21/keep-bar-design.md). The player, 2026-10-21 ~08:55: "circlets need to
have not just one good stat, not even 2 good stats, they need like 3 stats to worth anything ... why some item at least
beats shako"; "we need not just 1 row, but probably 3 stats with good rolls to keep"; ~09:20 the rulings on the
exceptions. The rolls of the named items are the loop's own reads (collection DB / identified reads, 2026-10-18..21).
"""

import json
from functools import cache

import pytest

from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot import build_wants, keep, wants
from inventory_tracking.loot.facts import MAGIC, RARE, UNIQUE, ItemFacts, Owner, Where
from inventory_tracking.loot.keep import Action, decide
from inventory_tracking.loot.value import assess
from inventory_tracking.macros.keepers import amulet_keeper


LIFE = 256  # maxhp and maxmana raw units a point
RES = {'39:0': 20, '41:0': 20, '43:0': 20, '45:0': 20}  # all res 20


@cache
def _bases() -> dict[str, tuple[str, str]]:
    return {row['name']: (row['code'], row['type']) for row in metadata()['bases'].values() if row.get('name')}


def item(base: str, quality: int, rolls: dict[str, int], *, name: str | None = None, unit: int = 1,
         ethereal: bool = False, owner: Owner = Owner.LOOP) -> ItemFacts:  # fmt: skip
    code, kind = _bases()[base]
    return ItemFacts(unit_id=unit, code=code, base_type=kind, size=(2, 2), quality=quality, identified=True,
                     ethereal=ethereal, sockets=rolls.get('194:0', 0), rolls=rolls, name=name or base,
                     where=Where.INVENTORY, owner=owner, base_name=base)  # fmt: skip


def decided(facts: ItemFacts, worth: float | None = None, verdict: str = 'check', owned=()):
    return decide(facts, assess(facts, worth=worth, verdict=verdict), list(owned))


def kept(facts: ItemFacts, **extra) -> bool:
    return decided(facts, **extra).action == Action.KEEP


# The four the player named (2026-10-21 ~08:30-08:45), as the loop read them
BONE_SKEWER = ('Mithral Point', RARE, {'0:0': 7, '83:7': 2, '17:0': 91})
DEMON_BROW = ('Circlet', RARE, {'0:0': 15, '43:0': 32, '83:6': 2, '31:0': 1})
RAVEN_CASQUE = ('Horned Helm', RARE, {'1:0': 10, '45:0': 12, '89:0': 2, '107:141': 1, '194:0': 2})
IMP_CHAIN = ('Spiderweb Sash', RARE, {'0:0': 25, '45:0': 6, '99:0': 24, '110:0': 25})
# Kept by the rulings of ~09:20
BONE_WAND = ('Bone Wand', MAGIC, {'83:2': 2, '107:88': 3, '107:93': 3})  # +2 Necro, +3 Bone Prison, +3 Bone Spirit
ANTLERS = ('Antlers', MAGIC, {'7:0': 32 * LIFE, '107:243': 1, '107:246': 1, '107:248': 3, '188:41': 3})  # +6 Fury
DIRE_MARK = ('Burnt Text', RARE, {'20:0': 3, **RES, '83:7': 2, '107:381': 1, '107:382': 2, '110:0': 75})
BO_HELM = ('Fanged Helm', RARE, {'188:34': 2, '107:149': 3})  # +2 Warcries, +3 Battle Orders, nothing else


@pytest.mark.parametrize('spec', [BONE_SKEWER, DEMON_BROW, RAVEN_CASQUE, IMP_CHAIN],
                         ids=['bone-skewer', 'demon-brow', 'raven-casque', 'imp-chain'])  # fmt: skip
def test_the_four_weak_keepers_the_player_named_are_given_up(spec):
    decision = decided(item(*spec))
    assert decision.action == Action.DROP, decision.said()
    assert decision.rule == 'K8', decision.said()


@pytest.mark.parametrize('spec', [BONE_SKEWER, DEMON_BROW, RAVEN_CASQUE, IMP_CHAIN],
                         ids=['bone-skewer', 'demon-brow', 'raven-casque', 'imp-chain'])  # fmt: skip
def test_with_the_bar_off_todays_rows_keep_them_again(spec, monkeypatch):
    monkeypatch.setattr(wants, 'KEEP_BAR', False)
    assert kept(item(*spec))


@pytest.mark.parametrize('spec', [BONE_WAND, ANTLERS, DIRE_MARK, BO_HELM],
                         ids=['bone-wand', 'antlers', 'dire-mark', 'bo-helm'])  # fmt: skip
def test_the_ruled_exceptions_are_kept(spec):
    decision = decided(item(*spec))
    assert decision.action == Action.KEEP, decision.said()
    assert any(row.bar == 'on' for row in assess(item(*spec), worth=None, verdict='check').wants)


def test_a_circlet_needs_three_good_stats_one_of_them_what_shako_cannot_give():
    warlock = {'83:7': 2, '105:0': 20}
    assert not kept(item('Tiara', RARE, warlock))  # +2 and 20 FCR: does not beat Shako + Um
    three = decided(item('Tiara', RARE, {**warlock, '194:0': 2}))
    assert three.action == Action.KEEP
    assert three.rule == 'K3'  # the Warlock's own helm row is always kept
    assert kept(item('Diadem', RARE, {'83:3': 2, '96:0': 30, '7:0': 45 * LIFE}))  # a Paladin's: FRW and life
    # Three good stats but none that Shako lacks (no FCR, FRW or sockets): given up
    assert not kept(item('Coronet', RARE, {'83:1': 2, '7:0': 45 * LIFE, **RES}))
    # Low rolls are no good stats: life 30 (of 60), str 15 (of 20-30), one res 25
    assert not kept(item('Circlet', RARE, {'83:0': 2, '105:0': 20, '7:0': 30 * LIFE, '0:0': 15, '39:0': 25}))


def test_the_magic_warlock_circlet_of_two_stats_is_not_kept():
    # The player, ~09:20: the magic +2 Warlock / 20 FCR circlet NOT kept
    decision = decided(item('Diadem', MAGIC, {'83:7': 2, '105:0': 20}))
    assert decision.action == Action.DROP
    assert decision.rule == 'K8'


def test_an_amulet_needs_two_skills_and_three_good_stats():
    order_torc = {'7:0': 10 * LIFE, '9:0': 90 * LIFE, '41:0': 39, '83:7': 2, '105:0': 10}
    assert decided(item('Amulet', RARE, order_torc)).rule == 'K3'  # the Warlock's
    assert kept(item('Amulet', RARE, {'83:2': 2, '105:0': 10, '0:0': 20}))  # a Necromancer's: FCR and str
    assert not kept(item('Amulet', RARE, {'9:0': 5 * LIFE, '39:0': 9, '105:0': 10}))  # Blood Heart: FCR only
    assert not kept(item('Amulet', RARE, {'188:42': 2, '0:0': 12, '41:0': 23, '80:0': 17}))  # Doom Mark: +2 tree
    assert not kept(item('Amulet', RARE, {'7:0': 41 * LIFE, '39:0': 35}))  # no skills: Mara's beats it
    # The magic +2 Warlock / 10 FCR (warlock.html:163) stays: two of two
    assert decided(item('Amulet', MAGIC, {'83:7': 2, '105:0': 10})).rule == 'K3'


def test_a_ring_needs_fcr_or_attack_rating_and_three_good_stats():
    beast_turn = {'0:0': 20, '7:0': 24 * LIFE, '41:0': 28, '105:0': 10}
    assert kept(item('Ring', RARE, beast_turn))
    assert not kept(item('Ring', RARE, {'9:0': 57 * LIFE, '41:0': 17, '105:0': 10}))  # Order Spiral: FCR only
    assert kept(item('Ring', RARE, {'19:0': 120, '60:0': 7, '0:0': 18}))  # melee: AR, leech, str
    assert not kept(item('Ring', RARE, {'7:0': 36 * LIFE, '39:0': 30, '60:0': 6}))  # neither FCR nor AR
    assert kept(item('Ring', RARE, {'105:0': 10, '60:0': 5, '62:0': 4}))  # the dual leech caster ring


def test_a_belt_needs_fhr_and_three_good_stats():
    plagueri_winding = {'41:0': 6, '43:0': 22, '45:0': 29, '99:0': 24}
    assert kept(item('Plated Belt', RARE, plagueri_winding))
    assert not kept(item('Light Belt', RARE, {'0:0': 5, '41:0': 6, '45:0': 25, '99:0': 24}))  # Loath Lock
    assert kept(item('Belt', RARE, {'99:0': 24, '7:0': 35 * LIFE, '45:0': 20}))


def test_rare_gloves_need_attack_speed_and_three_good_stats():
    # The player, ~09:20: rare gloves held to three
    assert kept(item('Chain Gloves', RARE, {'93:0': 20, '188:2': 2, '2:0': 15}))
    assert not kept(item('Chain Gloves', RARE, {'93:0': 20, '188:2': 2}))
    assert not kept(item('Chain Gloves', RARE, {'93:0': 20, '39:0': 30}))  # IAS and one resist: two


def test_class_items_need_their_core_and_three_good_stats():
    assert not kept(item(*BONE_SKEWER))
    assert kept(item('Mithral Point', RARE, {'83:7': 2, '107:402': 3, '93:0': 20}))  # +2, +3 Abyss, IAS
    assert kept(item('Mithral Point', RARE, {'17:0': 230, '93:0': 20}, ethereal=True))  # eth melee: ED and IAS
    assert not kept(item('Mithral Point', RARE, {'17:0': 230}, ethereal=True))
    assert not kept(item('Sparkling Ball', RARE, {'83:1': 2, '105:0': 20, '107:60': 2}))  # Blood Gyre: two
    assert kept(item('Sparkling Ball', RARE, {'83:1': 2, '105:0': 20, '107:56': 3}))  # and +3 Meteor
    assert not kept(item('Bone Knife', MAGIC, {'83:7': 2}))  # the magic Bone Knife: +2 alone
    assert not kept(item('Bone Wand', MAGIC, {'83:2': 2, '107:88': 3}))  # +3 Bone Prison: no paid skill
    assert not kept(item('Fanged Helm', RARE, {'188:34': 2, '107:149': 2}))  # +2 BO: under the exception
    assert kept(item('Fanged Helm', MAGIC, {'188:34': 2, '107:149': 3}))  # the BO helm, magic too


def test_rare_body_armor_shields_and_weapons_are_junk_unless_one_ist():
    # The player, ~09:20: no more K9 "keep the first unknown" for them
    for base in ('Archon Plate', 'Monarch', 'Colossus Blade', 'Hydra Bow'):
        decision = decided(item(base, RARE, {'7:0': 40 * LIFE}))
        assert decision.action == Action.DROP, (base, decision.said())
        assert decision.rule == 'K8', (base, decision.said())
    assert decided(item('Archon Plate', RARE, {'7:0': 40 * LIFE}), worth=1.2, verdict='sell').rule == 'K5'


def test_the_bar_junk_kinds_follow_the_switch_and_the_game_data(monkeypatch):
    types = {row['type'] for row in metadata()['bases'].values()}
    weapons = {row['type'] for row in metadata()['bases'].values() if row['category'] == 'weapons'} - {'tpot'}
    assert weapons == keep.WEAPONS
    assert types >= keep.JUNK_UNWANTED_BAR | keep.JUNK_MAGIC_BAR
    assert keep.junk_unwanted() >= keep.JUNK_UNWANTED
    monkeypatch.setattr(wants, 'KEEP_BAR', False)
    assert keep.junk_unwanted() == keep.JUNK_UNWANTED
    assert keep.junk_magic() == keep.JUNK_MAGIC


def test_the_paid_skill_ids_are_the_skills_the_game_data_names():
    skills = json.loads((build_wants.ROOT / 'third-parties/d2data/json/skills.json').read_text())
    names = {row['*Id']: row['skill'] for row in skills.values() if 'skill' in row}
    assert [names[i] for i in build_wants.BARBARIAN_PAID] == [
        'Battle Orders', 'Battle Command', 'War Cry', 'Grim Ward', 'Increased Speed']  # fmt: skip
    assert [names[i] for i in build_wants.NECROMANCER_PAID] == ['Poison Nova', 'Bone Spirit', 'Bone Spear']
    assert [names[i] for i in build_wants.PALADIN_PAID] == ['Fist of the Heavens', 'Blessed Hammer']
    assert [names[i] for i in build_wants.ASSASSIN_PAID] == [
        'Lightning Sentry', 'Venom', 'Fade', 'Death Sentry', 'Wake of Fire Sentry', 'Royal Strike']  # fmt: skip
    assert names[248] == 'Fury'
    assert names[56] == 'Meteor'
    assert {names[i] for i in build_wants.WARLOCK_PAID} >= {'Abyss', 'Hex Purge', 'Echoing Strike', 'Apocalypse'}
    for paid in build_wants.PAID_SKILLS.values():
        assert len(set(paid)) == len(paid)


def test_the_amulet_guard_spares_only_an_unread_amulet_under_the_bar(monkeypatch):
    from inventory_tracking.game.records import Carried

    txt = next(txt for txt, row in metadata()['bases'].items() if row['code'] == 'amu')
    amulet = Carried(unit_id=1, txt=int(txt), x=0, y=0, size=(1, 1), quality=6)
    assert amulet_keeper(amulet, {}) == 'its stats unread'
    assert amulet_keeper(amulet, {105: 10}) is None  # the keep rules judge it (the bar's amulet rows)
    monkeypatch.setattr(wants, 'KEEP_BAR', False)
    assert amulet_keeper(amulet, {105: 10}) == '10% faster cast rate'


def test_every_copy_of_mang_songs_lesson_is_kept():
    # The player, 2026-10-21 ~09:25: "mang's song - we keep if we find any" (the Warlock list's 14th weapon option, so
    # USABLE_SLOT_DEPTH names it no longer)
    assert build_wants.USABLE_SLOT_DEPTH is not None
    assert "Mang Song's Lesson" not in {row['names'][0] for row in build_wants.usable_rows()}
    staff = item('Archon Staff', UNIQUE, {'83:7': 2}, name="Mang Song's Lesson")
    better = item('Archon Staff', UNIQUE, {'83:7': 2, '17:0': 5}, name="Mang Song's Lesson", unit=2,
                  owner=Owner.PLAYER)  # fmt: skip
    decision = decided(staff, worth=0.5, verdict='vendor', owned=[better])
    assert decision.action == Action.KEEP, decision.said()
    assert decision.rule == 'K3'


def test_the_switch_puts_either_the_bar_rows_or_the_rows_they_replace_in_force(monkeypatch):
    rows = wants.load()
    on = {row.id for row in rows if row.bar == 'on'}
    off = {row.id for row in rows if row.bar == 'off'}
    assert {'bar-rare-circlet-three-good', 'bar-rare-amulet-three-good', 'bar-rare-belt-three-good'} <= on
    assert {'rare-circlet-plus2-class', 'rare-amulet-fcr-life-skills', 'rare-belt-24fhr-companion'} <= off
    assert {row.id for row in rows if wants.in_force(row)} >= on
    assert not any(wants.in_force(row) for row in rows if row.id in off)
    monkeypatch.setattr(wants, 'KEEP_BAR', False)
    assert not any(wants.in_force(row) for row in rows if row.id in on)
    assert all(wants.in_force(row) for row in rows if row.id in off)
    demon_brow = item(*DEMON_BROW)
    assert [row.id for row in wants.matching(demon_brow)] == ['rare-circlet-plus2-class']


def test_a_good_stat_tally_is_unknown_while_unread_stats_could_still_make_it():
    from dataclasses import replace

    from inventory_tracking.loot.wants import Need, _tally

    life = Need(('7:0',), min=40, scale=LIFE)
    all_res = Need(('39:0', '41:0', '43:0', '45:0'), min=15, count=4)
    needs = (Need(('105:0',), min=20), Need(('96:0',), min=30), Need((), either=(life, all_res)))
    circlet = item('Tiara', RARE, {'105:0': 20, '96:0': 30})
    assert _tally(needs, 2, circlet) is True
    assert _tally(needs, 3, circlet) is False
    assert _tally(needs, 3, replace(circlet, rolls={'105:0': 20, '96:0': 30, '7:0': 41 * LIFE})) is True
    assert _tally(needs, 3, replace(circlet, rolls={**RES, '105:0': 20, '96:0': 30})) is True  # all res: one either
    assert _tally(needs, 1, replace(circlet, rolls=None)) is None
