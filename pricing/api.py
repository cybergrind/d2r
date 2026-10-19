"""What `inventory_tracking` uses of pricing: the one place the host imports pricing from.

Each name is resolved from its home module on first use (`__getattr__`), so importing this module
loads nothing else: a host module pays only for the pricing code it actually names, as it did with
the deep import, and no import cycle with the game-data tables pricing reads from the host forms.
The `TYPE_CHECKING` block gives the type checker the same names. `tests/pricing/test_api.py` keeps
the two in step and pins the boundary.
"""

from importlib import import_module
from typing import TYPE_CHECKING


# name here -> (home module, name there), grouped by what the host does with it
_EXPORTS = {
    # Triage: the fast verdict for a drop, a shop item or an identify scan
    'triage': ('pricing.triage.runtime', 'retrieve'),
    'fast_triage': ('pricing.triage.runtime', 'fast_retrieve'),
    'shop_triage': ('pricing.triage.runtime', 'shop_retrieve'),
    'warm_triage': ('pricing.triage.runtime', 'warm'),
    'triage_enabled': ('pricing.triage.runtime', 'enabled'),
    'triage_revision': ('pricing.triage.engine', 'revision'),
    # Detail engine over one published (or in-memory) KB generation
    'retrieve_draft': ('pricing.knowledge.pipeline', 'retrieve_draft'),
    'DEFAULT_STORE': ('pricing.knowledge.publication', 'DEFAULT_STORE'),
    'pointer_generation': ('pricing.knowledge.publication', 'pointer_generation'),
    'published_generation': ('pricing.knowledge.publication', 'published_generation'),
    'LoadedRuntime': ('pricing.knowledge.published_runtime', 'LoadedRuntime'),
    'load_runtime': ('pricing.knowledge.published_runtime', 'load_runtime'),
    'published_snapshot': ('pricing.knowledge.published_runtime', 'published_snapshot'),
    'definitions_fingerprint': ('pricing.knowledge.definition_store', 'fingerprint'),
    # Item definitions and capture facts the Alt+D card shows
    'catalog': ('pricing.knowledge.definition_store', 'catalog'),
    'normalize': ('pricing.knowledge.assessment.adapters.capture', 'normalize'),
    'classify': ('pricing.knowledge.assessment.registry', 'classify'),
    'resolve_named_definition': ('pricing.knowledge.assessment.handlers.definitions', 'resolve_named_definition'),
    'equipment_base': ('pricing.knowledge.market_base_catalog', 'equipment_base'),
    'FactStatus': ('pricing.knowledge.assessment.domain.facts', 'FactStatus'),
    'freeze': ('pricing.knowledge.assessment.domain.facts', 'freeze'),
    'socket_state': ('pricing.knowledge.assessment.domain.sockets', 'socket_state'),
    # Roll, socket and defense mechanics behind the card's range lines
    'BASE_DEFENSE_IDENTITY': ('pricing.knowledge.assessment.policies.trade_base_defense', 'IDENTITY'),
    'capture_bounds': ('pricing.knowledge.assessment.policies.trade_base_defense', 'capture_bounds'),
    'girth_bounds': ('pricing.knowledge.assessment.policies.trade_defense', 'girth_bounds'),
    'compare_named_sockets': ('pricing.knowledge.assessment.handlers.socket_fillers', 'compare_named_sockets'),
    'native_socket_roll': ('pricing.knowledge.assessment.mechanics.named_sockets', 'native_socket_roll'),
    'socket_gaps': ('pricing.knowledge.assessment.mechanics.named_sockets', 'socket_gaps'),
    'socket_outcomes': ('pricing.knowledge.assessment.mechanics.named_sockets', 'socket_outcomes'),
    'BOUNDED_STATS': ('pricing.knowledge.assessment.mechanics.runeword_rolls', 'BOUNDED_STATS'),
    'enhancement_gaps': ('pricing.knowledge.assessment.mechanics.runeword_rolls', 'enhancement_gaps'),
    'base_tier': ('pricing.knowledge.assessment.mechanics.base_tiers', 'base_tier'),
    'relevant_set': ('pricing.knowledge.assessment.commodity_sets', 'relevant_set'),
    'softcore_watches': ('pricing.knowledge.assessment.policies.value_watch', 'softcore_watches'),
    # Role predicates the shop catalog evaluates
    'Truth': ('pricing.knowledge.assessment.roles.predicates', 'Truth'),
    'evaluate_predicate': ('pricing.knowledge.assessment.roles.predicates', 'evaluate'),
    'validate_predicate': ('pricing.knowledge.assessment.roles.predicates', 'validate'),
    # Item metadata build (`inventory_tracking.items.build_metadata`) and the range tables
    'build_definitions': ('pricing.knowledge.definitions', 'build_definitions'),
    'compile_fillers': ('pricing.knowledge.assessment.compile.comparison_fillers', 'compile_fillers'),
    'compile_scalars': ('pricing.knowledge.assessment.compile.socket_scalars', 'compile_scalars'),
    'merge_game_strings': ('pricing.knowledge.localization', 'merge_game_strings'),
    'named_upgrade_variants': ('pricing.knowledge.named_upgrades', 'named_upgrade_variants'),
    'selected_ranges': ('pricing.knowledge.property_groups', 'selected_ranges'),
    'select_scalar_candidates': ('pricing.knowledge.seasonal_variants', 'select_scalar_candidates'),
    # Triage score reports over the host's corpus (`inventory_tracking.corpus.replay`)
    'triage_report': ('pricing.triage.replay', 'report'),
    'guide_report': ('pricing.triage.guide_cases', 'report'),
    # Files
    'atomic_json': ('pricing.knowledge.refresh', 'atomic_json'),
}

if TYPE_CHECKING:
    from pricing.knowledge.assessment.adapters.capture import normalize
    from pricing.knowledge.assessment.commodity_sets import relevant_set
    from pricing.knowledge.assessment.compile.comparison_fillers import compile_fillers
    from pricing.knowledge.assessment.compile.socket_scalars import compile_scalars
    from pricing.knowledge.assessment.domain.facts import FactStatus, freeze
    from pricing.knowledge.assessment.domain.sockets import socket_state
    from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
    from pricing.knowledge.assessment.handlers.socket_fillers import compare_named_sockets
    from pricing.knowledge.assessment.mechanics.base_tiers import base_tier
    from pricing.knowledge.assessment.mechanics.named_sockets import native_socket_roll, socket_gaps, socket_outcomes
    from pricing.knowledge.assessment.mechanics.runeword_rolls import BOUNDED_STATS, enhancement_gaps
    from pricing.knowledge.assessment.policies.trade_base_defense import (
        IDENTITY as BASE_DEFENSE_IDENTITY,
        capture_bounds,
    )
    from pricing.knowledge.assessment.policies.trade_defense import girth_bounds
    from pricing.knowledge.assessment.policies.value_watch import softcore_watches
    from pricing.knowledge.assessment.registry import classify
    from pricing.knowledge.assessment.roles.predicates import (
        Truth,
        evaluate as evaluate_predicate,
        validate as validate_predicate,
    )
    from pricing.knowledge.definition_store import catalog, fingerprint as definitions_fingerprint
    from pricing.knowledge.definitions import build_definitions
    from pricing.knowledge.localization import merge_game_strings
    from pricing.knowledge.market_base_catalog import equipment_base
    from pricing.knowledge.named_upgrades import named_upgrade_variants
    from pricing.knowledge.pipeline import retrieve_draft
    from pricing.knowledge.property_groups import selected_ranges
    from pricing.knowledge.publication import DEFAULT_STORE, pointer_generation, published_generation
    from pricing.knowledge.published_runtime import LoadedRuntime, load_runtime, published_snapshot
    from pricing.knowledge.refresh import atomic_json
    from pricing.knowledge.seasonal_variants import select_scalar_candidates
    from pricing.triage.engine import revision as triage_revision
    from pricing.triage.guide_cases import report as guide_report
    from pricing.triage.replay import report as triage_report
    from pricing.triage.runtime import (
        enabled as triage_enabled,
        fast_retrieve as fast_triage,
        retrieve as triage,
        shop_retrieve as shop_triage,
        warm as warm_triage,
    )

__all__ = [
    'BASE_DEFENSE_IDENTITY',
    'BOUNDED_STATS',
    'DEFAULT_STORE',
    'FactStatus',
    'LoadedRuntime',
    'Truth',
    'atomic_json',
    'base_tier',
    'build_definitions',
    'capture_bounds',
    'catalog',
    'classify',
    'compare_named_sockets',
    'compile_fillers',
    'compile_scalars',
    'definitions_fingerprint',
    'enhancement_gaps',
    'equipment_base',
    'evaluate_predicate',
    'fast_triage',
    'freeze',
    'girth_bounds',
    'guide_report',
    'load_runtime',
    'merge_game_strings',
    'named_upgrade_variants',
    'native_socket_roll',
    'normalize',
    'pointer_generation',
    'published_generation',
    'published_snapshot',
    'relevant_set',
    'resolve_named_definition',
    'retrieve_draft',
    'select_scalar_candidates',
    'selected_ranges',
    'shop_triage',
    'socket_gaps',
    'socket_outcomes',
    'socket_state',
    'softcore_watches',
    'triage',
    'triage_enabled',
    'triage_report',
    'triage_revision',
    'validate_predicate',
    'warm_triage',
]


def __getattr__(name):
    """Look the name up in its home module every time, so a patch there is seen here too."""
    try:
        module, attribute = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}') from None
    return getattr(import_module(module), attribute)


def __dir__():
    return sorted([*globals(), *_EXPORTS])
