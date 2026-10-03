"""Class armor words: native rune effects and build-specific spell/attack distinctions."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


# Expectations are authored from native runes/gems/skills and the cited guide slots.
WORDS = {
    'Peace': (
        ('Shael', 'Thul', 'Amn'),
        ((83, 0, 2), (97, 9, 2), (99, 0, 20), (43, 0, 30), (78, 0, 14), (198, 32 * 64 + 15, 2), (201, 17 * 64 + 5, 4)),
        {},
        ('83:0', '99:0'),
        ('43:0', '97:9'),
    ),
    'Rain': (
        ('Ort', 'Mal', 'Ith'),
        (
            (83, 5, 2),
            (9, 0, 100 * 256),
            (41, 0, 30),
            (35, 0, 7),
            (114, 0, 15),
            (198, 240 * 64 + 15, 5),
            (201, 235 * 64 + 15, 5),
        ),
        {9: 150 * 256},
        ('83:5', '9:0'),
        ('41:0', '35:0', '114:0'),
    ),
    'Principle': (
        ('Ral', 'Gul', 'Eld'),
        ((83, 3, 2), (7, 0, 100 * 256), (39, 0, 30), (46, 0, 5), (154, 0, 15), (122, 0, 50), (198, 101 * 64 + 5, 100)),
        {7: 150 * 256},
        ('83:3', '7:0'),
        ('39:0', '46:0'),
    ),
    'Enlightenment': (
        # Rune3 is r12 (Sol); the dump's human RunesUsed label incorrectly says Sur.
        ('Pul', 'Ral', 'Sol'),
        ((83, 1, 2), (97, 37, 1), (39, 0, 30), (34, 0, 7), (16, 0, 30), (198, 47 * 64 + 15, 5), (201, 46 * 64 + 15, 5)),
        {},
        ('83:1',),
        ('97:37', '39:0', '34:0', '16:0'),
    ),
    'Bone': (
        ('Sol', 'Um', 'Um'),
        (
            (83, 2, 2),
            (9, 0, 100 * 256),
            (39, 0, 30),
            (41, 0, 30),
            (43, 0, 30),
            (45, 0, 30),
            (34, 0, 7),
            (198, 84 * 64 + 10, 15),
            (201, 68 * 64 + 10, 15),
        ),
        {9: 150 * 256},
        ('83:2', '9:0', '39:0', '41:0', '43:0', '45:0'),
        ('34:0',),
    ),
    'Authority': (
        ('Hel', 'Shael', 'Ral'),
        (
            (83, 7, 2),
            (99, 0, 20),
            (39, 0, 30),
            (17, 0, 40),
            (18, 0, 40),
            (91, 0, -15),
            (198, 399 * 64 + 15, 10),
            (201, 387 * 64 + 10, 2),
        ),
        {17: 60, 18: 60},
        ('83:7', '99:0'),
        ('39:0',),
    ),
}
SPECS = (
    ('fist-of-the-heavens-paladin', 'Paladin', 'Principle', 'Body Armors', 3),
    ('lightning-fury-amazon-guide', 'Amazon', 'Peace', 'Body Armors', 6),
    ('lightning-strike-amazon', 'Amazon', 'Peace', 'Body Armor', 6),
    ('enchant-sorceress', 'Sorceress', 'Enlightenment', 'Body Armor', 6),
    ('fire-warlock-guide', 'Warlock', 'Authority', 'Body Armors', 3),
    ('fissure-druid', 'Druid', 'Rain', 'Body Armor', 6),
    ('poison-nova-necromancer', 'Necromancer', 'Bone', 'Body Armor', 5),
    ('summoner-necromancer-guide', 'Necromancer', 'Bone', None, 33),
)


def armor(word, quality, maximum=False):
    runes, stats, maxima, _, _ = WORDS[word]
    return NativeRunewordItem(
        'Mage Plate',
        quality,
        word,
        (*((s, p, maxima.get(s, v) if maximum else v) for s, p, v in stats), (194, 0, 3)),
        sockets=3,
        socket_contents='filled',
        runeword=word,
        socket_items=tuple(SocketItem(r + ' Rune') for r in runes),
    )


def cases():
    for build, klass, word, slot, index in SPECS:
        role = (
            f'{build}-player-{word.lower()}-{slot.lower().replace(" ", "-")}-main-alternatives-support-word-alternative'
            if slot
            else f'{build}-bone-caster-armor-remainder'
        )
        source = (
            f'pricing/data/wp-a-builds.json:/{build}/slots/{slot}/{index}'
            if slot
            else 'pricing/data/appraisal-guide-sections.json:/sources/'
            f'pricing~1raw~1mr~1guides__{build}.html/sections/{index}'
        )
        config = role + '-stats'
        runes, stats, _, desirable, supporting = WORDS[word]
        keys = (*desirable, *supporting)
        ignored = tuple(f'{s}:{p}' for s, p, _ in stats if s in (198, 201))
        if word == 'Authority':
            ignored += ('17:0', '18:0')
        if word == 'Principle':
            ignored += ('122:0',)
        context = {'player_class': klass}
        for quality in ('normal', 'superior', 'low_quality'):
            item = armor(word, quality)
            variants = [
                ('minimum', item, context, 'true'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', observation(item, ethereal=None), context, 'unknown'),
                ('wrong-class', item, {'player_class': 'Barbarian'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-recipe', replace(item, socket_items=item.socket_items[::-1]), context, 'false'),
                ('empty', replace(item, socket_items=(), socket_contents='empty'), context, 'false'),
                ('wrong-family', replace(item, base='Bone Visage'), context, 'false'),
            ]
            if WORDS[word][2]:
                variants.append(('maximum', armor(word, quality, True), context, 'true'))
            for label, candidate, loadout, truth in variants:
                active = truth == 'true'
                expected = {}
                if label not in ('unidentified', 'wrong-recipe', 'empty', 'wrong-family'):
                    expected['roles'] = Contains(
                        IsPartialDict(id=role, side='player', rule_trace=IsPartialDict(truth=truth))
                    )
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(
                                    contributions=Contains(
                                        IsPartialDict(
                                            configuration_id=config,
                                            desirability='desirable' if key in desirable else 'supporting',
                                        )
                                    )
                                )
                                for key in keys
                            }
                        )
                    )
                yield Case(
                    id=f'class-armor-alternatives/{build}/{word}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    absent_configurations=() if active else (config,),
                    absent_stat_configurations=dict.fromkeys(('105:0', '93:0', *ignored), (config,)),
                    report_contains=(word, ', '.join(runes)) if active else (),
                    evidence=(
                        source,
                        f'third-parties/d2data/json/runes.json:/{word}',
                        'third-parties/d2data/json/gems.json',
                        'third-parties/d2data/json/skills.json',
                    ),
                )


CASES = tuple(cases())
