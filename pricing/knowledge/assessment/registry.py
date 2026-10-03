"""Explicit family dispatch from locally verified item type codes."""

from dataclasses import dataclass

from pricing.knowledge.bases import BASE_QUALITIES
from pricing.knowledge.socket_materials import TYPES as SOCKET_MATERIAL_TYPES


@dataclass(frozen=True)
class Family:
    name: str
    types: frozenset[str]


# Codes are item *types*, copied from the runtime base metadata, not item codes.
FAMILIES = (
    Family(
        'weapon',
        frozenset(
            {
                'knif',
                'swor',
                'axe',
                'mace',
                'club',
                'hamm',
                'scep',
                'wand',
                'staf',
                'orb',
                'h2h',
                'h2h2',
                'pole',
                'spea',
                'jave',
                'ajav',
                'aspe',
                'bow',
                'abow',
                'xbow',
                'tkni',
                'taxe',
            }
        ),
    ),
    Family('socket_material', SOCKET_MATERIAL_TYPES),
    Family('quest_material', frozenset({'ques'})),
    Family('supply', frozenset({'scro', 'book', 'key', 'bowq', 'xboq'})),
    Family('consumable', frozenset({'hpot', 'apot', 'wpot', 'mpot', 'rpot', 'spot'})),
    Family('jewelry', frozenset({'ring', 'amul'})),
    Family('helm', frozenset({'helm', 'circ', 'phlm', 'pelt'})),
    Family('armor', frozenset({'tors'})),
    Family('shield', frozenset({'shie', 'ashd', 'head', 'grim'})),
    Family('accessory', frozenset({'glov', 'boot', 'belt'})),
    Family('charm', frozenset({'scha', 'mcha', 'lcha', 'csch'})),
    Family('jewel', frozenset({'jewl', 'cjwl'})),
)


def classify(facts, families=FAMILIES):
    matches = [f.name for f in families if facts.item_type in f.types]
    if len(matches) > 1:
        raise ValueError(f'Ambiguous family dispatch: {matches}')
    policy = (
        'quest_material'
        if matches == ['quest_material']
        else 'socket_material'
        if matches == ['socket_material']
        else 'supply'
        if matches == ['supply']
        else 'consumable'
        if matches == ['consumable']
        else 'runeword'
        if facts.runeword
        else 'named'
        if facts.rarity in ('unique', 'set')
        else 'base'
        if facts.rarity in BASE_QUALITIES
        else 'affixed'
        if facts.rarity in ('magic', 'rare', 'crafted')
        else 'unsupported'
    )
    return (matches[0] if matches else 'unsupported'), policy
