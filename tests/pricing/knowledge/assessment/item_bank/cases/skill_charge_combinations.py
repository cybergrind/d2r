"""Magic +3 skill-tab/Teleport combinations and Poison Nova travel dependencies."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


NO_ENIGMA = 'This Teleport-charge alternative requires Enigma not to be equipped.'


def travel_cases():
    for base, suffix, level, maximum in (('Long Staff', 'staf', 6, 33), ('Amulet', 'amul', 2, 25)):
        role = 'poison-nova-necromancer-teleport-' + suffix
        for quality in ('magic', 'rare'):
            item = Item(base, quality, raw_stats=((204, 54 * 64 + level, (maximum << 8) | 1),), complete=True)
            for label, equipment, truth in (
                ('bramble', ['Bramble'], 'true'),
                ('no-enigma', [], 'true'),
                ('enigma', ['Enigma'], 'false'),
                ('unknown-equipment', None, 'unknown'),
            ):
                context = {'player_class': 'Necromancer'}
                if equipment is not None:
                    context['player_items'] = equipment
                yield Case(
                    id=f'skill-charge-travel/{suffix}/{quality}/{label}',
                    item=item,
                    context=context,
                    expected={
                        'assessment': IsPartialDict(
                            roles=Contains(
                                IsPartialDict(
                                    id=role,
                                    rule_trace=IsPartialDict(truth='true'),
                                    dependencies=Contains(IsPartialDict(label=NO_ENIGMA, status=truth)),
                                )
                            )
                        )
                    },
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    report_contains=(base, 'Teleport'),
                    detail_contains=(
                        f'{ {"true": "Setup", "false": "Needs", "unknown": "Check"}[truth] }: {NO_ENIGMA}',
                    ),
                    evidence=('pricing/data/wp-a-builds.json:/poison-nova-necromancer/variants/1/quotes/3',),
                )


def combination_cases():
    for build, player, tab, prefix, index in (
        ('fissure-druid', 'Druid', 42, 501, 7),
        ('poison-nova-necromancer', 'Necromancer', 17, 462, 6),
    ):
        role = build + '-skill-charge-combination'
        config = role + '-stats'
        charge = (204, 3458, (25 << 8) | 1)
        skill = (188, tab, 3)
        item = Item('Amulet', 'magic', raw_stats=(skill, charge), complete=True)
        context = {'player_class': player}
        rows = (
            ('both', item, context, 'true', 'true'),
            ('depleted', replace(item, raw_stats=(skill, (204, 3458, 25 << 8))), context, 'true', 'false'),
            ('two-skills', replace(item, raw_stats=((188, tab, 2), charge)), context, 'false', 'true'),
            ('wrong-tree', replace(item, raw_stats=((188, 16, 3), charge)), context, 'false', 'true'),
            ('charge-only', replace(item, raw_stats=(charge,)), context, 'false', 'true'),
            ('skills-only', replace(item, raw_stats=(skill,)), context, 'false', 'false'),
            ('unread-charge', replace(item, raw_stats=(skill,), complete=False), context, 'unknown', 'unknown'),
            ('unread-skills', replace(item, raw_stats=(charge,), complete=False), context, 'unknown', 'true'),
            ('ethereal', replace(item, ethereal=True), context, 'false', 'true'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown', 'true'),
            ('socketed', replace(item, sockets=1), context, 'false', 'true'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown', 'true'),
            ('wrong-class', item, {'player_class': 'Barbarian'}, 'false', 'true'),
            ('unknown-class', item, {}, 'unknown', 'true'),
        )
        for label, candidate, loadout, truth, charged in rows:
            yield Case(
                id=f'skill-charge-combination/{build}/{label}',
                item=candidate,
                context=loadout,
                expected={
                    'assessment': IsPartialDict(
                        roles=Contains(
                            IsPartialDict(
                                id=role,
                                rule_trace=IsPartialDict(truth=truth),
                                dependencies=Contains(IsPartialDict(status=charged, trace=IsPartialDict(expected=1))),
                            )
                        )
                    )
                },
                covers=(role,),
                scenario='negative'
                if charged == 'false'
                else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (config,),
                report_contains=('Amulet',),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/slots/Amulets/{index}',
                    f'third-parties/d2data/json/magicprefix.json:/{prefix}',
                    'third-parties/d2data/json/magicsuffix.json:/533',
                ),
            )
        yield Case(
            id=f'skill-charge-combination/{build}/rare-cannot-have-three-skill-prefix',
            item=replace(item, rarity='rare'),
            context=context,
            expected={},
            covers=(f'role:{role}:magic',),
            scenario='negative',
            absent_roles=(role,),
            absent_configurations=(config,),
            evidence=(f'third-parties/d2data/json/magicprefix.json:/{prefix}',),
        )


CASES = (*travel_cases(), *combination_cases())
