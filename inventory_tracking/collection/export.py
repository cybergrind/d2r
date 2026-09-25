"""Single-file HTML export of the collection: search by name, set, runeword, stats, sockets.

The page embeds its data as JSON and carries its own CSS and JavaScript, so it opens
from file:// with no network. Search words are matched the same way as the CLI query:
every word (or quoted phrase) must occur in the item's searchable text.
"""

import html
import json
from pathlib import Path
from typing import Any

from inventory_tracking.collection.store import CollectionStore


DEFAULT_HTML = Path('inventory_tracking/runs/collection/collection.html')
TEMPLATE_PATH = Path(__file__).with_name('template.html')
CONTAINER_LABELS = {
    'inventory': 'Inventory',
    'cube': 'Horadric Cube',
    'equipped': 'Equipped',
    'mercenary': 'Mercenary',
    'stash': 'Personal stash',
    'shared_stash': 'Shared stash',
    'materials': 'Gems, materials & runes',
}


def unresolved_text(entry: dict[str, Any]) -> str:
    if entry.get('text'):
        return str(entry['text'])
    stat = entry.get('memory_stat') or entry
    parts = [f'stat {stat.get("id")}']
    if stat.get('layer'):
        parts.append(f'layer {stat["layer"]}')
    if 'raw' in stat:
        parts.append(f'= {stat["raw"]}')
    if entry.get('name'):
        parts.insert(0, str(entry['name']))
    return ' '.join(parts)


def location_label(placement) -> str:
    where = CONTAINER_LABELS.get(placement.location.container, placement.location.container)
    if placement.location.tab is not None:
        where += f' {placement.location.tab}'
    return where


def export_payload(store: CollectionStore) -> dict[str, Any]:
    rows = []
    for item, placement in store.query():
        observation = item.observation
        rows.append(
            {
                'id': placement.id,
                'fingerprint': item.fingerprint,
                'name': item.name,
                'base': item.base_name,
                'code': item.base_code,
                'rarity': item.rarity,
                'set': item.set_name,
                'runeword': item.runeword,
                'identified': item.identified,
                'ethereal': item.ethereal,
                'sockets': item.sockets,
                'socket_contents': item.socket_contents,
                'socket_items': item.socket_items,
                'stats': item.stat_lines,
                'quantity': item.quantity,
                'size': f'{item.width}x{item.height}' if item.width and item.height else None,
                'unresolved': [unresolved_text(e) for e in observation.get('unresolved_stats', [])],
                'issues': list(observation.get('issues', [])),
                'owner': placement.location.owner,
                'container': placement.location.container,
                'tab': placement.location.tab,
                'where': location_label(placement),
                'x': placement.location.x,
                'y': placement.location.y,
                'seen_at': placement.seen_at,
                'search': item.search_text,
            }
        )
    return {
        'generated_at': store.db.execute("SELECT strftime('%Y-%m-%dT%H:%M:%SZ','now')").fetchone()[0],
        'characters': [c.model_dump() for c in store.characters()],
        'counts': store.counts(),
        'spaces': [
            {
                'owner': s.owner,
                'container': s.container,
                'tab': s.tab,
                'where': CONTAINER_LABELS.get(s.container, s.container) + (f' {s.tab}' if s.tab is not None else ''),
                'width': s.width,
                'height': s.height,
                'free': s.free,
                'rows': s.rows,
                'fits': s.fits,
            }
            for s in store.spaces()
        ],
        'rows': rows,
    }


def render_html(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    counts = payload['counts']
    characters = ', '.join(
        f'{c["name"]}' + (f' ({c["class_name"]} {c["level"]})' if c.get('class_name') else '')
        for c in payload['characters']
    )
    subtitle = html.escape(
        f'{counts["placements"]} items on {counts["characters"]} characters · {characters} · '
        f'generated {payload["generated_at"]}'
    )
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    return template.replace('__SUBTITLE__', subtitle).replace('__DATA__', data)


def export_html(store: CollectionStore, path: Path) -> dict[str, Any]:
    payload = export_payload(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(payload), encoding='utf-8')
    return payload
