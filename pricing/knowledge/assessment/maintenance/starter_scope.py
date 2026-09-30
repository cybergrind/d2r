"""Reviewed ordinary starter variants: exclude only their own unreviewed source mentions.

The value-focused scope (COMPLETION_CONTRACT.md, 2026-09-29) drops ordinary starter
progression. A `variants` review in value_scope_reviews.json names one guide variant, quotes
its exact purpose from wp-a-variants/<build>.json (and the same variant in wp-a-builds.json),
and lists the planner profiles the guide links for it: the planner must be linked from the
pinned guide HTML, carry the reviewed title and have a profile with the variant's exact name.
A label alone excludes nothing.

Only occurrences no other review has claimed are excluded, and never one tied to a retained
source rule. Item identities, uses, configurations, trade tiers, pricing and item-bank
obligations are untouched: the same item stays in scope through every other mention.
"""

import hashlib
import json
import re
from datetime import date

from pricing.knowledge.assessment.maintenance.value_scope import SCOPE, json_value


PLANNER_PATH = re.compile(r'pricing/raw/mr/planners/([a-z0-9]+)\.json')
INDEX = re.compile(r'(0|[1-9][0-9]*)')


def _read(root, pinned):
    path = pinned.get('path')
    if not isinstance(path, str) or not path:
        raise ValueError('Starter review lacks a source path')
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        raise ValueError(f'Missing starter review source: {path}')
    raw = target.read_bytes()
    if hashlib.sha256(raw).hexdigest() != pinned.get('sha256'):
        raise ValueError(f'Stale starter review source: {path}')
    return raw


def _variant(root, pinned, prefix, name, quote):
    locator = pinned.get('locator', '')
    if not locator.startswith(prefix) or not INDEX.fullmatch(locator.removeprefix(prefix)):
        raise ValueError(f'Starter review locator is not a variant of this build: {locator}')
    value = json_value(json.loads(_read(root, pinned)), locator)
    if not isinstance(value, dict) or value.get('name') != name or value.get('purpose') != quote:
        raise ValueError(f'Starter review quote or name differs from {pinned["path"]}{locator}')
    return pinned['path'], locator


def _planner(root, pinned, guide, name):
    from pricing.knowledge.builds import decode_planner

    match = PLANNER_PATH.fullmatch(pinned.get('path', ''))
    locator = pinned.get('profile', '')
    if match is None or not locator.startswith('/profiles/') or not INDEX.fullmatch(locator.removeprefix('/profiles/')):
        raise ValueError(f'Invalid starter planner reference: {pinned.get("path")}')
    ident = match.group(1)
    if f'data-d2planner-profile="{ident}"' not in guide and f'data-d2-id="{ident}"' not in guide:
        raise ValueError(f'Guide does not link starter planner {ident}')
    document = json.loads(_read(root, pinned))
    profiles = decode_planner(document)['profiles']
    index = int(locator.removeprefix('/profiles/'))
    if document.get('name') != pinned.get('title') or index >= len(profiles) or profiles[index].get('name') != name:
        raise ValueError(f'Starter planner {ident} title or profile differs from the review')
    return pinned['path'], locator


def _retained_rule(row, qualities, excluded_uses):
    for rule in row.get('source_rule_ids') or ():
        keys = [f'use:{rule}:{quality}' for quality in qualities.get(rule, ())]
        if not keys or any(key not in excluded_uses for key in keys):
            return True
    return False


def starter_exclusions(review, occurrences, root, taken, profiles, excluded_uses):
    """Occurrence id → exclusion for reviewed starter variants; `taken` ids keep their disposition."""
    if review is None or not review.get('variants'):
        return {}
    if review.get('schema_version') != 1 or review.get('scope') != SCOPE:
        raise ValueError('Unsupported starter scope review')
    sources = {}
    seen = set()
    for index, row in enumerate(review['variants']):
        build, name, quote = row.get('build'), row.get('variant'), row.get('quote')
        if (build, name) in seen:
            raise ValueError(f'Duplicate starter review: {build} {name}')
        seen.add((build, name))
        if (
            not isinstance(build, str)
            or not re.fullmatch(r'[a-z0-9-]+', build)
            or not isinstance(name, str)
            or not name
            or not isinstance(quote, str)
            or not quote
            or row.get('classification') != 'generic_leveling'
            or not isinstance(row.get('reason'), str)
            or not row['reason'].strip()
        ):
            raise ValueError(f'Starter review must be an explicit generic-leveling variant review: {build}')
        date.fromisoformat(row.get('reviewed_at', ''))
        source = row.get('source', {})
        if source.get('path') != f'pricing/data/wp-a-variants/{build}.json':
            raise ValueError(f'Starter review must quote the build variant file: {build}')
        disposition = {
            'state': 'excluded',
            'reason': row['reason'],
            'source': {'artifact': 'value_scope', 'locator': f'/variants/{index}'},
        }
        anchors = [_variant(root, source, '/variants/', name, quote)]
        for mirror in row.get('mirrors', []):
            if mirror.get('path') != 'pricing/data/wp-a-builds.json':
                raise ValueError(f'Unsupported starter review mirror: {mirror.get("path")}')
            anchors.append(_variant(root, mirror, f'/{build}/variants/', name, quote))
        guide = row.get('guide', {})
        if guide.get('path') != f'pricing/raw/mr/guides__{build}.html':
            raise ValueError(f'Starter review must pin the build guide: {build}')
        html = _read(root, guide).decode()
        anchors.extend(_planner(root, planner, html, name) for planner in row.get('planners', []))
        for anchor in anchors:
            if anchor in sources:
                raise ValueError(f'Starter review source claimed twice: {anchor}')
            sources[anchor] = (build, name, disposition)
    qualities = {profile['id']: profile.get('qualities', []) for profile in profiles}
    result = {}
    for row in occurrences:
        if row['id'] in taken or row.get('source_status') != 'verified':
            continue
        locator = row.get('source_locator', '')
        parts = locator.split('/')
        # A variant anchor is /variants/N or /<build>/variants/N; a planner anchor is /profiles/N.
        for depth in (3, 4):
            hit = sources.get((row.get('source_id'), '/'.join(parts[:depth])))
            if hit and len(parts) > depth:
                break
        else:
            continue
        build, name, disposition = hit
        if row.get('build') != build or row.get('variant') != name:
            continue
        if _retained_rule(row, qualities, excluded_uses):
            continue
        result[row['id']] = {
            'id': row['id'],
            **disposition,
            'source_id': row['source_id'],
            'source_locator': locator,
            'identity_id': row.get('identity_id'),
        }
    return result
