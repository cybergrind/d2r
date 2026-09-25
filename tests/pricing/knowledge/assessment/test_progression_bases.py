from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.base_use import assess_runeword_base
from tests.pricing.knowledge.assessment.test_base_use import capture, word


@pytest.mark.parametrize(
    ('recipe', 'base'),
    [
        ('Stealth', 'Quilted Armor'),
        ('Stealth', 'Leather Armor'),
        ('Stealth', 'Hard Leather Armor'),
        ('Stealth', 'Studded Leather'),
        ('Smoke', 'Mage Plate'),
        ('Smoke', 'Studded Leather'),
        ('Rhyme', 'Bone Shield'),
        ('Rhyme', 'Targe'),
        ('Rhyme', 'Preserved Head'),
        ('Lore', 'Cap'),
        ('Lore', 'Diadem'),
    ],
)
def test_reviewed_progression_bases_keep_wearer_and_ethereal_conditions(recipe, base):
    facts = normalize(capture(base, sockets=2, quality='normal', ethereal=False))
    result = word(assess_runeword_base(facts), recipe)
    assert result['status'] == 'preferred base'
    assert any('requirements' in s for s in result['missing'])
    assert result['ethereal_preference']['preference'] == 'avoid'
    eth = word(assess_runeword_base(replace(facts, ethereal=True)), recipe)
    assert any('non-ethereal' in s for s in eth['missing'])
    assert eth['status'] != 'perfect preferred base'
    if base == 'Diadem':
        assert '64' in ' '.join(result['missing'])
    if base == 'Targe':
        assert any('Paladin' in s and 'resistance' in s for s in result['missing'])
    if base == 'Preserved Head':
        assert any('Necromancer' in s and 'staffmods' in s for s in result['missing'])


def test_progression_socket_preparation_and_unreviewed_membership():
    blank = normalize(capture('Mage Plate', sockets=0, ethereal=False))
    result = word(assess_runeword_base(replace(blank, item_level=50)), 'Smoke')
    assert result['status'] == 'cannot prepare this base'
    normal = word(assess_runeword_base(replace(blank, rarity='normal', item_level=50)), 'Smoke')
    assert normal['status'] == 'needs sockets'
    assert any('16.7%' in s for s in normal['missing'])
    assert not assess_runeword_base(normalize(capture('Cap', sockets=2, quality='magic')))
    assert 'Lore' not in {r['runeword'] for r in assess_runeword_base(normalize(capture('Shako', sockets=2)))}


def test_progression_membership_has_cached_recommendations_and_rejects_overlap():
    from pricing.knowledge.assessment.base_use import recipe_index
    from pricing.knowledge.assessment.progression_base_templates import INDEX, TEMPLATES, compile_templates

    for (recipe, base), template in INDEX.items():
        assert template.source_locators
        assert any(
            r.get('details', {}).get('runeword') == recipe and r['details'].get('recommended')
            for r in recipe_index().by_base[base]
        )
    with pytest.raises(ValueError, match='membership'):
        compile_templates((*TEMPLATES, TEMPLATES[0]))
    with pytest.raises(ValueError, match='exception'):
        compile_templates(TEMPLATES[:1])
