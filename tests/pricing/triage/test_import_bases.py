from pricing.triage.engine import matches
from pricing.triage.import_bases import compile_bucket


def test_superior_bucket_preserves_ed_socket_ethereal_and_empty_requirements():
    rule = compile_bucket('Archon Plate', '3os/noneth/superior/15ed')
    item = {
        'category': 'base',
        'name': 'Archon Plate',
        'rarity': 'superior',
        'sockets': 3,
        'ethereal': False,
        'empty_sockets': True,
        'base_ed': 15,
    }
    assert matches(item, rule)
    for changed in (
        {'base_ed': 14},
        {'base_ed': None},
        {'sockets': 4},
        {'ethereal': True},
        {'empty_sockets': False},
        {'empty_sockets': None},
        {'rarity': 'magic'},
    ):
        assert not matches(item | changed, rule)


def test_plain_superior_does_not_overlap_perfect_and_paladin_resists_are_required():
    plain = compile_bucket('Archon Plate', '3os/noneth/superior')
    item = {
        'category': 'base',
        'name': 'Archon Plate',
        'rarity': 'superior',
        'sockets': 3,
        'ethereal': False,
        'empty_sockets': True,
        'base_ed': 14,
    }
    assert matches(item, plain)
    assert not matches(item | {'base_ed': 15}, plain)
    shield = compile_bucket('Sacred Targe', '4os/noneth/normal/res40-44')
    item.update(name='Sacred Targe', rarity='normal', sockets=4, base_ed=0)
    assert not matches(item, shield)
    assert matches(item | {'properties': {'441': 42}}, shield)
    assert not matches(item | {'properties': {'441': 45}}, shield)


def test_ambiguous_affixed_and_filled_buckets_are_not_empty_base_rules():
    for key in (
        '4os/noneth/normal/affixed',
        '4os/noneth/normal/filled',
        '4os/noneth/normal/res?',
        '4os/noneth/magic',
        '4os/noneth/unset',
        '4os/noneth/normal/unknown',
    ):
        assert compile_bucket('Example', key) is None


def test_listing_and_drop_base_facets_keep_unknown_contents_unknown():
    from pricing.triage.adapters import base_facets

    assert base_facets({}, 'normal', 0, None) == {'base_ed': 0, 'empty_sockets': True}
    assert base_facets({}, 'superior', 3, None) == {'base_ed': None, 'empty_sockets': None}
    assert base_facets({'425': 15}, 'superior', 3, []) == {'base_ed': 15, 'empty_sockets': True}
    assert base_facets({'510': 14}, 'superior', 3, ['rune']) == {'base_ed': 14, 'empty_sockets': False}


def test_clean_base_band_is_rebuilt_from_matching_scoped_sellers_only():
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import build_bands
    from pricing.triage.engine import assess
    from tests.pricing.triage.test_bands import listing

    rule = compile_bucket('Archon Plate', '3os/noneth/superior/15ed')
    policy = {
        'category': 'base',
        'require_bucket': True,
        'facets': ['rarity', 'ethereal', 'sockets', 'socket_contents'],
    }
    rows = [
        {
            **listing(i, 10),
            'category': 'base',
            'name': 'Archon Plate',
            'rarity': 'superior',
            'ethereal': False,
            'sockets': 3,
            'socket_contents': [],
            'properties': {**listing(i)['properties'], '425': 15},
        }
        for i in range(3)
    ]
    document = build_bands(rows, [], rules=[rule], policies=[policy])
    tables = {
        'bands': {(r['category'], r['name'].casefold(), r['bucket']): r for r in document['bands']},
        'rules': {'keep_ist': 0.25, 'rows': [rule], 'policies': [policy]},
        'own': {'rows': []},
    }
    item = from_listing(rows[0])
    assert assess(item, tables)['verdict'] == 'slow'
    for changed in ({'base_ed': 14}, {'sockets': 4}, {'empty_sockets': False}):
        result = assess(item | changed, tables)
        assert result['verdict'] == 'vendor'
        assert result['band'] is None


def test_normalized_empty_socket_marker_is_not_a_filled_socket():
    from pricing.triage.adapters import base_facets

    assert base_facets({}, 'normal', 4, 'empty')['empty_sockets'] is True
    assert base_facets({}, 'normal', 4, 'unknown')['empty_sockets'] is None
