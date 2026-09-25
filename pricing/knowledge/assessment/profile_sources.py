"""Resolve and validate reviewed profile evidence with an injected byte reader."""

import hashlib
import json
from pathlib import Path

from pricing.knowledge.assessment.policies.sources import resolve_pointer


def profile_source_paths(document, source_root):
    root = Path(source_root).resolve()
    paths = set()
    for profile in document['profiles']:
        path = (root / profile['source']['path']).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Profile source outside source root')
        paths.add(path)
    return paths


def validate_profile_sources(document, source_root, read_bytes):
    root = Path(source_root).resolve()
    hashes = {}
    sources = {}
    documents = {}
    for profile in document['profiles']:
        source = profile['source']
        path = (root / source['path']).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Profile source outside source root')
        if path not in hashes:
            raw = read_bytes(path)
            hashes[path] = hashlib.sha256(raw).hexdigest()
            sources[path] = raw
        if hashes[path] != source['sha256']:
            raise ValueError(f'Source changed; review required: {source["path"]}')
        try:
            if path not in documents:
                documents[path] = json.loads(sources[path])
            resolve_pointer(documents[path], source['locator'])
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise ValueError(f'Invalid source locator for {profile["id"]}: {source["locator"]}') from error
