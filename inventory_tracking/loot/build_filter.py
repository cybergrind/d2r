"""Generate lootfilter/warlock_lean_v2.json: the Warlock Lean profile with its "SHOW Unique Set" rule
narrowed to the bases whose unique or set item is worth picking up (user, 2026-10-09).

The game's filter matches a rule by rarity AND (category OR item code) and Show always beats Hide, so
hiding a unique "by base" means listing the bases worth showing: four Show rules (unique and set, each split
into armor and weapons; item codes only, no category) replace the one rule that showed every gold and green item.
Rings, amulets, jewels and charms stay shown by the accessories rule.

A named item is worth showing when any of these holds; everything else of normal or exceptional base is
hidden, and a base shared with a shown item stays shown:
- its good-roll ask (loot/data/uniques.json, the dated Traderie table) is at least ASK_MINIMUM Ist,
  the pricing primer's 2026-10-04 floor;
- a maxroll build guide names it (pricing/data/appraisal-demand.json, the knowledge index's demand rows,
  or the planner loadouts in wp-a-variants/index.json);
- the knowledge base recommends it for leveling (pricing/data/appraisal-recommendations.json);
- its base is elite: the ask table prices too few elite uniques to call the rest worthless.

Run: uv run --offline python -m inventory_tracking.loot.build_filter
"""

import json
from pathlib import Path

from inventory_tracking.items.metadata import metadata
from inventory_tracking.reports import publish
from pricing.knowledge.assessment.mechanics.base_tiers import base_tier


TEMPLATE = Path('lootfilter/warlock_lean.json')
OUTPUT = Path('lootfilter/warlock_lean_v2.json')
NAMES = Path('lootfilter/warlock_lean_v2.names.json')
PROFILE_NAME = 'Warlock Lean2'  # the game accepts at most 13 characters
REPLACED_RULE = 'SHOW Unique Set'
ASKS = Path('inventory_tracking/loot/data/uniques.json')
DEMAND = Path('pricing/data/appraisal-demand.json')
BUILDS = Path('pricing/data/wp-a-variants/index.json')
RECOMMENDATIONS = Path('pricing/data/appraisal-recommendations.json')
ASK_MINIMUM = 0.25
TABLES = {'unique': 'uniques', 'set': 'sets'}  # decoder identity table -> ask table kind
CATEGORIES = {'armor': 'ARMOR', 'weapons': 'WEAPONS'}  # the decoder's base categories


def named_items(table: str) -> dict[str, list[str]]:
    """Name -> base codes of every spawnable item of one identity table."""
    return {
        row['name']: row['base_codes']
        for row in metadata()['identities'][table].values()
        if row['game_definition'].get('spawnable') != 0 and row['base_codes']
    }


def asks(table: dict, kind: str) -> dict[str, float]:
    """Name -> good-roll ask (the highest per-bucket median), from the loot table of one kind."""
    highs: dict[str, float] = {}
    for base in table['bases'].values():
        for item in base[kind]:
            if item['high'] is not None:
                highs[item['name']] = max(highs.get(item['name'], 0.0), item['high'])
    return highs


def demand_builds(rows) -> dict[str, set[str]]:
    builds: dict[str, set[str]] = {}
    for row in rows:
        if row.get('category') in TABLES:
            builds.setdefault(row['name'], set()).add(row['build'])
    return builds


def evidence(table: str, sources: dict) -> dict[str, list[str]]:
    """Name -> why the item is worth showing (empty: nothing in the knowledge base says so)."""
    highs = asks(sources['asks'], TABLES[table])
    reasons = {}
    for name, codes in named_items(table).items():
        why = []
        if highs.get(name, 0.0) >= ASK_MINIMUM:
            why.append(f'asks {highs[name]:.2f} Ist ({sources["asks"]["date"]})')
        if builds := sources['demand'].get(name):
            why.append(f'named by {len(builds)} maxroll build guide(s)')
        if name in sources['builds']:
            why.append('in a maxroll planner loadout')
        if name in sources['recommended']:
            why.append('leveling recommendation')
        if base_tier(codes[0]) == 'Elite':
            why.append('elite base')
        reasons[name] = why
    return reasons


def shown_codes(table: str, reasons: dict[str, list[str]]) -> dict[str, set[str]]:
    """Equipment category -> the base codes some worthwhile item of this table spawns on."""
    categories = {base['code']: base['category'] for base in metadata()['bases'].values()}
    codes: dict[str, set[str]] = {category: set() for category in CATEGORIES}
    for name, bases in named_items(table).items():
        if reasons[name]:
            for code in bases:
                if categories[code] in codes:
                    codes[categories[code]].add(code)
    return codes


def rules(table: str, codes: dict[str, set[str]]) -> list[dict]:
    return [
        {
            'name': f'SHOW {table.title()} {label}',
            'enabled': True,
            'ruleType': 'show',
            'filterEtherealSocketed': False,
            'equipmentRarity': [table],
            'equipmentQuality': ['normal', 'exceptional', 'elite'],
            'equipmentItemCode': sorted(codes[category]),
        }
        for category, label in CATEGORIES.items()
    ]


def visibility(table: str, reasons: dict[str, list[str]], codes: dict[str, set[str]]) -> dict[str, dict]:
    """Shown and hidden names with the reason, for the guide and "why is X hidden" questions."""
    categories = {base['code']: base['category'] for base in metadata()['bases'].values()}
    shown, hidden = {}, {}
    for name, bases in named_items(table).items():
        if reasons[name]:
            shown[name] = '; '.join(reasons[name])
        elif any(code in codes.get(categories[code], ()) for code in bases):
            shown[name] = 'shares its base with a shown item'
        elif categories[bases[0]] not in codes:
            shown[name] = 'accessory: shown by SHOW Important Mats and Items'
        else:
            hidden[name] = f'{base_tier(bases[0]) or "unknown"} base, no ask, demand or leveling evidence'
    return {'shown': dict(sorted(shown.items())), 'hidden': dict(sorted(hidden.items()))}


def load_sources() -> dict:
    demand = json.loads(DEMAND.read_text())
    recommended = json.loads(RECOMMENDATIONS.read_text())
    return {
        'asks': json.loads(ASKS.read_text()),
        'demand': demand_builds(demand['rows'] if isinstance(demand, dict) else demand),
        'builds': set(json.loads(BUILDS.read_text())),
        'recommended': {row['name'] for row in (recommended['rows'] if isinstance(recommended, dict) else recommended)},
    }


def build(template: dict, sources: dict) -> tuple[dict, dict]:
    """The new profile and its names sidecar."""
    replacement, names = [], {}
    for table in TABLES:
        reasons = evidence(table, sources)
        codes = shown_codes(table, reasons)
        replacement.extend(rules(table, codes))
        names[table] = visibility(table, reasons, codes)
    position = next(i for i, rule in enumerate(template['rules']) if rule['name'] == REPLACED_RULE)
    profile = {
        **template,
        'name': PROFILE_NAME,
        'rules': template['rules'][:position] + replacement + template['rules'][position + 1 :],
    }
    sidecar = {
        'source': f'{TEMPLATE} with {REPLACED_RULE} narrowed by inventory_tracking.loot.build_filter',
        'asks_date': sources['asks']['date'],
        'ask_minimum_ist': ASK_MINIMUM,
        **names,
    }
    return profile, sidecar


def main() -> int:
    profile, sidecar = build(json.loads(TEMPLATE.read_text()), load_sources())
    publish(OUTPUT, profile)
    publish(NAMES, sidecar)
    for table in TABLES:
        print(f'{table}: {len(sidecar[table]["shown"])} shown, {len(sidecar[table]["hidden"])} hidden')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
