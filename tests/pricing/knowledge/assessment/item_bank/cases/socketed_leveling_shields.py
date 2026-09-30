"""Empty sockets preserve equip costs; socket payloads require variant evaluation."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


REVIEWS = (
    ("Moser's Blessed Circle", 'Round Shield', 225, 31, 53, 2, 25),
    ('The Ward', 'Gothic Shield', 101, 26, 60, 1, 40),
)


def cases():
    for name, base, native, level, strength, sockets, resistance in REVIEWS:
        stats = tuple((stat, 0, resistance) for stat in (39, 41, 43, 45))
        item = Item(base, 'unique', name, (*stats, (194, 0, sockets)), sockets=sockets)
        context = {
            'player_class': 'Sorceress',
            'player_level': level,
            'player_strength': strength,
            'player_dexterity': 0,
        }
        for label, candidate, loadout, scenario, fit in (
            ('empty', item, context, 'positive', 'met'),
            ('below-level', item, {**context, 'player_level': level - 1}, 'negative', 'unmet'),
            ('below-strength', item, {**context, 'player_strength': strength - 1}, 'negative', 'unmet'),
            ('unknown-contents', replace(item, socket_contents='unknown'), context, 'unknown', 'unknown'),
            (
                'filled',
                replace(
                    item, socket_contents='filled', socket_items=tuple(SocketItem('Hel Rune') for _ in range(sockets))
                ),
                context,
                'unknown',
                'unknown',
            ),
            ('unidentified', replace(item, identified=False), context, 'negative', None),
        ):
            visible = (name, 'Trade tier: low') if fit else ()
            if label in ('empty', 'below-level', 'below-strength'):
                visible += (f'Sockets: {sockets} — {sockets} empty',)
            elif label == 'filled':
                visible += (f'Sockets: {sockets} — ' + ', '.join('Hel' for _ in range(sockets)),)
            elif label == 'unknown-contents':
                visible += (f'Sockets: {sockets} — contents not captured',)
            yield Case(
                id=f'socketed-leveling-shield/{name}/{label}',
                item=candidate,
                context=loadout,
                scenario=scenario,
                covers=(f'named:unique:{name}',),
                expected={
                    'assessment': IsPartialDict(
                        trade_tier=IsPartialDict(tier='low' if fit else None),
                        leveling=Contains(IsPartialDict(tier='med', requirements_fit=IsPartialDict(status=fit)))
                        if fit
                        else [],
                    ),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                report_contains=visible,
                report_absent=('Leveling: mid', 'Leveling: low')
                + (('Trade tier:', 'Leveling:') if fit is None else ()),
                evidence=(
                    f'third-parties/d2data/json/uniqueitems.json:/{native}',
                    'third-parties/D2MOO/source/D2Common/src/Items/Items.cpp:ITEMS_GetLevelRequirement',
                    'pricing/knowledge/assessment/rules/named_baselines.json',
                    f'pricing/knowledge/assessment/rules/named_leveling_reviews.json:unique:{name}',
                ),
            )


CASES = tuple(cases())
