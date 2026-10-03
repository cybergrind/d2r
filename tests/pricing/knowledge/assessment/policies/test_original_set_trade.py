from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


@pytest.mark.parametrize(
    ('name', 'base', 'stats', 'status'),
    [
        ("Trang-Oul's Claws", 'Heavy Bracers', (), 'candidate'),
        ("Trang-Oul's Claws", 'Vambraces', (), 'unresolved'),
        ("Tal Rasha's Fine-Spun Cloth", 'Mesh Belt', ((80, 0, 15),), 'candidate'),
        ("Tal Rasha's Fine-Spun Cloth", 'Mesh Belt', ((80, 0, 14),), 'unresolved'),
        ("Tal Rasha's Fine-Spun Cloth", 'Mesh Belt', (), 'unresolved'),
        ("Tal Rasha's Fine-Spun Cloth", 'Mithril Coil', ((80, 0, 15),), 'unresolved'),
        ("Tal Rasha's Fine-Spun Cloth", 'Mesh Belt', ((80, 0, 16),), 'unresolved'),
    ],
)
def test_original_set_trade_is_not_transferred_to_upgraded_or_lower_rolls(name, base, stats, status):
    result = assess_trade_qualification(normalize(Item(base, 'set', name, stats).capture()))
    assert result['status'] == status
    assert 'price_estimate' not in result


@pytest.mark.parametrize(
    'changes',
    [
        {'ethereal': True},
        {'ethereal': None},
        {'sockets': 1},
        {'sockets': None},
        {'socket_contents': 'unknown'},
        {'identified': False},
    ],
)
def test_fixed_set_modifiers_still_require_verified_variant(changes):
    specimen = replace(Item('Heavy Bracers', 'set', "Trang-Oul's Claws", ()), **changes)
    assert assess_trade_qualification(normalize(specimen.capture()))['status'] == 'unresolved'


@pytest.mark.parametrize('change', ['unsupported-mode', 'bonus-only', 'conflicting-upgrade'])
def test_market_base_inference_cannot_silently_expand_the_review(change):
    import json

    from pricing.knowledge.assessment.policies.named_tiers import RULES, _policies

    document = json.loads(RULES.read_bytes())
    review = next(p for p in document['policies'] if p['name'] == "Trang-Oul's Claws")['trade_qualification']
    if change == 'unsupported-mode':
        review['base_inference'] = 'guess_from_name'
    else:
        row = next(r for r in review['market_evidence'] if not r.get('base_code'))
        if change == 'bonus-only':
            row['properties']['399'] = row['properties'].pop('1855')
        else:
            row['properties']['930'] = 'Elite'
    with pytest.raises(
        ValueError, match=r'Unsupported trade evidence base inference|Unverified trade evidence variant'
    ):
        _policies(json.dumps(document).encode())
