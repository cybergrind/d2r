"""One immutable assessment document with plain, terminal and OSD renderers."""

from dataclasses import dataclass

from rich.text import Text

from inventory_tracking.appraisal.intrinsic_rolls import display_stats
from inventory_tracking.appraisal.sections import (
    assessment_lines,
    base_lines,
    base_summary,
    leveling_lines,
    price_lines,
    review_lines,
    tier_lines,
    value_watch_lines,
)
from inventory_tracking.presentation import StyledLine, Tone, render_rich


ROLL_TONES = {'perfect': Tone.PERFECT, 'low': Tone.LOW}
RARITY_TONES = {
    'normal': Tone.NORMAL,
    'superior': Tone.NORMAL,
    'low': Tone.INFERIOR,
    'inferior': Tone.INFERIOR,
    'magic': Tone.MAGIC,
    'rare': Tone.RARE,
    'unique': Tone.UNIQUE,
    'set': Tone.SET,
    'crafted': Tone.CRAFTED,
    'runeword': Tone.RUNEWORD,
}


def item_tone(item):
    if item.get('runeword'):
        return Tone.RUNEWORD
    rarity = item.get('rarity')
    if rarity in ('normal', 'superior', 'low', 'inferior') and (item.get('ethereal') or item.get('sockets')):
        return Tone.SOCKETED
    return RARITY_TONES.get(rarity, Tone.DEFAULT)


def base_tones(assessment):
    return {
        f'{use["runeword"]} / {use["role"]}: {use["status"]}': Tone.PREFERRED
        for use in (assessment or {}).get('uses', [])
        if use['status'] == 'perfect preferred base'
    }


def watch_tones(result):
    rows = result.get('value_watch', [])[:1]
    if not rows:
        return {}
    if rows[0]['details']['priority'] == 'valuable_candidate':
        return {'VALUABLE CANDIDATE': Tone.VALUABLE}
    return {'BUILD DEMAND': Tone.DEMAND}


def ethereal_tone(result):
    ethereal = result.get('extraction', {}).get('item', {}).get('ethereal')
    preference = (result.get('assessment', {}).get('ethereal_preference') or {}).get('preference')
    if type(ethereal) is not bool:
        return Tone.DEFAULT
    if preference == 'preferred':
        return Tone.ETHEREAL_DESIRED if ethereal else Tone.ETHEREAL_TARGET
    if preference == 'avoid' and ethereal:
        return Tone.ETHEREAL_UNDESIRED
    return Tone.DEFAULT


def result_tones(result):
    """Compatibility for callers requesting a text-to-style lookup."""
    tones = {
        row['text']: ROLL_TONES[row['roll_quality']]
        for row in display_stats(result)
        if row.get('roll_quality') in ROLL_TONES
    }
    ethereal = result.get('extraction', {}).get('item', {}).get('ethereal')
    if type(ethereal) is bool and ethereal_tone(result) != Tone.DEFAULT:
        tones['Ethereal: ' + ('yes' if ethereal else 'no')] = ethereal_tone(result)
    return {**tones, **watch_tones(result), **base_tones(base_summary(result))}


@dataclass(frozen=True)
class ItemAssessment:
    lines: tuple[StyledLine, ...]

    @classmethod
    def from_record(cls, record, frozen=None) -> ItemAssessment:
        lines = []

        def add(text, tone=Tone.DEFAULT, *, osd=True):
            lines.append(StyledLine(text, tone, osd))

        add(
            f'Appraisal request {record["request_id"]} — {record.get("updated_at", "time unavailable")}',
            Tone.METADATA,
            osd=False,
        )
        if record['state'] == 'rejected':
            add(f'Unavailable: {record["reason"]}', Tone.WARNING)
            if record.get('diagnostics_file'):
                add(f'Panel diagnostics saved: {record["diagnostics_file"]}', Tone.METADATA, osd=False)
            return cls(tuple(lines))
        if record['state'] != 'complete':
            add(f'Status: {record["state"]}', Tone.METADATA)
            return cls(tuple(lines))
        result = record['result']
        extraction = result['extraction']
        item = extraction['item']
        frozen = frozen or record.get('frozen') or {}
        page = frozen.get('selection', {}).get('item', {}).get('details', {}).get('inventory_page')
        container = extraction.get('source', {}).get('container', {}).get('name')
        if container is None:
            container = {0: 'Main inventory', 3: 'Horadric Cube'}.get(page, 'Unrecorded')
        add(f'Item: {item.get("rarity", "unknown").capitalize()} {item.get("name", "Unknown item")}', item_tone(item))
        add(f'Container: {container}', Tone.METADATA, osd=False)
        if item.get('name') != item.get('base_name') and item.get('base_name'):
            add(f'Base: {item["base_name"]}')
        if item.get('set_name'):
            add(f'Set: {item["set_name"]}', Tone.SET)
        if type(item.get('ethereal')) is bool:
            add('Ethereal: ' + ('yes' if item['ethereal'] else 'no'), ethereal_tone(result))
        add('Observed stats:', Tone.HEADING)
        affixes = item.get('affixes', [])
        decoded = extraction.get('decoded_stats')
        if decoded is not None:
            for stat in display_stats(result):
                if stat['status'] == 'decoded' and stat.get('presentation') != 'internal':
                    add('  ' + stat['text'], ROLL_TONES.get(stat.get('roll_quality'), Tone.DEFAULT))
        else:
            for affix in affixes:
                add('  ' + affix['label'].replace('{{value}}', str(affix['value'])))
        if not decoded and not affixes:
            add('  No supported stats decoded.', Tone.WARNING)
        for line in assessment_lines(result):
            add(line, Tone.HEADING if line == 'Build use:' else Tone.DEFAULT)
        watches = watch_tones(result)
        for line in value_watch_lines(result):
            add(line, watches.get(line, Tone.DEFAULT))
        base_result = base_summary(result)
        bases = base_tones(base_result)
        for line in base_lines(base_result):
            add(line, bases.get(line.strip(), Tone.HEADING if line == 'Runeword base:' else Tone.DEFAULT))
        tier = result.get('assessment', {}).get('trade_tier', {}).get('tier')
        for line in tier_lines(result):
            add(line, Tone.VALUABLE if tier == 'high' else Tone.DEMAND if tier == 'med' else Tone.DEFAULT)
        for line in leveling_lines(result):
            add(line, Tone.LEVELING if line.startswith('Leveling:') else Tone.DEFAULT)
        for line in price_lines(result):
            add(line)
        issues = review_lines(extraction)
        if issues:
            add('Unreadable:', Tone.WARNING)
            for issue in issues:
                add('  ' + issue, Tone.WARNING)
        return cls(tuple(lines))

    def to_text(self) -> str:
        return ''.join(line.text + '\n' for line in self.lines)

    def to_rich(self) -> Text:
        return render_rich(self.lines)

    def to_osd(self) -> list[StyledLine]:
        return [line for line in self.lines if line.osd]
