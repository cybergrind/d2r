"""The loop's items identified, appraised, and the junk sold for the repair (macros/junk.py; routes/lower-kurast-loop-
plan.md §15). The player, 2026-10-17: "picking items with +skill, identifying them, appraising, selling [bad ones] and
repairing on these money ... we shouldn't sell our own equipment or valuable items"."""

from inventory_tracking.game.layout import IDENTIFY_TOME
from inventory_tracking.game.records import Carried, Pack
from inventory_tracking.items.metadata import metadata
from inventory_tracking.macros.cube import CUBE_CLASS, own_of
from inventory_tracking.macros.junk import identify, junk, junk_of, unidentified
from tests.inventory_tracking.macros.fakes import Game, player, world


FORTRESS = 103


def class_of(name: str) -> int:
    [found] = [int(cid) for cid, base in metadata()['bases'].items() if base['name'] == name]
    return found


GAUNTLETS = class_of('Gauntlets')
MAGIC, SET, RARE = 4, 5, 6
THE_CUBE = Carried(2, CUBE_CLASS, 1, 0, (2, 2))
TOME = Carried(3, IDENTIFY_TOME, 8, 0, (1, 2))
WORN_GLOVES = Carried(4, GAUNTLETS, 3, 0, (2, 2), MAGIC)  # the player's own, identified magic gloves: never sold
OWN = own_of((THE_CUBE, TOME, WORN_GLOVES))
KRISS = Carried(11, 41, 0, 2, (1, 3), MAGIC, identified=False)  # picked up by the loop
CIRCLET = Carried(12, 418, 2, 2, (2, 2), RARE, identified=False)
SET_GLOVES = Carried(13, GAUNTLETS, 5, 2, (2, 2), SET, identified=False)


def fortress(pack: Pack) -> Game:
    play = Game(world(FORTRESS, player=player(FORTRESS, x=5048.0, y=5044.0)))
    play.pack = pack
    return play


def test_the_loops_unidentified_items_are_identified_with_the_tome_and_the_panels_closed():
    play = fortress(Pack((THE_CUBE, TOME, WORN_GLOVES, KRISS, CIRCLET), identifies=10))

    assert play.pack is not None
    assert [i.unit_id for i in unidentified(play.pack, OWN)] == [KRISS.unit_id, CIRCLET.unit_id]
    done = identify(play.run(), 'i', unidentified(play.pack, OWN))

    assert [i.unit_id for i in done] == [KRISS.unit_id, CIRCLET.unit_id]
    assert play.pack is not None
    assert all(i.identified for i in play.pack.items)
    assert play.pack.identifies == 8
    assert play.world.open_panels == ()


def test_an_empty_tome_or_none_identifies_nothing():
    play = fortress(Pack((THE_CUBE, TOME, KRISS), identifies=0))
    assert identify(play.run(), 'i', (KRISS,)) == []
    play = fortress(Pack((THE_CUBE, KRISS), identifies=None))
    assert identify(play.run(), 'i', (KRISS,)) == []


def test_only_the_loops_identified_items_the_appraisal_calls_vendor_are_junk():
    kriss, circlet = (Carried(i.unit_id, i.txt, i.x, i.y, i.size, i.quality) for i in (KRISS, CIRCLET))
    set_gloves = Carried(13, GAUNTLETS, 5, 2, (2, 2), SET)
    pack = Pack((THE_CUBE, TOME, WORN_GLOVES, kriss, circlet, set_gloves, Carried(14, 41, 7, 2, (1, 3), MAGIC)))
    verdicts = {
        kriss.unit_id: 'vendor',
        circlet.unit_id: 'keep',  # a +2 skills circlet: kept
        set_gloves.unit_id: 'vendor',  # a set item too (the player, 11:10 on 2026-10-18: "set/unique junk items")
        WORN_GLOVES.unit_id: 'vendor',  # the player's own: never junk
    }  # the fourth, item 14, has no verdict: kept
    said: list[str] = []

    found = junk(pack, OWN, verdicts, said.append)

    assert found == {(kriss.txt, kriss.x, kriss.y), (set_gloves.txt, set_gloves.x, set_gloves.y)}
    assert said[:2] == ['appraised magic Kriss (41) at (0, 2): vendor', 'appraised rare Circlet (418) at (2, 2): keep']
    unknown = Pack((THE_CUBE, KRISS))
    assert junk(unknown, OWN, {KRISS.unit_id: 'vendor'}, said.append) == set()  # not identified: never junk


def test_a_rune_gem_or_a_set_or_unique_charm_is_never_junk_but_any_other_item_may_be():
    # A magic Large Charm appraised `vendor` was sold at 11:23:55 on 2026-10-17; the player: "you can sell identified
    # junk charms", and at 19:06: "actually, we can sell trash jewels/rings/amus"; 11:10 on 2026-10-18: "we should
    # sell junk rings and other junk items; imporant!: do not sell own equipment or valuable items", "also, we can
    # sell set/unique junk items". A unique charm (a Sunder, Gheed's, Annihilus, the Torch) never is"
    charm = Carried(15, class_of('Large Charm'), 0, 2, (1, 2), MAGIC)
    jewel = Carried(16, class_of('Jewel'), 1, 2, (1, 1), MAGIC)
    ring = Carried(17, class_of('Ring'), 2, 2, (1, 1), RARE)
    wand = Carried(18, class_of('Bone Wand'), 3, 2, (1, 2), MAGIC)
    amulet = Carried(19, class_of('Amulet'), 4, 0, (1, 1), RARE)
    unique_ring = Carried(20, class_of('Ring'), 4, 1, (1, 1), 7)
    set_amulet = Carried(21, class_of('Amulet'), 4, 2, (1, 1), SET)
    gem = Carried(22, class_of('Flawless Ruby'), 4, 3, (1, 1), 2)
    sunder = Carried(23, class_of('Grand Charm'), 5, 0, (1, 3), 7)
    annihilus = Carried(24, class_of('Small Charm'), 6, 0, (1, 1), 7)
    pack = Pack((THE_CUBE, TOME, charm, jewel, ring, wand, amulet, unique_ring, set_amulet, gem, sunder, annihilus))
    verdicts = dict.fromkeys(range(15, 25), 'vendor')
    found = junk(pack, own_of((THE_CUBE, TOME)), verdicts, lambda text: None)
    assert found == {(c.txt, c.x, c.y) for c in (charm, jewel, ring, wand, amulet, unique_ring, set_amulet)}


def test_a_magic_or_rare_item_of_any_type_appraised_vendor_is_junk():
    # 21:55:19 on 2026-10-19: a magic Matriarchal Javelin the loot filter showed, appraised `vendor` at Cain, was no
    # junk (only the skill types, charms, jewels and jewelry were) and went into the stash; the player: "we had put
    # trash item for sale and forgot to pick it and sell". Gloves the appraisal keeps, or a white base, are not
    javelin = Carried(30, class_of('Matriarchal Javelin'), 0, 0, (1, 3), MAGIC)
    armor = Carried(31, class_of('Sacred Armor'), 1, 0, (2, 3), RARE)
    gloves = Carried(32, GAUNTLETS, 3, 0, (2, 2), MAGIC)
    white = Carried(33, class_of('Sacred Armor'), 5, 0, (2, 3), 2)
    rune = Carried(34, class_of('Ber Rune'), 7, 0, (1, 1), 2)
    verdicts = {30: 'vendor', 31: 'vendor', 32: 'keep', 33: 'vendor', 34: 'vendor'}

    found = junk_of([javelin, armor, gloves, white, rune], lambda units: {u: verdicts[u] for u in units})

    assert found == [javelin, armor]


def test_a_white_void_base_is_junk_when_the_appraisal_calls_it_vendor_and_kept_otherwise():
    # The player, 2026-10-17 17:45: "we're storing every 3os dagger, while in reality we need something that is really
    # good for void". A white Kriss the appraisal calls `vendor` (no Warlock skill worth a sale) is sold; one it keeps
    # or calls `check` is stashed; a white base outside the Void line is never the loop's junk
    plain = Carried(21, 41, 0, 2, (1, 3), 2)  # white Kriss
    skilled = Carried(22, 42, 1, 2, (1, 3), 3)  # superior Blade
    checked = Carried(23, 41, 2, 2, (1, 3), 2)
    gloves = Carried(24, GAUNTLETS, 3, 2, (2, 2), 2)
    pack = Pack((THE_CUBE, TOME, plain, skilled, checked, gloves))
    verdicts = {21: 'vendor', 22: 'keep', 23: 'check', 24: 'vendor'}
    said: list[str] = []
    assert junk(pack, OWN, verdicts, said.append) == {(41, 0, 2)}
    assert said[0] == 'appraised white Kriss (41) at (0, 2): vendor'
    assert junk_of([plain, skilled, checked, gloves], lambda units: {u: verdicts[u] for u in units}) == [plain]
