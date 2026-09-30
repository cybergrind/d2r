"""Native Giant Skull rolls and socket capacity for physical ranged alternatives."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


def skull(sockets=2, *, high=False):
    # Base 100-157 + flat 250-320; no enhanced defense or socket payload assumed.
    stats = ((31, 0, 477 if high else 350), (0, 0, 35 if high else 25), (136, 0, 10), (81, 0, 1))
    if sockets is not None:
        stats += ((194, 0, sockets),)
    return Item('Bone Visage', 'unique', 'Giant Skull', stats, sockets=sockets, named_table_id=379, complete=True)


def cases():
    for build, klass, index in (
        ('strafe-amazon', 'Amazon', 5),
        ('double-throw-barbarian-guide', 'Barbarian', 9),
    ):
        role = f'{build}-giant-skull-equipment-tail-alternative'
        config = role + '-stats'
        context = {'player_class': klass}
        examples = [
            (f'{n}-sockets/{"max" if high else "min"}', skull(n, high=high), context, 'true')
            for n in (1, 2)
            for high in (False, True)
        ]
        examples += [
            ('wrong-class', skull(), {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', skull(), {}, 'unknown'),
            (
                'ethereal-max-defense',
                replace(skull(high=True), ethereal=True, raw_stats=((31, 0, 555), *skull(high=True).raw_stats[1:])),
                context,
                'false',
            ),
            ('ethereal-player', replace(skull(), ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(skull(), ethereal=None), context, 'unknown'),
            ('unknown-sockets', skull(None), context, 'unknown'),
            ('zero-sockets', skull(0), context, 'false'),
            ('three-sockets', skull(3), context, 'false'),
            (
                'shael-pair',
                replace(
                    skull(),
                    socket_contents='filled',
                    socket_items=(SocketItem('Shael Rune'), SocketItem('Shael Rune')),
                    raw_stats=(*skull().raw_stats, (99, 0, 40)),
                ),
                context,
                'true',
            ),
            ('unknown-contents', replace(skull(), socket_contents='unknown'), context, 'true'),
        ]
        for label, item, loadout, truth in examples:
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(config), desirability=grade)
                            for key, grade in (
                                ('81:0', 'desirable'),
                                ('194:0', 'desirable'),
                                ('136:0', 'supporting'),
                                ('0:0', 'supporting'),
                            )
                        }
                    )
                )
            if '-sockets/' in label:
                expected['trade_tier'] = IsPartialDict(tier='low' if item.sockets == 2 else 'trash')
            if label == 'unknown-contents':
                expected['contract'] = None
            yield Case(
                id=f'giant-skull/{build}/{label}',
                item=item,
                context=loadout,
                covers=(role,),
                scenario='unknown' if label.startswith('unknown-') else 'positive' if active else 'negative',
                expected={
                    'assessment': IsPartialDict(**expected),
                    **({'price_estimate': IsPartialDict(estimate_ist=None)} if label == 'unknown-contents' else {}),
                },
                absent_configurations=() if active else (config,),
                absent_stat_configurations={'31:0': (config,)},
                report_contains=(
                    'Giant Skull',
                    'Trade tier:',
                    'Knockback',
                    'Crushing Blow',
                    *(('(25-35)',) if label not in ('unknown-contents', 'shael-pair') else ()),
                    *(('40% Faster Hit Recovery', 'Shael, Shael') if label == 'shael-pair' else ()),
                    *((f'Defense: {item.raw_stats[0][2]} (350-477)',) if label != 'unknown-contents' else ()),
                )
                if active
                else ('Defense: 555 (400-555)',)
                if label == 'ethereal-max-defense'
                else (),
                absent_annotations=('93:0',),
                report_absent=('(25-35)',) if label == 'unknown-contents' else (),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/slots/Helmets/{index}',
                    'third-parties/d2data/json/uniqueitems.json:/379',
                    'pricing/knowledge/assessment/rules/named_tier_reviews.json:/rows/unique:Giant Skull',
                    'third-parties/d2data/json/armor.json:/uh9',
                    'third-parties/d2data/json/gems.json:/r13',
                ),
            )


CASES = tuple(cases())
