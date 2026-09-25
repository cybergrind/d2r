"""Plain-text presentation of offline appraisal drafts; never infer a valuation."""


def review_lines(extraction):
    lines = list(extraction.get('issues', []))
    unknown = [r['text'] for r in extraction.get('decoded_stats', []) if r['status'] == 'unresolved']
    lines.extend(unknown)
    count = len(extraction.get('unresolved_stats', []))
    if count and not unknown:
        lines.append(
            f'{count} stat entry remains undecoded.' if count == 1 else f'{count} stat entries remain undecoded.'
        )
    # OCR-specific uncertainty remains useful; memory decoder caveats belong in JSON.
    if extraction.get('source', {}).get('engine') != 'memory_snapshot':
        lines.extend(extraction.get('review', []))
    return list(dict.fromkeys(lines))


def unresolved_lines(record):
    issues = review_lines(record.get('result', {}).get('extraction', {}))
    return ['Unreadable:', *issues] if issues else []


def base_summary(result):
    """Current engine output owns suitability; fallback only for archived reports."""
    assessment = result.get('assessment', {})
    if 'base_uses' in assessment:
        return {
            'uses': assessment['base_uses'],
            # Generic recipe evidence is not a reviewed suitability judgment.
            'recipes': (result.get('base_assessment') or {}).get('recipes', []),
        }
    return result.get('base_assessment')


def base_lines(assessment):
    uses = (assessment or {}).get('uses', [])
    if uses:
        lines = ['Runeword base:']
        for use in uses:
            lines.append(f'  {use["runeword"]} / {use["role"]}: {use["status"]}')
        # Shared requirements/rolls appear once, with recipe labels when needed.
        for key in ('strengths', 'missing'):
            grouped = {}
            for use in uses:
                for line in use[key]:
                    grouped.setdefault(line, []).append(use['runeword'])
            for line, words in grouped.items():
                prefix = ', '.join(words) + ': ' if len(words) < len(uses) else ''
                lines.append('    ' + prefix + line)
        lines.extend('    ' + line for line in dict.fromkeys(u['tradeoff'] for u in uses))
        alternatives = sorted({n for u in uses if u['status'] == 'usable alternative' for n in u['alternatives']})
        if alternatives:
            lines.append('    Preferred alternatives (recipe-dependent): ' + ', '.join(alternatives))
        return lines
    recipes = sorted({r['runeword'] for r in (assessment or {}).get('recipes', []) if r.get('runeword')})
    return ['Runeword options (check recipe conditions): ' + ', '.join(recipes)] if recipes else []


def build_name(slug):
    return slug.removesuffix('-build-guide').removesuffix('-guide').replace('-', ' ').title()


def value_watch_lines(result):
    lines = []
    covered = {
        (r['build'], r['variant'], r['side'], r['slot'])
        for r in result.get('assessment', {}).get('roles', [])
        if r['status'] in ('matched', 'partial')
    }
    for row in result.get('value_watch', [])[:1]:
        details = row['details']
        lines.append('VALUABLE CANDIDATE' if details['priority'] == 'valuable_candidate' else 'BUILD DEMAND')
        contexts = sorted(
            details.get('build_contexts', []),
            key=lambda c: c.get('variant') in ('Main alternatives', 'Prose alternatives'),
        )
        shown = set()
        for context in contexts:
            key = (context['build'], context['variant'], context['side'], context['slot'])
            if key in covered or key in shown:
                continue
            shown.add(key)
            lines.append(
                f'  {build_name(context["build"])} / {context["variant"]} / {context["side"]}: '
                f'{context["original_label"]}'
            )
            if len(shown) == 3:
                break
        for key in ('roll_bucket', 'guide_conditions', 'stat_priority'):
            if details.get(key) and details[key] != '-':
                lines.append(f'  {details[key]}')
    return lines


def unavailable_price_line(result, estimate):
    reason = estimate.get('unavailable_reason')
    if reason == 'unclassified':
        assessment = result.get('assessment', {})
        gaps = assessment.get('price_gaps', [])
        if gaps and all(g.startswith('No verified market mapping') for g in gaps):
            return 'Price: not assessed — market comparisons do not support all of these modifiers yet.'
        if gaps:
            return 'Price: not assessed — ' + gaps[0].rstrip('.') + '.'
        return 'Price: not assessed — item data or pricing rules are incomplete.'
    reasons = {
        'no_matches': "no offline listings match this item's variant",
        'thin': f'only {estimate.get("sellers", "?")} matching sellers in the offline KB',
        'undated': 'too few matching sellers have verified observation dates',
        'stale': 'too few matching sellers are within the supported date window',
        'dispersed': 'matching asking prices vary too widely for an estimate',
    }
    if reason in reasons:
        return 'Price: unknown — ' + reasons[reason] + '.'
    if result.get('price_reference'):
        return 'Price: unknown — available same-base listings are not comparable to this item.'
    return 'Price: unknown — no verified item estimate is available.'


def current_price_lines(result):
    estimate = result.get('price_estimate')
    if estimate is None:
        return [f'Price: {result["decision"].get("price_status", "unresolved")}']
    value = estimate['estimate_ist']
    if value is None:
        if asks := estimate.get('comparable_asks'):
            count = len(asks)
            sellers = 'seller' if count == 1 else 'sellers'
            return [
                f'Comparable asks: {count} {sellers} (SC/NL/PC/RotW; not an estimate)',
                *[f'  {row["ask_ist"]:g} Ist — observed {row["observed_at"][:10]}' for row in asks],
            ]
        return [unavailable_price_line(result, estimate)]
    lines = [f'Price: ~{value:g} Ist (SC/NL/PC/RotW asks; {estimate["confidence"]} confidence)']
    if estimate.get('low_ist') is not None and estimate.get('high_ist') is not None:
        lines.append(
            f'  Asking range: {estimate["low_ist"]:g}-{estimate["high_ist"]:g} Ist; '
            f'{estimate.get("sellers", "?")} sellers.'
        )
    lines.append('  Observed: ' + (', '.join(estimate['dates']) or 'date unknown'))
    return lines


def assessment_lines(result):
    from inventory_tracking.appraisal.build_use_summary import build_use_summary

    return list(build_use_summary(result.get('assessment', {}).get('roles', []), result.get('guide_demand')).lines)


def full_assessment_lines(result):
    from inventory_tracking.appraisal.role_groups import display_groups, shared_details

    roles = [r for r in result.get('assessment', {}).get('roles', []) if r['status'] in ('matched', 'partial')]
    if not roles:
        return []
    groups = display_groups(roles)
    shared = shared_details(groups)
    lines = ['Build use:']
    if shared['missing'] or shared['improvements']:
        lines.append('  For all listed uses:')
        lines.extend('    ' + line for line in shared['missing'])
        if shared['improvements']:
            lines.append('    Better rolls: ' + '; '.join(shared['improvements']))
    for group in groups:
        role = group['role']
        status = 'possible fit' if role['status'] == 'partial' else 'matches item requirements'
        variants = ', '.join(group['variants'])
        lines.append(f'  {build_name(role["build"])} / {variants} / {role["side"]}: {status}')
        lines.extend('    ' + line for line in group['missing'] if line not in shared['missing'])
        improvements = [line for line in group['improvements'] if line not in shared['improvements']]
        if improvements:
            lines.append('    Better rolls: ' + '; '.join(improvements))
        if group['alternatives']:
            lines.append('    Alternatives: ' + '; '.join(group['alternatives']))
    return lines


def leveling_lines(result):
    lines = []
    for use in result.get('assessment', {}).get('leveling', []):
        classes = ', '.join(use['classes']) if len(use['classes']) < 8 else 'all classes'
        context = f'{use["side"]}, {classes}, {", ".join(use["archetypes"])}'
        level = f'; equip level {use["required_level"]}' if use.get('required_level') is not None else ''
        lines.append(f'Leveling: {use["tier"]} — {context}{level}. {use["reason"]}')
        for shortfall in use.get('requirements_fit', {}).get('shortfalls', []):
            lines.append('  Needs: ' + shortfall)
        for condition in use['conditions']:
            lines.append('  Needs: ' + condition)
    return lines


def tier_lines(result):
    tier = result.get('assessment', {}).get('trade_tier', {})
    if tier.get('status') not in ('reviewed', 'conditional', 'market_supported'):
        return []
    label = tier['tier'] or 'conditional: ' + ' / '.join(tier['possible_tiers'])
    line = f'Trade tier: {label} (cached asks, {tier["source"]["date"]})'
    if tier.get('intrinsic_rolls'):
        line += ' — before socket additions'
    if tier.get('tier') and tier.get('reasons'):
        line += ' — ' + '; '.join(tier['reasons'])
    return [line]


def price_lines(result):
    lines = current_price_lines(result)
    from inventory_tracking.appraisal.prepared_prices import prepared_price_lines

    lines.extend(prepared_price_lines(result))
    return lines
