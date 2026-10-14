"""The read models' registry (combat/threats/__init__.py): what is bound to a summoner (baal-sim.md fix 2)."""

from inventory_tracking.combat import threats
from inventory_tracking.combat.sim import baal as rules


def test_baals_clone_is_bound_to_his_rows_by_their_ai_not_by_a_name():
    masters = threats.masters(rules.CLONE)
    assert masters == {int(row) for row, kept in rules.data()['monsters'].items() if kept.get('AI') == rules.AIS[0]}
    assert 544 in masters
    assert threats.masters(544) == frozenset()
    assert threats.masters(564) == frozenset()  # a tentacle stands its own time
    assert threats.masters(243) == frozenset()  # Diablo


def test_a_hostile_is_bound_only_while_a_hostile_of_its_masters_class_is_about():
    assert threats.bound({1: 544, 2: rules.CLONE, 3: 564}) == {2: (1,)}
    assert threats.bound({2: rules.CLONE, 3: 564}) == {}
    assert threats.bound({1: 544, 4: 544, 2: rules.CLONE}) == {2: (1, 4)}
