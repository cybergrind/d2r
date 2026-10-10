"""Valuable materials by item class: shards, flawless and perfect gems, statues, keys, charms, essences."""

from inventory_tracking.loot.materials import GROUPS, material_classes


def test_each_group_names_its_item_classes():
    assert sorted(material_classes(['shards']).values())[0] == 'Deep Worldstone Shard'
    assert material_classes(['keys']) == {662: 'Key of Terror', 663: 'Key of Hate', 664: 'Key of Destruction'}
    assert material_classes(['statues'])[683] == "Worusk's End"  # the table says 'Uber Ancient Summon Material Act5'
    assert [len(material_classes([group])) for group in GROUPS] == [5, 14, 5, 3, 3, 4]


def test_charms_are_the_three_sizes():
    assert material_classes(['charms']) == {618: 'Small Charm', 619: 'Large Charm', 620: 'Grand Charm'}


def test_gems_are_the_flawless_and_perfect_ones_of_every_colour_and_skulls():
    gems = material_classes(['gems']).values()

    assert sorted(name.split()[0] for name in gems) == ['Flawless'] * 7 + ['Perfect'] * 7
    assert {name.split()[1] for name in gems} == {
        'Amethyst',
        'Diamond',
        'Emerald',
        'Ruby',
        'Sapphire',
        'Skull',
        'Topaz',
    }


def test_no_groups_means_no_classes():
    assert material_classes([]) == {}


def test_the_four_essences_are_a_group_of_their_own():
    found = material_classes(('essences',))
    assert sorted(found) == [669, 670, 671, 672]
    assert found[669] == 'Twisted Essence of Suffering'
    assert set(material_classes(('keys',)).values()) == {'Key of Terror', 'Key of Hate', 'Key of Destruction'}
