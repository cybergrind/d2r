"""Explicit staff alternatives separate magic-damage utility from elemental piercing."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_caster_weapons import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.models import Case


REVIEWS = (
    ('mang-song', 'mang-song-s-lesson', ('127:0', '105:0', '27:0'), ('333:0', '334:0', '335:0', '329:0')),
    ('ondal', 'ondal-s-wisdom', ('127:0', '105:0', '1:0', '31:0', '85:0', '35:0'), ()),
)


def cases():
    for slug, name, keys, irrelevant in REVIEWS:
        item = next(item for label, _, item, _, _, _ in EXAMPLES if label == slug)
        role = f'abyss-warlock-build-guide-{name}-caster-utility-alternative'
        context = {'player_class': 'Warlock'}
        rows = [
            ('observed', item, context, 'true', keys),
            ('ethereal-casting', replace(item, ethereal=True), context, 'true', keys),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'true', keys),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false', ()),
            ('unknown-class', item, {}, 'unknown', ()),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown', ()),
            ('invalid-sockets', replace(item, sockets=2), context, 'false', ()),
            ('unidentified', replace(item, identified=False), context, 'false', ()),
        ]
        if slug == 'ondal':
            rows += [
                (
                    'perfect-skills',
                    replace(
                        item,
                        raw_stats=tuple(
                            (stat, layer, 4 if stat == 127 else value) for stat, layer, value in item.raw_stats
                        ),
                    ),
                    context,
                    'true',
                    keys,
                ),
                ('one-empty-socket', replace(item, sockets=1), context, 'true', keys),
            ]
        else:
            rows.append(
                (
                    'no-facet',
                    replace(
                        item,
                        sockets=0,
                        socket_contents='empty',
                        socket_items=(),
                        raw_stats=((127, 0, 5), (105, 0, 30), (27, 0, 10), (333, 0, 7), (334, 0, 7), (335, 0, 7)),
                    ),
                    context,
                    'true',
                    keys,
                )
            )
        for label, candidate, loadout, truth, expected_keys in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if expected_keys:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in expected_keys}
                    )
                )
            yield Case(
                id=f'abyss/staff-alternatives/{slug}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if expected_keys else (role + '-stats',),
                absent_stat_configurations=dict.fromkeys(irrelevant, (role + '-stats',)),
                report_contains=(candidate.name, 'Trade tier:') if truth == 'true' else (candidate.name,),
                evidence=('pricing/data/wp-a-builds.json', 'third-parties/d2data/json/uniqueitems.json'),
            )


CASES = tuple(cases())
