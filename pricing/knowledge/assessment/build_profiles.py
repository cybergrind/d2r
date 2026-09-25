"""Compile and atomically publish reviewed build profiles from offline sources."""

import json
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / 'pricing/data/appraisal-build-profiles.json'


RULES = Path(__file__).resolve().parent / 'rules/reviewed_profiles.json'


def build(root=ROOT):
    from pricing.knowledge.assessment.maintenance.compile import compile_profiles
    from pricing.knowledge.assessment.maintenance.rule_bundle import load_rule_bundle

    return compile_profiles(load_rule_bundle(RULES), root)


def main():
    from pricing.knowledge.assessment.profiles import validate_profiles

    result = build()
    validate_profiles(result['profiles'])
    payload = json.dumps(result, indent=2, allow_nan=False) + '\n'
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', dir=OUTPUT.parent, prefix=OUTPUT.name + '.', suffix='.tmp', delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, OUTPUT)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(json.dumps(result['coverage']))


if __name__ == '__main__':
    main()
