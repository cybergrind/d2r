"""Shared tooltip parsing; never silently repair numbers or price items."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _text(value):
    """Only documented font/label substitutions; never change numeric characters."""
    value = value.upper().replace('@', 'O').replace('\u00ae', 'O')
    value = re.sub(r'\b(?:TE|TOE)\b', 'TO', value)
    value = re.sub(r'\bDAMAGEE\b', 'DAMAGE', value)
    return re.sub(r'\bSECKETED\b', 'SOCKETED', value)


def _signature(value):
    return re.sub(r'[^A-Z0-9]', '', _text(value))


def _confidence(line, field, value):
    words = line.get('words', [])
    if field == 'name':
        names = {_signature(part) for part in value.split()}
        words = [word for word in words if _signature(word['text']) in names]
    elif field.startswith(('requirements.', 'damage.')) or field in ('sockets', 'durability', 'defense'):
        numbers = value.values() if isinstance(value, dict) else value if isinstance(value, list) else [value]
        numbers = {str(number) for number in numbers}
        words = [word for word in words if numbers.intersection(re.findall(r'\d+', word['text']))]
    else:
        words = [word for word in words if re.search(r'[A-Za-z0-9]', word['text'])]
    values = [word['confidence'] for word in words if word.get('confidence', -1) >= 0]
    return round(min(values), 1) if values else None


def parse_lines(lines, catalog, properties):
    """Conservative English tooltip grammar; retain unrecognized item lines verbatim."""
    item = {
        'name': None,
        'base_code': None,
        'base_name': None,
        'observed_title': None,
        'damage': {},
        'elemental_damage': {},
        'defense': None,
        'durability': None,
        'requirements': {},
        'sockets': None,
        'affixes': [],
        'rarity': None,
        'ethereal': None,
        'superior': None,
        'socket_contents': None,
    }
    result = {
        'item': item,
        'evidence': {},
        'unparsed_lines': [],
        'review': [],
        'status': 'needs_review',
        'appraisal_ready': False,
        'offline': True,
    }
    started = False
    conflicts = set()

    def accept(field, value, line):
        previous = result['evidence'].get(field)
        if previous and previous['value'] != value:
            conflicts.add(field)
            result['review'].append(f'{field}: conflicting OCR values; inspect original pixels')
            return None
        result['evidence'][field] = {
            'value': value,
            'raw_text': line['text'],
            'box': line.get('box'),
            'minimum_word_confidence': _confidence(line, field, value),
        }
        return value

    for line in lines:
        text = _text(line['text'])
        if started and re.search(r'\b(?:SHIFT|CTRL|COMPARE|INVENTORY)\b', text):
            break
        if not started:
            # Complete titles only. Numeric edge artifacts are allowed for bases,
            # never for named items such as the Stone runeword.
            names = [
                row
                for row in catalog
                if _text(row['name']).strip() == text.strip()
                or (row.get('base_code') and _text(row['name']).strip() == re.sub(r'^\d+\s+|\s+\d+$', '', text.strip()))
            ]
            if not names:
                if not re.search(r'\b(?:SELL VALUE|SHIFT|CTRL|INVENTORY)\b', text):
                    result.setdefault('unresolved_headers', []).append(line)
                continue
            names.sort(key=lambda row: bool(row.get('base_code')), reverse=True)
            row = names[0]
            headers = result.get('unresolved_headers', [])
            previous = headers[-1] if headers else None
            if previous and previous.get('box') and line.get('box'):
                gap = line['box'][0][1] - previous['box'][1][1]
                height = line['box'][1][1] - line['box'][0][1]
                if gap > height * 2:
                    previous = None
            item['observed_title'] = previous['text'] if previous else line['text']
            item['name'] = accept('name', row['name'], line)
            item['base_code'] = row.get('base_code')
            item['base_name'] = row['name'] if row.get('base_code') else None
            started = True
            continue
        bases = [row for row in catalog if row.get('base_code') and _text(row['name']).strip() == text.strip()]
        if bases and not item['base_code'] and not item['requirements'] and not item['affixes']:
            item['base_code'] = accept('base_code', bases[0]['base_code'], line)
            item['base_name'] = bases[0]['name']
            continue
        match = re.search(r'DAMAGE:\s*(\d+)\s+TO\s+(\d+)\s*$', text)
        if match:
            key = 'two_hand' if re.search(r'\bTWO[- ]+HAND\b', text) else 'displayed'
            if re.search(r'\bONE[- ]+HAND\b', text):
                key = 'one_hand'
            if key == 'displayed':
                result['review'].append('Damage type not recognized; verify one/two-hand or throw label')
            item['damage'][key] = accept(f'damage.{key}', [int(match[1]), int(match[2])], line)
            continue
        match = re.fullmatch(r'DEFENSE:\s*(\d+)\s*', text.strip())
        if match:
            item['defense'] = accept('defense', int(match[1]), line)
            continue
        match = re.search(r'DURABILITY:\s*(\d+)\s+OF\s+(\d+)\s*$', text)
        if match:
            item['durability'] = accept('durability', {'current': int(match[1]), 'maximum': int(match[2])}, line)
            continue
        match = re.search(r'REQUIRED\s+(DEXTERITY|STRENGTH|LEVEL):\s*(\d+)\s*$', text)
        if match:
            key = match[1].lower()
            item['requirements'][key] = accept(f'requirements.{key}', int(match[2]), line)
            continue
        match = re.search(r'SOCKETED\s*\((\d+)\)', text)
        if match:
            item['sockets'] = accept('sockets', int(match[1]), line)
            if 'ETHEREAL' in text:
                item['ethereal'] = accept('ethereal', True, line)
            continue
        if 'ETHEREAL' in text:
            item['ethereal'] = accept('ethereal', True, line)
            # Keep other text on the line for review (e.g. Cannot Be Repaired).
        if re.search(r'\bCLASS\b.*\bATTACK SPEED\b', text):
            item['weapon_class_text'] = accept('weapon_class_text', text, line)
            continue
        match = re.fullmatch(r'ADDS\s+(\d+)\s*[-\u2013]\s*(\d+)\s+(FIRE|LIGHTNING|COLD|MAGIC) DAMAGE', text.strip())
        if match:
            key = match[3].lower()
            item['elemental_damage'][key] = accept(f'elemental_damage.{key}', [int(match[1]), int(match[2])], line)
            continue
        affixes = []
        for property_id, definition in properties.items():
            for label in definition['labels']:
                if label.count('{{value}}') != 1 or '{{' in label.replace('{{value}}', ''):
                    continue
                before, after = label.split('{{value}}')
                sign = re.search(r'([+*\-]?)\d+', text)
                expected_sign = before.strip()[-1:] if before.strip()[-1:] in ('+', '-') else ''
                actual_sign = sign[1].replace('*', '+') if sign else ''
                if expected_sign and actual_sign != expected_sign:
                    continue
                pattern = re.escape(_signature(before)) + r'(\d+)' + re.escape(_signature(after))
                match = re.fullmatch(pattern, _signature(text))
                if match:
                    affixes.append({'property_id': property_id, 'value': int(match[1]), 'label': label})
        if len(affixes) == 1:
            affix = affixes[0]
            accept(f'properties.{affix["property_id"]}', affix['value'], line)
            item['affixes'].append(affix)
        elif len(text.strip()) > 3:
            result['unparsed_lines'].append(line)
    # A third line cannot silently resolve an earlier conflict.
    if 'sockets' in conflicts:
        item['sockets'] = None
    for key in list(item['damage']):
        if f'damage.{key}' in conflicts:
            item['damage'][key] = None
    for key in list(item['elemental_damage']):
        if f'elemental_damage.{key}' in conflicts:
            item['elemental_damage'][key] = None
    for key in list(item['requirements']):
        if f'requirements.{key}' in conflicts:
            item['requirements'][key] = None
    if 'durability' in conflicts:
        item['durability'] = None
    if 'defense' in conflicts:
        item['defense'] = None
    item['affixes'] = [a for a in item['affixes'] if f'properties.{a["property_id"]}' not in conflicts]
    for field, evidence in result['evidence'].items():
        confidence = evidence['minimum_word_confidence']
        if confidence is None or confidence < 70:
            result['review'].append(f'{field}: inspect OCR text/box; confidence is not a calibrated probability')
    if not item['name']:
        result['review'].append('Item name not identified from a literal local catalog match')
    if result['unparsed_lines']:
        result['review'].append('Unparsed item lines may contain value-deciding modifiers')
    result['review'].append('Verify rarity, omitted modifiers, ethereal status and socket contents visually')
    return result
