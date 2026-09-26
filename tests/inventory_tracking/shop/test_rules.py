import pytest

from inventory_tracking.items.metadata import decode_stats, metadata
from inventory_tracking.shop.rules import match_item, skill_targets


def observation(base_name, stats, *, rarity='magic', identified=True):
    base = next(b for b in metadata()['bases'].values() if b['name'] == base_name)
    rows = [{'id': sid, 'layer': layer, 'raw': raw} for sid, layer, raw in stats]
    decoded, _, unresolved = decode_stats(rows, base=base)
    return {
        'item': {
            'name': base_name,
            'base_name': base_name,
            'item_type': base['type'],
            'category': base['category'],
            'rarity': rarity,
            'identified': identified,
        },
        'decoded_stats': decoded,
        'unresolved_stats': unresolved,
    }


def skill(name):
    return next(int(k) for k, v in metadata()['skills'].items() if v['name'] == name)


def test_jewelers_monarch_of_deflecting_needs_block_and_fbr_but_any_four_socket_monarch_sells():
    stats = [(194, 0, 4), (20, 0, 20), (102, 0, 30)]
    assert any('Deflecting' in r for r in match_item(observation('Monarch', stats)))
    for missing in (1, 2):
        result = match_item(observation('Monarch', stats[:missing] + stats[missing + 1 :]))
        assert result
        assert not any('Deflecting' in r for r in result)
    assert not match_item(observation('Monarch', stats[1:]))
    assert not match_item(observation('Monarch', [(194, 0, 3), (20, 0, 20), (102, 0, 30)]))
    assert match_item(observation('Archon Plate', [(194, 0, 4), (80, 0, 20)]))


@pytest.mark.parametrize('name', ['Hex: Purge', 'Eldritch Blast', 'Echoing Strike', 'Mirrored Blades'])
@pytest.mark.parametrize('bonus', [(83, 7, 2), (188, 57, 3), (188, 57, 2)])
def test_warlock_skill_combinations(name, bonus):
    result = match_item(observation('Kriss', [bonus, (107, skill(name), 3)]))
    assert any(name in reason for reason in result)


def test_unrelated_tree_does_not_inflate_hex_purge():
    # Chaos cannot add ranks to the Eldritch skill Hex: Purge, and a lone staffmod is a vendor item.
    assert not match_item(observation('Kriss', [(188, 58, 3), (107, skill('Hex: Purge'), 3)]))
    assert not match_item(observation('Kriss', [(83, 1, 2), (107, skill('Hex: Purge'), 3)]))


def test_two_warlock_staffmods_sell_at_any_rarity():
    stats = [(107, skill('Hex: Purge'), 3), (107, skill('Eldritch Blast'), 3)]
    assert any('Hex: Purge' in r and 'Eldritch Blast' in r for r in match_item(observation('Kriss', stats)))
    assert match_item(observation('Kriss', stats, rarity='normal'))


@pytest.mark.parametrize(
    ('base', 'bonus', 'name'),
    [
        ('Greater Talons', (188, 48, 3), 'Lightning Sentry'),
        ('War Scepter', (83, 3, 2), 'Fist of the Heavens'),
        ('Bone Wand', (188, 17, 3), 'Poison Nova'),
        ('Eldritch Orb', (188, 9, 3), 'Lightning'),
    ],
)
def test_other_class_staffmods(base, bonus, name):
    assert any(name in r for r in match_item(observation(base, [bonus, (107, skill(name), 3)])))


def test_gloves_of_alacrity():
    assert match_item(observation('Chain Gloves', [(188, 2, 3), (93, 0, 20)]))
    assert match_item(observation('Chain Gloves', [(188, 50, 3), (93, 0, 20)]))
    assert not match_item(observation('Chain Gloves', [(188, 2, 2), (93, 0, 20)]))  # Gymnastic: leave in the shop
    assert not match_item(observation('Chain Gloves', [(188, 2, 3), (93, 0, 10)]))


def test_amazon_javelin_needs_forty_ias_and_amazon_skills_or_the_six_javelin_automod():
    assert match_item(observation('Matriarchal Javelin', [(188, 2, 6), (93, 0, 40)]))
    assert match_item(observation('Matriarchal Javelin', [(188, 2, 3), (93, 0, 40), (83, 0, 1)]))
    assert not match_item(observation('Matriarchal Javelin', [(188, 2, 3), (93, 0, 40)]))
    assert not match_item(observation('Matriarchal Javelin', [(188, 2, 6), (93, 0, 20)]))


@pytest.mark.parametrize('base', ['Blade Talons', 'Greater Talons', 'Runic Talons'])
@pytest.mark.parametrize('ias', [30, 40])
def test_trap_claws_with_ias_alert_without_individual_skill_bonus(base, ias):
    assert f'+3 Traps / {ias} IAS claws' in match_item(observation(base, [(188, 48, 3), (93, 0, ias)]))


def test_claw_label_names_the_sentry_staffmods_and_witch_hunters_counts():
    stats = [(188, 48, 3), (93, 0, 40), (107, skill('Lightning Sentry'), 3)]
    assert '+3 Traps / 40 IAS claws (+3 Lightning Sentry)' in match_item(observation('Greater Talons', stats))
    assert '+2 Assassin / 40 IAS claws' in match_item(observation('Runic Talons', [(83, 6, 2), (93, 0, 40)]))


@pytest.mark.parametrize(
    ('base', 'stats'),
    [
        ('Greater Talons', [(188, 48, 3), (93, 0, 20)]),
        ('Greater Talons', [(188, 48, 2), (93, 0, 30)]),
        ('Greater Talons', [(188, 49, 3), (93, 0, 30)]),
        ('Greater Talons', [(188, 50, 3), (93, 0, 30)]),
        ('Greater Talons', [(107, skill('Lightning Sentry'), 3), (93, 0, 30)]),
        ('Chain Gloves', [(188, 48, 3), (93, 0, 30)]),
    ],
)
def test_trap_ias_target_requires_claws_and_matching_tree_and_thresholds(base, stats):
    assert not match_item(observation(base, stats))


def test_unidentified_and_duplicate_unresolved_stats_are_not_hits():
    stats = [(194, 0, 4), (20, 0, 20), (102, 0, 30)]
    assert not match_item(observation('Monarch', stats, identified=False))
    assert not match_item(observation('Monarch', [*stats, (194, 0, 4)]))


@pytest.mark.parametrize(
    ('base', 'mastery', 'main'),
    [
        ('Eldritch Orb', 'Lightning Mastery', 'Lightning'),
        ('Eldritch Orb', 'Lightning Mastery', 'Nova'),
        ('Eldritch Orb', 'Fire Mastery', 'Enchant'),
        ('Eldritch Orb', 'Fire Mastery', 'Fire Ball'),
        ('Eldritch Orb', 'Fire Mastery', 'Hydra'),
        ('Eldritch Orb', 'Cold Mastery', 'Blizzard'),
        ('Eldritch Orb', 'Cold Mastery', 'Frozen Orb'),
        ('Bone Wand', 'Skeleton Mastery', 'Raise Skeleton'),
        ('Kriss', 'Demonic Mastery', 'Summon Defiler'),
        ('Kriss', 'Demonic Mastery', 'Hex: Purge'),
        ('Kriss', 'Levitation Mastery', 'Mirrored Blades'),
        ('Slayer Guard', 'Throwing Mastery', 'Double Throw'),
        ('Slayer Guard', 'Blade Mastery', 'Berserk'),
        ('Slayer Guard', 'Blade Mastery', 'Whirlwind'),
        ('Slayer Guard', 'Mace Mastery', 'Frenzy'),
        ('Greater Talons', 'Claw Mastery', 'Dragon Talon'),
    ],
)
def test_mastery_and_main_skill_without_class_or_tree_prefix(base, mastery, main):
    result = match_item(observation(base, [(107, skill(mastery), 3), (107, skill(main), 3)]))
    assert any(mastery in r and main in r for r in result)


def test_every_class_mastery_is_in_catalog():
    catalog = {t['name'] for t in skill_targets()}
    assert {s['name'] for s in metadata()['skills'].values() if s['class'] and 'Mastery' in s['name']} <= catalog


@pytest.mark.parametrize(
    ('base', 'stats'),
    [
        ('Archon Plate', [(194, 0, 4), (7, 0, 100 * 256)]),
        ('Ancient Armor', [(194, 0, 4), (7, 0, 90 * 256)]),
        ('Ancient Armor', [(194, 0, 4), (34, 0, 15)]),
        ('Ancient Armor', [(194, 0, 4), (99, 0, 24)]),
        ('Ancient Armor', [(194, 0, 4), (2, 0, 15)]),
        ('Tiara', [(194, 0, 3), (96, 0, 30)]),
        ('Tiara', [(194, 0, 3), (2, 0, 30)]),
        ('Diadem', [(194, 0, 3), (80, 0, 35)]),
        ('Circlet', [(83, 1, 2), (105, 0, 20)]),
        ('Coronet', [(83, 7, 2)]),
        ('Slayer Guard', [(188, 34, 3)]),
        ('Eldritch Orb', [(105, 0, 20), (107, skill('Lightning'), 3)]),
        ('War Scepter', [(105, 0, 10), (107, skill('Fist of the Heavens'), 3)]),
        ('Preserved Head', [(194, 0, 2), (83, 2, 1)]),
        ('Grimoire', [(188, 57, 3)]),
    ],
)
def test_priced_magic_patterns_alert(base, stats):
    assert match_item(observation(base, stats))


@pytest.mark.parametrize(
    ('base', 'stats'),
    [
        ('Ancient Armor', [(194, 0, 4), (7, 0, 80 * 256)]),  # below the priced Whale band
        ('Ancient Armor', [(194, 0, 3), (7, 0, 100 * 256)]),
        ('Circlet', [(188, 57, 3), (105, 0, 20)]),  # +3 tree circlet is not a priced pattern
        ('Circlet', [(105, 0, 20), (194, 0, 2)]),
        ('Blade', [(188, 34, 3)]),  # Echoing weapon: 1-Ist median behind 63 sellers
        ('Winged Axe', [(17, 0, 300), (18, 0, 300), (93, 0, 40)]),  # Cruel / Quickness: no priced pattern
        ('Eldritch Orb', [(105, 0, 20)]),
        ('War Scepter', [(105, 0, 10), (107, skill('Fist of the Heavens'), 2)]),
        ('Preserved Head', [(194, 0, 1), (83, 2, 2)]),
        ('Grimoire', [(188, 57, 2)]),
        ('Grimoire', [(39, 0, 20), (41, 0, 20), (43, 0, 20), (45, 0, 20)]),  # all-res grimoire: starter piece
        ('Plated Belt', [(7, 0, 41 * 256), (39, 0, 21)]),  # starter life/res belt
        ('Chain Gloves', [(80, 0, 20), (39, 0, 21)]),  # starter MF/res gloves
        ('Heavy Boots', [(96, 0, 30)]),  # starter FRW boots
        ('Kriss', [(83, 7, 1), (105, 0, 10)]),  # pre-Spirit caster dagger
    ],
)
def test_build_candidates_and_unpriced_blues_stay_silent(base, stats):
    assert not match_item(observation(base, stats))


@pytest.mark.parametrize('name', ['Teleport', 'Life Tap', 'Lower Resist'])
def test_utility_charges_are_not_targets(name):
    assert not match_item(observation('Bone Wand', [(204, skill(name) * 64 + 1, 30 * 256)]))
    assert not match_item(observation('Battle Staff', [(204, skill(name) * 64 + 1, 30 * 256)]))


def test_white_staffmod_bases_are_not_shop_targets():
    assert not match_item(observation('Kriss', [(107, skill('Hex: Purge'), 3)], rarity='normal'))
