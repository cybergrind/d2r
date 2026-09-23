"""Local tooltip transcription with PyOCR; never silently repair numbers or price items."""

import argparse
import hashlib
import json
import os
import re
import time
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
        'damage': {},
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
            names = [
                row for row in catalog if re.search(r'(?<![A-Z])' + re.escape(row['name'].upper()) + r'(?![A-Z])', text)
            ]
            if not names:
                continue
            # Nested names are not aliases. Keep the longest literal catalog match.
            names.sort(key=lambda row: len(row['name']), reverse=True)
            row = names[0]
            item['name'] = accept('name', row['name'], line)
            item['base_code'] = row.get('base_code')
            item['superior'] = True if 'SUPERIOR' in text else None
            started = True
            continue
        match = re.search(r'DAMAGE:\s*(\d+)\s+TO\s+(\d+)\s*$', text)
        if match:
            key = 'two_hand' if 'TWO' in text else 'one_hand' if 'HAND' in text else 'displayed'
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


def extract_image(path, *, tessdata=None, diagnostics=None):
    """One local C-API pass, preserving color pixels for subsequent visual review."""
    from PIL import Image

    tessdata = Path(tessdata or ROOT / 'pricing/raw/ocr/tessdata').resolve()
    if not (tessdata / 'eng.traineddata').is_file():
        raise FileNotFoundError(f'English OCR model missing: {tessdata}; see pricing/knowledge/OCR.md')
    image_path = Path(path)
    started = time.perf_counter()
    previous = os.environ.get('TESSDATA_PREFIX')
    os.environ['TESSDATA_PREFIX'] = str(tessdata)
    try:
        from pyocr import builders, libtesseract

        if not libtesseract.is_available():
            raise RuntimeError('PyOCR libtesseract backend unavailable; install local Tesseract libraries')
        with Image.open(image_path) as image:
            image = image.convert('RGB')
            recognized = libtesseract.image_to_string(
                image, lang='eng', builder=builders.LineBoxBuilder(tesseract_layout=6)
            )
            lines = [
                {
                    'text': line.content,
                    'box': line.position,
                    'words': [
                        {'text': w.content, 'confidence': w.confidence, 'box': w.position} for w in line.word_boxes
                    ],
                }
                for line in recognized
            ]
            catalog = []
            for filename in ('appraisal-catalog.json', 'appraisal-trade-catalog.json'):
                catalog.extend(json.loads((ROOT / 'pricing/data' / filename).read_text())['rows'])
            properties = json.loads((ROOT / 'pricing/data/appraisal-properties.json').read_text())['properties']
            result = parse_lines(lines, catalog, properties)
            result.update(
                engine='PyOCR/libtesseract',
                language='eng',
                image_sha256=hashlib.sha256(image_path.read_bytes()).hexdigest(),
                model_sha256=hashlib.sha256((tessdata / 'eng.traineddata').read_bytes()).hexdigest(),
                dimensions=list(image.size),
                raw_lines=lines,
            )
            if diagnostics:
                directory = Path(diagnostics)
                directory.mkdir(parents=True, exist_ok=True)
                for number, row in enumerate(result['evidence'].values()):
                    if row.get('box'):
                        (left, top), (right, bottom) = row['box']
                        target = directory / f'field-{number:02d}.png'
                        image.crop((left, top, right, bottom)).save(target)
                        row['review_crop'] = str(target)
    finally:
        if previous is None:
            os.environ.pop('TESSDATA_PREFIX', None)
        else:
            os.environ['TESSDATA_PREFIX'] = previous
    result['elapsed_ms'] = round((time.perf_counter() - started) * 1000, 2)
    if diagnostics:
        (Path(diagnostics) / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--tessdata', type=Path)
    parser.add_argument('--diagnostics', type=Path)
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = extract_image(args.image, tessdata=args.tessdata, diagnostics=args.diagnostics)
    except (OSError, ImportError, RuntimeError) as error:
        parser.exit(2, f'Local OCR unavailable: {error}\n')
    if not args.full:
        result.pop('raw_lines', None)
        result.pop('evidence', None)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
