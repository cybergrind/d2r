"""Native early set pieces retain trade tiers independently of equip readiness."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


# Independently reviewed native requirements and standalone stats. No set bonuses
# are inserted merely because the item belongs to a useful combination.
REVIEWED = (
    ("Death's Guard", 'Sash', 48, 0, ((31, 0, 22), (153, 0, 1)), None),
    (
        "Death's Hand",
        'Leather Gloves',
        47,
        0,
        ((45, 0, 50), (110, 0, 75)),
        "Equip Death's Guard as the second Death's Disguise piece for the recommended attack-speed bonus.",
    ),
    (
        "Sigon's Gage",
        'Gauntlets',
        35,
        60,
        ((0, 0, 10), (19, 0, 20)),
        "Equip at least one other Sigon's Complete Steel piece for the recommended attack-speed bonus.",
    ),
    (
        "Sigon's Sabot",
        'Greaves',
        38,
        70,
        ((96, 0, 20), (43, 0, 40)),
        "With 2 pieces of Sigon's Complete Steel the boots add attack rating; "
        '3 pieces are required for magic find. Movement and cold resistance work on the boots alone.',
    ),
    (
        "Sigon's Visor",
        'Great Helm',
        36,
        63,
        ((9, 0, 30 * 256), (31, 0, 55)),
        "Equip at least one other Sigon's Complete Steel piece for the recommended attack-rating bonus.",
    ),
    (
        "Sigon's Wrap",
        'Plated Belt',
        39,
        60,
        ((39, 0, 20), (7, 0, 20 * 256)),
        'Life and fire resistance are standalone; its per-level defense bonus needs a second Sigon piece.',
    ),
)


def cases():
    for name, base, _native_id, strength, stats, condition in REVIEWED:
        item = Item(base, 'set', name, stats)
        context = {'player_class': 'Paladin', 'player_strength': strength, 'player_dexterity': 0, 'player_items': []}
        rows = [
            ('equip-level', item, {**context, 'player_level': 6}, 'positive', 'met'),
            ('below-level', item, {**context, 'player_level': 5}, 'negative', 'unmet'),
            ('unknown-level', item, context, 'unknown', 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'negative', None),
        ]
        if strength:
            rows.append(
                (
                    'below-strength',
                    item,
                    {**context, 'player_level': 6, 'player_strength': strength - 1},
                    'negative',
                    'unmet',
                )
            )
        for label, candidate, loadout, scenario, fit in rows:
            leveling = {
                'tier': 'med',
                'required_level': 6,
                'requirements_fit': IsPartialDict(status=fit),
                'source': IsPartialDict(id='mrllamasc-transcript'),
            }
            if condition:
                leveling['conditions'] = Contains(condition)
            expected = (
                IsPartialDict(
                    trade_tier=IsPartialDict(status='reviewed', tier='low'),
                    leveling=Contains(IsPartialDict(**leveling)),
                )
                if fit
                else IsPartialDict(leveling=[])
            )
            yield Case(
                id=f'leveling-set/{name}/{label}',
                item=candidate,
                context=loadout,
                scenario=scenario,
                covers=(f'named:set:{name}',),
                expected={'assessment': expected, 'price_estimate': IsPartialDict(estimate_ist=None)},
                report_contains=(
                    name,
                    'Trade tier: low',
                    *(('Leveling: high',) if name in ("Death's Hand", "Death's Guard") else ()),
                )
                if fit
                else (),
                report_absent=('Trade tier:', 'Leveling:')
                if fit is None
                else ('Leveling: mid', '30% Increased Attack Speed')
                if name in ("Death's Hand", "Sigon's Gage")
                else ('Leveling: mid',),
                evidence=(
                    f'third-parties/d2data/json/setitems.json:/{name}',
                    'pricing/knowledge/assessment/rules/named_tier_reviews.json',
                    f'pricing/knowledge/assessment/rules/named_leveling_reviews.json:set:{name}',
                    'pricing/data/appraisal-recommendations.json',
                ),
            )


CASES = tuple(cases())
