"""The jumps held while the demons take or hold the pack (combat/pack.py MARK_HOLDS_JUMPS, NO_SHORT_HOPS_T5;
rca/2026-10-25/tactics/teleports.md §3.4, §4.1-4.4, apply-0b.md). The player, 2026-10-24 ~19:58: "what is the logical
reason to do DM and then immediately call it off with tp?"; 2026-10-25 ~11:08: "we often try to move for short
distances in battle with T5 heralds => teleporting aggroed minions to us".

The shape of take 20261024T171005Z-46 at 20:11:11.08-11.40 (teleports.md §4.1): the mark first at the landing, and
0.32 s after its key the Extra Fast keep range's hop pulled both demons back mid-flight to the mark."""

import math
from types import SimpleNamespace

import pytest

from inventory_tracking.combat import pack


HERE = (5000.0, 5000.0)
MEMBERS = [SimpleNamespace(at=(5014.0, 5000.0), tier=5), SimpleNamespace(at=(5017.0, 5003.0), tier=5)]
ON_THE_PACK = [(5012.0, 5001.0)]  # 2 off a member, 12 off the character: it holds the pack
BY_US = [(5000.6, 5000.0)]  # taken along: it holds nothing


@pytest.fixture(autouse=True)
def holds_off(monkeypatch):
    """Both holds off unless a test turns one on: the tests pin each switch's own behaviour, whatever the tree ships."""
    monkeypatch.setattr(pack, 'MARK_HOLDS_JUMPS', False)
    monkeypatch.setattr(pack, 'NO_SHORT_HOPS_T5', False)


@pytest.fixture
def marks(monkeypatch):
    monkeypatch.setattr(pack, 'MARK_HOLDS_JUMPS', True)
    pack.FIRST.add(-1)
    yield
    pack.FIRST.discard(-1)


def test_off_there_is_no_hold():
    assert pack.jump_hold(10.0, HERE, MEMBERS, ON_THE_PACK) is None
    assert pack.held(None, (4970.0, 5000.0), pack.KEEP) is None
    assert not pack.walks_now(None)


def test_the_keep_range_hop_waits_for_the_demons_to_land_on_the_mark(marks):
    pack.keyed(-1, 11.08)  # the mark first at the landing
    hold = pack.jump_hold(11.40, HERE, MEMBERS, BY_US)  # 0.32 s on: the hop of the take
    said = pack.held(hold, (4985.0, 5000.0), pack.KEEP)
    assert said is not None
    assert said.endswith('MARK_HOLDS_JUMPS)')
    assert pack.held(hold, (4985.0, 5000.0), pack.RETREAT) is not None
    later = pack.jump_hold(11.08 + pack.MARK_LANDS + 0.05, HERE, MEMBERS, ON_THE_PACK)
    assert pack.held(later, (4985.0, 5000.0), pack.KEEP) is None  # judged again with the demons on the pack
    assert pack.held(later, (5008.0, 5010.0), pack.PLACE) is not None  # the better place is walked meanwhile
    assert pack.walks_now(later)
    gone = pack.jump_hold(11.08 + pack.MARK_WALKS + 0.05, HERE, MEMBERS, ON_THE_PACK)
    assert pack.held(gone, (5008.0, 5010.0), pack.PLACE) is None
    assert not pack.walks_now(gone)


def test_a_real_threat_lifts_the_hold(marks):
    pack.keyed(-1, 11.08)
    hold = pack.jump_hold(11.2, HERE, MEMBERS, BY_US, exempt='surrounded: 3 within 5')
    assert pack.held(hold, (4985.0, 5000.0), pack.KEEP) is None
    assert not pack.walks_now(hold)


def test_only_the_marks_own_skill_holds(marks):
    pack.keyed(-2, 11.08)  # another skill
    hold = pack.jump_hold(11.2, HERE, MEMBERS, BY_US)
    assert hold is not None
    assert hold.marked == math.inf
    assert pack.held(hold, (4985.0, 5000.0), pack.KEEP) is None


@pytest.mark.parametrize('on', [False, True])
def test_short_hops_by_a_held_t5_pack_are_not_made(monkeypatch, on):
    monkeypatch.setattr(pack, 'NO_SHORT_HOPS_T5', on)
    hold = pack.jump_hold(20.0, HERE, MEMBERS, ON_THE_PACK)
    assert (hold is not None) is on
    short = pack.held(hold, (4990.0, 5004.0), pack.PLACE)  # 11 units
    assert (short is not None) is on
    inside = pack.held(hold, (5010.0, 5012.0), pack.PLACE)  # 15.6 units, 12.6 from a member
    assert (inside is not None) is on
    # The keep range's hop goes (2026-10-25 arena, apply-short.md: herald seed 8, the held hops let a hulk walk in)
    assert pack.held(hold, (4990.0, 5004.0), pack.KEEP) is None
    assert pack.held(hold, (4975.0, 5000.0), pack.RETREAT) is None  # 25 units, 39 off the pack: a real retreat


def test_short_hops_are_free_while_the_demons_hold_nothing(monkeypatch):
    monkeypatch.setattr(pack, 'NO_SHORT_HOPS_T5', True)
    hold = pack.jump_hold(20.0, HERE, MEMBERS, BY_US)  # taken along: by the character
    assert pack.held(hold, (4990.0, 5004.0), pack.PLACE) is None
    tier4 = [SimpleNamespace(at=m.at, tier=4) for m in MEMBERS]
    assert pack.held(pack.jump_hold(20.0, HERE, tier4, ON_THE_PACK), (4990.0, 5004.0), pack.PLACE) is None
    assert pack.held(pack.jump_hold(20.0, HERE, MEMBERS, ON_THE_PACK, 'hit'), (4990.0, 5004.0), pack.PLACE) is None


def test_the_reaggro_is_due_with_the_demons_idle_by_us_and_the_pack_on_us(monkeypatch):
    """REAGGRO_BY_MARK (rewritten 2026-10-25, apply-1.md): the demons by the character, two on it within PACK_BACK."""
    on_us = [(5008.0, 5000.0), (5007.0, 5005.0)]  # within PACK_BACK of us, beyond DEMON_HOLDS of the demon
    assert not pack.reaggro_due(HERE, BY_US, on_us)  # off
    monkeypatch.setattr(pack, 'REAGGRO_BY_MARK', True)
    assert pack.reaggro_due(HERE, BY_US, on_us)
    assert not pack.reaggro_due(HERE, BY_US, on_us[:1])  # one is no pack on the character
    assert not pack.reaggro_due(HERE, [(5005.0, 5001.0)], on_us)  # a demon on a member: it holds it
    assert not pack.reaggro_due(HERE, BY_US, [(5014.0, 5000.0), (5015.0, 5000.0)])  # beyond PACK_BACK


def test_the_reaggro_bar_lasts_until_the_mark_has_landed(marks):
    assert not pack.reaggro_holds(20.0, None)
    assert pack.reaggro_holds(20.3, 20.0)
    assert not pack.reaggro_holds(20.0 + pack.REAGGRO_WAIT + 0.1, 20.0)  # the stretch's time is out
    pack.keyed(-1, 20.4)
    assert pack.reaggro_holds(20.6, 20.0)  # keyed, the demons still on their way
    assert not pack.reaggro_holds(20.4 + pack.MARK_LANDS + 0.01, 20.0)
    pack.keyed(-1, 19.0)  # a mark before the stretch is not its mark
    assert pack.reaggro_holds(20.6, 20.0)


def threat(hostiles, *, reach=0.0, life=2900.0):
    """`Safety.real_threat` on a look of `hostiles` (txt, at) with `reach` points of blows in reach of the character;
    '' for none."""
    from inventory_tracking.combat.harm import Hostile
    from inventory_tracking.macros.safety import Safety

    found = tuple(Hostile(unit=i, txt=txt, at=at) for i, (txt, at) in enumerate(hostiles))
    p = SimpleNamespace(
        here=HERE, look=SimpleNamespace(hostiles=found, life=life), burning=(), close=False, reach_blows=lambda s: reach
    )
    stub = SimpleNamespace(alarmed=False)
    said = Safety.real_threat(stub, p, SimpleNamespace(burst=0.0), 100.0, None)  # pyrefly: ignore[bad-argument-type]
    return said or ''


def test_a_ranged_pack_in_reach_lifts_the_hold():
    """2026-10-25 (apply-0b.md): the Canyon's Hell Slingers (txt 376) threw a volley at the walk the hold gave."""
    slingers = [(376, (5010.0 + i, 5005.0)) for i in range(pack.HOLD_SHOOTERS)]
    assert threat(slingers[:-1]) == ''
    assert threat(slingers).startswith('ranged fire')
    assert threat([(7, at) for _, at in slingers]) == ''  # Ghouls: melee, the demons hold them
    assert threat([(376, (5040.0 + i, 5000.0)) for i in range(5)]) == ''  # beyond the shot's reach


def test_blows_in_reach_that_take_the_life_lift_the_hold():
    """2026-10-25 (apply-0b.md): danger-durance-1956 seed 17, 4529 of 2907 in reach 0.43 s after the mark's key."""
    assert threat([], reach=4529.0, life=2907.0).startswith('within reach of blows')
    assert threat([], reach=2000.0, life=2907.0) == ''
