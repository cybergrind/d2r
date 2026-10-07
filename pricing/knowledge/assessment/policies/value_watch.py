"""Match stat-qualified trade watch entries without changing price contracts."""

import math

from inventory_tracking.items.metadata import metadata


# Explicit scope markers in cached setup labels. Do not treat arbitrary mention
# of Hardcore (including mixed-mode labels) as an exclusion.
HARDCORE_LABEL_MARKERS = ('(hardcore)', '(hardcore;', '(hardcore only)', '(hardcore section;', '(hardcore section)')


def matching_watches(rows, facts):
    matched = []
    for row in rows:
        conditions = row.get('details', {}).get('native_conditions')
        if conditions is None:
            if row.get('kind') != 'affixed_value_watch':
                qualified = named_watch(row, facts)
                if qualified is not None:
                    matched.append(qualified)
            continue
        if (
            facts.identified is not True
            or facts.rarity != row.get('rarity')
            or facts.base_name != row.get('name')
            or facts.ethereal is not False
            or facts.sockets != 0
            or facts.socket_contents != 'empty'
            or not conditions
            or (row['details'].get('require_complete_capture') and facts.capture_complete is not True)
        ):
            continue
        required = row['details'].get('required_affix_records')
        if required is not None and not matching_affix_records(required, facts.native_affixes):
            continue
        if not matching_raw_conditions(row['details'].get('raw_conditions', {}), facts.stats):
            continue
        for key, limits in conditions.items():
            stat = facts.stats.get(key, {})
            if (
                key not in facts.stats
                and key in row['details'].get('missing_zero_stats', ())
                and facts.capture_complete is True
            ):
                stat = {'status': 'decoded', 'value': 0}
            value = stat.get('value')
            if (
                stat.get('status') != 'decoded'
                or type(value) not in (int, float)
                or not math.isfinite(value)
                or value != int(value)
                or not limits['min'] <= value <= limits['max']
            ):
                break
        else:
            if all(
                len({facts.stats[key]['value'] for key in group}) == 1
                for group in row['details'].get('equal_stat_groups', ())
            ):
                matched.append(row)
    return softcore_watches(matched)


def named_watch(row, facts):
    """Conditional prose is not a trade qualification for every copy of a name."""
    details = row.get('details', {})
    conditions = details.get('local_conditions') or details.get('guide_conditions') or ''
    if not conditions:
        return row
    from pricing.triage.demand import EXCLUDED

    contexts = []
    for context in details.get('build_contexts', []):
        if '/variants/' not in context.get('source_locator', '') or EXCLUDED.search(context.get('variant') or ''):
            continue
        label = (context.get('original_label') or '').casefold()
        if any(marker in label for marker in HARDCORE_LABEL_MARKERS):
            continue
        ethereal = False if 'non-ethereal' in label else True if 'ethereal' in label else None
        if ethereal is not None and ethereal is not facts.ethereal:
            continue
        contexts.append(context)
    if not contexts:
        return None
    builds = sorted({c['build'] for c in contexts})
    return row | {
        'details': details
        | {
            'priority': 'build_demand',
            'build_contexts': contexts,
            'builds': builds,
            'build_count': len(builds),
            'local_conditions': None,
            'guide_conditions': None,
        }
    }


def matching_raw_conditions(conditions, stats):
    """Scaled rates are matched in native units, never rounded semantic values."""
    for key, limits in conditions.items():
        stat = stats.get(key, {})
        value = stat.get('raw')
        if stat.get('status') != 'decoded' or type(value) is not int or not limits['min'] <= value <= limits['max']:
            return False
    return True


def matching_affix_records(required, captured):
    """Resolve runtime table IDs to pinned source rows; totals cannot prove level."""
    if captured is None:
        return False
    entries = metadata()['affixes']
    actual = {
        table: sorted(entries[table][str(ident)]['source']['record_key'] for ident in ids)
        for table, ids in captured.items()
    }
    return actual == required


def softcore_watches(rows):
    """Keep original evidence intact while omitting explicitly Hardcore demand."""
    scoped = []
    for row in rows:
        details = row.get('details', {})
        contexts = details.get('build_contexts', [])
        kept, removed = [], []
        for context in contexts:
            variant = context.get('variant') or ''
            label = (context.get('original_label') or '').casefold()
            hardcore = (
                context.get('scope') == 'hardcore'
                or variant.strip().casefold().startswith('hardcore')
                or any(marker in label for marker in HARDCORE_LABEL_MARKERS)
            )
            (removed if hardcore else kept).append(context)
        if not removed:
            scoped.append(row)
            continue
        hardcore_only = {c['build'] for c in removed} - {c['build'] for c in kept}
        builds = [build for build in details.get('builds', []) if build not in hardcore_only]
        if details.get('priority') == 'build_demand' and not builds and not kept:
            continue
        scoped.append(
            {
                **row,
                'details': {**details, 'build_contexts': kept, 'builds': builds, 'build_count': len(builds)},
            }
        )
    return scoped
