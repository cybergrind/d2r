"""One linked jewel must prove all reviewed modifiers together."""

import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.planner_jewel_endorsement import validate_jewel_socket
from pricing.knowledge.assessment.maintenance.table_equivalence import _read
from pricing.knowledge.builds import decode_planner
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import ROOT, pin, read


@pytest.fixture(scope='module')
def records():
    planner = decode_planner(read('pricing/raw/mr/planners/s10106pr.json'))
    tables = {
        k: pin('third-parties/d2data/json/' + name + '.json')
        for k, name in (('mp', 'magicprefix'), ('ms', 'magicsuffix'))
    }
    evidence = {
        'jewel': {
            'item_id': '55',
            'expected_item': planner['items']['55'],
            'affix_definitions': tables,
            'stat_definitions': pin('third-parties/d2data/json/itemstatcost.json'),
        }
    }
    role = {
        'source': {
            'corroborating': [
                {**tables[k], 'locator': '/' + i}
                for k, i in (('mp', '336'), ('mp', '376'), ('mp', '200'), ('ms', '268'))
            ]
        },
        'must': {
            'all': [
                {'op': 'fact_eq', 'field': 'sockets', 'value': 1},
                {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'filled'},
                {
                    'op': 'socket_jewel_matches',
                    'count': 1,
                    'stats': {'99:0': 7, '39:0': 21, '41:0': 5, '43:0': 5, '45:0': 5, '114:0': 7},
                },
            ]
        },
    }
    return evidence, role, planner['items']['1'], planner


@pytest.mark.parametrize(
    'change',
    [
        'retained',
        'wrong-child',
        'split-sockets',
        'boolean-count',
        'changed-child',
        'missing-affix-pin',
        'partial-rule',
        'optional-rule',
        'wrong-stat-table',
    ],
)
def test_linked_jewel_native_evidence_is_required(records, change):
    evidence, role, item, planner = deepcopy(records)
    if change == 'wrong-child':
        item['socketedItems'] = [30]
    elif change == 'split-sockets':
        item['sockets'] = 2
        item['socketedItems'] = [55, 30]
    elif change == 'boolean-count':
        item['sockets'] = True
    elif change == 'changed-child':
        evidence['jewel']['expected_item'] = {**evidence['jewel']['expected_item'], 'name': 'Other Jewel'}
    elif change == 'missing-affix-pin':
        role['source']['corroborating'].pop()
    elif change == 'partial-rule':
        role['must']['all'][-1]['stats'].pop('45:0')
    elif change == 'optional-rule':
        role['must']['all'][-1] = {
            'any': [role['must']['all'][-1], {'op': 'fact_eq', 'field': 'identified', 'value': True}]
        }
    elif change == 'wrong-stat-table':
        evidence['jewel']['stat_definitions'] = pin('third-parties/d2data/json/skills.json')
    args = (evidence, role, item, planner, lambda ref: json.loads(_read(ROOT, ref)))
    if change == 'retained':
        validate_jewel_socket(*args)
    else:
        with pytest.raises(ValueError, match='jewel'):
            validate_jewel_socket(*args)
