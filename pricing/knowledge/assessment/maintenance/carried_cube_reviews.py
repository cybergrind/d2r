"""Review exact carried quest-container occurrences without excluding item identities."""

import hashlib
import json
import re
from datetime import date

from pricing.knowledge.builds import decode_planner


NATIVE = 'third-parties/d2data/json/misc.json'


def occurrence_fingerprint(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _index(rows):
    indexed = {row['id']: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError('Duplicate Cube review inventory identity')
    return indexed


def compile_carried_cube_reviews(document, inventory, root):
    if document is None:
        return []
    if document.get('schema_version') != 1 or document.get('scope') != 'carried_horadric_cube_only':
        raise ValueError('Unsupported carried Cube review scope')
    occurrences = _index(inventory['occurrences'])
    identities = _index(inventory['identities'])
    sources = _index(inventory.get('sources', []))
    inputs = document.get('inputs', {})
    loaded = {}

    def source(name):
        if name not in loaded:
            path = (root / name).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise ValueError(f'Missing or unsafe Cube source: {name}')
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != inputs.get(name):
                raise ValueError(f'Stale or unpinned Cube source: {name}')
            loaded[name] = json.loads(raw)
        return loaded[name]

    native = source(NATIVE).get('box', {})
    expected_native = {
        'name': 'Horadric Cube',
        'code': 'box',
        'type': 'ques',
        'quest': 10,
        'useable': 1,
        'gemsockets': 0,
        'spelldescstr': 'OpenHoradricCube',
    }
    if any(native.get(key) != value for key, value in expected_native.items()):
        raise ValueError('Native Cube container semantics changed')
    result, seen, planners = [], set(), {}
    for review in document['rows']:
        oid = review['occurrence_id']
        if oid in seen or oid not in occurrences:
            raise ValueError('Duplicate or missing reviewed Cube occurrence')
        seen.add(oid)
        row = occurrences[oid]
        if occurrence_fingerprint(row) != review.get('occurrence_sha256'):
            raise ValueError('Changed Cube occurrence')
        date.fromisoformat(review['reviewed_at'])
        if not isinstance(review.get('reason'), str) or not review['reason'].strip():
            raise ValueError('Cube source review requires a reason')
        expected = {
            'name': 'Horadric Cube',
            'original_label': 'Horadric Cube',
            'kind': 'demand',
            'category': 'misc',
            'base_code': 'box',
            'side': 'player',
            'source_status': 'verified',
            'identity_status': 'resolved',
        }
        details = {
            'base': 'box',
            'item_ref': 'box',
            'canonical_id': 'box',
            'container': 'inventory',
            'role': 'inventory',
        }
        identity = identities.get(row.get('identity_id'), {})
        if (
            any(row.get(k) != v for k, v in expected.items())
            or any(row.get('details', {}).get(k) != v for k, v in details.items())
            or identity.get('name') != 'Horadric Cube'
            or identity.get('category') != 'misc'
        ):
            raise ValueError('Unsupported Cube occurrence context')
        name = row['source_id']
        locator = re.fullmatch(r'/profiles/(0|[1-9]\d*)/inventory/(0|[1-9]\d*)', row['source_locator'])
        if not re.fullmatch(r'pricing/raw/mr/planners/[^/]+\.json', name) or locator is None:
            raise ValueError('Cube source must be an exact planner inventory token')
        binding = sources.get(name, {})
        if (
            binding.get('path') != name
            or binding.get('status') != 'verified'
            or not inputs.get(name)
            or binding.get('sha256') != inputs[name]
            or binding.get('actual_sha256') != inputs[name]
        ):
            raise ValueError('Cube source binding changed')
        if name not in planners:
            planners[name] = decode_planner(source(name))
        profile, slot = map(int, locator.groups())
        try:
            token = planners[name]['profiles'][profile]['inventory'][slot]
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError('Missing Cube inventory token') from error
        if token != 'box' or row.get('slot') != str(slot):
            raise ValueError('Decorated or displaced Cube inventory token')
        result.append(
            {
                'occurrence_id': oid,
                'identity_id': row['identity_id'],
                'state': 'reviewed',
                'classification': 'carried_quest_container',
                'reason': review['reason'],
                'reviewed_at': review['reviewed_at'],
                'source_id': name,
                'source_locator': row['source_locator'],
                'source_sha256': inputs[name],
                'native_sha256': inputs[NATIVE],
            }
        )
    return result
