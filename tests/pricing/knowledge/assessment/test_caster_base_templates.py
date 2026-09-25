from dataclasses import replace

import pytest

from pricing.knowledge.assessment.base_use import recipe_index
from pricing.knowledge.assessment.caster_base_templates import TEMPLATES, compile_templates


def test_reviewed_membership_is_legal_and_exceptions_are_scoped():
    index = compile_templates(TEMPLATES)
    assert len(index) == 10
    for (word, base), template in index.items():
        assert template.version == 1
        assert template.source_locators
        assert any(
            row['details'].get('runeword') == word and row['details'].get('legality') == 'verified_type_and_capacity'
            for row in recipe_index().by_base[base]
        )
    assert 'War Scepter' in index['Call to Arms', 'War Scepter'].exceptions
    assert ('Spirit', 'War Scepter') not in index
    assert ('Call to Arms', 'Broad Sword') not in index


def test_conflicting_membership_and_unassigned_exceptions_fail_closed():
    template = TEMPLATES[0]
    with pytest.raises(ValueError, match='membership'):
        compile_templates((template, replace(template, id='overlap')))
    with pytest.raises(ValueError, match='exception'):
        compile_templates((replace(template, exceptions={'Unreviewed Base': ('invented advice',)}),))
    with pytest.raises(ValueError, match='source'):
        compile_templates((replace(template, source_locators=()),))
