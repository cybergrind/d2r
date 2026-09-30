"""Pure bounded build-use presentation; matching and full evidence remain separate."""

import json
from dataclasses import dataclass

from inventory_tracking.appraisal.sections import build_name
from pricing.knowledge.assessment.domain.facts import freeze


@dataclass(frozen=True)
class BuildUseSummary:
    lines: tuple[str, ...]
    clusters: tuple
    details: tuple


def _mercenary_trace_signature(trace):
    """Unknown owner class distinguishes build names, not equivalent mercenary gear.

    This copy is only a grouping key. Full traces, match states, base requirements
    and actual loadout restrictions remain unchanged in the report details.
    """
    if not isinstance(trace, dict):
        return trace
    result = dict(trace)
    if 'children' in trace:
        result['children'] = [_mercenary_trace_signature(child) for child in trace['children']]
    if (
        trace.get('truth') == 'unknown'
        and trace.get('observed') is None
        and isinstance(trace.get('expected'), str)
        and trace.get('reason') == f'player_class: {trace["expected"]}'
        and not trace.get('children')
    ):
        result.update(reason='player_class', expected=None)
    return result


def _preparation_trace(trace):
    if not isinstance(trace, dict):
        return False
    reason = trace.get('reason', '')
    return (
        reason.startswith(('base_code:', 'sockets:', 'socket_contents:'))
        or reason == 'Exact linked socket rune contents'
        or reason.endswith('socket jewel(s) match all required stats')
        or any(_preparation_trace(child) for child in trace.get('children', ()))
    )


def _equipment_trace(trace):
    """Equipment conditions remain actionable inside negation and alternatives."""
    if not isinstance(trace, dict):
        return False
    return trace.get('reason', '').startswith(('player_items:', 'mercenary_items:', 'player_swap_items:')) or any(
        _equipment_trace(child) for child in trace.get('children', ())
    )


def companion_lines(role):
    """Expose companion requirements and missing item preparation for visible uses."""
    if role['status'] not in {'matched', 'partial'}:
        return ()
    grouped = {'true': [], 'false': [], 'unknown': []}
    for dependency in role.get('dependencies', ()):
        needs_preparation = dependency.get('status') in {'false', 'unknown'} and _preparation_trace(
            dependency.get('trace')
        )
        if needs_preparation or _equipment_trace(dependency.get('trace')):
            labels = grouped.get(dependency.get('status'))
            if labels is not None and dependency['label'] not in labels:
                labels.append(dependency['label'])
    headings = {'true': 'Setup', 'false': 'Needs', 'unknown': 'Check'}
    return tuple(f'    {headings[state]}: ' + '; '.join(labels) for state, labels in grouped.items() if labels)


def socket_plan_lines(role):
    """Expose explicit reviewed socket-plan notes once base predicates are satisfied.

    Older role records keep these plans in missing conditions rather than the
    single-payload socket_requirement field. Do not infer instructions from
    arbitrary advisory prose or promote an unknown base to a preparation target.
    """
    if role['status'] not in {'matched', 'partial'} or (role.get('rule_trace') or {}).get('truth') != 'true':
        return ()
    prefix = 'The sockets still need '
    payloads = []
    for note in role.get('missing', ()):
        if note.startswith(prefix):
            payload = note.removeprefix(prefix).removesuffix('; verify their properties before investing.')
            payload = payload.removesuffix(' specified for this build').removeprefix('the ')
            if payload and payload not in payloads:
                payloads.append(payload)
    return tuple('    Needs: ' + payload for payload in payloads)


def dependency_rank(role):
    """Advisory caveats must not tie a usable setup with known wrong equipment."""
    ranks = {'true': 0, 'unknown': 1, 'false': 2}
    return max((ranks.get(d.get('status'), 1) for d in role.get('dependencies', ())), default=0)


def build_use_summary(roles, demand=None):
    unique = {}
    for role in roles:
        if role['id'] in unique and role != unique[role['id']]:
            raise ValueError(f'Conflicting role result: {role["id"]}')
        unique[role['id']] = role
    ordered = sorted(unique.values(), key=lambda r: r['id'])
    if not ordered:
        return BuildUseSummary((), (), ())
    presentation = (demand or {}).get('role_presentation', {})

    def progression(role):
        return presentation.get(role['id'], {}).get('progression', role['variant'])

    groups = {}
    for role in ordered:
        signature = {
            k: role.get(k)
            for k in (
                'side',
                'slot',
                'role',
                'status',
                'dependencies',
                'alternatives',
                'missing',
                'failed',
                'equipment',
                'socket_requirement',
                'rule_trace',
                'skill_trace',
            )
        }
        if role['side'] == 'merc':
            signature['rule_trace'] = _mercenary_trace_signature(role.get('rule_trace'))
        signature['progression'] = progression(role)
        key = json.dumps(signature, sort_keys=True)
        groups.setdefault(key, []).append(role)
    rank = {'matched': 0, 'partial': 1, 'unknown': 2, 'failed': 3}
    stage_rank = {'Starter': 0, 'Budget': 1, 'Endgame': 2}
    clusters = sorted(
        groups.values(),
        key=lambda g: (rank[g[0]['status']], dependency_rank(g[0]), stage_rank.get(progression(g[0]), 3), g[0]['id']),
    )
    heading = 'Build use'
    if demand:
        qualifier = '' if demand.get('complete') else 'at least '
        if demand.get('scope') == 'matched_patterns':
            heading += ' · matching configurations'
        heading += f' · {demand["grade"]} · {qualifier}{demand["distinct_builds"]} builds'
    lines = [heading]
    counts = {s: len({r['build'] for r in ordered if r['status'] == s}) for s in rank}
    lines.append(f'  This item: {counts["matched"]} confirmed / {counts["partial"]} conditional builds')
    remaining_labels = 3
    visible = clusters[:3]
    shown_companions = set()
    for index, group in enumerate(visible):
        first = group[0]
        builds = sorted({r['build'] for r in group})
        reserved = len(visible) - index - 1
        names = builds[: remaining_labels - reserved]
        remaining_labels -= len(names)
        labels = ', '.join(build_name(name) for name in names)
        omitted = len(builds) - len(names)
        if omitted:
            labels += f' · +{omitted} more'
        state = {'matched': 'confirmed', 'partial': 'conditional', 'unknown': 'unknown', 'failed': 'failed'}[
            first['status']
        ]
        lines.append(f'  {first["side"]} · {first["role"]} · {progression(first)} · {state}: {labels.lstrip(" ·")}')
        for line in (*companion_lines(first), *socket_plan_lines(first)):
            if line not in shown_companions:
                lines.append(line)
                shown_companions.add(line)
    targets = sorted(
        {
            p['label']
            for r in ordered
            if r['status'] in {'matched', 'partial'}
            for p in r.get('preferences', [])
            if p['status'] == 'false'
        }
    )
    if targets:
        lines.append('  Targets: ' + '; '.join(targets))
    socket_items = sorted(
        {
            requirement['item'].removesuffix(' Rune')
            for role in ordered
            if role['status'] in {'matched', 'partial'}
            and (requirement := role.get('socket_requirement'))
            and requirement.get('applicable') is True
            and requirement.get('confirmed') is False
        }
    )
    if socket_items:
        lines.append('  Socket requirement: ' + '; '.join(socket_items) + ' (not confirmed)')
    failed = sum(r['status'] == 'failed' for r in ordered)
    unknown = sum(r['status'] == 'unknown' for r in ordered)
    if failed or unknown:
        reasons = sorted(
            {
                reason
                for role in ordered
                for reason in role.get('failed', [])
                if reason != 'Required role properties are not satisfied.'
            }
        )
        if reasons:
            extra = f'; +{len(reasons) - 1} more restrictions' if len(reasons) > 1 else ''
            lines.append(f'  {reasons[0]}{extra} ({failed} failed / {unknown} unknown uses; see full details)')
    elif not shown_companions and any(r.get('missing') for r in ordered):
        lines.append('  Conditional on the listed base/loadout requirements; see full details')
    omitted = max(0, len(clusters) - 3)
    detail = f'  Details: {len(ordered)} uses'
    if omitted:
        detail += f'; {omitted} more groups'
    lines.append(detail)
    # Broad family candidates with no applicable use should not clutter the overlay.
    # Preserve every failed evaluation for the detailed view and coverage audits.
    if not demand and all(role['status'] == 'failed' for role in ordered):
        lines = []
    return BuildUseSummary(
        tuple(lines), tuple(tuple(freeze(r) for r in g) for g in clusters), tuple(freeze(r) for r in ordered)
    )


def detail_lines(summary):
    """Full terminal view, including uses omitted or failed in the compact view."""
    lines = ['Build use details:']
    for role in summary.details:
        lines.append(f'  {build_name(role["build"])} / {role["variant"]} / {role["side"]}: {role["status"]}')
        lines.append('    Role: ' + role['role'])
        dependency_lines = []
        for dependency in role.get('dependencies', ()):
            heading = {'true': 'Setup', 'false': 'Needs', 'unknown': 'Check'}.get(dependency.get('status'), 'Check')
            dependency_lines.append(f'    {heading}: {dependency["label"]}')
        lines.extend(dict.fromkeys(dependency_lines))
        for key, label in [('failed', 'Failed'), ('missing', 'Needs'), ('alternatives', 'Alternatives')]:
            for text in dict.fromkeys(role.get(key, ())):
                line = f'    {label}: {text}'
                if line not in dependency_lines:
                    lines.append(line)
        for preference in role.get('preferences', ()):
            lines.append(f'    Preference: {preference["label"]} ({preference["status"]})')
        source = role.get('source', {})
        if source:
            lines.append(f'    Source: {source.get("path", "")} {source.get("locator", "")}')
    return tuple(lines)


def main(argv=None):
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description='Render build uses from a saved appraisal record.')
    parser.add_argument('record', type=Path)
    parser.add_argument('--full', action='store_true', help='Show all uses, conditions and source locators')
    args = parser.parse_args(argv)
    document = json.loads(args.record.read_text())
    result = document.get('result', document)
    summary = build_use_summary(result.get('assessment', {}).get('roles', []), result.get('guide_demand'))
    print('\n'.join(detail_lines(summary) if args.full else summary.lines))


if __name__ == '__main__':
    main()
