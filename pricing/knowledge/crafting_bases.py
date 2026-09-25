"""Compile concrete crafted equipment recipe chains from local cube tables."""


def crafting_bases(recipes, bases):
    result = {}
    fields = ('normcode', 'ubercode', 'ultracode')
    for key, row in recipes.items():
        if row.get('enabled') != 1 or row.get('output', '').strip('"') != 'usetype,crf':
            continue
        parts = row.get('input 1', '').strip('"').split(',')
        if len(parts) != 3 or parts[1:] != ['mag', 'upg']:
            continue  # Type-wide weapon recipes do not identify one base chain.
        original = bases.get(parts[0], {})
        chain = tuple(original.get(field) for field in fields)
        if parts[0] != chain[0] or len(set(chain)) != 3 or not all(chain):
            continue
        if any(tuple(bases.get(code, {}).get(field) for field in fields) != chain for code in chain):
            continue
        label = row.get('description', '').partition(' -> ')[2]
        if not label or label in result:
            raise ValueError('Ambiguous crafted recipe label')
        result[label] = {
            'tiers': {
                tier: {'code': code, 'name': bases[code]['name']}
                for tier, code in zip(('Normal', 'Exceptional', 'Elite'), chain, strict=True)
            },
            'source': {'path': 'third-parties/d2data/json/cubemain.json', 'record_key': key},
        }
    return result


def nonethereal_crafting_recipes(recipes):
    """Exact usetype,crf creates a new item with ITEMDROPFLAG_NEVERETH.

    Any alternative enabled recipe sharing the label makes that identity ambiguous.
    """
    grouped = {}
    for key, row in recipes.items():
        label = row.get('description', '').partition(' -> ')[2]
        if row.get('enabled') == 1 and label:
            grouped.setdefault(label, []).append((key, row))
    return {
        label: {'path': 'third-parties/d2data/json/cubemain.json', 'record_key': rows[0][0]}
        for label, rows in grouped.items()
        if len(rows) == 1 and rows[0][1].get('output', '').strip('"') == 'usetype,crf'
    }


def crafting_recipe_bases(recipes, bases, matches):
    """Resolve enabled exact crafted recipes to every permitted concrete base."""
    chains = crafting_bases(recipes, bases)
    for key, row in recipes.items():
        output = row.get('output', '').strip('"').split(',')
        if row.get('enabled') != 1 or 'crf' not in output:
            continue
        if output != ['usetype', 'crf']:
            raise ValueError('Unreviewed crafted output mechanics')
        parts = row.get('input 1', '').strip('"').split(',')
        label = row.get('description', '').partition(' -> ')[2]
        if parts[1:] == ['mag', 'upg'] and label in chains:
            codes = [r['code'] for r in chains[label]['tiers'].values()]
        elif parts[1:] == ['mag']:
            codes = (
                [parts[0]]
                if parts[0] in bases
                else [code for code, base in bases.items() if matches(base.get('type'), {parts[0]})]
            )
        else:
            raise ValueError('Unreviewed crafted input mechanics')
        if not codes:
            raise ValueError('Crafted recipe has no verified bases')
        yield key, row, codes
