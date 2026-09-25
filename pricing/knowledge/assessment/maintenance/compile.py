"""Compile reviewed profile data after validating source fingerprints."""

from copy import deepcopy
from pathlib import Path

from pricing.knowledge.assessment.profile_sources import validate_profile_sources


def compile_profiles(document, source_root):
    from pricing.knowledge.assessment.profiles import validate_profiles

    if document.get('schema_version') != 1 or document.get('rules_version') != 'assessment-1':
        raise ValueError('Incompatible profile schema/rules version')
    validate_profiles(document['profiles'])
    validate_profile_sources(document, source_root, Path.read_bytes)
    if document['coverage']['reviewed_profiles'] != len(document['profiles']):
        raise ValueError('Profile coverage count disagrees with records')
    return deepcopy(document)
