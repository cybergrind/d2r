"""Native named bases and their valid upgrade chain, never downgraded identities."""

from pricing.knowledge.definition_store import catalog


def named_base_codes(name, quality='unique'):
    definition = catalog().named[quality, name]
    base = definition['base_definition']
    if all(base.get(key) for key in ('normcode', 'ubercode', 'ultracode')):
        chain = tuple(base[key] for key in ('normcode', 'ubercode', 'ultracode'))
        return chain[chain.index(definition['base_code']) :]
    return (definition['base_code'],)


def named_base_condition(name, quality='unique'):
    return {'any': [{'op': 'fact_eq', 'field': 'base_code', 'value': code} for code in named_base_codes(name, quality)]}


def unique_base_codes(name):
    return named_base_codes(name)


def unique_base_condition(name):
    return named_base_condition(name)
