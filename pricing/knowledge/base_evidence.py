"""The price evidence of plain white and grey bases, per facet: what the allowlist builder
(inventory_tracking/loot/build_base_pickups.py) and any base reader decide a base's worth from.

One file, pricing/data/base-evidence.json, built by `uv run --offline python -m pricing.tools.build_base_evidence`
from the git-ignored Traderie pulls under pricing/raw/traderie (read only at build time) and the offline KB:
- `facets`: a facet is a base set x quality grade x ethereal flag x sockets (x all-res band or staff-mod condition).
  Each carries its own fills (Recent Trades: accepted and completed offers), asks (sell listings, one vote per seller)
  and bids (buy listings, one vote per distinct buyer), never pooled with another facet's (the player, 2026-10-23:
  "Sales-backed now"; eth 4os Archon asks said 9.3 Ist, sales 2.6).
- `kb`: the KB's asks band (pricing/triage on the KB's Traderie asks) for each plain key it prices exactly
  (code/quality/eth/sockets/ED grade, as loot/base_floor.py `key`).
- `wpb`: pricing/data/wp-b-prices.json's plain buckets per key, split by 15 ED.

Pure but for the file's one read; the host reaches it through pricing/api.py (`base_evidence`, `plain_base_item`).
"""

import json
from collections.abc import Mapping
from functools import cache
from pathlib import Path
from typing import Any


__all__ = ['ED_PROPERTY', 'EVIDENCE_FILE', 'base_evidence', 'key', 'plain_item']

EVIDENCE_FILE = Path(__file__).parents[1] / 'data' / 'base-evidence.json'
ED_PROPERTY = {'weapons': '510', 'armor': '425'}  # Traderie's enhanced damage / defense (pricing/triage/adapters.py)


@cache
def base_evidence() -> Mapping[str, Any]:
    """The built evidence (`facets`, `kb`, `wpb` and their sources). Raises when the file is missing: only offline
    builders read it, and a builder must not run on no evidence."""
    return json.loads(EVIDENCE_FILE.read_text())


def key(code: str, rarity: str, *, ethereal: bool, sockets: int, perfect: bool) -> str:
    """A plain key: 'fla/superior/noneth/0os/ordinary' (the same text as loot/base_floor.py `key`)."""
    return f'{code}/{rarity}/{"eth" if ethereal else "noneth"}/{sockets}os/{"perfect" if perfect else "ordinary"}'


def plain_item(base: Mapping[str, Any], rarity: str, ethereal: bool, sockets: int, ed: int) -> dict[str, Any]:
    """The triage's item for a clean, empty base of these facts (pricing/triage/adapters.py `from_drop`'s shape)."""
    from pricing.triage.adapters import base_facets

    properties = {ED_PROPERTY[base['category']]: ed} if rarity == 'superior' and ed else {}
    return {
        'category': 'base',
        'name': base['name'],
        'family': base['type'],
        'properties': properties,
        'native_rolls': {},
        'charm_suffix': None,
        'ethereal': ethereal,
        'sockets': sockets,
        'base_name': base['name'],
        'base_code': base['code'],
        'identified': True,
        'item_level': None,
        'rarity': rarity,
        'socket_contents': 'empty',
        'quantity': 1,
        **base_facets(properties, rarity, sockets, 'empty', base=dict(base)),
    }
