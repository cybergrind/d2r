import hashlib
import json

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.maintenance.compile import compile_profiles


def document_for(tmp_path, pointer):
    document = build()
    document['profiles'] = document['profiles'][:1]
    document['coverage']['reviewed_profiles'] = 1
    source = tmp_path / 'source.json'
    source.write_text(json.dumps({'variants': [{'player': {'Amulet/Swap': ['Verified item']}}]}))
    document['profiles'][0]['source'].update(
        path='source.json', sha256=hashlib.sha256(source.read_bytes()).hexdigest(), locator=pointer
    )
    return document


def test_profile_compiler_accepts_resolvable_escaped_source_pointer(tmp_path):
    document = document_for(tmp_path, '/variants/0/player/Amulet~1Swap')
    assert compile_profiles(document, tmp_path) == document


@pytest.mark.parametrize(
    'pointer',
    ['/variants/2', '/variants/-1', '/variants/00', '/missing', 'variants/0', '/variants/0/player/Amulet~2Swap'],
)
def test_profile_compiler_rejects_nonexistent_or_invalid_pointer_despite_matching_hash(tmp_path, pointer):
    with pytest.raises(ValueError, match='source locator'):
        compile_profiles(document_for(tmp_path, pointer), tmp_path)
