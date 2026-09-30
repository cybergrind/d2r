"""Bind a reviewed equipment-table string to one build, variant, side and slot."""

from pricing.knowledge.assessment.policies.sources import resolve_pointer


def equipment_quote_matches(evidence, role, read_json, *, allow_unquoted=False):
    ref = evidence.get('equipment_quote', {})
    source = role['source']
    locator = ref.get('locator', '')
    parts = locator.strip('/').split('/')
    origin = source['locator']
    aggregate = source['path'] == 'pricing/data/wp-a-builds.json'
    prefix = [role['build'], 'variants'] if aggregate else ['variants']
    index = len(prefix)
    if (
        (not aggregate and source['path'] != f'pricing/data/wp-a-variants/{role["build"]}.json')
        or ref.get('path') != source['path']
        or ref.get('sha256') != source['sha256']
        or len(parts) != index + 4
        or parts[:index] != prefix
        or parts[index + 1 : index + 3] != [role['side'], role['slot']]
        or any(not parts[i].isdecimal() or str(int(parts[i])) != parts[i] for i in (index, index + 3))
        or locator != '/' + '/'.join(parts)
        or not (locator == origin or locator.startswith(origin + '/'))
        or 'section_index' in evidence
        or evidence.get('guide_tab') != role['variant']
    ):
        raise ValueError('Equipment quote must bind the exact reviewed primary slot')
    try:
        document = read_json(ref)
        variants = document[role['build']]['variants'] if aggregate else document['variants']
        variant = variants[int(parts[index])]
        quote = resolve_pointer(document, locator)
    except (ValueError, KeyError, IndexError, TypeError) as error:
        raise ValueError('Equipment quote source missing') from error
    if (
        variant.get('name') != role['variant']
        or not isinstance(quote, str)
        or quote != evidence.get('quote')
        or (not allow_unquoted and quote not in source.get('quotes', []))
    ):
        raise ValueError('Equipment quote differs from its reviewed source')
    return True
