"""Bundled LvlPrest Def and level names (data/level_presets.json, built by build_presets.py)."""

import json
from pathlib import Path


_TABLE = json.loads((Path(__file__).parent / 'data' / 'level_presets.json').read_text())
PRESET_NAMES: dict[int, str] = {int(k): v for k, v in _TABLE['presets'].items()}
LEVEL_NAMES: dict[int, str] = {int(k): v for k, v in _TABLE['levels'].items()}


def preset_name(preset: int) -> str:
    return PRESET_NAMES.get(preset, f'preset {preset}')


def level_name(area: int) -> str:
    return LEVEL_NAMES.get(area, f'area {area}')
