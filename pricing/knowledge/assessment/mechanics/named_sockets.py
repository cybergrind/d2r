"""Native named socket rolls, clamped before any later base upgrade."""

import json
from functools import lru_cache
from pathlib import Path

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.domain.facts import FactStatus


UTILITY = Path(__file__).resolve().parents[3] / 'data/appraisal-utility.json'


@lru_cache(maxsize=2)
def _socket_caps(raw):
    rows = json.loads(raw)['rows']
    return {
        row['base_code']: tuple(row['details']['larzuk_unknown_ilvl']['maximum_by_ilvl_bracket'])
        for row in rows
        if row.get('kind') == 'base_rule' and row.get('details', {}).get('rule') == 'socket_potential'
    }


def native_socket_roll(definition):
    spec = definition.get('roll_ranges', {}).get('194')
    if spec:
        return spec['min'], spec['max']
    source = definition.get('game_definition', {})
    params = [source.get(f'par{i}') for i in range(1, 13) if source.get(f'prop{i}') == 'sock']
    if not params:
        return None
    if len(params) != 1 or type(params[0]) is not int or not 1 <= params[0] <= 6:
        return ()
    return params[0], params[0]


def socket_outcomes(definition, item_level=None):
    """Return native attainable counts and errors, independent of observed count."""
    roll = native_socket_roll(definition)
    if roll is None:
        return (), []
    if not roll or any(type(v) is not int or not 1 <= v <= 6 for v in roll) or roll[0] > roll[1]:
        return (), ['Named native socket roll is unverified.']
    base = definition.get('base_definition', {})
    try:
        caps = _socket_caps(read_artifact(UTILITY)).get(base.get('code'), ())
    except OSError, ValueError, KeyError, TypeError:
        caps = ()
    if len(caps) != 3 or any(type(c) is not int or not 1 <= c <= 6 for c in caps):
        return (), ['Named native socket capacity is unverified.']
    dimensions = (base.get('invwidth'), base.get('invheight'))
    if any(type(n) is not int or n <= 0 for n in dimensions):
        return (), ['Named native socket dimensions are unverified.']
    if item_level is not None:
        caps = (caps[0 if item_level <= 25 else 1 if item_level <= 40 else 2],)
    # PropertyFunc14 clamps to base/type/level capacity and inventory dimensions.
    # Unknown item level permits only the union of actual native outcomes.
    possible = sorted({min(n, cap, dimensions[0] * dimensions[1]) for cap in caps for n in range(roll[0], roll[1] + 1)})
    return tuple(possible), []


def socket_gaps(facts, definition):
    # SUnitNpc.cpp2273-2291 caps quest sockets at one for unique/set quality.
    # Native socket modifiers have their own ranges below and cannot be replaced
    # with this quest rule (Crown of Ages, Griswold's equipment, etc.).
    if (
        native_socket_roll(definition) is None
        and facts.rarity in ('unique', 'set')
        and type(facts.sockets) is int
        and facts.sockets > 1
    ):
        return ['Named item without native sockets can have at most one quest socket.']
    possible, errors = socket_outcomes(definition, facts.item_level)
    if errors or not possible:
        return errors
    row = facts.stats.get('194:0', {})
    if (
        facts.socket_state.total.status != FactStatus.KNOWN
        or facts.sockets not in possible
        or row.get('status') != 'decoded'
        or type(row.get('raw')) is not int
        or row['raw'] != facts.sockets
        or type(row.get('value')) is not int
        or row['value'] != facts.sockets
    ):
        return [f'Named sockets must match native outcomes {list(possible)} and the captured socket count.']
    return []
