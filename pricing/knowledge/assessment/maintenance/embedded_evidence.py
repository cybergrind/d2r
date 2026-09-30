"""Resolve pinned embedded tooltip evidence without approving its build semantics."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from pricing.knowledge.assessment.maintenance.embedded_items import embedded_guide_context
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.builds import decode_planner


def _read_pin(pin, root):
    root = Path(root).resolve()
    path = (root / pin['path']).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Embedded evidence path escapes source root')
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ValueError('Embedded evidence source is unavailable') from error
    if hashlib.sha256(raw).hexdigest() != pin['sha256']:
        raise ValueError('Embedded evidence source hash changed')
    return raw.decode('utf-8')


def _socket_definitions(item, definitions, ancestors):
    children = item.get('socketedItems', [])
    if not isinstance(children, list):
        raise ValueError('Malformed embedded socket container')
    result = {}
    for child in children:
        if isinstance(child, dict):
            result.update(_socket_definitions(child, definitions, ancestors))
            continue
        if type(child) not in (str, int) or not str(child).strip():
            raise ValueError('Malformed embedded socket reference')
        key = str(child)
        if key in ancestors:
            raise ValueError('Cyclic embedded socket reference')
        if key not in definitions:
            if key.isdecimal():
                raise ValueError('Missing embedded socket definition')
            # Literal base/rune codes are preserved in the parent definition.
            # Their game meaning is checked by the semantic review, not here.
            continue
        definition = definitions[key]
        if not isinstance(definition, dict):
            raise ValueError('Malformed embedded socket definition')
        result[key] = deepcopy(definition)
        result.update(_socket_definitions(definition, definitions, (*ancestors, key)))
    return result


def validate_embedded_evidence(row, root, *, allow_legacy=False):
    reference = row['reference']
    expected_path = f'pricing/raw/mr/planners/{reference["profile_id"]}.json'
    if row['planner']['path'] != expected_path:
        raise ValueError('Embedded reference points to a different planner')
    context = embedded_guide_context(_read_pin(row['guide'], root), reference)
    if context != row['expected_context']:
        raise ValueError('Embedded guide context changed')
    planner = decode_planner(json.loads(_read_pin(row['planner'], root)))
    profiles = [
        index
        for index, profile in enumerate(planner['profiles'])
        if isinstance(profile, dict) and profile.get('uid') == reference['set_id']
    ]
    legacy = allow_legacy and reference.get('format') == 'legacy_item' and reference.get('set_id') is None
    if not legacy and (reference.get('set_id') is None or len(profiles) != 1):
        raise ValueError('Missing or ambiguous embedded profile')
    key = str(reference['item_id'])
    item = planner['items'].get(key)
    if not isinstance(item, dict) or fingerprint(item) != row['item_fingerprint']:
        raise ValueError('Embedded item definition changed')
    return {
        'context': context,
        'profile_locator': None if legacy else f'/profiles/{profiles[0]}',
        'item': deepcopy(item),
        'socket_definitions': _socket_definitions(item, planner['items'], (key,)),
    }
