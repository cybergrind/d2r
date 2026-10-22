"""A tier 4-5 Herald's pack (combat/pack.py): who belongs, who presses the character, where the hop goes, who is
covered for the pointer. Places are those of take 20261021T063019Z-77 (rca/2026-10-21/herald-fight-findings.md): the
look of 09:30:50.95 (H-A, tanked) and of 09:32:23 (H-B, the pack on the demons, nothing lost)."""

import json
import math
from pathlib import Path

import pytest

from inventory_tracking.combat import pack
from inventory_tracking.combat.harm import Hostile


FIXTURES = Path(__file__).parents[1] / 'macros' / 'fixtures'
UNIQUE, MINION = 0x08, 0x10
DEFILER, URDAR, MERC = 744, 189, 338


def cut(name: str) -> tuple[tuple[float, float], list[pack.Member], list[tuple[float, float]]]:
    """The character's place, the pack and the demons' places of a fixture."""
    snap = json.loads((FIXTURES / f'{name}.json').read_text(encoding='utf-8'))
    here = (snap['player']['x'], snap['player']['y'])
    hostiles = [
        Hostile(m['unit'], m['txt'], (m['x'], m['y']), m['flags'], tuple(m['mods']), m['tier'])
        for m in snap['monsters']
        if not m['ally'] and m['owner'] == 0xFFFFFFFF
    ]
    demons = [(m['x'], m['y']) for m in snap['monsters'] if m['txt'] in (DEFILER, URDAR)]
    return here, pack.members(hostiles), demons


def test_the_pack_is_the_tier_4_and_5_heralds_and_their_minions() -> None:
    found = pack.members([
        Hostile(1, 128, (0.0, 0.0), UNIQUE, tier=5),
        Hostile(2, 128, (1.0, 0.0), MINION, tier=4),
        Hostile(3, 128, (2.0, 0.0), MINION, tier=3),
        Hostile(4, 8, (3.0, 0.0)),
    ])  # fmt: skip
    assert [(m.unit, m.herald) for m in found] == [(1, True), (2, False)]
    assert pack.key_of(found) == 1
    assert pack.key_of(found[1:]) == 2
    assert pack.key_of([]) is None


def test_with_the_tactic_off_no_hostile_is_of_a_pack(monkeypatch) -> None:
    monkeypatch.setattr(pack, 'PACK_TACTIC', False)
    assert pack.members([Hostile(1, 128, (0.0, 0.0), UNIQUE, tier=5)]) == []


def test_the_tanked_look_is_surrounded_and_its_hop_lands_in_range_with_the_defiler_between() -> None:
    here, members, demons = cut('herald-t5-tanked')
    assert len(members) == 10  # the Herald and nine Bramble Hulks read at that look
    why = pack.why_back(here, members, demons)
    assert why is not None
    assert why.startswith('surrounded: 3')  # 3.1, 3.6 and 4.2 off
    spots = pack.hop_spots(here, members, demons)
    assert spots
    first, middle = spots[0], pack.centre(here, members)
    assert pack.PACK_RANGE[0] <= math.dist(first, middle) <= pack.PACK_RANGE[1]
    assert all(math.dist(first, m.at) >= pack.PACK_BACK for m in members)
    defiler = demons[0]
    assert pack.between(first, members, defiler, here)


def test_the_held_look_is_no_reason_to_hop_the_pack_is_on_the_demons() -> None:
    here, members, demons = cut('herald-t5-held')
    near = [m for m in members if math.dist(here, m.at) < pack.PACK_BACK]
    assert near  # a Bramble Hulk 8 units off, 1.7 off the Defiler
    assert pack.holders(here, demons) == demons  # both 8.7-9.1 off the character
    assert pack.pressing(here, members, demons) == []
    assert pack.why_back(here, members, demons) is None


def test_the_marking_look_has_nothing_within_10_on_the_character() -> None:
    here, members, demons = cut('herald-t5-marking')
    assert min(math.dist(here, m.at) for m in members) == pytest.approx(10.01, abs=0.005)  # just outside 10
    assert pack.why_back(here, members, demons) is None


def test_a_demon_at_the_character_holds_nobody() -> None:
    here = (0.0, 0.0)
    members = [pack.Member(1, (6.0, 0.0))]
    assert pack.holders(here, [(0.5, 0.0)]) == []
    assert pack.pressing(here, members, [(0.5, 0.0)]) == members
    assert pack.pressing(here, members, [(5.0, 0.0)]) == []  # on the demon 1 off
    assert pack.pressing(here, [pack.Member(1, (11.0, 0.0))], []) == []  # beyond 10


def test_the_keep_range_switch_stops_every_hop(monkeypatch) -> None:
    here, members, demons = cut('herald-t5-tanked')
    monkeypatch.setattr(pack, 'PACK_KEEP_RANGE', False)
    assert pack.why_back(here, members, demons) is None


def test_with_no_demon_out_the_hop_goes_straight_away_from_the_pack() -> None:
    here = (0.0, 0.0)
    members = [pack.Member(1, (5.0, 0.0)), pack.Member(2, (7.0, 1.0)), pack.Member(3, (7.0, -1.0))]
    first = pack.hop_spots(here, members, [])[0]
    assert first[0] < 0
    assert abs(first[1]) < 1e-6
    assert math.dist(first, pack.centre(here, members)) == pytest.approx(pack.PACK_STAND)


def test_a_body_drawn_in_front_within_4_covers_one_for_the_pointer() -> None:
    assert pack.covered((0.0, 0.0), [(2.0, 1.0)])  # in front (x + y larger), 2.2 off
    assert not pack.covered((0.0, 0.0), [(-2.0, -1.0)])  # behind
    assert not pack.covered((0.0, 0.0), [(4.0, 3.0)])  # 5 off
    assert not pack.covered((0.0, 0.0), [(0.0, 0.0)])  # itself


# Sigil: Lethargy at the disc that covers the most of the pack, then on the demon that holds it (SIGIL_COVER; the
# player, 2026-10-21 ~09:40: "sigil of lethargy to slow whole group"). H-A's first sigil (under the Herald) held 6-7
# of 15; H-B's one, laid among the pack bunched on the demons, 10-11 of 12 (rca/2026-10-21/herald-fight-findings.md
# §2 step 3).
RADIUS = 6.0  # the medium sigil's (skills.txt 393 aurarangecalc at level 10-19; builds/warlock/buffs.py SIGIL_RADIUS)


def test_the_densest_disc_covers_more_of_the_tanked_pack_than_the_herald_s_place() -> None:
    here, members, _ = cut('herald-t5-tanked')
    herald = next(m for m in members if m.herald)
    spot, _ = pack.sigil_spot(here, members, [], RADIUS)
    under_herald = pack.cover_weight(herald.at, members, RADIUS)
    assert pack.cover_weight(spot, members, RADIUS) >= under_herald
    assert len(pack.covering(spot, members, RADIUS)) >= len(members) // 2


def test_the_disc_weighs_the_herald_twice() -> None:
    herald = pack.Member(1, (0.0, 0.0), herald=True)
    apart = [pack.Member(2, (20.0, 0.0)), pack.Member(3, (34.0, 0.0))]  # no disc of 6 covers both
    spot, _ = pack.sigil_spot((10.0, -20.0), [herald, *apart], [], RADIUS)
    assert math.dist(spot, herald.at) <= RADIUS  # 2 for the Herald alone against 1 for either minion
    three = [pack.Member(2, (20.0, 0.0)), pack.Member(3, (21.0, 0.0)), pack.Member(4, (20.0, 1.0))]
    spot, _ = pack.sigil_spot((10.0, -20.0), [herald, *three], [], RADIUS)
    assert math.dist(spot, herald.at) > RADIUS  # three minions together outweigh it


def test_the_held_look_s_sigil_covers_most_of_the_pack() -> None:
    here, members, demons = cut('herald-t5-held')
    spot, why = pack.sigil_spot(here, members, demons, RADIUS)
    assert len(pack.covering(spot, members, RADIUS)) >= 9  # H-B's one sigil held 10-11 of 12
    assert why.startswith('the disc covering')  # the demons stood at its edge: their discs cover 4 each


def test_the_sigil_goes_on_the_demon_that_holds_the_pack() -> None:
    demon = (10.0, 0.0)
    bunched = [pack.Member(k, (10.0 + 2.0 * math.cos(k), 2.0 * math.sin(k))) for k in range(6)]
    far = [pack.Member(10, (28.0, 0.0)), pack.Member(11, (28.0, 5.0))]
    spot, why = pack.sigil_spot((0.0, 0.0), [*bunched, *far], [demon], RADIUS)
    assert spot == demon
    assert why == 'on the demon holding 6 of 8'


def test_a_demon_at_the_character_holds_no_sigil() -> None:
    here, members, demons = cut('herald-t5-tanked')  # the demons at 0.0 and 3.2 from the character
    spot, why = pack.sigil_spot(here, members, demons, RADIUS)
    assert why.startswith('the disc covering')
    assert spot not in demons


def test_the_cover_share_counts_the_members_within_the_radius() -> None:
    members = [pack.Member(1, (0.0, 0.0)), pack.Member(2, (5.0, 0.0)), pack.Member(3, (7.0, 0.0))]
    assert pack.cover_share((0.0, 0.0), members, RADIUS) == pytest.approx(2 / 3)
    assert pack.cover_share((0.0, 0.0), [], RADIUS) == 0.0
