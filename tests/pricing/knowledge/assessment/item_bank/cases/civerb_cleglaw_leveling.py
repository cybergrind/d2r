"""Early attack sets retain piece-specific trade tiers and conditional leveling."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


REVIEWED = (
    ("Civerb's Cudgel", 'Grand Scepter', 9, 37, 0, 'low', "Civerb's Vestments", ((19, 0, 75), (22, 0, 20))),
    ("Civerb's Icon", 'Amulet', 9, 0, 0, 'trash', "Civerb's Vestments", ((26, 0, 40), (74, 0, 4))),
    ("Civerb's Ward", 'Large Shield', 9, 34, 0, 'trash', "Civerb's Vestments", ((20, 0, 15),)),
    ("Cleglaw's Claw", 'Small Shield', 4, 22, 0, 'low', "Cleglaw's Brace", ((110, 0, 75),)),
    ("Cleglaw's Pincers", 'Chain Gloves', 4, 25, 0, 'low', "Cleglaw's Brace", ((81, 0, 1), (150, 0, 25))),
    ("Cleglaw's Tooth", 'Long Sword', 4, 55, 39, 'low', "Cleglaw's Brace", ((141, 0, 50),)),
)


INTRINSIC_REPORT = {
    "Cleglaw's Pincers": ('Knockback', 'Slows Target by 25%'),
    "Cleglaw's Tooth": ('50% Deadly Strike',),
}


def cases():
    for name, base, level, strength, dexterity, tier, set_name, stats in REVIEWED:
        item = Item(base, 'set', name, stats)
        context = {
            'player_class': 'Paladin',
            'player_level': level,
            'player_strength': strength,
            'player_dexterity': dexterity,
            'player_items': [],
        }
        rows = [
            ('minimum-requirements', item, context, 'positive', 'met'),
            ('below-level', item, {**context, 'player_level': level - 1}, 'negative', 'unmet'),
            ('unknown-level', item, {k: v for k, v in context.items() if k != 'player_level'}, 'unknown', 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'negative', None),
        ]
        if strength:
            rows.append(('below-strength', item, {**context, 'player_strength': strength - 1}, 'negative', 'unmet'))
        if dexterity:
            rows.append(('below-dexterity', item, {**context, 'player_dexterity': dexterity - 1}, 'negative', 'unmet'))
        for label, candidate, loadout, scenario, fit in rows:
            expected = (
                IsPartialDict(leveling=[])
                if fit is None
                else IsPartialDict(
                    trade_tier=IsPartialDict(status='reviewed', tier=tier),
                    leveling=Contains(
                        IsPartialDict(
                            tier='med',
                            status='conditional',
                            required_level=level,
                            requirements_fit=IsPartialDict(status=fit),
                            conditions=Contains(
                                f'Requires a compatible {set_name} combination; '
                                'a single piece does not grant partial/full-set bonuses.'
                            ),
                        )
                    ),
                )
            )
            yield Case(
                id=f'civerb-cleglaw-leveling/{name}/{label}',
                item=candidate,
                context=loadout,
                scenario=scenario,
                covers=(f'named:set:{name}',),
                expected={'assessment': expected, 'price_estimate': IsPartialDict(estimate_ist=None)},
                report_contains=(name, f'Trade tier: {tier}', *INTRINSIC_REPORT.get(name, ())) if fit else (),
                report_absent=('Leveling: mid', 'Leveling: low')
                + (('Trade tier:', 'Leveling:') if fit is None else ('30% Increased Attack Speed',)),
                evidence=(
                    f'third-parties/d2data/json/setitems.json:/{name}',
                    'pricing/knowledge/assessment/rules/named_tier_reviews.json',
                    f'pricing/knowledge/assessment/rules/named_leveling_reviews.json:set:{name}',
                ),
            )


CASES = tuple(cases())
