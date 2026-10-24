"""Item judgements have one entry point (inventory_tracking/loot/assess.py; loot/design.md §10). The player,
2026-10-23: "we need to have one dedicated place where all assessments are happening - reuse it everywhere - single
entry point - easy to test"; "ok, let's unify everything into a single way to do assessments".

- Only the price sources reach the per-item pricing engines (pricing.api's triage and detail names, appraisal/
  retrieval.py, the engines' modules).
- Only the loot layers call the keep, ground and town decisions (keep.py `decide`, ground_judge.py `judge`, api.py
  `town_verdicts`...).
- The verdict rules outside the loot layers are the listed ones, called only where listed; no new one appears.

Today's violators are listed, each with the step of phase 2 that moves it ("phase 2: migrate"): the lists may only
shrink. A listed entry that no longer holds fails too, so the list is trimmed when a caller moves.
"""

import ast
import functools
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCANNED = (ROOT / 'inventory_tracking', ROOT / '.agents' / 'skills')
SKIPPED = frozenset(('runs', '__pycache__', 'data'))

# -- the per-item engines --------------------------------------------------------------------------------------

# pricing/api.py's engine names
ENGINE_NAMES = frozenset(('triage', 'fast_triage', 'shop_triage', 'retrieve_draft', 'triage_assess', 'triage_tables'))
ENGINE_MODULES = (
    'pricing.triage.engine',
    'pricing.triage.runtime',
    'pricing.knowledge.pipeline',
    'pricing.knowledge.assessment.engine',
    'inventory_tracking.appraisal.retrieval',
)
# The price sources: the engines' glue, the one place the live price source is built, the offline table builders
PRICE_SOURCES = {
    'inventory_tracking/appraisal/retrieval.py': 'the KB detail and triage of one read (the retrieval process)',
    'inventory_tracking/appraisal/memory_backend.py': 'the in-memory KB lookup',
    'inventory_tracking/appraisal/published_backend.py': 'the published KB lookup',
    'inventory_tracking/appraisal/service.py': "the composition root: the identify worker's retrieval (BOOK's source)",
    'inventory_tracking/loot/build_base_floor.py': 'offline builder of loot/data/base-floor.json',
    # Phase 2B (2026-10-23): each wires its engine into the entry point's price source and judges through it
    'inventory_tracking/shop/service.py': "SHOP's price source: shop_triage into a ResultAppraiser (`triage_stock`)",
    'inventory_tracking/corpus/score.py': "CORPUS's price source: the published KB's detail engine (`_assess`)",
    '.agents/skills/mules/snapshot.py': "CARD's price source for the stash: the triage per item (`loop_card`)",
}
ENGINE_CALLERS: dict[str, str] = {}  # the violators: none since phase 2B (2026-10-23)

# -- the decisions ---------------------------------------------------------------------------------------------

DECISIONS = {
    'inventory_tracking.loot.keep': frozenset(('decide', 'decide_all')),
    'inventory_tracking.loot.ground_judge': frozenset(('judge', 'base_verdict')),
    'inventory_tracking.loot.api': frozenset(
        ('town_verdicts', 'town_sold', 'town_kept', 'sold_copies', 'droppable', 'surplus', 'surplus_copy')
    ),
    'inventory_tracking.loot.value': frozenset(('appraise_result', 'assess')),
}
LOOT_LAYERS = frozenset((
    'inventory_tracking/loot/assess.py',  # the entry point
    'inventory_tracking/loot/keep.py',
    'inventory_tracking/loot/ground_judge.py',
    'inventory_tracking/loot/api.py',  # the field routine and the town's guards it composes
    'inventory_tracking/loot/value.py',
))  # fmt: skip
DECISION_CALLERS = {
    'inventory_tracking/loot/shadow.py': 'phase 2: retire (the M1 shadow, migration scaffolding)',
    # GROUND moved (ASSESS_GROUND, 2026-10-23): `ground_base` is the switch-off path's, legacy until it is proven
    'inventory_tracking/macros/pickmode.py': 'legacy until ASSESS_GROUND is proven (`ground_base` in `_taken`)',
    # TOWN moved (visit.py ASSESS_TOWN, 2026-10-23): the switch-off path and its shadow, legacy until it is proven
    'inventory_tracking/macros/visit.py': 'legacy until ASSESS_TOWN is proven (api.town_sold, api.sold_copies)',
    # GAMBLE moved (gamble.py ASSESSED, 2026-10-23): `_town_judged` is the switch-off path's and the shadow's
    'inventory_tracking/macros/gamble.py': 'legacy until gamble.ASSESSED is proven (`_town_judged`: town_verdicts)',
}

# -- the verdict rules outside the loot layers -----------------------------------------------------------------

LEGACY = {
    # the price source's own step (D4: loot/assess.py `identify_verdict`); the card shows CARD (2026-10-23)
    'inventory_tracking.identify.service': frozenset(
        ('verdict_for', 'assessed_verdict', 'owned_verdict', 'trade_reason')
    ),
    # SHOP moved (shop/service.py ASSESSED, 2026-10-23): legacy until it is proven (the switch-off path, the shadow)
    'inventory_tracking.shop.service': frozenset(('priced',)),
    # the switch-off path of GROUND (pickmode.py ASSESS_GROUND, 2026-10-23): legacy until it is proven
    'inventory_tracking.macros.pickmode': frozenset((
        'kept', 'sure', 'judged_base', 'ground_base', 'candidate', 'is_candidate', 'void_base', 'shield_base',
        'identified_for', 'sellable', 'junk_base', 'plain_base',
    )),
    'inventory_tracking.macros.keepers': frozenset(('amulet_keeper',)),
    'inventory_tracking.macros.junk': frozenset(('junk', 'junk_of')),
    'inventory_tracking.macros.copies': frozenset(('keep_copy', 'sold')),
    'inventory_tracking.macros.cube': frozenset(('droppable',)),
    'inventory_tracking.macros.charms': frozenset(('low_rolls',)),
}  # fmt: skip
# Where a legacy verdict is called outside its own module (phase 2: migrate, each)
LEGACY_CALLS = {
    # the identify verdict BOOK holds, its leveling override (D4): moves into the loot layers in phase 2
    ('inventory_tracking/loot/assess.py', 'verdict_for'): 'ResultAppraiser: the identify verdict',
    ('inventory_tracking/loot/today.py', 'keep_copy'): "retire: today's chain for the acceptance table",
    ('inventory_tracking/loot/today.py', 'amulet_keeper'): "retire: today's chain for the acceptance table",
    ('inventory_tracking/loot/today.py', 'sellable'): "retire: today's chain for the acceptance table",
    ('inventory_tracking/loot/today.py', 'sure'): "retire: today's chain for the acceptance table",
    ('inventory_tracking/macros/junk.py', 'sellable'): 'retire with junk_of (dead while TOWN_DECIDES)',
    ('inventory_tracking/macros/running/execution.py', 'amulet_keeper'): 'stays: engine.protected (D3)',
    ('inventory_tracking/macros/running/legs.py', 'junk_of'): 'retire (dead while TOWN_DECIDES)',
    ('inventory_tracking/macros/visit.py', 'sold'): 'retire with copies.py (dead while TOWN_DECIDES)',
}
# A new item verdict outside the loot layers would be named so; the names that match and are not one, each said why
VERDICT_NAME = re.compile(r'verdict|keeper|junk|sellable|droppable|keep_copy|surplus|worth_ist')
NOT_VERDICTS = {
    ('inventory_tracking/macros/lootpolicy.py', 'verdict'): 'site behaviour: take now / hold / trip (design.md §1.2)',
    ('inventory_tracking/identify/service.py', 'verdict_order'): "the card's sort of the verdicts made",
    ('inventory_tracking/identify/service.py', 'verdicts_now'): 'a copy of the verdicts made',
    ('inventory_tracking/macros/pickmode.py', '_left_junk'): "a leave's log line",
    ('inventory_tracking/macros/visit.py', '_keepers'): 'a log line',
    ('inventory_tracking/macros/safety.py', 'keeper'): 'combat safety: the hostile whose kill ends the harm',
}
NO_VERDICT_TREES = ('inventory_tracking/loot/', 'inventory_tracking/combat/', 'inventory_tracking/builds/')


@functools.cache
def trees() -> dict[str, ast.Module]:
    found = {}
    for root in SCANNED:
        for folder, folders, files in os.walk(root):
            folders[:] = [name for name in folders if name not in SKIPPED]
            for name in files:
                if name.endswith('.py'):
                    path = Path(folder) / name
                    found[path.relative_to(ROOT).as_posix()] = ast.parse(path.read_text(encoding='utf-8'))
    return found


def module_of(path: str) -> str:
    return path.removesuffix('.py').replace('/', '.')


def references(tree: ast.Module, wanted: dict[str, frozenset[str]]) -> set[tuple[str, str]]:
    """(module, name) of `wanted`'s functions the module names: imported by name, or as an attribute of the module
    imported (`from inventory_tracking.loot import keep`; `import ... as`)."""
    aliases: dict[str, str] = {}
    named: dict[str, tuple[str, str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for alias in node.names:
                if f'{node.module}.{alias.name}' in wanted:
                    aliases[alias.asname or alias.name] = f'{node.module}.{alias.name}'
                if alias.name in wanted.get(node.module, ()):
                    named[alias.asname or alias.name] = (node.module, alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in wanted and alias.asname:
                    aliases[alias.asname] = alias.name
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in named:
            found.add(named[node.id])
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in aliases:
            module = aliases[node.value.id]
            if node.attr in wanted[module]:
                found.add((module, node.attr))
    return found


def engine_users() -> set[str]:
    found = set()
    for path, tree in trees().items():
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = {alias.name for alias in node.names}
                full = {f'{node.module}.{name}' for name in names}
                if (node.module == 'pricing.api' and names & ENGINE_NAMES) or any(
                    module == engine or module.startswith(f'{engine}.')
                    for module in (node.module, *full)
                    for engine in ENGINE_MODULES
                ):
                    found.add(path)
            elif isinstance(node, ast.Import):
                if any(a.name == e or a.name.startswith(f'{e}.') for a in node.names for e in ENGINE_MODULES):
                    found.add(path)
    return found


def test_only_the_price_sources_reach_the_pricing_engines():
    assert engine_users() == set(PRICE_SOURCES) | set(ENGINE_CALLERS)


def test_only_the_loot_layers_call_the_decisions():
    callers = {path for path, tree in trees().items() if references(tree, DECISIONS)} - LOOT_LAYERS
    assert callers == set(DECISION_CALLERS)


def test_the_legacy_verdicts_are_where_listed():
    for module, names in LEGACY.items():
        path = module.replace('.', '/') + '.py'
        defined = {node.name for node in trees()[path].body if isinstance(node, ast.FunctionDef)}
        assert names <= defined, f'{path}: gone, trim LEGACY: {sorted(names - defined)}'


def test_the_legacy_verdicts_are_called_only_where_listed():
    found = set()
    for path, tree in trees().items():
        for module, name in references(tree, LEGACY):
            if module != module_of(path):
                found.add((path, name))
    assert found == set(LEGACY_CALLS)


def test_no_new_verdict_outside_the_loot_layers():
    legacy = {(module.replace('.', '/') + '.py', name) for module, names in LEGACY.items() for name in names}
    found = set()
    for path, tree in trees().items():
        if path.startswith(NO_VERDICT_TREES) or not path.startswith('inventory_tracking/'):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and VERDICT_NAME.search(node.name):
                found.add((path, node.name))
    assert found <= legacy | set(NOT_VERDICTS), sorted(found - legacy - set(NOT_VERDICTS))
    assert set(NOT_VERDICTS) <= found  # a stale exemption is trimmed


# The value sites of phase 2B (2026-10-23, the player: "I want to have one place that decides pickups/value"): each
# judges through the entry point (loot/assess.py `Assessor`, `live`, or the card's `card_of` over it) behind its switch
ENTRY_POINT = {'inventory_tracking.loot.assess': frozenset(('Assessor', 'live'))}
ON_THE_ENTRY_POINT = {
    'inventory_tracking/shop/service.py': 'SHOP (ASSESSED)',
    'inventory_tracking/corpus/score.py': 'CORPUS',
    'inventory_tracking/macros/gamble.py': 'GAMBLE (ASSESSED)',
    'inventory_tracking/identify/service.py': 'CARD (CARD_ASSESSED, `card_of`)',
}
CARD_USERS = {'.agents/skills/mules/snapshot.py': 'CARD (the loop_card column)'}


def test_the_value_sites_judge_through_the_entry_point():
    for path in ON_THE_ENTRY_POINT:
        assert references(trees()[path], ENTRY_POINT), f'{path}: no call of the entry point'
    card = {'inventory_tracking.identify.service': frozenset(('card_of',))}
    for path in CARD_USERS:
        assert references(trees()[path], card), f'{path}: no CARD line'
