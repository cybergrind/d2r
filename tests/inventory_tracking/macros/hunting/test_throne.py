"""The Throne's portal gate (macros/hunting/throne.py `portal_shut`, running/legs.py `throne_shut`): the frames of take
20261021T142136Z-131 (17:21-17:24 on 2026-10-21, rca/2026-10-21/worldstone-chamber-findings.md)."""

from inventory_tracking.game.records import Monster, World
from inventory_tracking.macros.hunting import throne
from inventory_tracking.macros.running.legs import throne_shut
from inventory_tracking.routes.model import fight, use
from tests.inventory_tracking.macros.fakes import player, world


SEAT = (15090.5, 5011.5)


def test_the_portal_is_shut_while_the_hall_holds_a_minion_or_baal_sits_and_opens_after_he_is_gone():
    waves = throne.Waves()
    waves.begin('g')
    minion = Monster(3146387288, 571, 1, 15092.8, 5021.9)  # alive to 17:24:26.9, 10 from the seat
    assert throne.portal_shut(waves, seat=SEAT, hall=[minion], now=0.0) == 'the throne hall first (1 left)'
    assert throne.portal_shut(waves, seat=SEAT, hall=[], now=1.0) == 'Baal has not left his throne'  # 543 to 36.9
    assert throne.portal_shut(waves, seat=(15090.5, 5007.5), hall=[], now=11.0) is not None  # 559 walking in
    assert throne.portal_shut(waves, seat=None, hall=[], now=12.0) == throne.PORTAL_OPENING  # gone at 38.5
    assert throne.portal_shut(waves, seat=None, hall=[], now=12.0 + throne.PORTAL_OPENS - 0.1) is not None
    assert throne.portal_shut(waves, seat=None, hall=[], now=12.0 + throne.PORTAL_OPENS) is None
    foot = throne.foot_of(throne.PORTAL_AT)
    assert throne.portal_shut(waves, seat=None, hall=[], now=20.0, here=(15082.1, 5006.9)) == throne.PORTAL_NEAR
    assert throne.portal_shut(waves, seat=None, hall=[], now=21.0, here=foot) == throne.PORTAL_OPENING
    assert throne.portal_shut(waves, seat=None, hall=[], now=21.0 + throne.FOOT_WAIT, here=foot) is None
    assert throne.PORTAL_GATE


def world_at(monsters, area=throne.THRONE, here=(15079.5, 5012.5)) -> World:
    return world(area, monsters=tuple(monsters), game_name='g', player=player(area, x=here[0], y=here[1]))


def test_the_way_on_at_the_chamber_portal_is_the_level_run_until_baal_is_gone(monkeypatch):
    from inventory_tracking.macros.running import legs

    stage = use('Worldstone Chamber', throne.CHAMBER)
    monkeypatch.setattr(legs.route, 'staged', lambda progress, area: ('Baal', stage))
    hunter = throne.Waves()
    baal = Monster(3586302371, throne.THRONE_BAAL, 1, *SEAT)
    minion = Monster(3146387288, 571, 1, 15092.8, 5021.9)
    assert throne_shut(hunter, None, world_at([baal, minion]), 0.0) == 'the throne hall first (1 left)'
    assert throne_shut(hunter, None, world_at([baal]), 1.0) == 'Baal has not left his throne'
    # Gone (17:24:38.5 in game 2): the character at (15079.5, 5012.5) is off the portal's foot: to it first
    assert throne_shut(hunter, None, world_at([]), 12.0) == throne.PORTAL_NEAR
    foot = throne.foot_of(throne.PORTAL_AT)
    assert throne_shut(hunter, None, world_at([], here=foot), 13.0) == throne.PORTAL_OPENING
    assert throne_shut(hunter, None, world_at([], here=foot), 13.0 + throne.FOOT_WAIT) is None
    # Started mid-Throne with Baal already gone (the restart of 17:3x): the foot and its wait, then the click
    fresh = throne.Waves()
    assert throne_shut(fresh, None, world_at([], here=foot), 100.0) is not None
    assert throne_shut(fresh, None, world_at([], here=foot), 100.0 + throne.FOOT_WAIT) is None
    # Not the portal's stage, not the Throne: nothing held
    monkeypatch.setattr(legs.route, 'staged', lambda progress, area: ('Baal', fight('Lister the Tormentor')))
    assert throne_shut(hunter, None, world_at([baal]), 0.0) is None
    monkeypatch.setattr(legs.route, 'staged', lambda progress, area: ('Baal', stage))
    assert throne_shut(hunter, None, world_at([baal], area=130), 0.0) is None
    assert throne_shut(None, None, world_at([baal]), 0.0) is None


def test_the_zones_own_way_into_the_chamber_holds_the_gate_while_lister_s_minions_live(monkeypatch):
    # Game 4 at 09:13:34.8 on 2026-10-22 (take 20261022T061049Z-131): Lister died with 3 of his 8 alive, the character
    # at the stand (15080.5, 5015.5), 14 from the portal: the way on's press, no gate (the zone's `enter`), three
    # `Untook` in 0.12 s. The zone's stage (macros/zonenav.py PORTAL_USES) is the route's `use`: the level run first
    from inventory_tracking.macros import zonenav
    from inventory_tracking.macros.running import legs
    from inventory_tracking.routes.catalog import ROUTES
    from inventory_tracking.routes.progress import Progress
    from inventory_tracking.routes.zone_graph import Chain, zone_graph

    keep = zone_graph('Act5-Manual', (Chain(129, (129, 130, 131, 132), frozenset((129, 130, 131, 132))),))
    judged = zonenav.judge(keep, {}, lambda area, finished: 'plus')
    stage = zonenav.scripts(keep, judged, Progress(ROUTES).scripts.get)[131][1].stages[-1]
    monkeypatch.setattr(legs.route, 'staged', lambda progress, area: ('Baal', stage))
    baal = Monster(1390514700, throne.THRONE_BAAL, 1, *SEAT)
    minions = [
        Monster(unit, 571, 1, x, y) for unit, x, y in ((1, 15086.1, 5025.9), (2, 15074.5, 5036.5), (3, 15092.0, 5030.0))
    ]
    waves = throne.Waves()
    here = (15080.5, 5015.5)
    assert throne_shut(waves, None, world_at([baal, *minions], here=here), 0.0) == 'the throne hall first (3 left)'
    assert throne_shut(waves, None, world_at([baal], here=here), 5.0) == 'Baal has not left his throne'
