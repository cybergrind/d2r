"""Generic guide alternatives allow casting bases, without valuing attack leech."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.hoto_variants import ITEM
from tests.pricing.knowledge.assessment.item_bank.models import Case


USES = (
    ('Warlock', False, (('blood-boil-warlock-guide', 29), ('summoner-warlock-guide', 29))),
    ('Sorceress', False, (('fire-wall-sorceress-guide', 30), ('hydra-sorceress', 29))),
    ('Sorceress', True, (('frozen-orb-sorceress', 29), ('frozen-orb-meteor-sorceress', 29))),
)
KEYS = ('127:0', '105:0', '77:0', '74:0', '2:0', '39:0', '41:0', '43:0', '45:0')


def cases():
    for klass, flail_only, sources in USES:
        roles = tuple(guide + '-heart-of-the-oak-weapon-core-caster-word-gear' for guide, _ in sources)
        configs = tuple(role + '-stats' for role in roles)
        context = {'player_class': klass}
        for quality in ('normal', 'superior', 'low_quality'):
            item = replace(ITEM, rarity=quality, ethereal=False, raw_stats=(*ITEM.raw_stats, (62, 0, 7)))
            examples = [
                ('minimum', item, context, 'true'),
                ('wrong-class', item, {'player_class': 'Amazon'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), context, 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
            ]
            if quality == 'normal':
                examples.extend(
                    (
                        ('knout', replace(item, base='Knout'), context, 'false' if flail_only else 'true'),
                        ('staff', replace(item, base='Battle Staff'), context, 'false' if flail_only else 'true'),
                        ('unidentified', replace(item, identified=False), context, 'false'),
                        ('empty', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                        (
                            'unknown-contents',
                            replace(item, socket_contents='unknown', socket_items=()),
                            context,
                            'unknown',
                        ),
                        ('component-fcr', item, {**context, 'player_total_fcr': 40}, 'true'),
                        (
                            'perfect',
                            replace(
                                item,
                                raw_stats=tuple(
                                    (sid, layer, 40 if sid in (39, 41, 43, 45) else raw)
                                    for sid, layer, raw in item.raw_stats
                                ),
                            ),
                            context,
                            'true',
                        ),
                    )
                )
            for label, candidate, loadout, truth in examples:
                expected = {
                    'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))
                }
                if flail_only and label in ('knout', 'staff'):
                    # The reviewed native base filter removes this role before
                    # predicate evaluation. Still forbid its stat annotations.
                    expected = {}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in KEYS}
                        )
                    )
                yield Case(
                    id=f'hoto-caster/{klass}/{"flail" if flail_only else "generic"}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=roles,
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_configurations=() if truth == 'true' else configs,
                    absent_stat_configurations={'62:0': configs},
                    report_contains=('Heart of the Oak', 'Sockets: 4 — Ko, Vex, Pul, Thul')
                    if label == 'minimum'
                    else (),
                    evidence=(
                        *(
                            'pricing/data/appraisal-guide-sections.json:/sources/'
                            f'pricing~1raw~1mr~1guides__{guide}.html/sections/{section}'
                            for guide, section in sources
                        ),
                        'third-parties/d2data/json/runes.json:/Heart of the Oak',
                    ),
                )


CASES = tuple(cases())
