"""The ground pickup through the one entry point (macros/pickmode.py ASSESS_GROUND, loot/assess.py GROUND; the player,
2026-10-23: "go ahead. I want to have one place that decides pickups/value") against today's rules (the switch off):
the same drops taken, the same must-haves, the same items remembered for the field identify and the cube, the same
allowlisted bases remembered, the same identify candidates. GOOD and MOST, the KP_6 loop on and off.

The drops: the cases of rca/2026-10-23/scripts/assess_ground.py (codes from the data files, never typed), the
acceptance table (tests/.../loot/fixtures/valuables.json, as today's look reads it: loot/today.py `drop`),
test_pickmode's allowlist and left bases, every allowlist KB key, and every item type of the items metadata at each
quality it drops at, by the look's sources for it. A difference here is the gate of the switch: explained to the
player first.
"""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.game.records import NAMED, VALUABLE, Drop, Loot, Rolls
from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot import api, assess, base_floor, today, value as loot_value
from inventory_tracking.loot.facts import base_of_code
from inventory_tracking.macros import pickmode
from tests.inventory_tracking.loot.test_valuables import CASES, counted, ground_facts
from tests.inventory_tracking.macros.test_pickmode import LEFT, TAKEN


ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / 'inventory_tracking' / 'loot' / 'data'
WANTS = {row['id']: row for row in json.loads((DATA / 'wants.json').read_text())['rows']}
PICKUPS = json.loads((DATA / 'base-pickups.json').read_text())
SIZES = {int(k): tuple(v) for k, v in json.loads((DATA / 'sizes.json').read_text())['sizes'].items()}
LOW, NORMAL, SUPERIOR, MAGIC, SET, RARE, UNIQUE = 1, 2, 3, 4, 5, 6, 7
GAME = ('game-1', 7)
EMPTY = ('..........',) * 4


def txt_of(code: str) -> int:
    found = base_of_code(code)
    assert found is not None, code
    return found[0]


def code_of_row(row_id: str, index: int = 0) -> str:
    return sorted(WANTS[row_id].get('codes') or [])[index]


def type_txt(kind: str) -> int:
    return min(int(cid) for cid, base in metadata()['bases'].items() if base.get('type') == kind)


def drop(txt: int, quality: int, rolls: Rolls | None = None, *, source: str = 'shown', unit: int = 0) -> Drop:
    return Drop(unit or 1000 + txt, 0.0, 0.0, str(txt), VALUABLE, SIZES.get(txt, (1, 1)),
                prized=source in ('unique', NAMED), source=source, txt=txt, quality=quality, rolls=rolls)  # fmt: skip


def skill_of(row_id: str) -> int:
    for need in WANTS[row_id].get('ground') or []:
        for key in [need.get('key'), *(need.get('keys') or [])]:
            if isinstance(key, str) and key.startswith('107:'):
                return int(key.partition(':')[2])
    raise KeyError(row_id)


def kb_drop(key: str, *, perfect: bool | None = None) -> Drop:
    code, rarity, eth, sockets, grade = key.split('/')
    best = grade == 'perfect' if perfect is None else perfect
    rolls = Rolls(int(sockets.removesuffix('os')), defense=15 if best else 5, ethereal=eth == 'eth',
                  damage=15 if best else 5)  # fmt: skip
    return drop(txt_of(code), SUPERIOR if rarity == 'superior' else NORMAL, rolls)


def script_cases() -> list:
    """rca/2026-10-23/scripts/assess_ground.py's 23 cases."""
    void = txt_of(code_of_row('void-dagger-3os-plus3'))
    apocalypse = skill_of('void-dagger-0os-plus3-apocalypse')
    ring = txt_of(code_of_row('jewelry-identify', 1))
    found = [
        (
            'eth 4os Dusk Shroud',
            drop(txt_of(code_of_row('merc-fortitude-dusk-eth-4os')), NORMAL, Rolls(4, ethereal=True)),
        ),
        ('plain 4os Monarch', drop(txt_of(code_of_row('spirit-monarch-plain-4os')), NORMAL, Rolls(4))),
        ('3os +3 Apocalypse Void dagger', drop(void, NORMAL, Rolls(3, skills=((apocalypse, 3),)))),
        ('0os +3 Apocalypse Void dagger', drop(void, NORMAL, Rolls(0, skills=((apocalypse, 3),)))),
        (
            'eth 4os Giant Thresher',
            drop(txt_of(code_of_row('merc-insight-gt-eth-4os')), NORMAL, Rolls(4, ethereal=True)),
        ),
        ('Sacred Rondache 45 4os', drop(txt_of(code_of_row('sacred-rondache-45-4os')), NORMAL, Rolls(4, resists=45))),
        ('magic Monarch', drop(txt_of(code_of_row('monarch-magic-identify')), MAGIC, Rolls(0))),
        ('magic orb', drop(type_txt('orb'), MAGIC, Rolls(0))),
        ('rare pelt', drop(type_txt('pelt'), RARE, Rolls(0))),
        ('rare claw', drop(type_txt('h2h2'), RARE, Rolls(0))),
        ('magic wand', drop(type_txt('wand'), MAGIC, Rolls(0))),
        ('rare body armor', drop(type_txt('tors'), RARE, Rolls(0))),
        ('rare circlet', drop(txt_of(code_of_row('circlet-identify')), RARE, Rolls(0))),
        ('magic ring', drop(ring, MAGIC, None, source='material')),
        ('rare ring', drop(ring, RARE, None, source='material')),
        ('unique (named)', drop(type_txt('tors'), UNIQUE, None, source=NAMED)),
    ]
    for key in sorted(PICKUPS['kb']):
        known = base_of_code(key.split('/')[0])
        if known is not None and (known[1]['name'], key.split('/')[2:4]) in (
            ('War Pike', ['eth', '6os']),
            ('Monarch', ['noneth', '0os']),
        ):
            found.append((f'KB key {key}', kb_drop(key)))
    found += [(f'KB key {key}', kb_drop(key)) for key in [k for k in sorted(PICKUPS['kb']) if '/eth/' in k][:4]]
    return [pytest.param(d, id=f'script: {title}') for title, d in found]


def table_cases() -> list:
    return [pytest.param(today.drop(ground_facts(case)), id=f'table: {case["id"]}') for case in CASES]


def named(name: str) -> int:
    [found] = [int(cid) for cid, base in metadata()['bases'].items() if base['name'] == name]
    return found


def base_cases() -> list:
    """test_pickmode's allowlisted and left bases, and every allowlist KB key with its grade and flag flipped."""
    found = [pytest.param(drop(named(n), q, r), id=f'taken: {n} {r.sockets}os q{q} {i}') for i, (n, r, q) in
             enumerate(TAKEN)]  # fmt: skip
    found += [pytest.param(drop(named(n), q, r), id=f'left: {n} q{q} {i}') for i, (n, r, q) in enumerate(LEFT)]
    for key in sorted(PICKUPS['kb']):
        found += [
            pytest.param(kb_drop(key), id=f'kb: {key}'),
            pytest.param(kb_drop(key, perfect=False), id=f'kb: {key} ordinary'),
        ]
        flipped = kb_drop(key)
        assert flipped.rolls is not None
        found.append(pytest.param(replace(flipped, rolls=replace(flipped.rolls, ethereal=not flipped.rolls.ethereal)),
                                  id=f'kb: {key} eth flipped'))  # fmt: skip
    return found


# The qualities each kind drops at (D2R): charms magic or unique, jewels and jewelry magic to unique (sets for
# jewelry), the other misc items as they are (runes, gems, potions, keys: normal); gear every quality
QUALITIES = {
    'charm': (MAGIC, UNIQUE),
    'jewel': (MAGIC, RARE, UNIQUE),
    'jewelry': (MAGIC, SET, RARE, UNIQUE),
    'gear': (LOW, NORMAL, SUPERIOR, MAGIC, SET, RARE, UNIQUE),
    'misc': (NORMAL,),
}
CHARM_KINDS, JEWEL_KINDS, JEWELRY_KINDS = (
    frozenset(('scha', 'mcha', 'lcha')),
    frozenset(('jewl', 'cjwl')),
    frozenset(('ring', 'amul')),
)


def quality_set(base: dict) -> tuple[int, ...]:
    kind = base.get('type')
    if kind in CHARM_KINDS:
        return QUALITIES['charm']
    if kind in JEWEL_KINDS:
        return QUALITIES['jewel']
    if kind in JEWELRY_KINDS:
        return QUALITIES['jewelry']
    return QUALITIES['gear'] if base.get('category') in ('weapons', 'armor') else QUALITIES['misc']


def sweep_cases() -> list:
    """Every item type at each quality it drops at, by the look's sources for it (a set or unique the filter shows is
    NAMED and prized; jewelry and misc items are read as materials too); a white one unread and read."""
    found = []
    bases = metadata()['bases']
    kinds = sorted({base['type'] for base in bases.values() if base.get('type')})
    for kind in kinds:
        txt = type_txt(kind)
        base = bases[str(txt)]
        gear = base.get('category') in ('weapons', 'armor')
        for quality in quality_set(base):
            sources = ['shown', 'material'] if gear or kind in JEWELRY_KINDS else ['material']
            if quality in (SET, UNIQUE):
                sources = [NAMED, *(['material'] if kind in JEWELRY_KINDS else [])]
            for source in sources:
                rolls = [None, Rolls(0)] if quality in (NORMAL, SUPERIOR) and gear else [None]
                for read in rolls:
                    said = f'sweep: {kind} q{quality} {source} {"read" if read else "unread"}'
                    found.append(pytest.param(drop(txt, quality, read, source=source), id=said))
        if gear:
            found.append(pytest.param(replace(drop(txt, RARE), size=(2, 4)), id=f'sweep: {kind} rare 2x4'))
            found.append(pytest.param(replace(drop(txt, MAGIC), size=(2, 2)), id=f'sweep: {kind} magic 2x2'))
            # marked: a material the marks name (a 'shown' drop is never prized: game/records.py `prized`)
            marked = replace(drop(txt, MAGIC, source='material'), prized=True)
            found.append(pytest.param(marked, id=f'sweep: {kind} magic marked'))
            found.append(pytest.param(replace(marked, size=(2, 4)), id=f'sweep: {kind} magic marked 2x4'))
    return found


def outcome(drop_: Drop, mode: str, looping: bool, assessed: bool, monkeypatch) -> tuple:
    """What the pickup level does with `drop_` (one look, a fresh field memory): the drop taken (its unit and
    must-have), the field identify's picks and waits, the cube's parking, the allowlisted bases remembered, the
    candidates."""
    field = api.Field(log=lambda *args: None)
    field.looping = lambda: looping
    monkeypatch.setattr(pickmode, 'FIELD', field)
    monkeypatch.setattr(pickmode, 'ASSESS_GROUND', assessed)
    monkeypatch.setattr(base_floor, 'TAKEN', {})
    loot = Loot(drops=(drop_,), game=GAME, room=EMPTY)
    got = pickmode.taken(loot, mode, lambda: 20).drops
    candidates = tuple(pickmode.identify_only(found) for found in got)
    return (tuple((d.unit_id, d.prized) for d in got), dict(field.picked), dict(field.waiting), dict(field.parking),
            dict(base_floor.TAKEN), candidates, pickmode.good(drop_))  # fmt: skip


@pytest.fixture(autouse=True)
def no_collection(monkeypatch):
    monkeypatch.setattr(loot_value, 'owned_bases', lambda facts: 0)  # never the host's collection


LEVELS = [pytest.param(mode, looping, id=f'{mode}-{"loop" if looping else "by hand"}')
          for mode in pickmode.MODES for looping in (True, False)]  # fmt: skip
# Where the entry point answers otherwise than today, each explained (none: the gate of ASSESS_GROUND)
OTHERWISE: dict[str, str] = {}


@pytest.mark.parametrize(('mode', 'looping'), LEVELS)
@pytest.mark.parametrize('found', script_cases() + table_cases() + base_cases() + sweep_cases())
def test_the_entry_point_takes_what_todays_rules_take(found, mode, looping, monkeypatch, request):
    new = outcome(found, mode, looping, True, monkeypatch)
    old = outcome(found, mode, looping, False, monkeypatch)
    if request.node.callspec.id in OTHERWISE:
        assert new != old
        return
    assert new[:-1] == old[:-1], (
        assess.Assessor(assess.NO_PRICES).assess(pickmode.from_drop(found), assess.Site.GROUND).said()
    )


def test_the_table_cases_take_the_counted_caps(monkeypatch):
    """The acceptance table's owned counts (the Spirit Monarch cap) through both ways."""
    for case in CASES:
        found = today.drop(ground_facts(case))
        monkeypatch.setattr(loot_value, 'owned_bases', counted(case))
        for mode in pickmode.MODES:
            new, old = outcome(found, mode, True, True, monkeypatch), outcome(found, mode, True, False, monkeypatch)
            assert new[:-1] == old[:-1], case['id']


def test_a_difference_is_logged_once_beside_the_new_decision(monkeypatch, caplog):
    """The shadow (loot/assess.py `shadow`): were the old rules to answer otherwise, one line says both."""
    monkeypatch.setattr(pickmode, 'SHADOWED', set())
    monkeypatch.setattr(assess, 'SHADOW_SAID', set())
    monkeypatch.setattr(pickmode, '_old_takes', lambda drop_, mode: False)
    rune = drop(type_txt('rune'), NORMAL, source='rune')
    with caplog.at_level('INFO'):
        for _ in range(2):
            pickmode.taken(Loot(drops=(rune,), game=GAME, room=EMPTY), pickmode.SURE)
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith('Macro: loot: assess: ground:')]
    assert len(lines) == 1
    assert lines[0].endswith('new pick / old leave (new decides)'), lines[0]


def test_a_failed_assessment_falls_back_to_todays_rules(monkeypatch):
    def broken(drop_):
        raise ValueError('wants mid-edit')

    monkeypatch.setattr(pickmode, 'assessed', broken)
    rune = drop(type_txt('rune'), NORMAL, source='rune')
    assert pickmode.taken(Loot(drops=(rune,), game=GAME, room=EMPTY), pickmode.SURE).drops == (rune,)
    assert pickmode.good(rune)
    assert not pickmode.identify_only(rune)


@pytest.mark.parametrize('assessed', [True, False], ids=['assessed', 'legacy'])
def test_squeeze_keeps_an_allowlisted_base_room(assessed, monkeypatch):
    """The squeeze's sure valuables are the entry point's `good` (2026-10-23, loot/design.md §10.7): an allowlisted
    superior 0os Monarch (5% ED: no `sure` base rule takes it) keeps its 2x3 from a magic Monarch the field would take;
    today's `sure` (the switch off) gave the room away."""
    key = 'uit/superior/noneth/0os/ordinary'  # Monarch (d2data armor.json:10216), a base-pickups.json KB key
    base = replace(kb_drop(key), unit_id=1)
    magic = drop(base.txt, MAGIC, Rolls(0, ethereal=False), unit=2)
    field = api.Field(log=lambda *args: None)
    field.looping = lambda: True
    monkeypatch.setattr(pickmode, 'FIELD', field)
    monkeypatch.setattr(pickmode, 'ASSESS_GROUND', assessed)
    monkeypatch.setattr(base_floor, 'TAKEN', {})
    room = ('########..',) * 3 + ('##########',)  # one 2x3 block free
    got = pickmode.taken(Loot(drops=(base, magic), game=GAME, room=room), pickmode.SURE, lambda: 20).drops
    assert pickmode.good(base) is assessed
    assert [d.unit_id for d in got] == ([1] if assessed else [1, 2])
    assert (2 in field.picked) is not assessed
