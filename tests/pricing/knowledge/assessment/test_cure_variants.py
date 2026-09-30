from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('quality', ['normal', 'superior', 'low_quality'])
@pytest.mark.parametrize(
    ('slug', 'index', 'cls', 'base', 'merc'),
    [
        ('echoing-strike-warlock-guide', 1, 'Warlock', 'Grand Crown', 'Act 2 Prayer'),
        ('echoing-strike-warlock-guide', 2, 'Warlock', 'Grand Crown', 'Act 2 Prayer'),
        ('enchant-sorceress', 1, 'Sorceress', 'Demonhead', 'Act 2 Prayer'),
        ('enchant-sorceress', 2, 'Sorceress', 'Demonhead', 'Act 2 Prayer'),
        ('nova-sorceress-guide', 1, 'Sorceress', 'Diadem', 'Act 2 Holy Freeze'),
        ('nova-sorceress-guide', 2, 'Sorceress', 'Diadem', 'Act 2 Might'),
        ('nova-sorceress-guide', 3, 'Sorceress', 'Diadem', 'Act 2 Holy Freeze'),
    ],
)
def test_cure_guide_variants_keep_the_actual_base_and_mercenary(slug, index, cls, base, merc, quality):
    bundle = build()
    role = next((r for r in bundle['profiles'] if r['id'] == f'{slug}-{index}-merc-cure'), None)
    assert role is not None
    item = replace(
        facts(base, quality, name='Cure'), runeword='Cure', sockets=3, socket_contents='filled', ethereal=True
    )

    def truth(candidate=item, mercenary=merc):
        return assess_roles(candidate, [role], {'player_class': cls, 'mercenary_type': mercenary})[0]['rule_trace'][
            'truth'
        ]

    assert truth() == 'true'
    assert truth(mercenary=None) == 'unknown'
    assert truth(mercenary='Act 1 Cold') == 'false'
    assert truth(replace(item, base_code=facts('Crown').base_code)) == 'false'
    assert truth(replace(item, ethereal=False)) == 'false'
    if slug == 'nova-sorceress-guide':
        assert truth(mercenary='Act 2 Prayer') == 'false'
        assert any('does not' in c and 'healing' in c for c in role['conditions'])
