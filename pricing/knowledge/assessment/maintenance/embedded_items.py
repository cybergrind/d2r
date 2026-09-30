"""Resolve guide tooltip references into exact cached planner evidence."""

from copy import deepcopy


def embedded_guide_context(html, reference):
    """Bind an exact tooltip to its guide slot without inventing an item label."""
    from pricing.knowledge.assessment.maintenance.guide_positions import PositionedMentions
    from pricing.knowledge.assessment.maintenance.guide_sections import SectionParser

    sections = SectionParser()
    sections.feed(html)
    sections.close()
    if sum(row == reference for row in (*sections.embedded_item_refs, *sections.legacy_item_refs)) != 1:
        raise ValueError('Changed or ambiguous embedded guide reference')
    mentions = PositionedMentions()
    mentions.feed(html)
    mentions.close()
    indices = [i for i, position in enumerate(mentions.positions) if list(position) == reference['position']]
    if len(indices) != 1:
        raise ValueError('Embedded guide reference has no unique item span')
    index = indices[0]
    mention = mentions.mentions[index]
    return {
        'span_index': index,
        **{key: mention[key] for key in ('label', 'side', 'slot')},
        'reference': deepcopy(reference),
    }


def resolve_embedded_item(reference, planner, occurrences, *, native_items=None):
    result = {'reference': deepcopy(reference), 'review_state': 'pending', 'occurrence_ids': []}
    item = planner['items'].get(str(reference['item_id']))
    if item is not None:
        result['item_definition'] = deepcopy(item)
        result['item_locator'] = f'/items/{reference["item_id"]}'
    if reference.get('format') == 'legacy_item' and reference.get('set_id') is None:
        native = (native_items or {}).get(str(reference['item_id']))
        if item is None and native is not None:
            if native['definition'].get('code') != str(reference['item_id']):
                raise ValueError('Native item reference differs from its definition')
            return {**result, 'status': 'native_definition_only', 'native_item': deepcopy(native)}
        # Legacy markup names a planner item, not a selected equipment profile.
        # Shared item references cannot endorse every profile that contains it.
        return {**result, 'status': 'definition_only' if item is not None else 'missing_item'}
    matches = [
        (i, p)
        for i, p in enumerate(planner['profiles'])
        if reference.get('set_id') is not None and p.get('uid') == reference['set_id']
    ]
    if len(matches) != 1:
        return {**result, 'status': 'missing_set' if not matches else 'ambiguous_set'}
    number, profile = matches[0]
    item = planner['items'].get(str(reference['item_id']))
    if item is None:
        return {**result, 'status': 'missing_item'}
    prefix = f'/profiles/{number}/'
    links = sorted(
        row['id']
        for row in occurrences
        if row['source_locator'].startswith(prefix)
        and row.get('details', {}).get('item_ref') == str(reference['item_id'])
    )
    return {
        **result,
        'status': 'linked' if links else 'definition_only',
        'occurrence_ids': links,
        'profile_locator': f'/profiles/{number}',
        'profile_name': profile.get('name'),
        'item_locator': f'/items/{reference["item_id"]}',
        'item_definition': deepcopy(item),
    }
