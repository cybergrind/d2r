"""Hardcore-only tooltip references do not erase adjacent Softcore or identity work."""

import hashlib
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.embedded_items import embedded_guide_context
from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews, embedded_identity
from pricing.knowledge.assessment.maintenance.guide_sections import legacy_item_references, section_inventory
from tests.pricing.knowledge.assessment.maintenance.test_embedded_evidence import evidence


TAG = '<span class="d2-planner-tooltip" data-d2-id="p" data-d2-set-id="s" data-d2-item-id="143"></span>'


def setup(root, *, legacy=False):
    source = evidence(root)
    tag = '<span class="d2planner-item" data-d2planner-profile="p" data-d2planner-id="143"></span>' if legacy else TAG
    html = (
        '<h2>Standard</h2>' + tag + '<h2>Hardcore</h2><p>Review these changes for Hardcore.</p>'
        '<h3>Gear Changes</h3>' + tag + '<h2>Mechanics</h2>' + tag + '<h2>Summary</h2>' + tag
    )
    path = root / source['guide']['path']
    path.write_text(html)
    source['guide']['sha256'] = hashlib.sha256(html.encode()).hexdigest()
    refs = legacy_item_references(html) if legacy else section_inventory(html)['embedded_item_refs']
    source['reference'] = refs[1]
    source['expected_context'] = embedded_guide_context(html, refs[1])
    row = {
        'kind': 'hardcore',
        'review_date': '2026-09-28',
        'reason': 'Exact Hardcore advice only; the item and all other source uses remain scoped.',
        'evidence': source,
        'section_range': {
            'start': 2,
            'stop': 4,
            'start_heading': 'Hardcore',
            'stop_heading': 'Mechanics',
            'quote': 'Review these changes for Hardcore.',
        },
    }
    links = [{'source_id': source['guide']['path'], 'reference': ref, 'status': 'definition_only'} for ref in refs]
    return {'schema_version': 1, 'rows': [row]}, links


def test_exact_hardcore_tooltip_is_excluded_without_a_softcore_role(tmp_path):
    document, links = setup(tmp_path)
    before = deepcopy(links)
    result = compile_embedded_reviews(document, links, [], [], tmp_path)
    assert len(result) == 1
    assert result[0]['id'] == embedded_identity(links[1])
    assert result[0]['state'] == 'excluded'
    assert 'profile_id' not in result[0]
    assert links == before


@pytest.mark.parametrize('index', [0, 2, 3])
def test_same_item_outside_hardcore_stays_scoped(tmp_path, index):
    document, links = setup(tmp_path)
    row = document['rows'][0]
    row['evidence']['reference'] = links[index]['reference']
    html = (tmp_path / row['evidence']['guide']['path']).read_text()
    row['evidence']['expected_context'] = embedded_guide_context(html, links[index]['reference'])
    with pytest.raises(ValueError, match=r'Hardcore|embedded'):
        compile_embedded_reviews(document, links, [], [], tmp_path)


@pytest.mark.parametrize('change', ['past-mechanics', 'quote', 'kind', 'role-claim', 'duplicate', 'stale-guide'])
def test_hardcore_reference_exclusion_rejects_unsupported_evidence(tmp_path, change):
    document, links = setup(tmp_path)
    row = document['rows'][0]
    if change == 'past-mechanics':
        row['section_range'].update(stop=5, stop_heading='Summary')
    elif change == 'quote':
        row['section_range']['quote'] = 'Not present in source'
    elif change == 'kind':
        row['kind'] = 'not-useful'
    elif change == 'role-claim':
        row['profile_id'] = 'some-softcore-role'
    elif change == 'duplicate':
        document['rows'].append(deepcopy(row))
    else:
        row['evidence']['guide']['sha256'] = 'stale'
    with pytest.raises(ValueError, match=r'Hardcore|[Ee]mbedded'):
        compile_embedded_reviews(document, links, [], [], tmp_path)


def test_completion_closes_only_the_exact_tooltip_and_retains_item_obligations(tmp_path):
    from pricing.knowledge.assessment.maintenance.completion import compile_completion
    from tests.pricing.knowledge.assessment.maintenance.test_completion import inputs

    document, links = setup(tmp_path)
    matrix, inventory = inputs()
    inventory['embedded_item_links'] = links
    matrix['rows'][0]['dimensions']['market']['state'] = 'pending'
    result = compile_completion(matrix, inventory, {}, embedded_reviews=document, source_root=tmp_path)
    pending = {row['id'] for row in result['queue']}
    assert 'embedded_reference:' + embedded_identity(links[1]) not in pending
    for index in (0, 2, 3):
        assert 'embedded_reference:' + embedded_identity(links[index]) in pending
    assert 'identity:a/market' in pending
    assert not result['complete']


@pytest.mark.parametrize('index', [0, 1, 2, 3])
def test_legacy_hardcore_exclusion_is_bounded_without_inventing_planner_set(tmp_path, index):
    document, links = setup(tmp_path, legacy=True)
    row = document['rows'][0]
    reference = links[index]['reference']
    row['evidence']['reference'] = reference
    html = (tmp_path / row['evidence']['guide']['path']).read_text()
    row['evidence']['expected_context'] = embedded_guide_context(html, reference)
    assert reference['set_id'] is None
    if index != 1:
        with pytest.raises(ValueError, match=r'Hardcore|embedded'):
            compile_embedded_reviews(document, links, [], [], tmp_path)
    else:
        result = compile_embedded_reviews(document, links, [], [], tmp_path)
        assert result == [
            {
                'id': embedded_identity(links[index]),
                'state': 'excluded',
                'reason': row['reason'],
                'review_date': row['review_date'],
            }
        ]
