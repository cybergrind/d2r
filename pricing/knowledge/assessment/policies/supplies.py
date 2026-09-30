"""Ordinary supply identities and quantities from the pinned native misc table."""

import hashlib
import json
from functools import lru_cache

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.policies.consumables import SOURCE, SOURCE_SHA256


# Exact codes verified in misc.json; shared types also contain quest/unused rows.
USES = {
    'isc': ('Identifies an unidentified item.', 'Carry for identifying finds away from town.'),
    'tsc': ('Opens a portal to town.', 'Carry for returning to town during a run.'),
    'ibk': ('Stores Scrolls of Identify.', 'Refill with Identify scrolls; each identification consumes one.'),
    'tbk': ('Stores Scrolls of Town Portal.', 'Refill with Town Portal scrolls; each portal consumes one.'),
    'key': ('Opens locked containers.', 'Carry keys when opening locked chests.'),
    'aqv': ('Ammunition for bows.', 'Keep a quiver for bow setups that consume arrows.'),
    'cqv': ('Ammunition for crossbows.', 'Keep a quiver for crossbow setups that consume bolts.'),
}
SCROLLS = frozenset({'isc', 'tsc'})


@lru_cache(maxsize=2)
def _definitions(raw):
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('Native supplies changed; review identities and quantities before publication.')
    native = json.loads(raw)
    return {code: native[code] for code in USES}


def definitions():
    return _definitions(read_artifact(SOURCE))


def assess_supply(facts):
    native = definitions().get(facts.base_code)
    if native is None:
        return None
    gaps = [*facts.gaps, *facts.projection_gaps]
    if (facts.name, facts.base_name, facts.item_type) != (native['name'], native['name'], native['type']):
        gaps.append('Supply identity conflicts with the native definition.')
    for field, expected in (('rarity', 'normal'), ('ethereal', False), ('sockets', 0), ('socket_contents', 'empty')):
        if getattr(facts, field) != expected:
            gaps.append(f'Ordinary supply requires {field}={expected!r}.')
    stacked = native['stackable'] == 1
    allowed_stats = {'70:0'} if stacked else set()
    if facts.runeword or facts.properties or facts.socket_items or facts.stats.keys() - allowed_stats:
        gaps.append('Ordinary supply has unexpected modifiers, runeword or socket contents.')
    quantity = None
    if stacked:
        stat = facts.stats.get('70:0', {})
        value = stat.get('value')
        minimum = 0 if native['type'] == 'book' else 1
        if stat.get('status') != 'decoded' or type(value) is not int or not minimum <= value <= native['maxstack']:
            gaps.append(f'Stack quantity must be captured within {minimum}-{native["maxstack"]}.')
        else:
            quantity = value
    effect, use = USES[facts.base_code]
    effects = [effect]
    if stacked:
        effects.append(f'Contents: {quantity if quantity is not None else "unknown"}/{native["maxstack"]}.')
    return {
        'status': 'review' if gaps else 'usable',
        'kind': 'supply',
        'effects': effects,
        'uses': [use],
        'improvements': ['Refill this empty tome before using it.'] if quantity == 0 else [],
        'quantity': quantity,
        'variable_rolls': False,
        'gaps': list(dict.fromkeys(gaps)),
        'sources': [
            {
                'path': str(SOURCE.relative_to(SOURCE.parents[3])),
                'sha256': SOURCE_SHA256,
                'locator': '/' + facts.base_code,
            }
        ],
    }
