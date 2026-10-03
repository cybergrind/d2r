"""Class-specific Torch evidence, separate from variable attribute/resistance rolls."""

from pricing.knowledge.assessment.adapters.market_projection import market_properties
from pricing.knowledge.assessment.domain.facts import FactStatus, StatKey
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.handlers.random_skills import comparison_gaps
from pricing.knowledge.definition_store import catalog


IDENTITY = ('unique', 'Hellfire Torch')


def specification(review):
    if 'class_skill_ids' not in review:
        return None
    classes = review['class_skill_ids']
    if (
        not isinstance(classes, list)
        or not classes
        or any(type(i) is not int for i in classes)
        or len(set(classes)) != len(classes)
    ):
        raise ValueError('Invalid trade class selection')
    definitions = catalog().named_variants.get(IDENTITY, ())
    if len(definitions) != 1:
        raise ValueError('Ambiguous native trade class definition')
    definition = definitions[0]
    game = definition.get('game_definition', {})
    if (
        definition.get('table_id') != 400
        or definition.get('base_name') != 'Large Charm'
        or (game.get('prop1'), game.get('min1'), game.get('max1')) != ('randclassskill', 0, 7)
        or any(not 0 <= i <= 7 for i in classes)
    ):
        raise ValueError('Unverified native trade class definition')
    properties = {i: market_properties().get(f'83:{i}') for i in range(8)}
    if any(not isinstance(p, str) or not p for p in properties.values()) or len(set(properties.values())) != 8:
        raise ValueError('Unverified trade class property mapping')
    return definition, frozenset(classes), properties


def market_class(review, row):
    spec = specification(review)
    if spec is None:
        return None
    _, allowed, properties = spec
    selected = [i for i, field in properties.items() if field in row['properties']]
    if (row.get('rarity'), row.get('name')) != IDENTITY or len(selected) != 1 or selected[0] not in allowed:
        raise ValueError('Trade evidence has another or ambiguous class')
    value = row['properties'][properties[selected[0]]]
    if type(value) not in (int, float) or value != 3:
        raise ValueError('Trade evidence has an invalid class skill bonus')
    return selected[0]


def validate_class_cohorts(review, identity=IDENTITY):
    spec = specification(review)
    if spec is None:
        return
    if identity != IDENTITY:
        raise ValueError('Trade class selection belongs to another named item')
    classes = {r['id']: market_class(review, r) for r in review['market_evidence']}
    rows = {r['id']: r for r in review['market_evidence']}
    groups = [(review['default_status'], review['default_evidence_ids'])]
    groups.extend((band['status'], band['evidence_ids']) for band in review['bands'])
    for status, ids in groups:
        if status == 'unresolved' and not ids:
            continue
        for class_id in spec[1]:
            sellers = {rows[key]['seller_id'] for key in ids if key in rows and classes[key] == class_id}
            if len(sellers) < 3:
                raise ValueError('Insufficient independent trade evidence for this class and band')


def valid_capture(review, facts):
    spec = specification(review)
    if spec is None:
        return True
    if (facts.rarity, facts.name) != IDENTITY or facts.capture_complete is not True:
        return False
    definition, errors = resolve_named_definition(facts, identity_only=True)
    if errors or definition is None or definition['table_id'] != spec[0]['table_id']:
        return False
    if comparison_gaps(facts, definition, require_projection=False):
        return False
    keys = [key for key in facts.stats if key.startswith('83:')]
    if len(keys) != 1:
        return False
    class_id = int(keys[0].split(':')[1])
    value = facts.stat(StatKey(83, class_id))
    return class_id in spec[1] and value.status == FactStatus.KNOWN and type(value.value) is int and value.value == 3
