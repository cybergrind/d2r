from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import decode_stats
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results, assess_roles
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('slug', 'slot', 'ordinal', 'base', 'skill', 'class_name'),
    [
        ('berserk-barbarian', 'Amulets', 6, 'Amulet', 54, 'Barbarian'),
        ('poison-nova-necromancer', 'Weapon-Swap', 2, 'Short Staff', 54, 'Necromancer'),
        ('blizzard-sorceress', 'Weapon-Swap', 4, 'Wand', 91, 'Sorceress'),
        ('dream-paladin', 'Weapon-Swap', 4, 'Bone Wand', 82, 'Paladin'),
        ('summoner-necromancer-guide', 'Weapon-Swap', 2, 'Long Staff', 54, 'Necromancer'),
    ],
)
def test_charged_alternatives_preserve_skill_remaining_charges_and_explicit_base(
    slug, slot, ordinal, base, skill, class_name
):
    bundle = build()
    rid = f'{slug}-charge-alternative-{slot.lower()}-{ordinal}'
    role = next((r for r in bundle['profiles'] if r['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]

    def item(count, skill_id=skill, ethereal=False):
        decoded, _, _ = decode_stats([{'id': 204, 'layer': skill_id * 64 + 2, 'raw': (30 << 8) | count}])
        return normalize(
            {
                'item': replace(facts(base, 'magic'), ethereal=ethereal).to_dict(),
                'decoded_stats': decoded,
                'source': {'stat_capture_complete': True},
            }
        )

    context = {'player_class': class_name}

    def assess(candidate):
        return assess_roles(candidate, [role], context)[0]

    assert assess(item(1))['dependencies'][0]['status'] == 'true'
    assert assess(item(0))['dependencies'][0]['status'] == 'false'
    assert assess(item(1, skill_id=48))['status'] == 'failed'
    if base != 'Amulet':
        assert assess(item(1, ethereal=True))['dependencies'][0]['status'] == 'true'
        assert assess(item(0, ethereal=True))['status'] == 'partial'
    for count, expected in [(1, {f'204:{skill * 64 + 2}'}), (0, set())]:
        candidate = item(count)
        evaluated = StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )
        assert set(evaluated.annotations) == expected
    if base in ('Long Staff', 'Bone Wand'):
        wrong = replace(item(1), base_code=facts('Short Staff' if base == 'Long Staff' else 'Wand').base_code)
        assert assess(wrong)['status'] == 'failed'


def test_decorated_charge_combinations_are_not_reduced_to_generic_charge_utility():
    from pricing.knowledge.assessment.maintenance.profile_templates import expand_profile

    row = {
        'id': 'example',
        'template': 'charged_utility',
        'item': 'Staff of Teleportation',
        'class': 'Druid',
        'build': 'fissure-druid',
        'variant': 'Main alternatives',
        'side': 'player',
        'slot': 'Weapon-Swap',
        'source': {},
    }
    for changes in (
        {'item': 'Gaean Amulet of Teleportation', 'slot': 'Amulets'},
        {'item': "Arch-Devil's Kris of Lower Resistance", 'slot': 'Weapon'},
        {'side': 'merc'},
        {'slot': 'Gloves'},
        {'class': 'Unreviewed'},
    ):
        with pytest.raises(ValueError, match=r'membership|slot'):
            expand_profile({**row, **changes})


@pytest.mark.parametrize(
    ('slug', 'base', 'class_name', 'key', 'minimum', 'skill', 'rare_allowed'),
    [
        ('fissure-druid', 'Amulet', 'Druid', '188:42', 3, 54, False),
        ('poison-nova-necromancer', 'Amulet', 'Necromancer', '188:17', 3, 54, False),
        ('abyss-warlock-build-guide', 'Kriss', 'Warlock', '83:7', 2, 91, True),
    ],
)
def test_decorated_charges_require_both_native_prefix_and_usable_spell(
    slug, base, class_name, key, minimum, skill, rare_allowed
):
    role = next((r for r in build()['profiles'] if r['id'] == slug + '-skill-charge-combination'), None)
    assert role is not None
    decoded, _, _ = decode_stats([{'id': 204, 'layer': skill * 64 + 1, 'raw': (60 << 8) | 1}])
    item = normalize(
        {'item': facts(base, 'magic').to_dict(), 'decoded_stats': decoded, 'source': {'stat_capture_complete': True}}
    )
    item = replace(item, stats={**item.stats, key: {'status': 'decoded', 'value': minimum}})
    context = {'player_class': class_name}

    def assess(candidate):
        return assess_roles(candidate, [role], context)

    assert assess(item)[0]['rule_trace']['truth'] == 'true'
    assert (
        assess(replace(item, stats={**item.stats, key: {'status': 'decoded', 'value': minimum - 1}}))[0]['status']
        == 'failed'
    )
    assert assess(replace(item, stats={key: {'status': 'decoded', 'value': minimum}}))[0]['status'] != 'matched'
    rare = assess(replace(item, rarity='rare'))
    assert bool(rare) == rare_allowed
    if rare_allowed:
        assert rare[0]['rule_trace']['truth'] == 'true'
