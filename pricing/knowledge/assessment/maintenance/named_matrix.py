"""Link baseline reviews without confusing them with prices or build suitability."""


def native_tier_exclusion(row, named_gate):
    """Verify the precise native identity and reason before excluding a tier."""
    if row['kind'] != 'identity':
        return None
    for index, entry in enumerate((named_gate or {}).get('excluded', [])):
        quality, name = entry.get('quality'), entry.get('name')
        native = entry.get('native_definition', {})
        table_id = entry.get('table_id')
        if (
            (quality, name) != (row.get('category'), row.get('name'))
            or quality not in ('unique', 'set')
            or not isinstance(table_id, int)
            or row.get('catalog_ids') != [f'{quality}{table_id}']
            # Native string-table keys can differ from localized display names.
            or native.get('*ID') != table_id
            or not entry.get('reason')
        ):
            continue
        justified = {
            'quest_item': bool(entry.get('base_quest')),
            'disabled_definition': native.get('spawnable') == 0,
            'definition_placeholder': not native.get('spawnable')
            and not any(native.get(f'prop{i}') for i in range(1, 13)),
        }.get(entry.get('kind'), False)
        if justified:
            return {
                'state': 'excluded',
                'reason': entry['reason'],
                'sources': [{'artifact': 'named_gate', 'locator': f'/excluded/{index}'}],
            }
    return None


def captured_baseline(row, identities, baselines):
    """Bind a saved named capture to its exact catalog identity and tier review."""
    facts = row.get('facts', {})
    quality = facts.get('rarity')
    capture_sources = row['dimensions'].get('discovery', {}).get('sources', [])
    if not capture_sources:
        return None
    if quality in ('normal', 'superior', 'low_quality', 'low quality', 'magic', 'rare', 'crafted'):
        return {
            'state': 'excluded',
            'reason': 'Captured quality is not unique/set; named baseline tiers do not apply.',
            'sources': capture_sources,
        }
    native = facts.get('provenance', {}).get('capture', {}).get('item_identity', {})
    if (
        quality not in ('unique', 'set')
        or facts.get('identified') is not True
        or native.get('table') != quality
        or type(native.get('table_id')) is not int
        or native.get('mode_eligibility') == 'ladder_only'
    ):
        return None
    matches = [
        identity
        for identity in identities.values()
        if (identity.get('category'), identity.get('name')) == (quality, facts.get('name'))
        and identity.get('catalog_ids') == [f'{quality}{native["table_id"]}']
    ]
    baseline = baselines.get((quality, facts.get('name')))
    if len(matches) != 1 or baseline is None:
        return None
    entry, source = baseline
    return {
        'state': 'blocked'
        if entry.get('baseline_error')
        else 'reviewed'
        if entry.get('tier') in ('high', 'med', 'low', 'trash')
        else 'pending',
        'reason': 'Captured native identity matches its reviewed named baseline; report and price remain separate.',
        'sources': [*capture_sources, source, *matches[0]['dimensions'].get('discovery', {}).get('sources', [])],
        'identity_ids': [matches[0]['id']],
    }


def apply_named_dimensions(rows, named_gate):
    identities = {row['id']: row for row in rows if row['kind'] == 'identity'}
    baselines = {}
    for index, entry in enumerate((named_gate or {}).get('rows', [])):
        key = entry['quality'], entry['name']
        if key in baselines:
            raise ValueError('Duplicate named baseline in coverage evidence')
        baselines[key] = (entry, {'artifact': 'named_gate', 'locator': f'/rows/{index}'})
    for row in rows:
        kind = row['kind']
        if kind == 'observed_capture':
            if review := captured_baseline(row, identities, baselines):
                row['dimensions']['named_tiers'] = review
            continue
        quality = row.get('quality', row.get('category'))
        exclusion = native_tier_exclusion(row, named_gate)
        if exclusion and (quality, row['name']) not in baselines:
            row['dimensions']['named_tiers'] = exclusion
            continue
        if kind in ('base_quality', 'use_quality') and quality in (
            'normal',
            'superior',
            'low_quality',
            'low quality',
            'magic',
            'rare',
            'crafted',
        ):
            row['dimensions']['named_tiers'] = {
                'state': 'excluded',
                'reason': 'This quality is not a unique or set item; named baseline tiers do not apply.',
                'sources': row['dimensions']['discovery']['sources'],
            }
            continue
        if (
            named_gate is None
            or quality not in ('unique', 'set')
            or kind not in ('identity', 'use_quality', 'evidence')
        ):
            continue
        if kind == 'evidence':
            # A same-name mention alone is insufficient: evidence must already
            # resolve to exactly one catalog identity of the same quality.
            links = row.get('identity_ids', [])
            identity = identities.get(links[0]) if len(links) == 1 else None
            if not identity or (identity['name'], identity['category']) != (row['name'], quality):
                continue
        names = row['names'] if kind == 'use_quality' else [row['name']]
        matches = [baselines.get((quality, name)) for name in names]
        found = [entry for entry in matches if entry is not None]
        sources = [source for _, source in found] or [{'artifact': 'named_gate', 'locator': '/rows'}]
        errors = any(entry.get('baseline_error') for entry, _ in found)
        reviewed = (
            bool(names)
            and len(found) == len(names)
            and all(entry.get('tier') in ('high', 'med', 'low', 'trash') for entry, _ in found)
        )
        row['dimensions']['named_tiers'] = {
            'state': 'blocked' if errors else 'reviewed' if reviewed else 'pending',
            'reason': 'Universal named baseline review; premium rolls and numeric market evidence remain separate.',
            'sources': sources,
        }
        if kind == 'evidence':
            row['dimensions']['named_tiers']['identity_ids'] = list(row['identity_ids'])
        # This closes the identity-level review, not a particular leveling setup.
        if (
            kind == 'identity'
            and not errors
            and len(found) == 1
            and found[0][0].get('leveling_review')
            in ('recommendation', 'conditional_combination', 'no_specific_recommendation')
        ):
            row['dimensions']['leveling'] = {
                'state': 'reviewed',
                'reason': 'Named identity has an explicit leveling review; combinations retain their own conditions.',
                'sources': sources,
            }
