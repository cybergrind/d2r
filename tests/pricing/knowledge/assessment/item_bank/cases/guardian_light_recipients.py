"""Hex Purge magic bonuses for Echoing Strike setups; not physical-hit multipliers."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = (('echoing-strike-warlock-guide', (2, 3), 'Warlock'),)
RANGES = ((357, 5, 10), (358, 5, 10), (85, 3, 5), (80, 15, 35), (79, 25, 50))


def jewel(perfect=()):
    return Item(
        'Colossal Jewel',
        'unique',
        "Guardian's Light",
        (
            *((sid, 0, high if sid in perfect else low) for sid, low, high in RANGES),
            (52, 0, 15),
            (53, 0, 35),
            (201, 387 * 64 + 25, 1),
        ),
        named_table_id=425,
        complete=True,
    )


def cases():
    for guide, variants, klass in USES:
        for variant in variants:
            role = f'{guide}-guardian-s-light-v{variant}-helmet-0-named-socket-jewel'
            config = role + '-stats'
            recipient = 'Harlequin Crest' if variant == 2 else "Hellwarden's Will"
            context = {'player_class': klass, 'player_items': [recipient]}
            item = jewel()
            examples = [
                ('minimum', item, context, 'true', True, ()),
                ('maximum', jewel(tuple(s[0] for s in RANGES)), context, 'true', True, tuple(s[0] for s in RANGES)),
                ('mastery-only-perfect', jewel((357,)), context, 'true', True, (357,)),
                ('pierce-only-perfect', jewel((358,)), context, 'true', True, (358,)),
                ('wrong-class', item, dict(context, player_class='Barbarian'), 'false', False, ()),
                ('unknown-class', item, {'player_items': [recipient]}, 'unknown', False, ()),
                ('missing-recipient', item, dict(context, player_items=[]), 'true', False, ()),
                ('unknown-recipient', item, {'player_class': klass}, 'true', False, ()),
                ('unidentified', replace(item, identified=False), context, 'false', False, ()),
                ('ethereal', replace(item, ethereal=True), context, 'false', False, ()),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown', False, ()),
                ('socketed', replace(item, sockets=1), context, 'false', False, ()),
                ('unknown-sockets', replace(item, sockets=None), context, 'unknown', False, ()),
            ]
            for sid in (357, 358):
                stats = tuple(s for s in item.raw_stats if s[0] != sid)
                examples.extend(
                    (
                        (f'missing-{sid}', replace(item, raw_stats=stats), context, 'false', False, ()),
                        (
                            f'unread-{sid}',
                            replace(item, raw_stats=stats, complete=False),
                            context,
                            'unknown',
                            False,
                            (),
                        ),
                    )
                )
            for label, candidate, loadout, truth, active, perfect in examples:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {f'{sid}:0': IsPartialDict(configuration_ids=Contains(config)) for sid, _, _ in RANGES}
                        )
                    )
                result = {'assessment': IsPartialDict(**expected)}
                if active:
                    result['extraction'] = IsPartialDict(
                        decoded_stats=Contains(
                            *(
                                IsPartialDict(
                                    memory_stat=IsPartialDict(id=sid),
                                    roll_range=IsPartialDict(min=low, max=high),
                                    roll_quality='perfect' if sid in perfect else 'low',
                                )
                                for sid, low, high in RANGES
                            )
                        )
                    )
                yield Case(
                    id=f'guardian-light/{role}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=(role,),
                    scenario='positive'
                    if active
                    else 'unknown'
                    if label.startswith(('unknown-', 'unread-'))
                    else 'negative',
                    expected=result,
                    absent_configurations=() if active else (config,),
                    absent_stat_configurations=dict.fromkeys(('52:0', '53:0', f'201:{387 * 64 + 25}'), (config,)),
                    report_contains=("Guardian's Light",) if active else (),
                    evidence=(
                        'third-parties/d2data/json/uniqueitems.json:/425',
                        f'pricing/data/wp-a-builds.json:/{guide}/variants/{variant}/player/Helmet/0',
                    ),
                )


CASES = tuple(cases())
