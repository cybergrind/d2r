"""Gerke's standalone Sorceress alternative: flat reduction, no invented ES/max block."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'lightning-sorceress-gerke-s-sanctuary-caster-shield-alternative'
CONFIG = ROLE + '-stats'
# Native uniqueitems 228: flat physical 11-16, magic 14-18, ED 180-240,
# 20-30 all resistances; fixed 15 replenish life and 30 increased block.
ITEM = Item(
    'Pavise',
    'unique',
    "Gerke's Sanctuary",
    ((34, 0, 11), (35, 0, 14), (16, 0, 180), (74, 0, 15), (20, 0, 30), *((stat, 0, 20) for stat in (39, 41, 43, 45))),
)


def cases():
    context = {'player_class': 'Sorceress'}
    for label, item, ctx, truth in (
        ('minimum-rolls', ITEM, context, 'true'),
        (
            'maximum-rolls',
            replace(
                ITEM,
                raw_stats=(
                    (34, 0, 16),
                    (35, 0, 18),
                    (16, 0, 240),
                    (74, 0, 15),
                    (20, 0, 30),
                    *((stat, 0, 30) for stat in (39, 41, 43, 45)),
                ),
            ),
            context,
            'true',
        ),
        ('upgraded', replace(ITEM, base='Aegis'), context, 'true'),
        ('empty-socket', replace(ITEM, sockets=1, raw_stats=(*ITEM.raw_stats, (194, 0, 1))), context, 'true'),
        ('ethereal', replace(ITEM, ethereal=True), context, 'false'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown'),
        ('unknown-sockets', replace(ITEM, sockets=None, socket_contents='unknown'), context, 'unknown'),
        ('wrong-class', ITEM, {'player_class': 'Paladin'}, 'false'),
        ('unknown-class', ITEM, {}, 'unknown'),
        ('unidentified', replace(ITEM, identified=False), context, 'false'),
    ):
        active = truth == 'true'
        expected = {'roles': Contains(IsPartialDict(id=ROLE, side='player', rule_trace=IsPartialDict(truth=truth)))}
        if active:
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(CONFIG))
                        for key in ('34:0', '35:0', '20:0', '39:0', '41:0', '43:0', '45:0', '74:0')
                    }
                )
            )
        yield Case(
            id='gerke-lightning/' + label,
            item=item,
            context=ctx,
            covers=(ROLE,),
            scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
            expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
            absent_configurations=() if active else (CONFIG,),
            report_contains=(
                ("Gerke's Sanctuary", 'Trade tier:')
                + (() if label == 'unknown-sockets' else ('(11-16)', '(14-18)', '(180-240%)'))
            )
            if item.identified
            else (),
            # Unknown socket contributions cannot be ranked as an intrinsic roll.
            report_absent=('11% Damage Reduced', '14% Magic Damage Reduced', '75% Chance to Block')
            + (('(11-16)', '(14-18)', '(180-240%)') if label == 'unknown-sockets' else ()),
            evidence=(
                'pricing/data/wp-a-builds.json:/lightning-sorceress/slots/Off-Hand/2',
                'third-parties/d2data/json/uniqueitems.json:/228',
            ),
        )


CASES = tuple(cases())
