"""Exact embedded planner evidence must accompany the reviewed table entries."""

import pytest

from pricing.knowledge.assessment.build_profiles import build


@pytest.mark.parametrize(
    ('role_id', 'reference'),
    [
        ('abyss-warlock-table-dagger-void', 7),
        ('abyss-warlock-table-rare-kris', 8),
        ('abyss-warlock-table-dagger-arch-devil', 9),
    ],
)
def test_dagger_source_pins_the_embedded_reference(role_id, reference):
    role = next(r for r in build()['profiles'] if r['id'] == role_id)
    assert any(
        source['path'] == 'pricing/data/appraisal-guide-sections.json'
        and source['locator']
        == f'/sources/pricing~1raw~1mr~1guides__abyss-warlock-build-guide.html/embedded_item_refs/{reference}'
        for source in role['source']['corroborating']
    )
    assert 'whole-planner' not in role['source']['review'].lower()
    assert 'not a unique item' not in role['source']['review'].lower()
