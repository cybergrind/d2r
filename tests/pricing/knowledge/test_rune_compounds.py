import json
from pathlib import Path


def test_tal_poison_is_compiled_as_separate_native_components():
    from pricing.knowledge.rune_effects import socket_compound_effects

    root = Path(__file__).resolve().parents[3]
    gems = json.loads((root / 'third-parties/d2data/json/gems.json').read_text())
    gems = {r['code']: r for r in gems.values() if r.get('code')}
    properties = json.loads((root / 'third-parties/d2data/json/properties.json').read_text())
    properties = {r['code']: r for r in properties.values() if r.get('code')}
    tal = next(code for code, row in gems.items() if row.get('name') == 'Tal Rune')
    result = socket_compound_effects([tal], gems, properties)
    assert result['weapon'] == [
        {
            'kind': 'poison',
            'rune': tal,
            'slot': 1,
            'minimum_rate_raw': 154,
            'maximum_rate_raw': 154,
            'duration_frames': 125,
            'source_count': 1,
        }
    ]
    assert result['shield'] == []
    assert result['armor'] == []
    # Keep repeated sources distinct: adding their durations would be incorrect.
    assert len(socket_compound_effects([tal, tal], gems, properties)['weapon']) == 2
    changed = {**properties, 'dmg-pois': {**properties['dmg-pois'], 'func3': 1}}
    assert socket_compound_effects([tal], gems, changed)['weapon'] == []


def test_ral_and_ort_preserve_both_damage_endpoints_without_poison_units():
    from pricing.knowledge.rune_effects import socket_compound_effects

    root = Path(__file__).resolve().parents[3]
    gems = {
        r['code']: r
        for r in json.loads((root / 'third-parties/d2data/json/gems.json').read_text()).values()
        if r.get('code')
    }
    properties = {
        r['code']: r
        for r in json.loads((root / 'third-parties/d2data/json/properties.json').read_text()).values()
        if r.get('code')
    }
    for name, kind, minimum, maximum in [('Ral Rune', 'fire', 5, 30), ('Ort Rune', 'lightning', 1, 50)]:
        code = next(code for code, row in gems.items() if row.get('name') == name)
        effects = socket_compound_effects([code], gems, properties)
        assert effects['weapon'] == [
            {'kind': kind, 'rune': code, 'slot': 1, 'minimum_damage': minimum, 'maximum_damage': maximum}
        ]
        assert effects['shield'] == []


def test_thul_compiles_cold_damage_and_frame_duration():
    from pricing.knowledge.rune_effects import socket_compound_effects

    root = Path(__file__).resolve().parents[3]
    gems = {
        r['code']: r
        for r in json.loads((root / 'third-parties/d2data/json/gems.json').read_text()).values()
        if r.get('code')
    }
    properties = {
        r['code']: r
        for r in json.loads((root / 'third-parties/d2data/json/properties.json').read_text()).values()
        if r.get('code')
    }
    code = next(code for code, row in gems.items() if row.get('name') == 'Thul Rune')
    assert socket_compound_effects([code], gems, properties)['weapon'] == [
        {
            'kind': 'cold',
            'rune': code,
            'slot': 1,
            'minimum_damage': 3,
            'maximum_damage': 14,
            'duration_frames': 75,
        }
    ]


def test_physical_rune_mirrors_keep_exact_native_function_and_repeat_count():
    from pricing.knowledge.rune_effects import socket_compound_effects

    root = Path(__file__).resolve().parents[3]
    gems = {
        r['code']: r
        for r in json.loads((root / 'third-parties/d2data/json/gems.json').read_text()).values()
        if r.get('code')
    }
    properties = json.loads((root / 'third-parties/d2data/json/properties.json').read_text())
    for name, stat, property_code in [('Sol Rune', 159, 'dmg-min'), ('Ith Rune', 160, 'dmg-max')]:
        code = next(k for k, v in gems.items() if v['name'] == name)
        effects = socket_compound_effects([code, code], gems, properties)
        assert (
            effects['weapon'] == [{'kind': 'physical_mirror', 'rune': code, 'slot': 1, 'stat_id': stat, 'value': 9}] * 2
        )
        assert not any(e['kind'] == 'physical_mirror' for e in effects['shield'])
        changed = {**properties, property_code: {**properties[property_code], 'func1': 1}}
        assert socket_compound_effects([code], gems, changed)['weapon'] == []
