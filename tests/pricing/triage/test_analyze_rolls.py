from pricing.triage.analyze_rolls import analyze
from pricing.triage.compiled_rolls import compile_model, lookup
from tests.pricing.triage.test_bands import listing


GAME = {'stats': {}, 'skills': {}}


def test_unmodified_defense_range_drives_comparisons_for_original_nonethereal_base():
    definition = {'name': 'Example', 'base_code': 'test-base', 'base_defense_range': {'min': 98, 'max': 141}}
    rows = [listing(i, 1, ethereal=False, sockets=0, socket_contents='empty', base_code='test-base') for i in range(4)]
    for row in rows:
        row['properties']['1855'] = 141
    reports = analyze(rows, [definition], GAME)
    assert len(reports) == 1
    assert reports[0]['deciding']['1855']['min'] == 98
    model = compile_model(reports[0], rows)
    item = {
        'category': 'uniques',
        'name': 'Example',
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'base_code': 'test-base',
        'properties': {'1855': 100},
    }
    assert lookup(item, [model], keep_ist=0.25)['verdict'] == 'check'
    wrong_base = lookup(item | {'base_code': 'upgraded'}, [model], keep_ist=0.25)
    assert wrong_base is None  # An original-base model cannot assess an upgraded base.
    for change in ({'ethereal': True}, {'base_code': 'upgraded'}, {'base_code': None}):
        assert not analyze([r | change for r in rows], [definition], GAME)


def test_all_resistance_listing_and_drop_use_one_shared_deciding_property():
    definition = {
        'name': 'Example',
        'roll_ranges': {
            str(stat): {'min': 30, 'max': 50, 'better': 'higher', 'property': 'res-all'} for stat in (39, 41, 43, 45)
        },
    }
    rows = [listing(i, 1, ethereal=False, sockets=0, socket_contents='empty') for i in range(4)]
    for row in rows:
        row['properties']['441'] = 50
    reports = analyze(rows, [definition], GAME)
    assert set(reports[0]['deciding']) == {'441'}
    model = compile_model(reports[0], rows)
    item = {
        'category': 'uniques',
        'name': 'Example',
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': {'441': 35},
    }
    assert lookup(item, [model], keep_ist=0.25)['verdict'] == 'check'
    # Independent resist rolls must not be collapsed into all resistance.
    independent = {
        'name': 'Example',
        'roll_ranges': {
            k: v | {'property': 'res-fire' if k == '39' else 'res-cold'} for k, v in definition['roll_ranges'].items()
        },
    }
    assert all('441' not in r['deciding'] for r in analyze(rows, [independent], GAME))


def test_conflicting_projection_is_not_restored_by_a_later_component():
    from pricing.triage.analyze_rolls import ranges_for

    definition = {
        'roll_ranges': {
            '39': {'min': 10, 'max': 20, 'better': 'higher', 'property': 'res-all'},
            '41': {'min': 30, 'max': 40, 'better': 'higher', 'property': 'res-all'},
            '43': {'min': 10, 'max': 20, 'better': 'higher', 'property': 'res-all'},
        }
    }
    ranges, missing = ranges_for(definition, [], GAME)
    assert '441' not in ranges
    assert '43:0' in missing
