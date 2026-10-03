"""Reviewed original unsocketed Vampire Gaze roll partitions; upgrades remain separate."""

from collections import Counter
from itertools import product

from inventory_tracking.items.metadata import decode_stats, metadata
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.definition_store import catalog
from pricing.knowledge.market_base_catalog import equipment_base


NAME = 'Vampire Gaze'
AXES = (range(6, 9), range(6, 9), range(15, 21), range(10, 16), (False, True))


def template_contract(life, mana, physical, magic, ethereal, *, base_name='Grim Helm', defense=None, sockets=0):
    for value, bounds in zip((life, mana, physical, magic), AXES[:4], strict=True):
        if type(value) is not int or value not in bounds:
            raise ValueError('Unreviewed Vampire Gaze roll')
    if type(ethereal) is not bool:
        raise ValueError('Ethereal status must be explicit')
    if type(sockets) is not int or sockets not in (0, 1):
        raise ValueError('Vampire Gaze requires zero or one open quest socket')
    definition = catalog().named['unique', NAME]
    expected = {'62': (6, 8), '60': (6, 8), '154': (15, 15), '36': (15, 20), '35': (10, 15), '16': (100, 100)}
    actual = {key: (value['min'], value['max']) for key, value in definition['roll_ranges'].items()}
    base = definition['base_definition']
    if (
        actual != expected
        or definition['table_id'] != 208
        or base['name'] != 'Grim Helm'
        or base['maxac'] != 125
        or base['durability'] != 40
    ):
        raise ValueError('Vampire Gaze native definition changed; review required')
    native = definition['game_definition']
    for slot, prop, lower, upper in (
        (1, 'manasteal', 6, 8),
        (2, 'lifesteal', 6, 8),
        (4, 'red-dmg%', 15, 20),
        (5, 'red-mag', 10, 15),
    ):
        if (native.get(f'prop{slot}'), native.get(f'min{slot}'), native.get(f'max{slot}')) != (prop, lower, upper):
            raise ValueError('Vampire Gaze independent roll properties changed')
    if definition['fixed_elemental_effects'] != (
        {'kind': 'cold', 'slot': 7, 'minimum_damage': 6, 'maximum_damage': 22, 'duration_frames': 100},
    ):
        raise ValueError('Vampire Gaze elemental definition changed')
    if base_name == 'Grim Helm':
        expected_defense = 378 if ethereal else 252
        if defense is not None and (type(defense) is not int or defense != expected_defense):
            raise ValueError('Original Vampire Gaze defense conflicts with native fixed ED')
        defense = expected_defense
    elif base_name == 'Bone Visage':
        if ethereal:
            raise ValueError('Ethereal upgrade defense requires separate reviewed proof')
        target = equipment_base(base_name)
        if (
            target is None
            or target[0]['base_code'] != base['ultracode']
            or tuple(target[0]['details'].get('base_defense', ())) != (100, 157)
        ):
            raise ValueError('Vampire Gaze upgrade definition changed')
        if type(defense) is not int or defense not in range(200, 315, 2):
            raise ValueError('Upgraded Vampire Gaze requires attainable explicit defense')
        base = {'name': base_name, 'code': target[0]['base_code']}
    else:
        raise ValueError('Unreviewed Vampire Gaze base')
    values = {
        60: life,
        62: mana,
        36: physical,
        35: magic,
        154: 15,
        16: 100,
        54: 6,
        55: 22,
        56: 100,
        31: defense,
        72: 21 if ethereal else 40,
        73: 21 if ethereal else 40,
    }
    if sockets:
        values[194] = sockets
    raw = [
        {'id': stat, 'layer': 0, 'raw': value << metadata()['stats'][str(stat)]['shift']}
        for stat, value in values.items()
    ]
    decoded, affixes, unresolved = decode_stats(raw, base=base)
    facts = normalize(
        {
            'item': {
                'name': NAME,
                'base_name': base['name'],
                'base_code': base['code'],
                'rarity': 'unique',
                'identified': True,
                'ethereal': ethereal,
                'sockets': sockets,
                'socket_contents': 'empty',
                'socket_items': [],
                'affixes': affixes,
            },
            'source': {
                'stat_capture_complete': True,
                'kind': 'reviewed_definition_template',
                'item_identity': {'table': 'unique', 'table_id': 208},
            },
            'decoded_stats': decoded,
            'unresolved_stats': unresolved,
        }
    )
    contract, gaps = NamedHandler().contract(facts, 'armor')
    if contract is None or gaps:
        raise ValueError(f'Vampire Gaze comparison implementation incomplete: {gaps}')
    return contract.to_dict()


def audit(observations, as_of, *, base_name='Grim Helm', sockets=0):
    candidates = [row for row in observations if row.get('name') == NAME]
    rows = []
    if base_name == 'Grim Helm':
        variants = ((rolls, None) for rolls in product(*AXES))
    elif base_name == 'Bone Visage':
        variants = ((rolls, defense) for rolls in product(*AXES[:4], (False,)) for defense in range(200, 315, 2))
    else:
        raise ValueError('Unreviewed Vampire Gaze market partition')
    for rolls, defense in variants:
        contract = template_contract(*rolls, base_name=base_name, defense=defense, sockets=sockets)
        compared = evaluate(contract, candidates)
        price = price_from_comparables(compared, today=as_of)
        if price.get('unavailable_reason') == 'unclassified':
            raise ValueError('Unclassified result cannot establish reviewed absence')
        rows.append(
            {
                'variant': dict(
                    zip(
                        ('life_leech', 'mana_leech', 'physical_reduction', 'magic_reduction', 'ethereal'),
                        rolls,
                        strict=True,
                    )
                ),
                **({'base_name': base_name, 'total_defense': defense} if defense is not None else {}),
                **({'open_sockets': sockets} if sockets else {}),
                'contract': contract,
                'price': price,
                'disposition': 'estimate' if price['estimate_ist'] is not None else 'evidence_unavailable',
                'cached_observations': len(candidates),
                'accepted_listing_ids': [r.get('listing_id') for r in compared['accepted']],
                'rejection_counts': dict(Counter(reason for r in compared['rejected'] for reason in r['reasons'])),
            }
        )
    return rows
