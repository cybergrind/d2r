"""Reviewed quality exclusions for runeword creation, not all cube recipes."""

import hashlib


SPECIAL_QUALITIES = frozenset({'magic', 'set', 'rare', 'unique', 'crafted'})
NATIVE_SOURCES = frozenset(
    {
        'third-parties/D2MOO/source/D2Common/src/Items/Items.cpp',
        'third-parties/D2MOO/source/D2Common/include/D2Items.h',
    }
)


def apply_recipe_applicability(rows, review, root):
    if review is None:
        return
    if review.get('schema_version') != 1 or len(review.get('rules', [])) != 1:
        raise ValueError('Unsupported recipe applicability review')
    rule = review['rules'][0]
    if (
        rule.get('id') != 'special-quality-not-runeword-base'
        or rule.get('scope') != 'runeword_creation'
        or rule.get('dimension') != 'recipe_eligibility'
        or rule.get('disposition') != 'excluded'
        or set(rule.get('qualities', [])) != SPECIAL_QUALITIES
        or not rule.get('reason')
    ):
        raise ValueError('Unsupported recipe quality exclusion')
    if set(review.get('inputs', {})) != NATIVE_SOURCES:
        raise ValueError('Missing native recipe quality evidence')
    for name, digest in review['inputs'].items():
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'Stale recipe quality evidence: {name}')
    identities = {row['id']: row for row in rows if row['kind'] == 'identity'}
    for row in rows:
        if row['kind'] not in ('identity', 'base_quality', 'use_quality', 'evidence'):
            continue
        quality = row.get('quality', row.get('category'))
        if quality not in SPECIAL_QUALITIES:
            continue
        if row['kind'] == 'evidence':
            links = row.get('identity_ids', [])
            identity = identities.get(links[0]) if len(links) == 1 else None
            if (
                not identity
                or not identity.get('catalog_ids')
                or identity['dimensions']['discovery']['state'] != 'reviewed'
                or (identity.get('name'), identity.get('category')) != (row.get('name'), quality)
            ):
                continue
        # Unresolved name/pattern rows cannot borrow a known item's quality.
        if row['dimensions']['discovery']['state'] != 'reviewed':
            continue
        row['dimensions']['recipe_eligibility'] = {
            'state': 'excluded',
            'reason': rule['reason'],
            'sources': [
                *row['dimensions']['discovery']['sources'],
                {'artifact': 'recipe_applicability', 'locator': '/rules/0'},
            ],
        }
        if row['kind'] == 'evidence':
            row['dimensions']['recipe_eligibility']['identity_ids'] = list(row['identity_ids'])
