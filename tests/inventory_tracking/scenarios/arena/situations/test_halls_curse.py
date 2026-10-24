"""halls_curse.py: the Halls of the Dead fight cut before Amplify Damage came on (2026-10-24, the coordinator: "We need
off to die and on to survive, before CURSED_PRICED can go live under the survival rule")."""

from tests.inventory_tracking.scenarios.arena.situations import halls_curse


def test_the_cut_holds_the_cursed_hollow_one_and_no_scripted_amplify():
    situation = halls_curse.stored()
    mobs = situation.scene.mobs + [mob for spawn in situation.spawns for mob in spawn.mobs]
    hollow = [mob for mob in mobs if mob.unit == halls_curse.HOLLOW_ONE]
    assert len(hollow) == 1
    assert halls_curse.CURSED in hollow[0].mods
    assert hollow[0].life > 0
    assert not [row for row in situation.curses if row[1] == 'physical']  # `Cursing` puts it on
    assert situation.scene.hero.sets[0].resist['physical'] == 0.82  # the take's uncursed 18
    assert len([mob for mob in mobs if mob.tier == 5]) == 15  # the Herald pack to come


def test_the_curse_comes_by_the_rule_only_near_a_cursed_hostile():
    class Player:
        x, y = 0.0, 0.0

    class Hostile:
        ally = False

        def __init__(self, x: float, mods: tuple[int, ...]) -> None:
            self.x, self.y, self.modifiers = x, 0.0, mods

    class World:
        def __init__(self, monsters) -> None:
            self.player, self.monsters = Player(), monsters

    class Clock:
        now = 0.0

    class FakeStage:
        def __init__(self, monsters) -> None:
            self.world, self.clock = World(monsters), Clock()
            self.resists = [{'physical': 0.82}]

    def run(monsters, seconds: float) -> FakeStage:
        stage, cursing = FakeStage(monsters), halls_curse.Cursing(1, halls_curse.AMPLIFIED)
        for tick in range(int(seconds * 25) + 1):
            stage.clock.now = tick / 25
            cursing(stage, None)  # type: ignore[arg-type]
        return stage

    far = run([Hostile(halls_curse.CURSE_RANGE + 1, (halls_curse.CURSED,))], 30.0)
    plain = run([Hostile(5.0, (5, 17))], 30.0)
    near = run([Hostile(5.0, (halls_curse.CURSED,))], 30.0)
    assert far.resists[0]['physical'] == 0.82
    assert plain.resists[0]['physical'] == 0.82
    assert near.resists[0]['physical'] == halls_curse.AMPLIFIED
