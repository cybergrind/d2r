"""Individual set utility does not imply active companion bonuses or a full price."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    (
        "Guillaume's Face",
        'Winged Helm',
        104,
        'low',
        ((136, 0, 35), (141, 0, 15), (99, 0, 30), (0, 0, 15)),
        ('35% Chance of Crushing Blow',),
    ),
    (
        "Immortal King's Soul Cage",
        'Sacred Armor',
        71,
        'trash',
        ((188, 32, 2), (45, 0, 50), (201, 52 * 64 + 5, 5)),
        ('Combat Skills', 'Poison Resist +50%'),
    ),
    (
        "Tal Rasha's Adjudication",
        'Amulet',
        77,
        'low',
        ((83, 1, 2), (7, 0, 50 * 256), (9, 0, 42 * 256), (41, 0, 33)),
        ('Sorceress Skill Levels', '+50 to Life'),
    ),
    (
        "Tal Rasha's Horadric Crest",
        'Death Mask',
        80,
        'low',
        ((60, 0, 10), (62, 0, 10), (7, 0, 60 * 256), (9, 0, 30 * 256), (39, 0, 15)),
        ('10% Life stolen per hit', '10% Mana stolen per hit'),
    ),
    (
        "Tal Rasha's Lidless Eye",
        'Swirling Crystal',
        78,
        'low',
        ((105, 0, 20), (107, 61, 2), (107, 63, 1), (107, 65, 2)),
        ('Fire Mastery', 'Lightning Mastery', 'Cold Mastery', '(1-2)'),
    ),
    (
        "Trang-Oul's Girth",
        'Troll Belt',
        89,
        'low',
        ((9, 0, 50 * 256), (7, 0, 66 * 256), (153, 0, 1)),
        ('Cannot Be Frozen', '(25-50)'),
    ),
)


def cases():
    for name, base, native, tier, stats, snippets in SPECS:
        item = Item(base, 'set', name, stats, named_table_id=native)
        for label, candidate, scenario in (
            ('intrinsic', item, 'positive'),
            ('unidentified', replace(item, identified=False), 'negative'),
            ('impossible-ethereal', replace(item, ethereal=True), 'negative'),
            ('unread-ethereal', replace(item, ethereal=None), 'unknown'),
        ):
            reviewed = candidate.identified and candidate.ethereal is not True
            specimen_tier = 'med' if name == "Trang-Oul's Girth" and label == 'intrinsic' else tier
            yield Case(
                id=f'remaining-named-set/{name}/{label}',
                item=candidate,
                context={},
                scenario=scenario,
                covers=('named:set:' + name,),
                expected={
                    'assessment': IsPartialDict(trade_tier=IsPartialDict(tier=specimen_tier if reviewed else None)),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                report_contains=(name, 'Trade tier: ' + ('mid' if specimen_tier == 'med' else specimen_tier), *snippets)
                if reviewed
                else (name,),
                report_absent=(('Trade tier:',) if not reviewed else ())
                + (('10% Faster Cast Rate',) if name == "Tal Rasha's Adjudication" else ()),
                evidence=(
                    f'third-parties/d2data/json/setitems.json:/{name}',
                    'pricing/data/wp-i-uniques-misc.json:/ST-' + name.lower().replace("'", '-').replace(' ', '-'),
                ),
            )


CASES = tuple(cases())
