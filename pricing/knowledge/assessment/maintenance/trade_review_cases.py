"""Identity, native variant and execution binding shared by trade review scopes."""

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint


LEGAL = (True, False, 0, 'empty')
REQUIRED = frozenset(
    {
        LEGAL,
        (False, False, 0, 'empty'),
        (True, True, 0, 'empty'),
        (True, None, 0, 'empty'),
        (True, False, None, 'empty'),
        (True, False, 1, 'empty'),
        (True, False, 0, 'unknown'),
    }
)


ETHEREAL_LEGAL = (True, True, 0, 'empty')
ETHEREAL_REQUIRED = frozenset(
    {
        ETHEREAL_LEGAL,
        (False, True, 0, 'empty'),
        (True, False, 0, 'empty'),
        (True, None, 0, 'empty'),
        (True, True, 1, 'empty'),
        (True, True, None, 'empty'),
        (True, True, 0, 'unknown'),
    }
)


def variant_predicate(rule):
    if set(rule) == {'all'}:
        return bool(rule['all']) and all(variant_predicate(child) for child in rule['all'])
    allowed = {'ethereal': False, 'sockets': 0, 'socket_contents': 'empty'}
    return (
        set(rule) == {'op', 'field', 'value'}
        and rule['op'] == 'fact_eq'
        and rule['field'] in allowed
        and type(rule['value']) is type(allowed[rule['field']])
        and rule['value'] == allowed[rule['field']]
    )


def executed_cases(review, receipt, definition, *, additional_bases=(), allowed_variants=REQUIRED):
    identity = (review['quality'], review['name'])
    result = []
    for name, digest in review['cases'].items():
        executed = receipt.get('cases', {}).get(name, {})
        if any(executed.get('phases', {}).get(p) != 'passed' for p in ('setup', 'call', 'teardown')):
            return (), 'A required trade case did not pass every phase.'
        case = executed.get('trade_case', {})
        if fingerprint(case) != digest:
            return (), 'Executed trade inputs or assertions differ from the review.'
        item, checks = case.get('item', {}), case.get('checks', {})
        if (
            (item.get('rarity'), item.get('name')) != identity
            or item.get('base') not in (definition['base_name'], *additional_bases)
            or case.get('context') != {}
            or f'named:{identity[0]}:{identity[1]}' not in executed.get('covers', [])
            or checks.get('schema_version') != 1
        ):
            return (), 'Trade case does not address this standalone named identity.'
        signature = tuple(item.get(k) for k in ('identified', 'ethereal', 'sockets', 'socket_contents'))
        if (
            type(signature[0]) is not bool
            or (signature[1] is not None and type(signature[1]) is not bool)
            or (signature[2] is not None and type(signature[2]) is not int)
            or signature not in allowed_variants
        ):
            return (), 'Trade case has an unreviewed variant.'
        result.append((item, checks, signature))
    return result, None
