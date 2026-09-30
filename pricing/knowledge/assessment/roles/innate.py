"""Named additive rolls with linked socket contributions removed."""

from pricing.knowledge.assessment.domain.facts import Fact, FactStatus, StatKey
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.roles.socket_payload import child_stat


# Explicitly reviewed additive scalar. Do not extrapolate to percent defense,
# weapon damage, flags, poison duration or a completed runeword's recipe stats.
ADDITIVE_KEYS = frozenset({'358:0'})


def innate_stat(facts, key):
    unknown = Fact(None, FactStatus.UNKNOWN)
    if key not in ADDITIVE_KEYS or facts.rarity != 'unique' or facts.identified is not True or facts.runeword:
        return unknown
    definition, gaps = resolve_named_definition(facts)
    if definition is None or gaps:
        return unknown
    spec = definition.get('roll_ranges', {}).get(key.split(':')[0])
    if not spec:
        return unknown
    stat, parameter = map(int, key.split(':'))
    observed = facts.stat(StatKey(stat, parameter))
    if observed.status != FactStatus.KNOWN or type(observed.value) is not int:
        return unknown
    state = facts.socket_state
    if (
        state.total.status != FactStatus.KNOWN
        or state.occupied.status != FactStatus.KNOWN
        or state.empty.status != FactStatus.KNOWN
        or not state.identities_complete
    ):
        return unknown
    children = facts.socket_items
    if state.occupied.value:
        ids = [child.get('unit_id') for child in children]
        positions = [child.get('position') for child in children]
        if (
            facts.socket_contents != 'filled'
            or len(children) != state.occupied.value
            or any(type(uid) is not int for uid in ids)
            or len(set(ids)) != len(ids)
            or positions != list(range(len(children)))
        ):
            return unknown
    elif facts.socket_contents != 'empty' or children:
        return unknown
    values = [child_stat(child, key) for child in children]
    if any(type(value) is not int or value < 0 for value in values):
        return unknown
    innate = observed.value - sum(values)
    if not spec['min'] <= innate <= spec['max']:
        return unknown
    return Fact(innate, FactStatus.KNOWN, 'socket_adjusted_named_roll')
