"""Bulk offline draft of deciding named rolls, with held-out asking-price errors."""

import json
import re
from collections import defaultdict

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.adapters.market_projection import market_properties
from pricing.triage.adapters import expanded_properties
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
    ranges, missing, ambiguous = {}, [], set()
    for key, spec in definition.get('roll_ranges', {}).items():
        if spec['min'] >= spec['max']:
            continue
        native = key if ':' in key else key + ':0'
        prop = '441' if spec.get('property') == 'res-all' else mapping.get(native)
        if prop is None:
            missing.append(native)
            continue
        if prop == '441':
            label = 'All Resistances'
        elif native.startswith('107:'):
            label = game['skills'][native.split(':')[1]]['name']
        else:
            label = game['stats'].get(native.split(':')[0], {}).get('label') or spec['property']
            label = label.replace('{{value}}', '').strip('+ %').strip()
        value = {k: spec[k] for k in ('min', 'max', 'better')}
        value.update(label=label, native_key=native)
        # Only combine the two equal enhanced-damage halves; ambiguous projections
        # are retained as omissions rather than selecting one arbitrary range.
        if prop in ambiguous:
            missing.append(native)
            continue
        if prop in ranges and any(ranges[prop][k] != value[k] for k in ('min', 'max', 'better')):
            missing.append(native)
            ranges.pop(prop)
            ambiguous.add(prop)
        else:
            ranges[prop] = value
    return ranges, missing


def analyze(rows, definitions, game):
    groups = defaultdict(list)
    for row in latest_rows(rows):
        if eligible(row) and row['category'] in ('uniques', 'sets'):
            groups[row['name'].casefold()].append(row | {'properties': expanded_properties(row.get('properties', {}))})
    reports = []
    for definition in definitions:
        members = groups.get(definition['name'].casefold(), [])
        if not members:
            continue
        ranges, missing = ranges_for(definition, members, game)
        # Never calibrate an ethereal/non-ethereal mixture. Unknown remains its
        # own research group and cannot price a known non-ethereal drop.
        cohorts = defaultdict(list)
        for row in members:
            if row['amount'] == 1 and row.get('socket_contents') in ('empty', 'unknown', None):
                cohorts[
                    row.get('ethereal'), row.get('socket_contents'), row.get('sockets'), row.get('base_code')
                ].append(row)
        for (ethereal, contents, sockets, base_code), cohort in cohorts.items():
            cohort_ranges = dict(ranges)
            defense = definition.get('base_defense_range')
            if (
                defense
                and defense['min'] < defense['max']
                and ethereal is False
                and contents == 'empty'
                and definition.get('base_code')
                and all(r.get('base_code') == definition['base_code'] for r in cohort)
            ):
                cohort_ranges['1855'] = {
                    'min': defense['min'],
                    'max': defense['max'],
                    'better': 'higher',
                    'label': 'Defense',
                    'native_key': '31:0',
                    'base_code': definition['base_code'],
                }
            if not cohort or not cohort_ranges:
                continue
            deciding = deciding_stats(cohort, cohort_ranges, minimum_sellers=1)
            reports.append(
                {
                    'name': definition['name'],
                    'ethereal': ethereal,
                    'socket_contents': contents,
                    'sockets': sockets,
                    'base_code': base_code,
                    'deciding': deciding,
                    'unmapped_variable_stats': missing,
                    'validation': leave_one_out(cohort, deciding, ranges=cohort_ranges, minimum_sellers=1),
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
