import pytest

from pricing.knowledge.assessment.maintenance.completion_evidence import invalid_reference


@pytest.mark.parametrize(('version', 'expected_valid'), [(2, True), (1, False), (None, False)])
def test_configuration_citation_pins_exact_version(version, expected_valid):
    docs = {'profiles': {'stat_evaluation': {'configurations': [{'id': 'skill-priorities', 'version': 2}]}}}
    source = {'artifact': 'profiles', 'configuration_id': 'skill-priorities', 'version': version}
    assert (invalid_reference(source, docs) is None) is expected_valid


def test_duplicate_configuration_cannot_establish_evidence():
    row = {'id': 'skill-priorities', 'version': 2}
    docs = {'profiles': {'stat_evaluation': {'configurations': [row, row]}}}
    source = {'artifact': 'profiles', 'configuration_id': 'skill-priorities', 'version': 2}
    assert invalid_reference(source, docs)


def test_escaped_locator_resolves_inside_the_pinned_document():
    docs = {'inventory': {'a/b': [{'id': 'item'}]}}
    assert invalid_reference({'artifact': 'inventory', 'locator': '/a~1b/0'}, docs) is None
