"""Magic charm choices respect native size, skill-tab and utility affixes."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (('small', 'Small Charm', 5, 3), ('large', 'Large Charm', 8, 1), ('grand', 'Grand Charm', 12, 1))
RESISTS = (39, 41, 43, 45)


def cases():
    for slug, base, fhr, mf in EXAMPLES:
        role = 'abyss-warlock-table-charm-' + slug
        item = Item(base, 'magic', raw_stats=tuple((s, 0, 3) for s in RESISTS), complete=True)
        keys = tuple(f'{s}:0' for s in RESISTS)
        rows = [
            ('minimum-allres', item, {'player_class': 'Warlock'}, 'true', keys),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false', ()),
            ('unknown-class', item, {}, 'unknown', ()),
            ('ethereal', replace(item, ethereal=True), {'player_class': 'Warlock'}, 'false', ()),
            ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Warlock'}, 'unknown', ()),
            ('invalid-sockets', replace(item, sockets=1), {'player_class': 'Warlock'}, 'false', ()),
            ('mf-only', replace(item, raw_stats=((80, 0, mf),)), {'player_class': 'Warlock'}, 'true', ('80:0',)),
            ('fhr-only', replace(item, raw_stats=((99, 0, fhr),)), {'player_class': 'Warlock'}, 'true', ('99:0',)),
            (
                'one-missing-resist',
                replace(item, raw_stats=item.raw_stats[1:]),
                {'player_class': 'Warlock'},
                'false',
                (),
            ),
            ('unread-utility', replace(item, raw_stats=(), complete=False), {'player_class': 'Warlock'}, 'unknown', ()),
            (
                'attack-only',
                replace(item, raw_stats=((19, 0, 10), (22, 0, 1))),
                {'player_class': 'Warlock'},
                'false',
                (),
            ),
        ]
        if slug == 'grand':
            rows += [
                (
                    'chaos-skiller',
                    replace(item, raw_stats=((188, 58, 1), (7, 0, 37 * 256))),
                    {'player_class': 'Warlock'},
                    'true',
                    ('188:58', '7:0'),
                ),
                ('different-tab', replace(item, raw_stats=((188, 56, 1),)), {'player_class': 'Warlock'}, 'false', ()),
                ('other-class-tab', replace(item, raw_stats=((188, 40, 1),)), {'player_class': 'Warlock'}, 'false', ()),
            ]
        for label, candidate, context, truth, expected_keys in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in expected_keys}
                    )
                )
            yield Case(
                id=f'abyss/magic-charms/{slug}/{label}',
                item=candidate,
                context=context,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                absent_stat_configurations=dict.fromkeys(('19:0', '22:0', '188:56', '188:40'), (role + '-stats',)),
                report_contains=(base,),
                evidence=(
                    'pricing/data/appraisal-guide-sections.json',
                    'third-parties/d2data/json/magicprefix.json',
                    'third-parties/d2data/json/magicsuffix.json',
                ),
            )


CASES = tuple(cases())
