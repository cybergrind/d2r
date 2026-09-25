import json
from pathlib import Path

from inventory_tracking.items.decode import decode_items
from pricing.knowledge.assessment.comparables import reject_reasons
from pricing.knowledge.assessment.engine import assess


def test_saved_sazabi_requires_variable_resists_and_defense_but_allows_omitted_fixed_skill():
    capture = json.loads(
        (Path(__file__).parents[3] / 'inventory_tracking/fixtures/sazabi_mental_sheath.json').read_text()
    )
    row = capture['snapshot']['resources']['items'][0]
    extraction = decode_items(
        capture['snapshot'],
        capture['report'],
        inventory_page=row['details']['inventory_page'],
        inventory_owner_id=row['details']['owner_id'],
    )[0]
    contract = assess(extraction, profiles=[])['contract']
    assert contract['intrinsic_properties']['587'] == 1
    required = {k: v for k, v in contract['properties'].items() if k not in contract['intrinsic_properties']}
    assert {'427', '428', '1855'} <= required.keys()
    listing = {
        **{k: contract[k] for k in ('name', 'base_code', 'rarity', 'ethereal', 'sockets', 'socket_contents')},
        'properties': required,
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'fixture',
        'ask_ist': 1,
    }
    assert not reject_reasons(contract, listing)
    assert reject_reasons(contract, {**listing, 'properties': {**required, '587': 2}})
    assert reject_reasons(contract, {**listing, 'properties': {k: v for k, v in required.items() if k != '428'}})
    assert reject_reasons(contract, {**listing, 'base_code': None})
