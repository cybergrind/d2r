import json
import re
from collections import Counter
from pathlib import Path

import pytest

from inventory_tracking.items.metadata import decode_stats, metadata
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.mechanics.triggers import MARKET_FIELDS, named_trigger_properties
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'expected'),
    [
        ("The Reaper's Toll", {'640': 33}),
        ("Dracul's Grasp", {'767': 5}),
        ('Stormlash', {'715': 15, '728': 20}),
        ('Wisp Projector', {'731': 10}),
        ('Lacerator', {'543': 33}),
        ("Defender's Bile", {'808': 1}),
        ("Guardian's Thunder", {}),
        ("Protector's Frost", {}),
        ("Defender's Fire", {'700': 1}),
        ("Protector's Stone", {'763': 1}),
        ("Guardian's Light", {'1883': 1}),
    ],
)
def test_fixed_named_procs_project_chance_for_the_exact_event(name, expected):
    definition = catalog().named['unique', name]
    raw = [
        {'id': s['stat_id'], 'layer': s['skill_id'] * 64 + s['level'], 'raw': s['chance']}
        for s in definition['fixed_triggers']
    ]
    assert raw  # An omitted definition is not a successful empty projection.
    decoded, _, _ = decode_stats(raw)
    base = next(b['name'] for b in metadata()['bases'].values() if b['code'] == definition['base_codes'][0])
    item = normalize(
        {
            'item': facts(base, 'unique', name).to_dict(),
            'decoded_stats': decoded,
            'source': {'stat_capture_complete': True},
        }
    )
    properties, consumed, gaps = named_trigger_properties(item, definition)
    assert not gaps
    assert properties == expected
    assert consumed == {f'{r["id"]}:{r["layer"]}' for r in raw}
    from dataclasses import replace

    assert named_trigger_properties(replace(item, stats={}), definition)[2]


def test_reviewed_trigger_map_matches_exact_offline_labels_and_unambiguous_native_skills():
    root = Path(__file__).resolve().parents[5]
    properties = json.loads((root / 'pricing/data/appraisal-properties.json').read_text())['properties']
    skills = {v['name']: int(k) for k, v in metadata()['skills'].items()}
    skill_counts = Counter(v['name'] for v in metadata()['skills'].values())
    events = {
        'on attack': 195,
        'on striking': 198,
        'when struck': 201,
        'when you Die': 197,
        'when you Level-Up': 199,
        'when you Kill an Enemy': 196,
    }
    expected = {}
    for prop, row in properties.items():
        for label in row['labels']:
            match = re.fullmatch(
                r'\{\{value\}\}% Chance to cast level \{\{level\}\} (.+) '
                r'(on attack|on striking|when struck|when you Die|when you Level-Up|when you Kill an Enemy)',
                label,
            )
            if match and match[1] in skills:
                assert skill_counts[match[1]] == 1
                key = (events[match[2]], skills[match[1]])
                assert key not in expected or expected[key] == prop
                expected[key] = prop
    assert expected == MARKET_FIELDS
    assert MARKET_FIELDS[198, 66] != MARKET_FIELDS[201, 66]


def test_fixed_unmapped_proc_is_verified_without_inventing_market_property():
    from dataclasses import replace

    from tests.pricing.knowledge.assessment.test_fortitude_coefficient import fortitude

    definition = catalog().runewords['Fortitude']
    item = fortitude()
    key = '201:3855'
    properties, consumed, gaps = named_trigger_properties(item, definition)
    assert not gaps
    assert properties == {}
    assert consumed == {key}
    for row in (
        {**item.stats[key], 'raw': 19},
        {**item.stats[key], 'value': 15},
        {**item.stats[key], 'unit': None},
        {**item.stats[key], 'market_property': '999999'},
        {},
    ):
        _, consumed, gaps = named_trigger_properties(replace(item, stats={**item.stats, key: row}), definition)
        assert key not in consumed
        assert gaps
