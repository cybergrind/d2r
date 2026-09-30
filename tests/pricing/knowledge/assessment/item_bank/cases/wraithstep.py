"""Wraithstep's random Warlock tab is distinct from its movement and attributes."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'fire-warlock-guide-wraithstep-caster-utility-alternative'
CONFIG = ROLE + '-stats'
PRIORITIES = {
    '188:58': 'desirable',
    '96:0': 'desirable',
    '99:0': 'desirable',
    '31:0': 'supporting',
    '2:0': 'supporting',
    '1:0': 'supporting',
}
# Native Mirrored Boots: 59-68 base defense, Wraithstep adds 40-60; no ED.
RAW = ((188, 58, 1), (96, 0, 30), (99, 0, 20), (31, 0, 99), (2, 0, 10), (1, 0, 10))


def cases():
    original = Item('Mirrored Boots', 'unique', 'Wraithstep', RAW, named_table_id=413)
    ctx = {'player_class': 'Warlock'}
    rows = [
        (
            f'{tree}-{roll}',
            replace(
                original,
                raw_stats=((188, tab, 1), (96, 0, 30), (99, 0, 20), (31, 0, defense), (2, 0, roll), (1, 0, roll)),
            ),
            ctx,
            'true',
        )
        for tree, tab in (('Demon', 56), ('Eldritch', 57), ('Chaos', 58))
        for roll, defense in ((10, 99), (15, 128))
    ]
    rows += [
        ('complete-' + label, replace(item, complete=True), context, truth) for label, item, context, truth in rows
    ]
    rows += [
        ('unidentified', replace(original, identified=False), ctx, 'false'),
        ('wrong-class', original, {'player_class': 'Sorceress'}, 'false'),
        ('unknown-class', original, {}, 'unknown'),
        ('ethereal', replace(original, ethereal=True), ctx, 'false'),
        ('unknown-ethereal', replace(original, ethereal=None), ctx, 'unknown'),
        ('invalid-socket', replace(original, sockets=1, raw_stats=(*RAW, (194, 0, 1))), ctx, 'false'),
        ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), ctx, 'unknown'),
        ('unread-all-stats', replace(original, raw_stats=()), ctx, 'true'),
    ]
    for key in PRIORITIES:
        pair = tuple(map(int, key.split(':')))
        rows.append(('unread-' + key, replace(original, raw_stats=tuple(s for s in RAW if s[:2] != pair)), ctx, 'true'))
    for label, item, context, truth in rows:
        active = truth == 'true'
        captured = {f'{s}:{p}' for s, p, _ in item.raw_stats}
        assessment = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if active:
            assessment['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(
                            contributions=Contains(
                                IsPartialDict(configuration_id=CONFIG, role_id=ROLE, desirability=grade)
                            )
                        )
                        for key, grade in PRIORITIES.items()
                        if key in captured
                    }
                )
            )
        rolled = label.removeprefix('complete-').startswith(('Demon-', 'Eldritch-', 'Chaos-'))
        defense_range = ('(99-128)',) if label.startswith('complete-') else ()
        yield Case(
            id='wraithstep/fire/' + label,
            item=item,
            context=context,
            expected={'assessment': IsPartialDict(**assessment), 'price_estimate': IsPartialDict(estimate_ist=None)},
            covers=(ROLE,),
            scenario='unknown'
            if truth == 'unknown' or label.startswith('unread')
            else 'positive'
            if active
            else 'negative',
            absent_configurations=() if active else (CONFIG,),
            absent_stat_configurations={
                key: (CONFIG,)
                for key in (*PRIORITIES, '188:56', '188:57')
                if key not in captured or key not in PRIORITIES
            },
            report_contains=(
                f'+1 to {label.removeprefix("complete-").split("-")[0]} Skills (Warlock Only)',
                '(10-15)',
                'Trade tier: high',
                *defense_range,
            )
            if rolled
            else (),
            detail_contains=('prioritize Chaos for this fire build', 'Skill bonuses do not grant hard-point synergies')
            if active
            else (),
            evidence=(
                'pricing/data/wp-a-builds.json:/fire-warlock-guide/slots/Boots/0',
                'third-parties/d2data/json/uniqueitems.json:/413',
                'third-parties/d2data/json/armor.json:/utb',
                'third-parties/d2data/json/propertygroups.json:/skilltab-war',
            ),
        )


CASES = tuple(cases())
