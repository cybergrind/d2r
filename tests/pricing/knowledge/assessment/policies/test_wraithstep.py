from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.policies.test_remaining_rolls import item


@pytest.mark.parametrize(('layer', 'tree'), [(56, 'Demon'), (57, 'Eldritch'), (58, 'Chaos')])
def test_wraithstep_values_each_random_tree_and_names_the_selected_segment(layer, tree):
    candidate = item('Mirrored Boots', 'Wraithstep', {f'188:{layer}': 1})
    result = assess_tier(candidate)
    assert result['tier'] == 'high'
    assert tree in ' '.join(result['reasons'])
    assert assess_tier(replace(candidate, capture_complete=False))['tier'] is None
    assert assess_tier(replace(candidate, ethereal=True))['tier'] is None


@pytest.mark.parametrize('stats', [{}, {'188:56': 2}, {'188:0': 1}, {'188:56': 1, '188:57': 1}])
def test_missing_wrong_or_multiple_trees_do_not_claim_reviewed_wraithstep_variant(stats):
    assert assess_tier(item('Mirrored Boots', 'Wraithstep', stats))['tier'] is None
