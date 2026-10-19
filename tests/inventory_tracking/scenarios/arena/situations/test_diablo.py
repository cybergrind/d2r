"""The recorded Diablo fight (diablo.py) and the duel of tactics against his red lightning (diablo_duel.py);
rca/2026-10-13/diablo.md sections 3 and 5."""

import statistics

from inventory_tracking.macros.hunt import Hunter
from tests.inventory_tracking.scenarios.arena.situations import catalog, diablo, diablo_duel


def test_the_fight_is_in_the_catalog_with_today_and_new():
    entry = catalog.catalog()[diablo.NAME]
    labels = [label for label, _situation, _presses in entry.variants()]
    assert labels == [
        'as recorded: today', 'as recorded: new', 'attack mode alone: today', 'attack mode alone: new',
    ]  # fmt: skip


def test_the_recorded_fight_plays_with_his_missiles_taking_life(monkeypatch):
    # The take's macro held through his casts: its calibration is played so, without the mode alone's safety step
    # that came later (hunting/judging.py `guard`, rca/2026-10-14/baal-sim.md fix 3: seed 1 then takes 64 of his spell)
    monkeypatch.setattr(Hunter, 'guard', lambda *args: None)
    situation = diablo.stored()
    assert situation.source is not None
    assert situation.recorded is not None
    assert situation.source['take'] == diablo.TAKE
    assert situation.recorded['taken'] == 255.0
    outcome = situation.play(seed=1)
    assert not outcome.dead
    assert any(what.endswith('Diablo') for _at, what, _n in outcome.appeared)
    by = outcome.taken_by()
    # The game lost 255; the arena his stream and wall by the client's rules, in the same order of size.
    assert 100 <= by['Diablo', 'spell'] <= 800


def test_pricing_his_stream_halves_what_it_takes_at_little_cost_in_time():
    found = diablo_duel.compare(range(1, 7), ('today', 'priced'))

    def light(policy):
        return statistics.mean(f.taken.get('lightning', 0.0) for f in found[policy])

    def kill(policy):
        return statistics.mean(f.killed_at for f in found[policy] if f.killed_at is not None)

    assert all(f.killed_at is not None and f.died_at is None for fights in found.values() for f in fights)
    assert light('priced') < 0.6 * light('today')
    assert kill('priced') <= 1.1 * kill('today')


def test_attack_mode_alone_steps_across_his_lightning_and_strikes_on():
    """rca/2026-10-14/baal-sim.md fix 3: with the pursuit loop off, attack mode takes the loop's priced step across
    his stream (hunting/judging.py `guard`), then strikes again; it does not wander. Seed 1 held through it before: 295
    of his lightning, not a unit moved."""
    situation, presses = {label: (s, p) for label, s, p in diablo.variants()}['attack mode alone: today']
    assert not situation.pursuit
    outcome = situation.play(presses, seed=1)
    assert outcome.said_count("Stepping across Diablo's lightning") >= 1
    assert outcome.taken_by()['Diablo', 'spell'] < 150
    assert outcome.moved < 30  # steps of a few units each, no walk away
    assert not outcome.dead
