"""Native identities for loose runes and gems, including every skull grade."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from pricing.knowledge.artifacts import read_artifact


SOURCE = Path(__file__).resolve().parents[2] / 'third-parties/d2data/json/misc.json'
SOURCE_SHA256 = '116264d5df4e7724beaf9a7ae1f005c58544a5a50a331baf4b370a4f01110072'
TYPES = frozenset({'rune', 'gems', 'geme', 'gemr', 'gema', 'gemd', 'gemt', 'gemz'})


@lru_cache(maxsize=2)
def _definitions(raw):
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('Loose rune/gem definitions changed; review comparison mechanics.')
    return {code: row for code, row in json.loads(raw).items() if row.get('type') in TYPES}


def definitions():
    return _definitions(read_artifact(SOURCE))
