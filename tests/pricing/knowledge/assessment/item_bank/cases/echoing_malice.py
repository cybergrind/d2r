"""Malice supplies Open Wounds in the documented full-Sazabi Frenzy setup."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


ROLE = 'echoing-strike-warlock-guide-malice-ubers-source-recipe'
COMPANIONS = ("Sazabi's Cobalt Redeemer", "Sazabi's Ghost Liberator", "Sazabi's Mental Sheath")
CONTEXT = {'player_class': 'Warlock', 'mercenary_type': 'Act 5 Frenzy', 'mercenary_items': list(COMPANIONS)}
# Partial captured stats include El attack rating and Eth target defense.
# Weapon damage and canceled light-radius totals are deliberately not invented.
ITEM = Item(
    'Mythical Sword',
    'normal',
    'Malice',
    (
        (135, 0, 100),
        (17, 0, 33),
        (18, 0, 33),
        (19, 0, 50),
        (116, 0, 25),
        (117, 0, 1),
        (74, 0, -5),
        (120, 0, -100),
        (194, 0, 3),
    ),
    ethereal=True,
    sockets=3,
    socket_contents='filled',
    runeword='Malice',
    socket_items=tuple(SocketItem(name) for name in ('Ith Rune', 'El Rune', 'Eth Rune')),
)


def cases():
    rows = [('complete-setup', ITEM, CONTEXT, True)]
    rows.extend((quality, replace(ITEM, rarity=quality), CONTEXT, True) for quality in ('superior', 'low_quality'))
    rows.extend(
        (f'missing-piece-{i}', ITEM, {**CONTEXT, 'mercenary_items': [n for n in COMPANIONS if n != name]}, False)
        for i, name in enumerate(COMPANIONS)
    )
    rows.extend(
        [
            ('unknown-companions', ITEM, {k: v for k, v in CONTEXT.items() if k != 'mercenary_items'}, False),
            ('player-companions', ITEM, {**CONTEXT, 'mercenary_items': [], 'player_items': list(COMPANIONS)}, False),
            ('wrong-class', ITEM, {**CONTEXT, 'player_class': 'Paladin'}, False),
            ('wrong-mercenary', ITEM, {**CONTEXT, 'mercenary_type': 'Act 2 Might'}, False),
            ('unknown-mercenary', ITEM, {**CONTEXT, 'mercenary_type': None}, False),
            ('wrong-base', replace(ITEM, base='Crystal Sword'), CONTEXT, False),
            ('nonethereal', replace(ITEM, ethereal=False), CONTEXT, False),
            ('unknown-ethereal', replace(ITEM, ethereal=None), CONTEXT, False),
            ('unidentified', replace(ITEM, identified=False), CONTEXT, False),
        ]
    )
    for label, item, context, usable in rows:
        yield Case(
            id='echoing/malice/' + label,
            item=item,
            context=context,
            expected={
                'assessment': IsPartialDict(
                    stat_evaluation=IsPartialDict(
                        annotations=IsPartialDict({'135:0': IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))})
                    )
                )
            }
            if usable
            else {},
            covers=(ROLE,),
            scenario='positive' if usable else 'unknown' if label.startswith('unknown') else 'negative',
            absent_configurations=() if usable else (ROLE + '-stats',),
            absent_stat_configurations={'117:0': (ROLE + '-stats',), '74:0': (ROLE + '-stats',)},
            report_contains=("Setup: Sazabi's Cobalt Redeemer in the mercenary setup",) if usable else (),
            evidence=(
                'pricing/raw/mr/guides__echoing-strike-warlock-guide.html:/sections/25',
                'third-parties/d2data/json/runes.json:/Malice',
            ),
        )


def quality_boundaries():
    # These exact Uber mercenary uses are not generic starter-equipment cases.
    for quality in ('superior', 'low_quality'):
        item = replace(ITEM, rarity=quality)
        native = NativeRunewordItem(**vars(item))
        for label, candidate, context, usable in (
            ('native', native, CONTEXT, True),
            ('wrong-mercenary', native, {**CONTEXT, 'mercenary_type': 'Act 2 Might'}, False),
            ('missing-set-piece', native, {**CONTEXT, 'mercenary_items': list(COMPANIONS[:2])}, False),
            ('unknown-companions', native, {k: v for k, v in CONTEXT.items() if k != 'mercenary_items'}, False),
            ('nonethereal', replace(native, ethereal=False), CONTEXT, False),
            ('unknown-ethereal', replace(item, ethereal=None), CONTEXT, False),
        ):
            yield Case(
                id=f'echoing/malice/{quality}/{label}',
                item=candidate,
                context=context,
                covers=(ROLE,),
                scenario='positive' if usable else 'unknown' if label.startswith('unknown') else 'negative',
                expected={
                    'assessment': IsPartialDict(
                        stat_evaluation=IsPartialDict(
                            annotations=IsPartialDict(
                                {
                                    '135:0': IsPartialDict(configuration_ids=Contains(ROLE + '-stats')),
                                }
                            )
                        )
                    )
                }
                if usable
                else {},
                absent_configurations=() if usable else (ROLE + '-stats',),
                absent_stat_configurations={'117:0': (ROLE + '-stats',), '74:0': (ROLE + '-stats',)},
                report_contains=('Malice', 'Ith, El, Eth', *(('(33-48%)',) if quality == 'superior' else ()))
                if usable
                else (),
                evidence=(
                    'pricing/raw/mr/guides__echoing-strike-warlock-guide.html:/sections/25',
                    'third-parties/d2data/json/runes.json:/Malice',
                ),
            )


CASES = (*cases(), *quality_boundaries())
