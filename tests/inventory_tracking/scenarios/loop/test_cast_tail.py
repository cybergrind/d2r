"""CAST_TAIL (hunt.py, 2026-10-24): a Teleport's landing is read before its cast ends, with Teleport still on the right
button (Quick Cast) and Echoing Strike on no key; the fight starts from the look that sees the strike back, not after
a FRAME nap and another pass of the loop (rca/2026-10-24/realtime-4-findings.md §7)."""

import sys
from dataclasses import replace

import pytest

from inventory_tracking.macros import hunt
from inventory_tracking.macros.skills import TELEPORT
from tests.inventory_tracking.scenarios.loop.helpers import NO_MARK_SLOTS, attack_mode, foe, game, hunter, left_click


ECHOING_STRIKE = 388
STRIKE_OFF_KEYS = tuple(None if skill == ECHOING_STRIKE else skill for skill in NO_MARK_SLOTS)
CASTING = 10


def landed_casting(cast_until: float):
    """A foe in reach of the character, who is in its Teleport's cast's tail until `cast_until`: Teleport on the right
    button meanwhile, Echoing Strike back on it after; the strike on no skill key."""
    play = game(foe(10, 5008.0, 5000.0), slots=STRIKE_OFF_KEYS)
    play.toughness[10] = 1000
    player = play.world.player
    assert player is not None
    free = replace(player, right_skill=ECHOING_STRIKE)
    play.world = replace(play.world, player=replace(free, mode=CASTING, right_skill=TELEPORT))
    play.arrivals.append((cast_until, lambda: setattr(play, 'world', replace(play.world, player=free))))
    return play


@pytest.fixture
def looks(monkeypatch):
    seen: dict = {'choose': [], 'loop naps': [], 'clock': lambda: 0.0}
    seen = {'choose': [], 'loop naps': [], 'clock': None}
    choose, nap = hunt.Hunter.choose, hunt.Hunter.nap

    def counted_choose(self, *args, **kwargs):
        seen['choose'].append(seen['clock']())
        return choose(self, *args, **kwargs)

    def counted_nap(self, run, seconds, **kwargs):
        if seconds == hunt.FRAME and sys._getframe(1).f_code.co_name == '_attack_looks':
            seen['loop naps'].append(run.clock())
        return nap(self, run, seconds, **kwargs)

    monkeypatch.setattr(hunt.Hunter, 'choose', counted_choose)
    monkeypatch.setattr(hunt.Hunter, 'nap', counted_nap)
    return seen


@pytest.mark.parametrize(('on', 'again'), [(False, False), (True, False), (True, True)], ids=['off', 'on', 'again'])
def test_the_fight_starts_at_the_look_that_sees_the_cast_end(monkeypatch, looks, on, again):
    # again (CAST_TAIL_AGAIN): the loop's next pass at once from that look, then the fight; no FRAME nap either way
    monkeypatch.setattr(hunt, 'CAST_TAIL', on)
    monkeypatch.setattr(hunt, 'CAST_TAIL_AGAIN', again)
    play = landed_casting(0.05)
    looks['clock'] = lambda: play.clock.now
    attack_mode(play, hunter(play), until=0.5)
    first = looks['choose'][0]
    if on:
        assert 0.05 <= first <= 0.05 + hunt.SLICE + 0.002  # the look after the cast's end
        assert looks['loop naps'] == []  # no FRAME nap and no second pass of the loop
    else:
        assert first >= 0.08  # two FRAME naps: the loop's own pace
        assert len(looks['loop naps']) == 2
    assert play.struck_at, 'the strike comes'


def test_a_cast_tail_past_its_most_falls_back_to_the_naps(monkeypatch, looks):
    monkeypatch.setattr(hunt, 'CAST_TAIL', True)
    play = landed_casting(0.4)  # longer than CAST_TAIL_MOST
    looks['clock'] = lambda: play.clock.now
    attack_mode(play, hunter(play), until=1.0)
    assert hunt.CAST_TAIL_MOST < 0.4
    assert looks['loop naps'], 'the loop napped as before'
    assert looks['choose'][0] >= 0.4
    assert play.struck_at


def test_a_click_in_the_cast_tail_is_the_players(monkeypatch, looks):
    monkeypatch.setattr(hunt, 'CAST_TAIL', True)
    play = landed_casting(0.05)
    looks['clock'] = lambda: play.clock.now
    attack_mode(play, hunter(play), until=0.6, events=[left_click(play, 0.02, seconds=0.2)])
    assert all(at >= 0.22 for at, _ in play.struck_at), 'no strike while the player holds the button'
