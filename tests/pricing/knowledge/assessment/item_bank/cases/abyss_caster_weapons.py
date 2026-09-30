"""Abyss named caster weapons; attack and elemental bonuses are not magic damage."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


FACET = SocketItem('Jewel', ((48, 0, 17), (49, 0, 45), (333, 0, 5), (329, 0, 5), (197, 56 * 64 + 31, 100)), True)
EXAMPLES = (
    (
        'mang-song',
        14,
        Item(
            'Archon Staff',
            'unique',
            "Mang Song's Lesson",
            ((127, 0, 5), (105, 0, 30), (27, 0, 10), (333, 0, 12), (334, 0, 7), (335, 0, 7), (329, 0, 5)),
            sockets=1,
            socket_contents='filled',
            socket_items=(FACET,),
        ),
        None,
        ('127:0', '105:0', '27:0'),
        ('333:0', '334:0', '335:0', '329:0'),
    ),
    (
        'ondal',
        15,
        Item(
            'Elder Staff',
            'unique',
            "Ondal's Wisdom",
            ((127, 0, 2), (105, 0, 45), (1, 0, 40), (31, 0, 450), (85, 0, 5), (35, 0, 5)),
        ),
        None,
        ('127:0', '105:0', '1:0', '85:0'),
        (),
    ),
    (
        'razorswitch',
        16,
        Item(
            'Jo Staff',
            'unique',
            'Razorswitch',
            (
                (127, 0, 1),
                (105, 0, 30),
                (9, 0, 175 * 256),
                (7, 0, 80 * 256),
                (35, 0, 15),
                (78, 0, 15),
                *((s, 0, 50) for s in (39, 41, 43, 45)),
            ),
        ),
        'Walking Stick',
        ('127:0', '105:0', '9:0', '7:0', '39:0'),
        ('78:0',),
    ),
    (
        'suicide-branch',
        17,
        Item(
            'Burnt Wand',
            'unique',
            'Suicide Branch',
            (
                (127, 0, 1),
                (105, 0, 50),
                (77, 0, 10),
                (7, 0, 40 * 256),
                (78, 0, 25),
                *((s, 0, 10) for s in (39, 41, 43, 45)),
            ),
        ),
        'Polished Wand',
        ('127:0', '105:0', '77:0', '7:0'),
        ('78:0',),
    ),
    (
        'spectral-shard',
        18,
        Item(
            'Blade',
            'unique',
            'Spectral Shard',
            ((105, 0, 50), (9, 0, 50 * 256), (19, 0, 55), *((s, 0, 10) for s in (39, 41, 43, 45))),
        ),
        'Legend Spike',
        ('105:0', '9:0', '39:0'),
        ('19:0',),
    ),
    (
        'wizardspike',
        19,
        Item(
            'Bone Knife',
            'unique',
            'Wizardspike',
            ((105, 0, 50), (217, 0, 16 * 256), (77, 0, 15), (27, 0, 15), *((s, 0, 75) for s in (39, 41, 43, 45))),
        ),
        None,
        ('105:0', '217:0', '77:0', '27:0', '39:0'),
        (),
    ),
)


def cases():
    context = {'player_class': 'Warlock'}
    for slug, span, item, upgrade, keys, irrelevant in EXAMPLES:
        role = 'abyss-warlock-player-table-' + slug
        rows = [
            ('native-low', item, context, 'positive'),
            ('wrong-class', item, {'player_class': 'Paladin'}, 'negative'),
            ('unknown-class', item, {}, 'unknown'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
            ('ethereal', replace(item, ethereal=True), context, 'negative' if slug == 'wizardspike' else 'positive'),
            (
                'unknown-ethereal',
                replace(item, ethereal=None),
                context,
                'unknown' if slug == 'wizardspike' else 'positive',
            ),
        ]
        if upgrade:
            rows.append(('upgraded', replace(item, base=upgrade), context, 'positive'))
        if slug == 'mang-song':
            rows.extend(
                (
                    ('wrong-filler', replace(item, socket_items=(SocketItem('El Rune'),)), context, 'negative'),
                    ('unread-filler', replace(item, socket_items=()), context, 'unknown'),
                    ('empty', replace(item, socket_contents='empty', socket_items=()), context, 'negative'),
                )
            )
        else:
            rows.append(('empty-socket', replace(item, sockets=1), context, 'positive'))
        for label, candidate, ctx, scenario in rows:
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        side='player',
                        rule_trace=IsPartialDict(
                            truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                        ),
                    )
                )
            }
            if scenario == 'positive':
                if slug == 'wizardspike':
                    expected['facts'] = IsPartialDict(stats=IsPartialDict({'217:0': IsPartialDict(value=160)}))
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            yield Case(
                id=f'abyss/caster-weapons/{slug}/{label}',
                item=candidate,
                context=ctx,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                absent_stat_configurations=dict.fromkeys(irrelevant, (role + '-stats',)),
                report_contains=(item.name, 'Trade tier:'),
                evidence=(
                    'pricing/data/appraisal-guide-sections.json:/sources/'
                    f'pricing~1raw~1mr~1guides__abyss-warlock-build-guide.html/item_spans/{span}',
                ),
            )


CASES = tuple(cases())
