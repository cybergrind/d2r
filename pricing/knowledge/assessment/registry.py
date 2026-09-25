"""Explicit family dispatch from locally verified item type codes."""

from dataclasses import dataclass

from pricing.knowledge.bases import BASE_QUALITIES


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
        'runeword'
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
