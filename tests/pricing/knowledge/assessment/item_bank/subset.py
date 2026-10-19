"""The default item-bank run is a deterministic, stratified subset; `D2R_ITEM_BANK=full` runs every case.

The full bank (31.7k cases, ≈ 2.1 h serially) stays required before a generation is published. A default run
keeps, per stratum, the case with the lowest sha256 of its id, for three kinds of strata: case module and
scenario, case module and rarity, rarity and scenario. Every case module, rarity and scenario is in it
(cleanup phase 2, 2026-10-19).
"""

import hashlib
import importlib
import os
import pkgutil
from functools import cache

import tests.pricing.knowledge.assessment.item_bank.cases as package


def full_bank():
    return os.environ.get('D2R_ITEM_BANK') == 'full'


def owners():
    """Case id → the case module that defines it."""
    result = {}
    for module in pkgutil.iter_modules(package.__path__):
        for case in getattr(importlib.import_module(f'{package.__name__}.{module.name}'), 'CASES', ()):
            result.setdefault(case.id, module.name)
    return result


def rank(case):
    return hashlib.sha256(case.id.encode()).hexdigest()


@cache
def default_ids():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    module = owners()
    chosen = {}
    for case in CASES:
        owner = module.get(case.id, case.id.rsplit('/', 1)[0])
        for stratum in (
            ('module-scenario', owner, case.scenario),
            ('module-rarity', owner, case.item.rarity),
            ('rarity-scenario', case.item.rarity, case.scenario),
        ):
            if stratum not in chosen or rank(case) < rank(chosen[stratum]):
                chosen[stratum] = case
    return frozenset(case.id for case in chosen.values())
