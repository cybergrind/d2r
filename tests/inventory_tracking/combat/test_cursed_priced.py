"""CURSED_PRICED (combat/harm.py, 2026-10-24; rca/2026-10-24/cast-hold-findings.md §4): a Cursed hostile (monumod 7)
puts Amplify Damage on the party from afar, so its pack's physical blows are priced at the cursed share."""

from inventory_tracking.combat import harm as module
from inventory_tracking.combat.harm import Hostile, Look, Protection, harm


PIT_LORD = 361
UNCURSED = Protection(resists=(('physical', 18.0),), level=96)  # the Halls' character before the curse
PLACE = (0.0, 0.0)


def pack(mods: tuple[int, ...], away: float = 3.0) -> Look:
    return Look((Hostile(1, PIT_LORD, (away, 0.0), 16, mods, 5, level=85),), battle=UNCURSED, travel=UNCURSED)


def test_off_a_cursed_pack_is_priced_as_any(monkeypatch):
    monkeypatch.setattr(module, 'CURSED_PRICED', False)
    assert harm(pack((7, 9, 5)), PLACE, 2.0, 'battle') == harm(pack((9, 5)), PLACE, 2.0, 'battle')


def test_on_a_cursed_pack_in_reach_costs_more_and_another_the_same(monkeypatch):
    monkeypatch.setattr(module, 'CURSED_PRICED', False)
    plain = harm(pack((9, 5)), PLACE, 2.0, 'battle')
    before = harm(pack((7, 9, 5)), PLACE, 2.0, 'battle')
    monkeypatch.setattr(module, 'CURSED_PRICED', True)
    cursed = harm(pack((7, 9, 5)), PLACE, 2.0, 'battle')
    assert cursed.mean > before.mean * 1.2  # the physical share 0.82 -> 1.82 on most rollouts (fire unchanged)
    assert cursed.worst > before.worst * 1.2
    assert harm(pack((9, 5)), PLACE, 2.0, 'battle') == plain  # bit-identical with no Cursed hostile


def test_on_a_cursed_hostile_out_of_reach_curses_nothing(monkeypatch):
    monkeypatch.setattr(module, 'CURSED_PRICED', True)
    far = pack((7, 9, 5), away=module.CURSED_REACH + 5.0)
    assert module.amplify_rate(far, PLACE, 2.0) == 0.0
    assert module.amplify_rate(pack((7, 9, 5)), PLACE, 2.0) == 2.0 / module.CURSED_SECONDS
