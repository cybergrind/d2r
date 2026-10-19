"""Generate lootfilter/warlock_lean_v2.json: the Warlock Lean profile with its "SHOW Unique Set" rule
narrowed to the bases whose unique or set item is worth picking up (user, 2026-10-09).

Show beats Hide and a rule matches rarity AND (category OR item code), so four Show rules (unique and set, each
split into armor and weapons, item codes only) list the bases worth showing; accessories stay shown by their rule.

A named item is shown when any holds (a base shared with a shown item stays shown):
- it trades (pricing/data/named-trades.json): TRADES_PER_MONTH sales in 30 days at a median of ASK_MINIMUM
  Ist or more, or any sale in 90 days at SLOW_MINIMUM;
- a maxroll planner loadout equips it (wp-a-variants/index.json);
- the KB recommends it for leveling (appraisal-recommendations.json) and the player owns no copy yet;
- the Chronicle lacks it (user, 2026-10-11; inventory_tracking.probes.chronicle; rerun both as it fills).
Items the trades file does not cover use the ask-based reasons: a good-roll ask of ASK_MINIMUM Ist
(loot/data/uniques.json), a maxroll guide mention (appraisal-demand.json), or an elite base.

Run: uv run --offline python -m inventory_tracking.loot.build_filter
The profile is also put on the clipboard (wl-copy), ready for the game's import.
"""

import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

from inventory_tracking.items.metadata import metadata
from inventory_tracking.reports import publish
from pricing.api import base_tier


TEMPLATE = Path('lootfilter/warlock_lean.json')
OUTPUT = Path('lootfilter/warlock_lean_v2.json')
NAMES = Path('lootfilter/warlock_lean_v2.names.json')
PROFILE_NAME = 'Warlock Lean2'  # the game accepts at most 13 characters
REPLACED_RULE = 'SHOW Unique Set'
ASKS = Path('inventory_tracking/loot/data/uniques.json')
DEMAND = Path('pricing/data/appraisal-demand.json')
BUILDS = Path('pricing/data/wp-a-variants/index.json')
RECOMMENDATIONS = Path('pricing/data/appraisal-recommendations.json')
TRADES = Path('pricing/data/named-trades.json')
COLLECTION = Path('inventory_tracking/runs/collection/collection.sqlite')
CHRONICLE = Path('inventory_tracking/runs/chronicle/chronicle.json')
ASK_MINIMUM = 0.25
TRADES_PER_MONTH = 3
SLOW_MINIMUM = 1.0  # Ist: a dear item that sells only now and then is still worth the pickup
TABLES = {'unique': 'uniques', 'set': 'sets'}  # decoder identity table -> ask table kind
CATEGORIES = {'armor': 'ARMOR', 'weapons': 'WEAPONS'}  # the decoder's base categories


def named_items(table: str) -> dict[str, list[str]]:
    """Name -> base codes of every spawnable item of one identity table."""
    return {
        row['name']: row['base_codes']
        for row in metadata()['identities'][table].values()
        if row['game_definition'].get('spawnable') != 0 and row['base_codes']
    }


def chronicled(table: str) -> set[str]:
    """Names the Chronicle can hold and a monster can drop: not switched off there, not a quest item (level 0)."""
    return {
        row['name']
        for row in metadata()['identities'][table].values()
        if not row['game_definition'].get('disableChronicle') and row['game_definition'].get('lvl')
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


def trade_reason(row: dict) -> str | None:
    """Why a traded item is worth showing, or None when the market does not take it."""
    median = row['median_ist']
    source = f'(Traderie Recent Trades {row.get("date", "")})'
    if row['last_30d'] >= TRADES_PER_MONTH and (median is None or median >= ASK_MINIMUM):
        paid = f', median {median:.2f} Ist' if median is not None else ''
        return f'{row["last_30d"]} trades in 30 days{paid} {source}'
    if median is not None and median >= SLOW_MINIMUM and row.get('last_90d', 0) >= 1:
        return f'slow but dear: {row["last_90d"]} trades in 90 days, median {median:.2f} Ist {source}'
    return None


def evidence(table: str, sources: dict) -> dict[str, list[str]]:
    """Name -> why the item is worth showing (empty: nothing in the knowledge base says so)."""
    highs = asks(sources['asks'], TABLES[table])
    traded = sources.get('trades', {})
    found = sources.get('chronicle')
    missing = set() if found is None else chronicled(table) - found
    reasons = {}
    for name, codes in named_items(table).items():
        why = []
        if name in traded:
            if reason := trade_reason(traded[name]):
                why.append(reason)
        else:
            if highs.get(name, 0.0) >= ASK_MINIMUM:
                why.append(f'asks {highs[name]:.2f} Ist ({sources["asks"]["date"]})')
            if builds := sources['demand'].get(name):
                why.append(f'named by {len(builds)} maxroll build guide(s)')
            if base_tier(codes[0]) == 'Elite':
                why.append('elite base')
        if name in sources['builds']:
            why.append('in a maxroll planner loadout')
        if name in sources['recommended'] and name not in sources.get('owned', ()):
            why.append('leveling recommendation, not owned yet')
        if name in missing:
            why.append('not in the Chronicle yet')
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


def visibility(table: str, reasons: dict[str, list[str]], codes: dict[str, set[str]], sources: dict) -> dict[str, dict]:
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
        elif name in sources.get('trades', {}):
            row = sources['trades'][name]
            paid = f', median {row["median_ist"]:.2f} Ist' if row['median_ist'] is not None else ''
            owned = ' (owned)' if name in sources.get('owned', ()) else ''
            hidden[name] = f'{row["last_30d"]} trades in 30 days{paid}; no loadout or unowned leveling use{owned}'
        else:
            hidden[name] = f'{base_tier(bases[0]) or "unknown"} base, no ask, demand or leveling evidence'
    return {'shown': dict(sorted(shown.items())), 'hidden': dict(sorted(hidden.items()))}


def load_owned(path: Path = COLLECTION) -> set[str]:
    """Unique and set names the player already holds, from the collection database; empty without one."""
    if not path.exists():
        return set()
    with sqlite3.connect(path) as db:
        return {row[0] for row in db.execute("select distinct name from items where rarity in ('unique', 'set')")}


def load_chronicle(path: Path = CHRONICLE) -> set[str] | None:
    """Unique and set names in the character's Chronicle (probes/chronicle.py); None without a dump."""
    if not path.exists():
        return None
    entries = json.loads(path.read_text())['entries']
    return {row['name'] for table in TABLES for row in entries[table]}


def load_trades(path: Path = TRADES) -> dict[str, dict]:
    """Name -> trade summary row, with the pull date on each row; empty when no trades file exists yet."""
    if not path.exists():
        return {}
    document = json.loads(path.read_text())
    return {row['name']: {**row, 'date': document.get('date', '')} for row in document['items']}


def load_sources() -> dict:
    demand = json.loads(DEMAND.read_text())
    recommended = json.loads(RECOMMENDATIONS.read_text())
    return {
        'asks': json.loads(ASKS.read_text()),
        'demand': demand_builds(demand['rows'] if isinstance(demand, dict) else demand),
        'builds': set(json.loads(BUILDS.read_text())),
        'recommended': {row['name'] for row in (recommended['rows'] if isinstance(recommended, dict) else recommended)},
        'trades': load_trades(),
        'owned': load_owned(),
        'chronicle': load_chronicle(),
    }


def build(template: dict, sources: dict) -> tuple[dict, dict]:
    """The new profile and its names sidecar."""
    replacement, names = [], {}
    for table in TABLES:
        reasons = evidence(table, sources)
        codes = shown_codes(table, reasons)
        replacement.extend(rules(table, codes))
        names[table] = visibility(table, reasons, codes, sources)
    position = next(i for i, rule in enumerate(template['rules']) if rule['name'] == REPLACED_RULE)
    profile = {
        **template,
        'name': PROFILE_NAME,
        'rules': template['rules'][:position] + replacement + template['rules'][position + 1 :],
    }
    trade_rows = sources.get('trades', {})
    sidecar = {
        'source': f'{TEMPLATE} with {REPLACED_RULE} narrowed by inventory_tracking.loot.build_filter',
        'asks_date': sources['asks']['date'],
        'ask_minimum_ist': ASK_MINIMUM,
        'trades': {
            'items_covered': len(trade_rows),
            'date': next(iter(trade_rows.values()))['date'] if trade_rows else None,
            'rule': f'at least {TRADES_PER_MONTH} trades in 30 days at a median of {ASK_MINIMUM} Ist or more, '
            f'or any trade in 90 days at a median of {SLOW_MINIMUM} Ist or more',
        },
        **names,
    }
    return profile, sidecar


def copy(text: str) -> bool:
    """Put the profile on the Wayland clipboard; False without wl-copy or a display to copy to."""
    if shutil.which('wl-copy') is None:
        return False
    try:
        # wl-copy stays behind to serve the clipboard: it must not inherit a pipe someone waits on
        done = subprocess.run(
            ['wl-copy'],
            input=text.encode(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
        return done.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def main() -> int:
    profile, sidecar = build(json.loads(TEMPLATE.read_text()), load_sources())
    publish(OUTPUT, profile)
    publish(NAMES, sidecar)
    for table in TABLES:
        print(f'{table}: {len(sidecar[table]["shown"])} shown, {len(sidecar[table]["hidden"])} hidden')
    copied = copy(OUTPUT.read_text())
    print(f'{OUTPUT}: {"copied to the clipboard" if copied else "not copied (no wl-copy or no display)"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
