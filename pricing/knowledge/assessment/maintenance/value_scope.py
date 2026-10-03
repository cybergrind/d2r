"""Source-backed use exclusions for the Softcore / Non-Ladder value scope."""

import hashlib
import json


SCOPE = 'non_ladder_value_and_exceptional_leveling'


def profile_fingerprint(profile):
    return hashlib.sha256(json.dumps(profile, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def use_exclusions(profiles, review, root):
    if review is None:
        return {}
    if review.get('schema_version') != 1 or review.get('scope') != SCOPE:
        raise ValueError('Unsupported value scope review')
    indexed = {p['id']: p for p in profiles}
    if len(indexed) != len(profiles):
        raise ValueError('Duplicate scope profile')
    result = {}
    seen = set()
    for index, row in enumerate(review['uses']):
        key = row['profile_id']
        profile = indexed.get(key)
        if key in seen or profile is None or row.get('profile_sha256') != profile_fingerprint(profile):
            raise ValueError(f'Missing, duplicate or changed scope profile: {key}')
        seen.add(key)
        if row.get('classification') not in ('generic_leveling', 'hardcore_only', 'ladder_only') or not row.get(
            'reason'
        ):
            raise ValueError('Only explicitly reviewed generic leveling, Hardcore or Ladder uses may be excluded')
        source = row.get('source', {})
        path = (root / source.get('path', '')).resolve()
        if (
            source != profile.get('source')
            or not row.get('quote')
            or 'variant_context' in row
            or not path.is_relative_to(root.resolve())
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != source.get('sha256')
            or not verified_dimension_quote(row, source, path)
        ):
            raise ValueError(f'Stale or unverified generic leveling source: {key}')
        if row['classification'] in ('hardcore_only', 'ladder_only'):
            from datetime import date

            from pricing.knowledge.assessment.profile_sources import structured_variant_scope, structured_variant_season

            date.fromisoformat(row.get('reviewed_at', ''))
            mode, field, resolve = (
                ('hardcore', 'scope', structured_variant_scope)
                if row['classification'] == 'hardcore_only'
                else ('ladder', 'season', structured_variant_season)
            )
            if profile.get(field) != mode or resolve(profile, json.loads(path.read_text())) != mode:
                raise ValueError(
                    f'{mode.capitalize()} exclusion lacks an exact {mode.capitalize()} source variant: {key}'
                )
        if (
            row['classification'] == 'generic_leveling'
            and profile.get('variant') == 'Gear alternatives'
            and source['path'] == 'pricing/data/appraisal-guide-sections.json'
            and 'table_context' not in row
        ):
            raise ValueError('Table-based generic use exclusions require exact cell context')
        if 'table_context' in row:
            from pricing.knowledge.assessment.maintenance.early_merc_table_scope import validate_table_context

            validate_table_context(row, profile, root)
        for quality in profile['qualities']:
            result[f'use:{key}:{quality}'] = {
                'state': 'excluded',
                'reason': row['reason'],
                'source': {'artifact': 'value_scope', 'locator': f'/uses/{index}'},
            }
    return result


def occurrence_exclusions(profiles, excluded_uses, occurrences):
    """Apply already validated use reviews to exact named source occurrences."""
    from collections import defaultdict

    from pricing.knowledge.assessment.maintenance.guide_spans import occurrence_source

    indexed = defaultdict(list)
    for profile in profiles:
        keys = [f'use:{profile["id"]}:{q}' for q in profile['qualities']]
        if (
            not keys
            or any(key not in excluded_uses for key in keys)
            or len(profile.get('names', [])) != 1
            or not profile.get('source', {}).get('locator')
        ):
            continue
        indexed[occurrence_source(profile['source'])].append((profile, excluded_uses[keys[0]]))
    result = {}
    for row in occurrences:
        if row.get('source_status') != 'verified' or row.get('identity_status') != 'resolved':
            continue
        for profile, disposition in indexed[row.get('source_id'), row.get('source_locator')]:
            if (
                row.get('name') == row.get('original_label') == profile['names'][0]
                and row.get('source_rule_ids') == [profile['id']]
                and all(row.get(k) == profile.get(k) for k in ('build', 'variant', 'side', 'slot'))
            ):
                result[row['id']] = {
                    'id': row['id'],
                    **disposition,
                    'profile_id': profile['id'],
                    'source_id': row['source_id'],
                    'source_locator': row['source_locator'],
                }
    return result


def dimension_exclusions(profiles, review, root):
    """Exclude only reviewed non-leveling use obligations, never an item or source."""
    from datetime import date

    if review is None:
        return {}
    if review.get('schema_version') != 1 or review.get('scope') != SCOPE:
        raise ValueError('Unsupported dimension scope review')
    indexed = {profile['id']: profile for profile in profiles}
    if len(indexed) != len(profiles):
        raise ValueError('Duplicate dimension scope profile')
    seen, result = set(), {}
    for index, row in enumerate(review.get('dimensions', [])):
        key = row['profile_id']
        profile = indexed.get(key)
        if key in seen or profile is None or row.get('profile_sha256') != profile_fingerprint(profile):
            raise ValueError(f'Missing, duplicate or changed dimension scope profile: {key}')
        seen.add(key)
        if (
            row.get('classification') != 'non_leveling_use'
            or row.get('dimension') != 'leveling'
            or not row.get('reason')
        ):
            raise ValueError('Only explicitly reviewed non-leveling use obligations may be excluded')
        date.fromisoformat(row.get('reviewed_at', ''))
        source = row.get('source', {})
        path = (root / source.get('path', '')).resolve()
        if (
            source != profile.get('source')
            or not path.is_relative_to(root.resolve())
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != source.get('sha256')
            or not verified_dimension_quote(row, source, path, profile)
        ):
            raise ValueError(f'Stale or unverified dimension scope source: {key}')
        for quality in profile['qualities']:
            result[f'use:{key}:{quality}/leveling'] = {
                'state': 'excluded',
                'reason': row['reason'],
                'source': {'artifact': 'value_scope', 'locator': f'/dimensions/{index}'},
            }
    return result


def verified_dimension_quote(row, source, path, profile=None):
    """Verify a local quote or an explicitly linked containing variant's purpose.

    Older profiles omit quotes. A maintenance review may bind their source text
    without rewriting runtime profiles or weakening whole-use exclusions.
    """
    quote = row.get('quote')
    if type(quote) is not str or not quote:
        return False
    evidence = row.get('quote_source')
    if evidence is None:
        return 'variant_context' not in row and quote in source.get('quotes', [])
    if (
        type(evidence) is not dict
        or set(evidence) != {'path', 'sha256', 'locator'}
        or any(evidence[key] != source.get(key) for key in ('path', 'sha256'))
    ):
        return False
    anchor, locator = source.get('locator'), evidence['locator']
    if not (type(anchor) is str and anchor.startswith('/') and type(locator) is str and locator.startswith('/')):
        return False
    try:
        document = json.loads(path.read_text())
        if 'variant_context' in row:
            if not verified_variant_context(row, profile, source, document):
                return False
        elif not (locator == anchor or locator.startswith(anchor + '/')):
            return False
        value = json_value(document, locator)
    except ValueError, KeyError, IndexError, TypeError:
        return False
    return type(value) is str and value == quote


def json_value(value, locator):
    for part in locator.removeprefix('/').split('/'):
        part = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not part.isascii() or not part.isdecimal() or str(int(part)) != part:
                raise ValueError('Noncanonical array index')
            value = value[int(part)]
        else:
            value = value[part]
    return value


def verified_variant_context(row, profile, source, document):
    """Only this build's actual containing player/merc variant may supply context."""
    context = row['variant_context']
    if type(context) is not dict or set(context) != {'locator', 'name'} or not profile:
        return False
    build = profile.get('build')
    if type(build) is not str or not build or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in build):
        return False
    if source['path'] == 'pricing/data/wp-a-builds.json':
        prefix = f'/{build}/variants/'
    elif source['path'] == f'pricing/data/wp-a-variants/{build}.json':
        prefix = '/variants/'
    else:
        return False
    anchor = context['locator']
    if type(anchor) is not str or not anchor.startswith(prefix):
        return False
    index = anchor.removeprefix(prefix)
    if not index.isascii() or not index.isdecimal() or str(int(index)) != index:
        return False
    if row['quote_source']['locator'] != anchor + '/purpose':
        return False
    if not any(
        source['locator'] == anchor + side or source['locator'].startswith(anchor + side + '/')
        for side in ('/player', '/merc')
    ):
        return False
    variant = json_value(document, anchor)
    json_value(document, source['locator'])  # The referenced equipment location must actually exist.
    return (
        type(variant) is dict
        and type(context['name']) is str
        and bool(context['name'])
        and variant.get('name') == context['name'] == profile.get('variant')
    )
