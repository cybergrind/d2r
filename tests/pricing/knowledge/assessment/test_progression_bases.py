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
        if template.reviewed_sources:
            import json
            from pathlib import Path

            path, locator = template.reviewed_sources[0].split('#')
            value = json.loads(Path(path).read_text())
            for part in locator.split('/')[1:]:
                value = value[int(part)] if isinstance(value, list) else value[part]
            assert any(label.startswith(f'{recipe} {base}') for label in value)
            continue
        assert any(
            r.get('details', {}).get('runeword') == recipe and r['details'].get('recommended')
            for r in recipe_index().by_base[base]
        )
    with pytest.raises(ValueError, match='membership'):
        compile_templates((*TEMPLATES, TEMPLATES[0]))
    with pytest.raises(ValueError, match='exception'):
        compile_templates(TEMPLATES[:1])


def test_duress_empty_dusk_shroud_has_reviewed_use_without_best_base_claim():
    facts = normalize(capture('Dusk Shroud', sockets=3, quality='normal', ethereal=False))
    result = word(assess_runeword_base(facts), 'Duress')
    assert result is not None
    assert result['status'] == 'usable alternative'
    assert any('kicker' in s for s in result['strengths'])
    assert any('90' in s for s in result['missing'])
    assert any('dragon-talon-assassin' in s for s in result['sources'] if s)
    assert result['ethereal_preference']['preference'] == 'avoid'
    ethereal = word(assess_runeword_base(replace(facts, ethereal=True)), 'Duress')
    assert any('non-ethereal' in s for s in ethereal['missing'])
    blank = normalize(capture('Dusk Shroud', sockets=0, quality='normal', ethereal=False))
    preparation = word(assess_runeword_base(replace(blank, item_level=80)), 'Duress')
    assert preparation['status'] == 'needs sockets'
    assert any('16.7%' in s for s in preparation['missing'])
    wrong = word(assess_runeword_base(replace(facts, sockets=4)), 'Duress')
    assert wrong['status'] == 'wrong socket count'
    assert not assess_runeword_base(replace(facts, runeword='Duress'))
    assert not any(
        r['runeword'] == 'Duress'
        for r in assess_runeword_base(normalize(capture('Archon Plate', sockets=3, quality='normal', ethereal=False)))
    )


def test_lionheart_mage_plate_supports_strafe_progression_and_real_socket_outcomes():
    facts = normalize(capture('Mage Plate', sockets=3, quality='normal', ethereal=False))
    result = word(assess_runeword_base(facts), 'Lionheart')
    assert result is not None
    assert any('Strafe' in s for s in result['strengths'])
    assert any('strafe-amazon' in s for s in result['sources'] if s)
    assert result['ethereal_preference']['preference'] == 'avoid'
    assert result['status'] != 'perfect preferred base'
    ethereal = word(assess_runeword_base(replace(facts, ethereal=True)), 'Lionheart')
    assert any('non-ethereal' in s for s in ethereal['missing'])
    blank = replace(facts, sockets=0, item_level=50)
    preparation = word(assess_runeword_base(blank), 'Lionheart')
    assert preparation['status'] == 'needs sockets'
    assert any('66.7%' in s for s in preparation['missing'])
    superior = word(assess_runeword_base(replace(blank, rarity='superior')), 'Lionheart')
    assert superior['status'] == 'needs sockets'  # Larzuk remains possible; cube does not.
    assert not any('66.7%' in s for s in superior['missing'])
    for quality in ('magic', 'rare'):
        assert not assess_runeword_base(replace(facts, rarity=quality))
