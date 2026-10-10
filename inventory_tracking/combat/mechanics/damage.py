"""The damage model's numbers (data/damage.json): points per blade contact by monster type, the
companions' rates, Health Link, Hex Purge, Death Mark and the mana. The simulator (sim/engine.py) and
the policy (policy.py) read them through these lookups; each is dated and sourced in the data file."""

import json
from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Any


DAMAGE = Path(__file__).parent.parent / 'data' / 'damage.json'
DEFILER = 744  # the companion whose Health Link links the monsters


@cache
def damage_data() -> dict[str, Any]:
    return json.loads(DAMAGE.read_text())


def damage_table() -> Callable[[int], float]:
    data = damage_data()
    per = {int(txt): float(points) for txt, points in data['points_per_contact'].items()}
    default = float(data['default'])
    return lambda txt: per.get(txt, default)


def link_table() -> tuple[float, int, float]:
    """(aura range, links, share of damage dealt again to each other linked monster)."""
    data = damage_data().get('health_link')
    return (float(data['range']), int(data['links']), float(data['share'])) if data else (0.0, 0, 0.0)


def mark_table() -> tuple[float, int]:
    """(share of extra damage a marked monster takes, frames the mark lasts)."""
    data = damage_data().get('death_mark')
    return (float(data['more_damage']), int(data['frames'])) if data else (0.0, 0)


def explosion_table() -> tuple[float, float]:
    """(radius, points) of Hex Purge's explosion when a hexed monster dies."""
    data = damage_data().get('hex_purge')
    return (float(data['radius']), float(data['points'])) if data else (0.0, 0.0)


def companion_table() -> dict[int, tuple[float, float]]:
    """Companion txt id -> (reach in units, points per frame on the nearest hostile within it)."""
    return {
        int(txt): (float(c['reach']), float(c['points_per_frame']))
        for txt, c in damage_data().get('companions', {}).items()
    }


def mana_table() -> tuple[float, float, float]:
    """(pool, regeneration per frame, cost per cast) of the mana model; zeros turn it off."""
    data = damage_data().get('mana')
    if not data or not data.get('limits', True):
        return (0.0, 0.0, 0.0)  # the recorded mana never limited casting (data file, 2026-10-10)
    pool = float(data['pool'])
    return (pool, pool / (float(data['regen_seconds']) * 25.0), float(data['cost']))


def mana_numbers() -> tuple[float, float, float]:
    """(pool, regeneration per frame, cost) as the data file has them, whether or not the pool limits."""
    data = damage_data()['mana']
    pool = float(data['pool'])
    return (pool, pool / (float(data['regen_seconds']) * 25.0), float(data['cost']))


def fit_takes() -> frozenset[str]:
    """The takes the numbers were fitted on; every other take is held out (the gate's scoreboard)."""
    return frozenset(damage_data().get('fit_takes', ()))
