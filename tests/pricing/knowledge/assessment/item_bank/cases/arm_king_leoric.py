"""Summoner wand skill priorities and on-struck hazards survive native/elite appraisal."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'summoner-necromancer-arm-king-leoric-alternative'
CONFIG = ROLE + '-stats'
RAW = (
    (188, 18, 2),
    (188, 17, 2),
    (107, 69, 3),
    (107, 70, 3),
    (107, 77, 2),
    (107, 80, 2),
    (105, 0, 10),
    (217, 0, 10 * 256),  # mana/lvl coefficient includes the native mana ValShift
    (201, 93 * 64 + 10, 5),
    (201, 88 * 64 + 2, 10),
)
PRIORITIES = {
    '188:18': 'desirable',
    '188:17': 'supporting',
    '107:69': 'desirable',
    '107:70': 'desirable',
    '105:0': 'supporting',
    '217:0': 'supporting',
}


def cases():
    context = {'player_class': 'Necromancer'}
    for base in ('Tomb Wand', 'Lich Wand'):
        original = Item(base, 'unique', 'Arm of King Leoric', RAW, named_table_id=141)
        rows = [
            ('native-skills', original, context, 'true'),
            ('ethereal-casting', replace(original, ethereal=True), context, 'true'),
            ('unknown-ethereal', replace(original, ethereal=None), context, 'true'),
            ('wrong-class', original, {'player_class': 'Warlock'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
            ('unidentified', replace(original, identified=False), context, 'false'),
            ('uncaptured-stats', replace(original, raw_stats=()), context, 'true'),
            ('lower-viewer-level', replace(original, viewer_level=36), context, 'true'),
        ]
        for key in PRIORITIES:
            stat, layer = map(int, key.split(':'))
            rows.append(
                (
                    'unread-' + key,
                    replace(original, raw_stats=tuple(s for s in RAW if s[:2] != (stat, layer))),
                    context,
                    'true',
                )
            )
        for label, item, loadout, truth in rows:
            captured = {f'{a}:{b}' for a, b, _ in item.raw_stats}
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
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
            yield Case(
                id=f'arm-king-leoric/{base}/{label}',
                item=item,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=(ROLE,),
                scenario='unknown'
                if truth == 'unknown' or label.startswith(('uncaptured', 'unread'))
                else 'positive'
                if active
                else 'negative',
                absent_configurations=() if active else (CONFIG,),
                absent_stat_configurations=dict.fromkeys(
                    ('107:77', '107:80', '201:5962', '201:5634', *(k for k in PRIORITIES if k not in captured)),
                    (CONFIG,),
                ),
                report_contains=(
                    ('Arm of King Leoric', 'Trade tier:')
                    + ((f'+{item.viewer_level * 10 // 8} to Mana',) if '217:0' in captured else ())
                )
                if item.identified
                else (),
                detail_contains=('Bone Prison can trigger when struck',) if active else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/summoner-necromancer-guide/slots/Weapon/2',
                    'third-parties/d2data/json/uniqueitems.json:/141',
                ),
            )


CASES = tuple(cases())
