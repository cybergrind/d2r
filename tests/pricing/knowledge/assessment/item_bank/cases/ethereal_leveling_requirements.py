"""Ethereal equip boundaries retain native level and the intended wearer's costs."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


REVIEWS = (
    (
        'Shaftstop',
        'Mesh Armor',
        215,
        38,
        82,
        0,
        'merc',
        'med',
        0,
        ((16, 0, 200), (36, 0, 30), (7, 0, 60 * 256)),
        '(180-220%)',
    ),
    (
        'Bonehew',
        'Ogre Axe',
        387,
        64,
        185,
        65,
        'merc',
        'med',
        2,
        ((17, 0, 300), (18, 0, 300), (93, 0, 30), (194, 0, 2)),
        '(270-320%)',
    ),
    (
        'Steeldriver',
        'Great Maul',
        24,
        29,
        40,
        0,
        'player',
        'high',
        0,
        ((17, 0, 200), (18, 0, 200), (93, 0, 40), (91, 0, -50)),
        '(150-250%)',
    ),
)


def cases():
    for name, base, native, level, strength, dexterity, side, tier, sockets, stats, roll in REVIEWS:
        item = Item(base, 'unique', name, stats, ethereal=True, sockets=sockets)
        wearer = 'mercenary' if side == 'merc' else 'player'
        context = {
            'player_class': 'Paladin',
            'player_level': 99,
            'player_strength': 300,
            'player_dexterity': 300,
            f'{wearer}_level': level,
            f'{wearer}_strength': strength,
            f'{wearer}_dexterity': dexterity,
        }
        variants = [
            ('minimum', item, context, 'positive', 'met', True),
            ('below-level', item, {**context, f'{wearer}_level': level - 1}, 'negative', 'unmet', True),
            ('below-strength', item, {**context, f'{wearer}_strength': strength - 1}, 'negative', 'unmet', True),
            ('unknown-strength', item, {**context, f'{wearer}_strength': None}, 'unknown', 'unknown', True),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown', 'unknown', False),
            ('unidentified', replace(item, identified=False), context, 'negative', None, False),
        ]
        if dexterity:
            variants.append(
                ('below-dexterity', item, {**context, f'{wearer}_dexterity': dexterity - 1}, 'negative', 'unmet', True)
            )
        for label, candidate, loadout, scenario, fit, known in variants:
            requirements = {'level': level, 'strength': strength, 'dexterity': dexterity} if known else {}
            yield Case(
                id=f'ethereal-leveling-requirements/{name}/{label}',
                item=candidate,
                context=loadout,
                scenario=scenario,
                covers=(f'named:unique:{name}',),
                expected={
                    'assessment': IsPartialDict(
                        trade_tier=IsPartialDict(tier='low' if fit else None),
                        leveling=Contains(
                            IsPartialDict(
                                tier=tier,
                                side=side,
                                requirements=requirements,
                                requirements_fit=IsPartialDict(status=fit),
                            )
                        )
                        if fit
                        else [],
                    ),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                report_contains=(name, 'Trade tier: low', *(('Leveling: high',) if tier == 'high' else ()), roll)
                if fit
                else (),
                report_absent=('Leveling: mid', 'Leveling: low')
                + (('Trade tier:', 'Leveling:') if fit is None else ()),
                evidence=(
                    f'third-parties/d2data/json/uniqueitems.json:/{native}',
                    'third-parties/D2MOO/source/D2Common/src/Items/Items.cpp:ITEMS_CheckRequirements',
                    'pricing/knowledge/assessment/rules/named_baselines.json',
                    f'pricing/knowledge/assessment/rules/named_leveling_reviews.json:unique:{name}',
                ),
            )


CASES = tuple(cases())
