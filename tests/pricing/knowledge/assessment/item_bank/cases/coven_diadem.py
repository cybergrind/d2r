"""Coven Diadem: inserted Ist MF and recipe rolls remain distinct."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


ROLE = 'fire-warlock-guide-coven-helmets-aura-recipe'
CONFIG = ROLE + '-stats'
LETHARGY = (393 << 6) | 10
# Native recipe: 1 skills,20FCR,30-50EDef,1-15MF,1-5LAEK,5%level10Lethargy.
# Helmet Ist contributes25MF, Ral30fire resistance, Io10vitality.
RAW = (
    (127, 0, 1),
    (105, 0, 20),
    (16, 0, 30),
    (80, 0, 26),
    (86, 0, 1),
    (39, 0, 30),
    (3, 0, 10),
    (201, LETHARGY, 5),
    (194, 0, 3),
)


def cases():
    context = {'player_class': 'Warlock'}
    for quality in ('normal', 'superior', 'low_quality'):
        original = NativeRunewordItem(
            'Diadem',
            quality,
            'Coven',
            RAW,
            sockets=3,
            socket_contents='filled',
            runeword='Coven',
            socket_items=tuple(SocketItem(r) for r in ('Ist Rune', 'Ral Rune', 'Io Rune')),
        )
        for label, item, ctx, truth, mf in (
            ('minimum', original, context, 'true', True),
            (
                'maximum',
                replace(
                    original,
                    raw_stats=tuple(
                        (s, p, 50 if s == 16 else 40 if s == 80 else 5 if s == 86 else v) for s, p, v in RAW
                    ),
                ),
                context,
                'true',
                True,
            ),
            ('tiara-is-different-source-base', replace(original, base='Tiara'), context, 'false', True),
            ('ethereal', replace(original, ethereal=True), context, 'false', True),
            ('wrong-class', original, {'player_class': 'Sorceress'}, 'false', True),
            ('unknown-class', original, {}, 'unknown', True),
            (
                'unread-mf',
                replace(original, raw_stats=tuple(row for row in RAW if row[0] != 80)),
                context,
                'true',
                False,
            ),
        ):
            active = truth == 'true'
            keys = ['127:0', '105:0', '16:0', '86:0', '39:0', '3:0']
            if mf:
                keys.append('80:0')
            expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(CONFIG)) for key in keys})
                )
            excluded = [f'201:{LETHARGY}'] + ([] if mf else ['80:0'])
            yield Case(
                id=f'coven-diadem/{quality}/{label}',
                item=item,
                context=ctx,
                covers=(ROLE,),
                scenario='unknown' if truth == 'unknown' or not mf else 'positive' if active else 'negative',
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if active else (CONFIG,),
                absent_stat_configurations=dict.fromkeys(excluded, (CONFIG,)),
                report_contains=(
                    'Coven',
                    'Sockets: 3 — Ist, Ral, Io',
                    'Sigil: Lethargy',
                    '(30-65%)' if quality == 'superior' else '(30-50%)',
                    '(1-5)',
                    *(('(26-40%)',) if mf else ()),
                ),
                detail_contains=(
                    'Added Ist magic find is separate from the recipe roll.',
                    'Sigil Lethargy when struck is not assumed active;',
                )
                if label == 'minimum'
                else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/fire-warlock-guide/slots/Helmets/4',
                    'third-parties/d2data/json/runes.json:/Coven',
                    'third-parties/d2data/json/gems.json:/r24',
                    'third-parties/d2data/json/skills.json:/393',
                ),
            )


CASES = tuple(cases())
