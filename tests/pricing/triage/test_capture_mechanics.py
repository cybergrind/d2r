from pricing.triage.adapters import from_drop


def observation(code, **fields):
    return {
        'item': {'name': 'Example', 'base_code': code, 'rarity': 'unique', 'affixes': [], **fields},
        'source': {},
        'decoded_stats': [],
    }


def test_old_jewelry_capture_uses_verified_nonsocketable_nonethereal_mechanics():
    item = from_drop(observation('rin'))
    assert item['ethereal'] is False
    assert item['sockets'] == 0
    assert item['socket_contents'] == 'empty'


def test_missing_armor_flags_are_not_inferred_from_no_listed_ethereal_sellers():
    item = from_drop(observation('uap'))
    assert item['ethereal'] is None
    assert item['sockets'] is None
    assert item['socket_contents'] is None


def test_explicit_capture_flags_are_not_silently_overwritten():
    item = from_drop(observation('rin', ethereal=True, sockets=1, socket_contents='filled'))
    assert item['ethereal'] is True
    assert item['sockets'] == 1
    assert item['socket_contents'] == 'filled'
