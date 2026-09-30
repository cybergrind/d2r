"""Optional set pieces keep conditional leveling advice separate from trade demand."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


REVIEWED = (
    ('Angelic Mantle', 'Ring Mail', 12, 36, 0, 'med', 'Angelic Raiment', ((34, 0, 3), (16, 0, 40))),
    ('Angelic Sickle', 'Saber', 12, 25, 25, 'med', 'Angelic Raiment', ((19, 0, 75),)),
    ("Death's Touch", 'War Sword', 6, 71, 45, 'high', "Death's Disguise", ((17, 0, 25), (18, 0, 25), (60, 0, 4))),
)


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
            ('below-strength', item, {**context, 'player_strength': strength - 1}, 'negative', 'unmet'),
            ('unknown-level', item, {k: v for k, v in context.items() if k != 'player_level'}, 'unknown', 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'negative', None),
        ]
        if dexterity:
            rows.append(('below-dexterity', item, {**context, 'player_dexterity': dexterity - 1}, 'negative', 'unmet'))
        for label, candidate, loadout, scenario, fit in rows:
            expected = (
                IsPartialDict(leveling=[])
                if fit is None
                else IsPartialDict(
                    trade_tier=IsPartialDict(status='reviewed', tier='trash'),
                    leveling=Contains(
                        IsPartialDict(
                            tier=tier,
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
                id=f'optional-leveling-set/{name}/{label}',
                item=candidate,
                context=loadout,
                scenario=scenario,
                covers=(f'named:set:{name}',),
                expected={'assessment': expected, 'price_estimate': IsPartialDict(estimate_ist=None)},
                report_contains=(name, 'Trade tier: trash', *(('Leveling: high',) if tier == 'high' else ()))
                if fit
                else (),
                report_absent=('Leveling: mid', 'Leveling: low')
                + (('Trade tier:', 'Leveling:') if fit is None else ('30% Increased Attack Speed',)),
                evidence=(
                    f'third-parties/d2data/json/setitems.json:/{name}',
                    'pricing/knowledge/assessment/rules/named_tier_reviews.json',
                    f'pricing/knowledge/assessment/rules/named_leveling_reviews.json:set:{name}',
                ),
            )


CASES = tuple(cases())
