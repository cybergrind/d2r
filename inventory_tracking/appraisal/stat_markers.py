"""Map prepared semantic annotations only to unambiguous decoded native-stat lines."""

from inventory_tracking.appraisal.price_rolls import deciding_specs, listed_roll_tone, native_keys
from inventory_tracking.presentation import StyledLine, StyledSpan, Tone


ROLL_TONES = {'perfect': Tone.PERFECT, 'low': Tone.LOW}
MARKER_TONES = {'desirable': Tone.STAT_DESIRABLE, 'supporting': Tone.STAT_SUPPORTING}


def stat_line(stat, annotations, *, comparison=None):
    text = '  ' + stat['text']
    tone = ROLL_TONES.get(stat.get('roll_quality'), Tone.DEFAULT)
    if comparison is not None:
        tone = listed_roll_tone(stat, comparison)
        if deciding_specs(stat, comparison):
            return StyledLine('  [price roll] ' + stat['text'], tone)
    keys = native_keys(stat)
    if stat.get('status') != 'decoded' or not keys:
        return StyledLine(text, tone)
    meaning = (
        annotations.get(next(iter(keys)), {}).get('desirability')
        if len(keys) == 1
        else combined_meaning(keys, annotations)
    )
    if meaning not in MARKER_TONES:
        return StyledLine(text, tone)
    prefix = f'  ● [{meaning}] '
    return StyledLine(
        prefix + stat['text'],
        tone,
        spans=(
            StyledSpan(prefix, MARKER_TONES[meaning]),
            StyledSpan(stat['text'], tone),
        ),
    )


def combined_meaning(keys, annotations):
    """Require one reviewed use to support every component with the same meaning."""
    common = None
    for key in sorted(keys):
        uses = {
            (use.get('configuration_id'), use.get('desirability'))
            for use in annotations.get(key, {}).get('contributions', ())
            if isinstance(use.get('configuration_id'), str)
            and use['configuration_id']
            and use.get('desirability') in MARKER_TONES
        }
        common = uses if common is None else common & uses
        if not common:
            return None
    meanings = {meaning for _, meaning in common}
    return next((meaning for meaning in MARKER_TONES if meaning in meanings), None)
