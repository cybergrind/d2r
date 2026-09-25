"""Per-jewel socket predicates with partial-capture uncertainty."""

import math
from collections import Counter

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.domain.facts import FactStatus


def has_verified_socket_item(facts, name):
    """A child name cannot override contradictory or unknown occupancy."""
    state = facts.socket_state
    return (
        facts.socket_contents == 'filled'
        and state.total.status == FactStatus.KNOWN
        and state.occupied.status == FactStatus.KNOWN
        and state.occupied.value > 0
        and any(child.get('name') == name for child in facts.socket_items)
    )


def child_stat(child, key):
    row = child.get('stats', {}).get(key)
    if row is None and child.get('stats_complete') is True:
        return 0
    if row and row.get('status') == 'decoded':
        value = row.get('value')
        if type(value) in (int, float) and math.isfinite(value):
            return value
    return None


def jewel_matches(facts, thresholds, *, name=None):
    """Existential across children, conjunctive within one actual jewel."""
    state = facts.socket_state
    if state.total.status == FactStatus.CONFLICTING:
        return 'unknown', None
    unknown = not state.identities_complete
    observations = []
    for child in facts.socket_items:
        kind = child.get('item_type')
        if kind is None:
            unknown = True
            continue
        if kind != 'jewl':
            continue
        if name is not None and child.get('name') != name:
            if child.get('name') is None:
                unknown = True
            continue
        values = {key: child_stat(child, key) for key in thresholds}
        observations.append(values)
        if any(value is not None and value < thresholds[key] for key, value in values.items()):
            continue
        if any(value is None for value in values.values()):
            unknown = True
        else:
            return 'true', values
    return ('unknown' if unknown else 'false'), observations


def jewel_stat(facts, key, threshold):
    truth, observed = jewel_matches(facts, {key: threshold})
    if isinstance(observed, dict):
        observed = observed[key]
    elif isinstance(observed, list):
        observed = [row[key] for row in observed if row[key] is not None]
    return truth, observed


def runes_equal(facts, names):
    """Compare complete linked rune multisets; a matching subset proves nothing."""
    state = facts.socket_state
    if (
        state.total.status != FactStatus.KNOWN
        or state.occupied.status != FactStatus.KNOWN
        or not state.identities_complete
    ):
        return 'unknown', None
    children = facts.socket_items
    if not children:
        return 'false', []
    if facts.socket_contents != 'filled':
        return 'unknown', None
    ids = [child.get('unit_id') for child in children]
    if (
        any(type(unit) is not int for unit in ids)
        or len(set(ids)) != len(ids)
        or [child.get('position') for child in children] != list(range(len(children)))
    ):
        return 'unknown', None
    bases = {base['code']: base for base in metadata()['bases'].values()}
    observed = []
    for child in children:
        base = bases.get(child.get('base_code'))
        if base is None or base['name'] != child.get('name'):
            return 'unknown', None
        observed.append(base['name'])
    return ('true' if Counter(observed) == Counter(names) else 'false'), observed
