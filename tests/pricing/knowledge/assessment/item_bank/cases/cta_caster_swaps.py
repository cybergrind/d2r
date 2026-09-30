"""Native CTA recipes and independent prebuff rolls in seven caster swap uses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


RUNES = tuple(SocketItem(name + ' Rune') for name in ('Amn', 'Ral', 'Mal', 'Ist', 'Ohm'))
USES = (
    ('Warlock', False, (('blood-boil-warlock-guide', 29), ('summoner-warlock-guide', 29))),
    (
        'Sorceress',
        True,
        (
            ('frozen-orb-sorceress', 29),
            ('frozen-orb-meteor-sorceress', 29),
            ('fire-wall-sorceress-guide', 30),
            ('hydra-sorceress', 29),
        ),
    ),
    ('Necromancer', True, (('summoner-necromancer-guide', 33),)),
)


def cta(quality, *, bo=1, bc=2, cry=1):
    return NativeRunewordItem(
        'Crystal Sword',
        quality,
        'Call to Arms',
        (
            (194, 0, 5),
            (97, 149, bo),
            (97, 155, bc),
            (97, 146, cry),
            (127, 0, 1),
            (93, 0, 40),
            (17, 0, 250),
            (18, 0, 250),
            (74, 0, 12),
            (60, 0, 7),
            (48, 0, 5),
            (49, 0, 30),
            (117, 0, 1),
            (80, 0, 30),
        ),
        sockets=5,
        socket_contents='filled',
        socket_items=RUNES,
        runeword='Call to Arms',
        complete=True,
    )


def cases():
    for klass, exact, sources in USES:
        roles = tuple(g + '-call-to-arms-weapon-swap-core-caster-word-gear' for g, _ in sources)
        configs = tuple(r + '-stats' for r in roles)
        context = {'player_class': klass}
        for quality in ('normal', 'superior', 'low_quality'):
            item = cta(quality)
            examples = [
                ('minimum', item, context, 'true'),
                ('maximum', cta(quality, bo=6, bc=6, cry=4), context, 'true'),
                ('bo-perfect-only', cta(quality, bo=6), context, 'true'),
                ('bc-perfect-only', cta(quality, bc=6), context, 'true'),
                ('wrong-class', item, {'player_class': 'Amazon'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), context, 'true'),
                ('unknown-ethereal', observation(item, ethereal=None), context, 'true'),
                ('wrong-recipe', replace(item, socket_items=RUNES[::-1]), context, 'false'),
                ('empty', replace(item, socket_items=(), socket_contents='empty'), context, 'false'),
                ('unidentified', replace(item, identified=False), context, 'false'),
            ]
            if quality == 'normal':
                examples.append(('flail', replace(item, base='Flail'), context, 'false' if exact else 'true'))
                for skill in (149, 155):
                    raw = tuple(s for s in item.raw_stats if s[:2] != (97, skill))
                    examples.extend(
                        (
                            (f'missing-{skill}', replace(item, raw_stats=raw), context, 'false'),
                            (f'unread-{skill}', replace(item, raw_stats=raw, complete=False), context, 'unknown'),
                        )
                    )
            for label, candidate, loadout, truth in examples:
                assessment = {
                    'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))
                }
                if label in ('wrong-recipe', 'empty', 'unidentified') or (label == 'flail' and exact):
                    assessment = {}
                if truth == 'true':
                    assessment['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(*configs))
                                for key in ('97:149', '97:155', '127:0')
                            }
                        )
                    )
                expected = {'assessment': IsPartialDict(**assessment)}
                if label in ('wrong-recipe', 'empty', 'unidentified'):
                    expected['extraction'] = IsPartialDict(item=IsPartialDict(runeword=None))
                if label in ('minimum', 'maximum', 'bo-perfect-only', 'bc-perfect-only'):
                    expected['extraction'] = IsPartialDict(
                        item=IsPartialDict(runeword='Call to Arms'),
                        decoded_stats=Contains(
                            *(
                                IsPartialDict(
                                    memory_stat=IsPartialDict(id=97, layer=skill),
                                    roll_range=IsPartialDict(min=low, max=high),
                                    roll_quality='perfect' if raw == high else 'low',
                                )
                                for skill, low, high in ((149, 1, 6), (155, 2, 6), (146, 1, 4))
                                for sid, layer, raw in candidate.raw_stats
                                if (sid, layer) == (97, skill)
                            )
                        ),
                    )
                yield Case(
                    id=f'cta-caster/{klass}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=roles,
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    expected=expected,
                    absent_configurations=() if truth == 'true' else configs,
                    absent_stat_configurations=dict.fromkeys(('17:0', '18:0', '93:0', '60:0'), configs),
                    report_contains=('Call to Arms', 'Sockets: 5 — Amn, Ral, Mal, Ist, Ohm')
                    if label == 'minimum'
                    else (),
                    evidence=(
                        'third-parties/d2data/json/runes.json:/Call to Arms',
                        *(
                            'pricing/data/appraisal-guide-sections.json:/sources/'
                            f'pricing~1raw~1mr~1guides__{g}.html/sections/{section}'
                            for g, section in sources
                        ),
                    ),
                )


CASES = tuple(cases())
