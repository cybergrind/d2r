"""Shared named-tier evidence validation for runtime and maintenance."""

import hashlib
import json
import re
from functools import lru_cache

from pricing.knowledge.artifacts import read_artifact


@lru_cache(maxsize=8)
def source_document(raw):
    return hashlib.sha256(raw).hexdigest(), json.loads(raw)


def resolve_pointer(document, locator):
    """Resolve a non-root JSON pointer without Python's negative-index shortcuts."""
    if not isinstance(locator, str) or not locator.startswith('/'):
        raise ValueError('Invalid source locator')
    node = document
    for token in locator[1:].split('/'):
        if re.search(r'~(?![01])', token):
            raise ValueError('Invalid source locator escape')
        key = token.replace('~1', '/').replace('~0', '~')
        if isinstance(node, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', key):
                raise ValueError('Invalid source locator array index')
            node = node[int(key)]
        elif isinstance(node, dict):
            node = node[key]
        else:
            raise ValueError('Source locator traverses a scalar')
    return node


def source_identity(key, row):
    quality = {'uniques': 'unique', 'sets': 'set'}.get(row.get('type'), row.get('type'))
    if key.startswith('UQ-'):
        quality = 'unique'
    elif key.startswith('ST-'):
        quality = 'set'
    return quality, row.get('name')


def source_error(source, identity, root):
    try:
        path = (root / source['path']).resolve()
        if not path.is_relative_to(root):
            return 'Source outside repository root'
        digest, node = source_document(read_artifact(path))
        if digest != source['sha256']:
            return 'Source fingerprint changed; review required'
        locator = source['locator']
        node = resolve_pointer(node, locator)
        parts = locator[1:].split('/')
        if source_identity(parts[-1], node) != identity:
            return 'Source locator does not identify this item and quality'
    except OSError, ValueError, KeyError, IndexError, TypeError, AttributeError:
        return 'Missing or invalid source evidence'
    return None
