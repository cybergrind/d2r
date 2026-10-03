"""Bulk offline draft of deciding named rolls, with held-out asking-price errors."""

import json
import re
from collections import defaultdict
from itertools import product

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.adapters.market_projection import market_properties
from pricing.triage.bands import eligible, latest_rows
from pricing.triage.build import ROOT, market_rows
from pricing.triage.roll_comparisons import deciding_stats, leave_one_out


SKILL_LABEL = re.compile(r'^\+\{\{value\}\} to (.+) \([^()]+ Only\)$')


def ranges_for(definition, rows, game):
    mapping = {f'{key}:0': stat['property_id'] for key, stat in game['stats'].items() if stat.get('property_id')}
    mapping.update(market_properties())
    mapping.update({'17:0': '510', '18:0': '510'})
    # A raw label supplies missing market IDs for class-only skills; never alias
    # staffmods to oskills, charged skills, auras or skill tabs.
    skills = {v['name']: key for key, v in game['skills'].items()}
    for row in rows:
        for prop in row.get('raw_properties', []):
            match = SKILL_LABEL.fullmatch(prop.get('property', ''))
            if match and match[1] in skills:
                mapping[f'107:{skills[match[1]]}'] = str(prop['property_id'])
    ranges, missing = {}, []
    for key, spec in definition.get('roll_ranges', {}).items():
        if spec['min'] >= spec['max']:
            continue
        native = key if ':' in key else key + ':0'
        prop = mapping.get(native)
        if prop is None:
            missing.append(native)
            continue
        if native.startswith('107:'):
            label = game['skills'][native.split(':')[1]]['name']
        else:
            label = game['stats'].get(native.split(':')[0], {}).get('label') or spec['property']
            label = label.replace('{{value}}', '').strip('+ %').strip()
        value = {k: spec[k] for k in ('min', 'max', 'better')}
        value.update(label=label, native_key=native)
        # Only combine the two equal enhanced-damage halves; ambiguous projections
        # are retained as omissions rather than selecting one arbitrary range.
        if prop in ranges and any(ranges[prop][k] != value[k] for k in ('min', 'max', 'better')):
            missing.append(native)
            ranges.pop(prop)
        else:
            ranges[prop] = value
    return ranges, missing


def analyze(rows, definitions, game):
    groups = defaultdict(list)
    for row in latest_rows(rows):
        if eligible(row) and row['category'] in ('uniques', 'sets'):
            groups[row['name'].casefold()].append(row)
    reports = []
    for definition in definitions:
        members = groups.get(definition['name'].casefold(), [])
        if not members:
            continue
        ranges, missing = ranges_for(definition, members, game)
        # Never calibrate an ethereal/non-ethereal mixture. Unknown remains its
        # own research group and cannot price a known non-ethereal drop.
        for ethereal, contents in product((False, True, None), ('empty', 'unknown', None)):
            cohort = [
                r
                for r in members
                if r.get('ethereal') is ethereal and r.get('socket_contents') == contents and r['amount'] == 1
            ]
            deciding = deciding_stats(cohort, ranges)
            if not deciding:
                continue
            reports.append(
                {
                    'name': definition['name'],
                    'ethereal': ethereal,
                    'socket_contents': contents,
                    'deciding': deciding,
                    'unmapped_variable_stats': missing,
                    'validation': leave_one_out(cohort, deciding, ranges=ranges),
                }
            )
    return reports


def main():
    from pricing.knowledge.refresh import atomic_json

    rows, _ = market_rows()
    definitions = json.loads((ROOT / 'pricing/data/appraisal-definitions.json').read_text())['rows']
    reports = analyze(rows, definitions, metadata())
    path = ROOT / 'inventory_tracking/corpus/data/score-roll-models.json'
    atomic_json(path, {'models': reports, 'live_enabled': False})
    print(
        json.dumps(
            {
                'drafts': len(reports),
                'beat_name_median': sum(r['validation']['use_roll_model'] for r in reports),
                'report': str(path.relative_to(ROOT)),
                'live_enabled': False,
            }
        )
    )


if __name__ == '__main__':
    main()
