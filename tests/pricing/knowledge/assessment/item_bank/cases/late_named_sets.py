"""Late set baselines persist with missing facets; companions never invent stats."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


REVIEWED = (
    (
        "Griswold's Honor",
        'Vortex Shield',
        ((102, 0, 65), (20, 0, 20), (39, 0, 45), (41, 0, 45), (43, 0, 45), (45, 0, 45)),
        3,
        'med',
        ('65% Faster Block Rate', 'Sockets: 3'),
        "Griswold's Honor",
    ),
    (
        "M'avina's True Sight",
        'Diadem',
        ((93, 0, 30), (74, 0, 10), (9, 0, 25 * 256)),
        0,
        'med',
        ('30% Increased Attack Speed',),
        "M'avina's True Sight",
    ),
    (
        "Tal Rasha's Guardianship",
        'Lacquered Plate',
        ((80, 0, 88), (39, 0, 40), (41, 0, 40), (43, 0, 40)),
        0,
        'med',
        ('88% Better Chance of Getting Magic Items',),
        "Tal Rasha's Howling Wind",
    ),
    (
        "Tal Rasha's Fine-Spun Cloth",
        'Mesh Belt',
        ((80, 0, 12), (9, 0, 30 * 256), (2, 0, 20)),
        0,
        'low',
        (),
        "Tal Rasha's Fire-Spun Cloth",
    ),
)


def cases():
    for name, base, stats, sockets, tier, snippets, native in REVIEWED:
        item = Item(base, 'set', name, stats + (((194, 0, sockets),) if sockets else ()), sockets=sockets)
        for label, candidate, scenario in (
            ('intrinsic', item, 'positive'),
            ('unknown-sockets', replace(item, raw_stats=stats, sockets=None, socket_contents='unknown'), 'unknown'),
            ('unidentified', replace(item, identified=False), 'negative'),
            ('impossible-ethereal-set', replace(item, ethereal=True), 'negative'),
        ):
            reviewed = candidate.identified and candidate.ethereal is False
            leveling = []
            if reviewed and name == "Tal Rasha's Fine-Spun Cloth":
                leveling = Contains(
                    IsPartialDict(
                        tier='med', requirements_fit=IsPartialDict(status='met' if label == 'intrinsic' else 'unknown')
                    )
                )
            expected = IsPartialDict(
                trade_tier=IsPartialDict(status='reviewed', tier=tier) if reviewed else IsPartialDict(tier=None),
                leveling=leveling,
            )
            visible = (name, f'Trade tier: {"mid" if tier == "med" else tier}') if reviewed else ()
            if label == 'intrinsic':
                visible += snippets
            yield Case(
                id=f'late-named-set/{name}/{label}',
                item=candidate,
                context={
                    'player_class': 'Sorceress',
                    'player_level': 80,
                    'player_strength': 200,
                    'player_dexterity': 200,
                },
                scenario=scenario,
                covers=(f'named:set:{name}',),
                expected={'assessment': expected, 'price_estimate': IsPartialDict(estimate_ist=None)},
                report_contains=visible,
                report_absent=('Leveling: mid', 'Leveling: low')
                + (('Trade tier:', 'Leveling:') if not reviewed else ('10% Faster Cast Rate',)),
                evidence=(
                    f'third-parties/d2data/json/setitems.json:/{native}',
                    'pricing/knowledge/assessment/rules/named_baselines.json',
                    f'pricing/knowledge/assessment/rules/named_leveling_reviews.json:set:{name}',
                ),
            )


CASES = tuple(cases())

# Tal's intrinsic -20% requirements use base58 + trunc(58 * -20 / 100) = 47.
# The item's own dexterity bonus is not subtracted from an equip requirement.
TAL_BELT = Item('Mesh Belt', 'set', "Tal Rasha's Fine-Spun Cloth", ((80, 0, 12), (91, 0, -20), (2, 0, 20)))
CASES += tuple(
    Case(
        id=f'tal-belt-requirements/{label}',
        item=TAL_BELT,
        context={'player_level': level, 'player_strength': strength, 'player_dexterity': 0},
        scenario=scenario,
        covers=("named:set:Tal Rasha's Fine-Spun Cloth",),
        expected={
            'assessment': IsPartialDict(
                trade_tier=IsPartialDict(tier='low'),
                leveling=Contains(
                    IsPartialDict(
                        requirements={'level': 53, 'strength': 47, 'dexterity': 0},
                        requirements_fit=IsPartialDict(status=fit),
                    )
                ),
            ),
            'price_estimate': IsPartialDict(estimate_ist=None),
        },
        report_contains=('Trade tier: low',),
        report_absent=('Leveling: mid', 'Leveling: low'),
        evidence=(
            "third-parties/d2data/json/setitems.json:/Tal Rasha's Fire-Spun Cloth",
            'third-parties/D2MOO/source/D2Common/src/Items/Items.cpp:ITEMS_CheckRequirements',
        ),
    )
    for label, level, strength, scenario, fit in (
        ('minimum', 53, 47, 'positive', 'met'),
        ('below-strength', 53, 46, 'negative', 'unmet'),
        ('below-level', 52, 47, 'negative', 'unmet'),
        ('unknown-strength', 53, None, 'unknown', 'unknown'),
    )
)
