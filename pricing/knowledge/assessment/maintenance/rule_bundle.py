"""Assemble per-build reviewed rules without changing the runtime bundle schema."""

import json
from pathlib import Path

from pricing.knowledge.artifacts import artifact_snapshot
from pricing.knowledge.assessment.base_use import UTILITY
from pricing.knowledge.assessment.maintenance.profile_templates import expand_profile


def load_rule_bundle(manifest_path):
    # Every template in this compile sees the same recipe generation.
    with artifact_snapshot([UTILITY]):
        return _load_rule_bundle(manifest_path)


def _load_rule_bundle(manifest_path):
    path = Path(manifest_path)
    document = json.loads(path.read_text())
    root = path.parent.resolve()
    profiles, seen_files = {}, set()
    for relative in document['profile_files']:
        source = (root / relative).resolve()
        if not source.is_relative_to(root):
            raise ValueError('Profile file outside rules root')
        if source in seen_files:
            raise ValueError('Duplicate profile file')
        seen_files.add(source)
        for source_profile in json.loads(source.read_text())['profiles']:
            profile = expand_profile(source_profile)
            identity = profile['id']
            if identity in profiles:
                raise ValueError(f'Duplicate profile ID: {identity}')
            profiles[identity] = profile
    order = document['profile_order']
    if len(order) != len(set(order)) or set(order) != set(profiles):
        raise ValueError('Profile order must enumerate every profile exactly once')
    return {
        **{k: v for k, v in document.items() if k not in ('profile_files', 'profile_order')},
        'profiles': [profiles[key] for key in order],
    }
