"""Fortitude report intervals require native recipe identity, not a supplied name."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.fortitude_variant_roles import RUNES, STATS
from tests.pricing.knowledge.assessment.item_bank.models import Case
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


ROLE = 'double-throw-barbarian-guide-1-player-fortitude'


def cases():
    for quality in ('normal', 'superior'):
        for coefficient, value, tone in ((2048, 80, 'low'), (2304, 90, 'normal'), (3072, 120, 'perfect')):
            for resistance in (25, 30):
                item = NativeRunewordItem(
                    'Archon Plate',
                    quality,
                    'Fortitude',
                    tuple(
                        (sid, layer, coefficient if sid == 216 else resistance if sid in (39, 41, 43, 45) else raw)
                        for sid, layer, raw in STATS
                    ),
                    sockets=4,
                    socket_contents='filled',
                    socket_items=RUNES,
                    runeword='Fortitude',
                )
                yield Case(
                    id=f'fortitude-native-ranges/{quality}/{coefficient}/{resistance}',
                    item=item,
                    context={'player_class': 'Barbarian'},
                    covers=(ROLE,),
                    expected={
                        'extraction': IsPartialDict(
                            decoded_stats=Contains(
                                IsPartialDict(memory_stat=IsPartialDict(id=216), roll_quality=tone),
                                IsPartialDict(
                                    memory_stat=IsPartialDict(id=39),
                                    roll_quality='low' if resistance == 25 else 'perfect',
                                ),
                            )
                        ),
                        'assessment': IsPartialDict(
                            roles=Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth='true')))
                        ),
                    },
                    report_contains=(
                        f'+{value} (80-120) to Life (Based on Character Level)',
                        f'Fire Resist +{resistance}% (25-30%)',
                        'Sockets: 4 — El, Sol, Dol, Lo',
                    ),
                    evidence=(
                        'third-parties/d2data/json/runes.json:/Fortitude',
                        'pricing/data/wp-a-builds.json:/double-throw-barbarian-guide/variants/1',
                    ),
                )


CASES = tuple(cases())
