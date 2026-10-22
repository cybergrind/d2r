"""Back through the portal for a boss after a beset recovery only when the safety allows it (macros/safety.py
RETURN_GATE `return_refused`, macros/running/recovery.py `back_for_bosses`, asked at macros/tzloop.py `perform`'s
portal return after the town visit; Battle Orders is not asked there, it is cast on the arrival (running/legs.py
`orders_on_arrival`); the coordinator, 2026-10-22, from
rca/2026-10-22/boss-ledger-findings.md's open item; the player: recoveries "yes, should try", "we must not die")."""

from types import SimpleNamespace

from inventory_tracking.game.records import Loot
from inventory_tracking.macros import safety
from inventory_tracking.macros.bossledger import Boss
from inventory_tracking.macros.running import recovery
from inventory_tracking.macros.safety import Safety, chosen_veto, return_refused


HEALING, REJUVENATION = 603, 531
FULL_BELT = (HEALING, HEALING, REJUVENATION, REJUVENATION) * 4


def loot(life: int = 1896, belt=FULL_BELT, read: bool = True) -> Loot:
    return Loot(belt=belt, life=life, max_life=1896, belt_read=read)


def decision(veto: str | None = None) -> dict:
    return {
        'chosen': 'Move', 'chosen_place': (10.0, 10.0),
        'candidates': [
            {'act': 'Hold', 'place': (0.0, 0.0), 'veto': 'lethal exposure in the short rollouts'},
            {'act': 'Move', 'place': (10.0, 10.0), 'veto': veto},
        ],
    }  # fmt: skip


def test_restocked_with_no_veto_goes_back() -> None:
    assert return_refused(loot(), decision()) is None


def test_life_or_potions_short_after_the_visit_refuse() -> None:
    assert 'life 1500/1896' in (return_refused(loot(1500), decision()) or '')
    assert return_refused(None, decision()) == 'the life is not read'
    short = (HEALING, HEALING, REJUVENATION, None) + (None,) * 12  # 2 healing, 1 rejuvenation
    said = return_refused(loot(belt=short), decision())
    assert said is not None
    assert '2 healing and 1 rejuvenation' in said
    assert return_refused(loot(read=False), decision()) == 'the belt is not read'


def test_a_veto_on_the_last_chosen_act_refuses() -> None:
    assert chosen_veto(decision()) is None  # the Hold's veto is not the chosen act's
    assert chosen_veto({}) is None
    said = return_refused(loot(), decision('lethal exposure in the short rollouts'))
    assert said == 'the last danger pricing vetoed its act (lethal exposure in the short rollouts)'


def test_the_switch_off_goes_back_whatever(monkeypatch) -> None:
    monkeypatch.setattr(safety, 'RETURN_GATE', False)
    assert return_refused(None, decision('x')) is None


def runner(guard: Safety) -> SimpleNamespace:
    loop = SimpleNamespace(on=True, kind=SimpleNamespace(agenda=True), agenda=object())
    return SimpleNamespace(loop=loop, hunter=SimpleNamespace(safety=guard))


def test_the_recovery_s_gate_says_go_back_or_the_stop_line_naming_the_bosses(monkeypatch) -> None:
    ismail = Boss('Ismail Vilehand', 102)
    monkeypatch.setattr(recovery, 'tz_bosses_alive', lambda agenda: [ismail])
    allowed = Safety(decision=decision())
    assert recovery.back_for_bosses(runner(allowed), loot()) is None  # type: ignore[arg-type]
    line = recovery.back_for_bosses(runner(allowed), loot(900))  # type: ignore[arg-type]
    assert line is not None
    assert 'not back through the portal: life 900/1896' in line
    assert 'Ismail Vilehand' in line
    assert line.endswith('the loop stops here for the player')
    monkeypatch.setattr(recovery, 'tz_bosses_alive', lambda agenda: [])
    assert recovery.back_for_bosses(runner(allowed), loot(900)) is None  # type: ignore[arg-type]
    monkeypatch.setattr(recovery, 'BOSS_RECOVERY', False)
    monkeypatch.setattr(recovery, 'tz_bosses_alive', lambda agenda: [ismail])
    assert recovery.back_for_bosses(runner(allowed), loot(900)) is None  # type: ignore[arg-type]
