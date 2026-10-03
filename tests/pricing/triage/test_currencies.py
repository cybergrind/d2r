from pricing.triage.currencies import apply_gem_quotes
from tests.pricing.triage.test_bands import listing


def test_scoped_gem_quotes_recover_cheap_asks_without_pricing_barter_or_ambiguous_units():
    gems = [
        listing(i, 0.02) | {'name': 'Perfect Sapphire', 'category': 'gems', 'amount': 40, 'unit_policy': 'stack_total'}
        for i in range(3)
    ]
    target = listing('item') | {
        'ask_ist': None,
        'prices': [{'name': 'Perfect Sapphire', 'quantity': 2, 'group': 0, 'type': 'gems'}],
    }
    uncertain = target | {'listing_id': 'unknown', 'amount': 2, 'unit_policy': 'ambiguous'}
    barter = target | {'listing_id': 'barter', 'prices': [{'name': 'Small Charm', 'quantity': 1, 'type': 'charms'}]}
    rows = apply_gem_quotes([*gems, target, uncertain, barter], {'ist': 1})
    assert rows[-3]['ask_ist'] == 0.04
    assert rows[-3]['conversion']['gem_quotes']['perfect sapphire']['sellers'] == 3
    assert rows[-2]['ask_ist'] is None
    assert rows[-1]['ask_ist'] is None
    assert target['ask_ist'] is None
    # Neither foreign scope nor repeated copies from one seller establish a rate.
    foreign = gems[-1] | {'properties': gems[-1]['properties'] | {'800': True}}
    assert apply_gem_quotes([gems[0], gems[0], gems[1], foreign, target], {'ist': 1})[-1]['ask_ist'] is None


def test_gem_alternative_can_lower_existing_ask_and_stack_price_is_divided_once():
    gems = [
        listing(i, 0.02) | {'name': 'Perfect Sapphire', 'category': 'gems', 'amount': 40, 'unit_policy': 'stack_total'}
        for i in range(3)
    ]
    row = listing('item', 1) | {
        'prices': [
            {'name': 'Ist Rune', 'quantity': 1, 'group': 0, 'type': 'runes'},
            {'name': 'Perfect Sapphire', 'quantity': 2, 'group': 1, 'type': 'gems'},
        ]
    }
    assert apply_gem_quotes([*gems, row], {'ist': 1})[-1]['ask_ist'] == 0.04
    stack = row | {'amount': 2, 'unit_policy': 'stack_total'}
    assert apply_gem_quotes([*gems, stack], {'ist': 1})[-1]['ask_ist'] == 0.02
