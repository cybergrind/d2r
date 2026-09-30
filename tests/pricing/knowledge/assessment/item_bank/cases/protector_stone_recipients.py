"""Protector's Stone priorities depend on the wearer and intended recipient."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    ('double-throw-barbarian-guide', 2, 'Helmet', 'Barbarian', 'Harlequin Crest', True, True),
    ('gold-find-barbarian', 1, 'Helmet', 'Barbarian', "Immortal King's Will", True, False),
    ('gold-find-barbarian', 3, 'Helmet', 'Barbarian', "Immortal King's Will", True, True),
    ('mirrored-blades-warlock-guide', 1, 'Weapon', 'Warlock', 'Tomb Reaver', True, True),
    ('mirrored-blades-warlock-guide', 2, 'Helmet', 'Warlock', "Guillaume's Face", True, True),
    ('smite-paladin', 1, 'Off-Hand', 'Paladin', 'Herald of Zakarum', True, True),
    ('smite-paladin', 2, 'Helmet', 'Paladin', 'Crown of Ages', True, True),
    ('strafe-amazon', 1, 'Weapon', 'Amazon', 'Windforce', True, True),
    ('strafe-amazon', 2, 'Weapon', 'Amazon', 'Witchwild String', True, True),
    ('summoner-necromancer-guide', 1, 'Helmet', 'Necromancer', 'Harlequin Crest', False, False),
    ('summoner-necromancer-guide', 2, 'Helmet', 'Necromancer', 'Harlequin Crest', False, False),
)


def stone(*, maximum=False, damage_only=False):
    ed, flat = (50, 30) if maximum or damage_only else (30, 10)
    pierce, xp, mf, gold = (10, 5, 35, 50) if maximum else (5, 3, 15, 25)
    # uniqueitems:424; property selectors verified from native property tables.
    return Item(
        'Colossal Jewel',
        'unique',
        "Protector's Stone",
        (
            (17, 0, ed),
            (18, 0, ed),
            (21, 0, flat),
            (22, 0, flat),
            (366, 0, pierce),
            (85, 0, xp),
            (80, 0, mf),
            (79, 0, gold),
            (201, 267 * 64 + 15, 1),
        ),
        named_table_id=424,
        complete=True,
    )


def cases():
    for guide, variant, slot, klass, host, damage, pierce in SPECS:
        role = f'{guide}-protector-s-stone-v{variant}-{slot.lower().replace(" ", "-")}-0-named-socket-jewel'
        config = role + '-stats'
        context = {'player_class': klass, 'player_items': [host]}
        item = stone()
        examples = (
            ('minimum', item, context, 'true', True),
            ('maximum', stone(maximum=True), context, 'true', True),
            ('damage-perfect-find-low', stone(damage_only=True), context, 'true', True),
            ('wrong-class', item, dict(context, player_class='Sorceress'), 'false', False),
            ('unknown-class', item, {'player_items': [host]}, 'unknown', False),
            ('missing-recipient', item, dict(context, player_items=[]), 'true', False),
            ('unknown-recipient', item, {'player_class': klass}, 'true', False),
            ('unidentified', replace(item, identified=False), context, 'false', False),
            ('ethereal', replace(item, ethereal=True), context, 'false', False),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown', False),
            ('impossible-socket', replace(item, sockets=1), context, 'false', False),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown', False),
            (
                'unread-pierce',
                replace(item, complete=False, raw_stats=tuple(s for s in item.raw_stats if s[0] != 366)),
                context,
                'unknown',
                False,
            ),
        )
        for label, candidate, loadout, truth, active in examples:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                keys = ['85:0', '80:0', '79:0']
                if damage:
                    keys.extend(('17:0', '18:0'))
                if pierce:
                    keys.append('366:0')
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            absent = {'21:0': (config,), '22:0': (config,), f'201:{267 * 64 + 15}': (config,)}
            if not damage:
                absent.update({'17:0': (config,), '18:0': (config,)})
            if not pierce:
                absent['366:0'] = (config,)
            result = {'assessment': IsPartialDict(**expected)}
            if active:
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        *(
                            IsPartialDict(
                                memory_stat=IsPartialDict(id=sid),
                                roll_range=IsPartialDict(min=low, max=high),
                                roll_quality='perfect' if label == 'maximum' else 'low',
                            )
                            for sid, low, high in ((366, 5, 10), (85, 3, 5), (80, 15, 35), (79, 25, 50))
                        )
                    )
                )
            ed = 30 if label == 'minimum' else 50
            yield Case(
                id=f'protector-stone/{role}/{label}',
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
                absent_stat_configurations=absent,
                report_contains=("Protector's Stone", f'+{ed}% (30-50%) Enhanced Damage') if active else (),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/424',
                    f'pricing/data/wp-a-builds.json:/{guide}/variants/{variant}/player/{slot}/0',
                ),
            )


CASES = tuple(cases())
