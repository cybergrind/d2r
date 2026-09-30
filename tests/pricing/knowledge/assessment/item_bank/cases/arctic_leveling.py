"""Arctic pieces offer conditional Amazon leveling, not standalone set bonuses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


# Native requirements and intrinsic modifiers, independently transcribed from
# setitems/armor/weapons. Partial and full set modifiers are deliberately absent.
REVIEWED = (
    ('Arctic Binding', 'Light Belt', 0, 0, ((43, 0, 40), (31, 0, 32))),
    ('Arctic Furs', 'Quilted Armor', 12, 0, ((16, 0, 300), (39, 0, 10), (41, 0, 10), (43, 0, 10), (45, 0, 10))),
    ('Arctic Horn', 'Short War Bow', 35, 55, ((17, 0, 50), (18, 0, 50))),
    ('Arctic Mitts', 'Light Gauntlets', 45, 0, ((7, 0, 20 * 256), (93, 0, 10))),
)


def cases():
    for name, base, strength, dexterity, stats in REVIEWED:
        item = Item(base, 'set', name, stats)
        context = {
            'player_class': 'Amazon',
            'player_level': 2,
            'player_strength': strength,
            'player_dexterity': dexterity,
            'player_items': [],
        }
        rows = [
            ('equip-level', item, context, 'positive', 'met'),
            ('below-level', item, {**context, 'player_level': 1}, 'negative', 'unmet'),
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
                    trade_tier=IsPartialDict(status='reviewed', tier='low'),
                    leveling=Contains(
                        IsPartialDict(
                            tier='high',
                            status='conditional',
                            required_level=2,
                            requirements_fit=IsPartialDict(status=fit),
                            conditions=Contains(
                                'Requires a compatible Arctic Gear combination; '
                                'a single piece does not grant partial/full-set bonuses.'
                            ),
                        )
                    ),
                )
            )
            yield Case(
                id=f'arctic-leveling/{name}/{label}',
                item=candidate,
                context=loadout,
                scenario=scenario,
                covers=(f'named:set:{name}',),
                expected={'assessment': expected, 'price_estimate': IsPartialDict(estimate_ist=None)},
                report_contains=(name, 'Trade tier: low', 'Leveling: high') if fit else (),
                report_absent=('Trade tier:', 'Leveling:') if fit is None else ('Cannot Be Frozen',),
                evidence=(
                    f'third-parties/d2data/json/setitems.json:/{name}',
                    'third-parties/d2data/json/armor.json',
                    'third-parties/d2data/json/weapons.json',
                    f'pricing/knowledge/assessment/rules/named_leveling_reviews.json:set:{name}',
                    f'pricing/knowledge/assessment/rules/named_tier_reviews.json:set:{name}',
                ),
            )


CASES = tuple(cases())
