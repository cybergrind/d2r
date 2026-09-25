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
                'rule_trace',
                'skill_trace',
            )
        }
        signature['progression'] = progression(role)
        key = json.dumps(signature, sort_keys=True)
        groups.setdefault(key, []).append(role)
    rank = {'matched': 0, 'partial': 1, 'unknown': 2, 'failed': 3}
    stage_rank = {'Starter': 0, 'Budget': 1, 'Endgame': 2}
    clusters = sorted(
        groups.values(), key=lambda g: (rank[g[0]['status']], stage_rank.get(progression(g[0]), 3), g[0]['id'])
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
    for group in clusters[:3]:
        first = group[0]
        builds = sorted({r['build'] for r in group})
        names = builds[:remaining_labels]
        remaining_labels -= len(names)
        labels = ', '.join(build_name(name) for name in names)
        omitted = len(builds) - len(names)
        if omitted:
            labels += f' · +{omitted} more'
        state = {'matched': 'confirmed', 'partial': 'conditional', 'unknown': 'unknown', 'failed': 'failed'}[
            first['status']
        ]
        lines.append(f'  {first["side"]} · {first["role"]} · {progression(first)} · {state}: {labels.lstrip(" ·")}')
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
        lines.append('  Better rolls: ' + '; '.join(targets))
    failed = sum(r['status'] == 'failed' for r in ordered)
    unknown = sum(r['status'] == 'unknown' for r in ordered)
    if failed or unknown:
        reasons = sorted({reason for role in ordered for reason in role.get('failed', [])})
        reason = reasons[0] if reasons else 'Requirements unconfirmed'
        extra = f'; +{len(reasons) - 1} more restrictions' if len(reasons) > 1 else ''
        lines.append(f'  {reason}{extra} ({failed} failed / {unknown} unknown uses; see full details)')
    elif any(r.get('missing') for r in ordered):
        lines.append('  Conditional on the listed base/loadout requirements; see full details')
    omitted = max(0, len(clusters) - 3)
    lines.append(f'  Details: {len(ordered)} uses; {omitted} more groups')
    return BuildUseSummary(
        tuple(lines), tuple(tuple(freeze(r) for r in g) for g in clusters), tuple(freeze(r) for r in ordered)
    )


def detail_lines(summary):
    """Full terminal view, including uses omitted or failed in the compact view."""
    lines = ['Build use details:']
    for role in summary.details:
        lines.append(f'  {build_name(role["build"])} / {role["variant"]} / {role["side"]}: {role["status"]}')
        lines.append('    Role: ' + role['role'])
        for key, label in [('failed', 'Failed'), ('missing', 'Needs'), ('alternatives', 'Alternatives')]:
            for text in dict.fromkeys(role.get(key, ())):
                lines.append(f'    {label}: {text}')
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
