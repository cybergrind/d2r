import json
from pathlib import Path

import pytest

from pricing.knowledge.assessment.property_equivalence import canonical_properties


@pytest.mark.parametrize(('property_id', 'label'), [('591', 'Cannot Be Frozen'), ('432', 'Indestructible')])
def test_native_flag_has_verified_boolean_market_representation(property_id, label):
    source = Path(__file__).resolve().parents[4] / 'pricing/data/appraisal-properties.json'
    assert json.loads(source.read_text())['properties'][property_id]['types'] == ['bool']
    assert canonical_properties({property_id: True}) == canonical_properties({property_id: 1}) == {property_id: 1}
    assert type(canonical_properties({property_id: True})[property_id]) is int
    assert canonical_properties({property_id: False}) == {property_id: 0}
    assert canonical_properties({'461': True})['461'] is True  # Never coerce a numeric MF property.
    for value in (2, -1, 1.0, 'true', None):
        with pytest.raises(ValueError, match=label):
            canonical_properties({property_id: value})
