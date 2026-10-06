from pricing.triage.adapters import from_listing
from pricing.triage.engine import assess, prepare_tables
from tests.pricing.triage.test_bands import listing


def gloves():
    row = listing('seller', 22.842) | {'name': 'Chain Gloves', 'category': 'base', 'rarity': None}
    row['properties'].update({'456': 2, '457': 20, '428': 18, '463': 3, '425': 39})
    return row


def test_unreported_affixed_gloves_are_not_plain_bases_or_guessed_rares():
    item = from_listing(gloves())
    assert item['category'] == 'affixed_unknown'
    assert item['rarity'] is None
    assert item['family'] == 'glov'


def test_native_mods_and_unknown_socket_contents_do_not_prove_affixed_quality():
    for name, props in [('War Scepter', {'1077': 3}), ('Sacred Targe', {'441': 45}), ('Archon Plate', {'425': 15})]:
        row = listing('seller', 2) | {'name': name, 'category': 'base', 'rarity': None, 'sockets': None}
        row['properties'].update(props)
        assert from_listing(row)['category'] == 'base'
    assert from_listing(gloves() | {'rarity': 'rare'})['category'] == 'rare'


def test_unknown_rarity_can_match_reviewed_stats_but_never_borrow_a_price():
    rules = {
        'keep_ist': 0.25,
        'rows': [
            {
                'category': 'rare',
                'family': 'glov',
                'pattern': {'properties': {'456': {'min': 2}, '457': {'min': 20}}},
                'pattern_label': 'Javelin skills and attack speed',
            }
        ],
    }
    data = prepare_tables({'bands': []}, rules, {'rows': []})
    result = assess(from_listing(gloves()), data)
    assert result['verdict'] == 'check'
    assert 'rarity' in result['reason']
    assert result['decision_ist'] is None
    assert result['band'] is None
    assert result['reference_band'] is None
    weak = gloves()
    weak['properties']['457'] = 10
    assert assess(from_listing(weak), data)['verdict'] == 'vendor'


def test_socketed_unknown_item_cannot_treat_insert_effects_as_native_affixes():
    row = listing('seller', 2) | {'name': 'Archon Plate', 'category': 'base', 'rarity': None, 'sockets': 3}
    row['properties'].update({'418': 50, '427': 30})
    assert from_listing(row)['category'] == 'base'


def test_replay_keeps_unreported_rarity_separate_and_counts_only_reviewed_attention():
    from pricing.triage.replay import listing_score

    rules = {
        'keep_ist': 0.25,
        'rows': [
            {
                'category': 'rare',
                'family': 'glov',
                'pattern': {'properties': {'456': {'min': 2}, '457': {'min': 20}}},
                'pattern_label': 'Javelin skills and attack speed',
            }
        ],
    }
    data = prepare_tables({'bands': []}, rules, {'rows': []})
    result = listing_score([gloves()], data)
    assert 'base' not in result['categories']
    assert result['categories']['affixed_unknown']['flagged_valuable'] == 1
    assert result['categories']['affixed_unknown']['sell_flagged_valuable'] == 0
