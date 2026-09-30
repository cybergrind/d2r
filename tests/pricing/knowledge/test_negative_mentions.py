"""Explicit source rejection must survive demand regeneration."""

from pathlib import Path

import pytest

from pricing.knowledge.builds import guide_mentions


GUIDE = 'pricing/raw/mr/guides__echoing-strike-warlock-guide.html'


def test_gheed_removal_does_not_erase_other_guide_recommendations():
    from pricing.knowledge.negative_mentions import recommendation

    html = Path(GUIDE).read_text()
    mentions = guide_mentions(html)
    assert recommendation(GUIDE, 11, mentions[11], html) is False
    assert recommendation(GUIDE, 121, mentions[121], html) is True
    assert recommendation(GUIDE, 10, mentions[10], html) is True
    assert recommendation('another-guide.html', 11, mentions[11], html) is True


@pytest.mark.parametrize('change', ['source', 'label'])
def test_changed_negative_evidence_requires_review_instead_of_silent_endorsement(change):
    from pricing.knowledge.negative_mentions import recommendation

    html = Path(GUIDE).read_text()
    mention = guide_mentions(html)[11]
    if change == 'source':
        html = html.replace('Make sure to replace a ', 'Make sure to keep a ')
    else:
        mention = {**mention, 'label': 'Sling'}
    with pytest.raises(ValueError, match='negative demand'):
        recommendation(GUIDE, 11, mention, html)
