"""Plain-text presentation of offline appraisal drafts; never infer a valuation."""

from pricing.knowledge.market import valid_positive


def review_lines(extraction):
    lines = list(extraction.get('review', []))
    count = len(extraction.get('unresolved_stats', []))
    if count:
        lines.insert(
            0, f'{count} stat entry remains undecoded.' if count == 1 else f'{count} stat entries remain undecoded.'
        )
    return lines


def unresolved_lines(record):
    extraction = record.get('result', {}).get('extraction', {})
    return [
        'Unresolved / review:',
        *review_lines(extraction),
        *(s['text'] for s in extraction.get('decoded_stats', []) if s['status'] == 'unresolved'),
    ]


def evidence_lines(identity):
    lines = ['Offline evidence (candidate matches; review required):']
    evidence = identity.get('evidence', {})
    for kind in ('demand', 'leveling'):
        for row in evidence.get(kind, [])[:3]:
            details = row.get('details', {})
            source = row.get('source', {})
            source = source if isinstance(source, dict) else {}
            date = source.get('source_date') or details.get('profile_date') or source.get('fetched_at')
            description = details.get('description') or 'guide mention; context required'
            label = row.get('build') or row.get('class') or row.get('name', 'Unknown')
            variant = row.get('variant', '')
            label = label.replace('-', ' ')
            if variant:
                label += f' / {variant}'
            lines.append(f'  {kind.capitalize()}: {label}: {description} ({date or "date unknown"})')
    # The current market schema exposes asks only. Do not relabel them as fills,
    # or present a bucket minimum as this item's value.
    for row in (identity.get('market') or {}).get('representatives', []):
        if row.get('observed_at') and valid_positive(row.get('ask_ist')):
            lines.append(f'  {row["observed_at"]} ask: {row["ask_ist"]:g} Ist ({row.get("source", "cached market")})')
    lines.extend(f'  Gap: {gap}' for gap in identity.get('gaps', []))
    if len(lines) == 1:
        lines.append('  No summarized evidence available; see JSON report.')
    return lines


def base_lines(assessment):
    if not assessment:
        return []
    lines = ['Base research:']
    for row in assessment['historical_asks'][:3]:
        details = row['details']
        lines.append(
            f'  {row.get("date") or "date unknown"} historical asks [{row["bucket"]}]: '
            f'median {details["median_ist"]:g} Ist; {details.get("n_priced", "?")} priced listings.'
        )
    if assessment['historical_asks']:
        lines.append(f'  {assessment["caveat"]}')
    for row in assessment['research'][:1]:
        details = row['details']
        demand = details.get('demand', {})
        words = ', '.join(demand.get('runewords', []))
        lines.append(f'  Research ({row.get("date") or "date unknown"}): demand for {words or "see JSON record"}.')
        if demand.get('eth_wanted'):
            lines.append('  Research favors ethereal variants; their prices do not apply to non-ethereal bases.')
    recipes = sorted({r['runeword'] for r in assessment['recipes']})
    if recipes:
        lines.append('  Type/socket-compatible recipes (mode restrictions require review): ' + ', '.join(recipes))
    if assessment['price_status'] == 'unresearched_variant':
        lines.append('  No comparable price for this variant; unknown does not mean worthless.')
    return lines


def format_appraisal(record, frozen=None):
    """Format a published record using actual newline characters."""
    lines = [f'Appraisal request {record["request_id"]} — {record.get("updated_at", "time unavailable")}']
    if record['state'] == 'rejected':
        diagnostics = (
            [f'Panel diagnostics saved: {record["diagnostics_file"]}'] if record.get('diagnostics_file') else []
        )
        return '\n'.join([*lines, f'Unavailable: {record["reason"]}', *diagnostics, ''])
    if record['state'] != 'complete':
        return '\n'.join([*lines, f'Status: {record["state"]}', ''])
    result = record['result']
    extraction = result['extraction']
    item = extraction['item']
    decision = result['decision']
    page = (frozen or {}).get('selection', {}).get('item', {}).get('details', {}).get('inventory_page')
    container = extraction.get('source', {}).get('container', {}).get('name')
    if container is None:
        container = {0: 'Main inventory', 3: 'Horadric Cube'}.get(page, 'Unrecorded')
    lines.extend(
        [
            f'Item: {item.get("rarity", "unknown").capitalize()} {item.get("name", "Unknown item")}',
            f'Container: {container}',
            'Observed stats:',
        ]
    )
    if item.get('name') != item.get('base_name') and item.get('base_name'):
        lines.insert(len(lines) - 1, f'Base: {item["base_name"]}')
    if item.get('set_name'):
        lines.insert(len(lines) - 1, f'Set: {item["set_name"]}')
    if type(item.get('ethereal')) is bool:
        lines.insert(len(lines) - 1, 'Ethereal: ' + ('yes' if item['ethereal'] else 'no'))
    affixes = item.get('affixes', [])
    decoded = extraction.get('decoded_stats')
    if decoded is not None:
        lines.extend(f'  {stat["text"]}' for stat in decoded)
    else:
        lines.extend(f'  {a["label"].replace("{{value}}", str(a["value"]))}' for a in affixes)
    if not decoded and not affixes:
        lines.append('  No supported stats decoded.')
    lines.append('Unresolved / review:')
    lines.extend(f'  {note}' for note in review_lines(extraction))
    lines.extend(
        [
            f'Verdict: {decision["verdict"]} — partial draft, not a final appraisal.',
            f'Price: {decision.get("price_status", "unresolved")}',
            decision.get('reason', ''),
            *base_lines(result.get('base_assessment')),
            *evidence_lines(result.get('evidence', {}).get('identity', {})),
            f'Next: {decision.get("next_step", "Review local evidence.")}',
        ]
    )
    return '\n'.join([*lines, ''])


def roll_styles(record):
    colors = {'perfect': 'bright_green', 'low': 'bright_red'}
    rows = record.get('result', {}).get('extraction', {}).get('decoded_stats', [])
    return {row['text']: colors[row['roll_quality']] for row in rows if row.get('roll_quality') in colors}
