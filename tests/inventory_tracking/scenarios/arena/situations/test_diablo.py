"""The recorded Diablo fight (diablo.py) and the duel of tactics against his red lightning (diablo_duel.py);
rca/2026-10-13/diablo.md sections 3 and 5."""

import statistics

from tests.inventory_tracking.scenarios.arena.situations import catalog, diablo, diablo_duel


def test_the_fight_is_in_the_catalog_with_today_and_new():
    entry = catalog.catalog()[diablo.NAME]
    labels = [label for label, _situation, _presses in entry.variants()]
    assert labels == [
        'as recorded: today', 'as recorded: new', 'attack mode alone: today', 'attack mode alone: new',
    ]  # fmt: skip


def test_the_recorded_fight_plays_with_his_missiles_taking_life():
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
    assert 100 <= by[('Diablo', 'spell')] <= 800


def test_pricing_his_stream_halves_what_it_takes_at_little_cost_in_time():
    found = diablo_duel.compare(range(1, 7), ('today', 'priced'))

    def light(policy):
        return statistics.mean(f.taken.get('lightning', 0.0) for f in found[policy])

    def kill(policy):
        return statistics.mean(f.killed_at for f in found[policy] if f.killed_at is not None)

    assert all(f.killed_at is not None and f.died_at is None for fights in found.values() for f in fights)
    assert light('priced') < 0.6 * light('today')
    assert kill('priced') <= 1.1 * kill('today')
