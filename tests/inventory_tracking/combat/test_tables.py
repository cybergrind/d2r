"""The bundled game tables (combat/data/tables.json) and what the mechanics read from them."""

from inventory_tracking.combat.mechanics.tables import area_level, monster_points, tables


def test_echoing_strike_is_a_weapon_attack_with_mirrored_blades_duplicates():
    skill = tables()['skills']['388']
    assert skill['SrcDam'] == '116'  # 116/128 of the weapon's damage
    assert (skill['MinDam'], skill['MaxDam']) == ('8', '12')
    assert skill['calc5'].startswith("(skill('Mirrored Blades'.blvl) > 0) ? (1+(skill('Mirrored Blades'.blvl)/5))")
    assert skill['calc6'] == '(100/clc5)/2'  # duplicates after the first blade: 10% each with five blades
    assert skill['ToHitCalc'] == 'lvl*10'
    blade = tables()['missiles']['706']
    assert (blade['Vel'], blade['Range'], blade['ReturnFire'], blade['NextDelay']) == ('24', '20', '1', '20')


def test_a_chaos_sanctuary_monster_has_its_hell_points_from_the_area_level():
    assert area_level(108) == 85
    assert monster_points(310, 108) == (5564, 6955)  # Doom Knight: 4637 * 120%..150%
    assert monster_points(362, 108) == (9737, 11592)  # Venom Lord: 210%..250%
    assert monster_points(99999, 108) is None
