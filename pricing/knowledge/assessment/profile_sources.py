"""Resolve and validate reviewed profile evidence with an injected byte reader."""

import hashlib
import json
import re
from pathlib import Path

from pricing.knowledge.assessment.policies.sources import resolve_pointer


def profile_references(document):
    for profile in document['profiles']:
        source = profile['source']
        yield profile['id'], source
        for evidence in source.get('corroborating', []):
            yield profile['id'], evidence


def profile_source_paths(document, source_root):
    root = Path(source_root).resolve()
    paths = set()
    for _, source in profile_references(document):
        path = (root / source['path']).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Profile source outside source root')
        paths.add(path)
    return paths


def validate_profile_sources(document, source_root, read_bytes):
    root = Path(source_root).resolve()
    hashes = {}
    sources = {}
    documents = {}
    for profile_id, source in profile_references(document):
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
            raise ValueError(f'Invalid source locator for {profile_id}: {source["locator"]}') from error

    for profile in document['profiles']:
        source = profile['source']
        scope = structured_variant_scope(profile, documents[(root / source['path']).resolve()])
        if scope is not None and profile.get('scope', 'softcore') != scope:
            raise ValueError(f'Profile scope disagrees with containing guide variant: {profile["id"]}')
        season = structured_variant_season(profile, documents[(root / source['path']).resolve()])
        if season is not None and profile.get('season', 'non_ladder') != season:
            raise ValueError(f'Profile season disagrees with containing guide variant: {profile["id"]}')


def structured_variant_scope(profile, document):
    """Infer mode only from the actual containing variant in canonical guide data."""
    name = _structured_variant_name(profile, document)
    if name is None:
        return None
    return 'hardcore' if re.search(r'\bhardcore\b', name, re.IGNORECASE) else 'softcore'


def structured_variant_season(profile, document):
    """Explicit Ladder labels are separate from Hardcore and item availability."""
    name = _structured_variant_name(profile, document)
    if name is None:
        return None
    if re.search(r'\bnon[ -]?ladder\b', name, re.IGNORECASE):
        return 'non_ladder'
    return 'ladder' if re.search(r'\bladder\b', name, re.IGNORECASE) else None


def _structured_variant_name(profile, document):
    source = profile['source']
    build = profile.get('build')
    if source['path'] == 'pricing/data/wp-a-builds.json':
        prefix = f'/{build}/variants/'
    elif source['path'] == f'pricing/data/wp-a-variants/{build}.json':
        prefix = '/variants/'
    else:
        return None
    locator = source['locator']
    if not locator.startswith(prefix):
        return None
    index = locator.removeprefix(prefix).split('/')[0]
    if not index.isascii() or not index.isdecimal() or str(int(index)) != index:
        raise ValueError('Invalid variant scope locator')
    variant = resolve_pointer(document, prefix + index)
    name = variant.get('name')
    if not isinstance(name, str) or not name:
        raise ValueError('Missing variant scope name')
    return name
