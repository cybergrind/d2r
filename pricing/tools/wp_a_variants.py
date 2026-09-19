#!/usr/bin/env python3
"""wp_a_variants.py [--write] — merge pricing/data/wp-a-variants/<slug>.json into the build ledger and build a demand index.

Outputs (with --write):
  pricing/data/wp-a-builds.json            adds "variants": [...] per build (main "slots"/"merc" untouched); backup .bak-YYYYMMDD
  pricing/data/wp-a-variants/index.json    item -> [{build, tier, class, variant, side, slot}]  (side = player | merc)
  pricing/data/wp-a-variants/new-demand.md items named ONLY in variant / merc / prose sections (absent from the main gear tables), by weight
Without --write: prints the new-demand report to stdout.
Weight: S = 2, A = 1 per build (same as WP-A); a build counts once per item however many variants name it.
"""
import json, glob, os, re, sys, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, 'data', 'wp-a-builds.json')
VDIR = os.path.join(ROOT, 'data', 'wp-a-variants')
W = {'S': 2, 'A': 1}

def norm(name):
    n = re.sub(r'\s+', ' ', name or '').strip()
    n = n.replace('’', "'")
    return n

def canon(name):
    """Collapse 'Enigma Mage Plate (ethereal)', 'Demon Limb (in Horadric Cube)', 'Shimmering SC of Good Luck x7' → a key
    that matches the main-table spelling ('Enigma', 'Demon Limb'). Parenthetical / bracket notes, 'xN' counts and
    'socketed …' tails are dropped; everything is lower-cased."""
    n = norm(name).lower()
    n = re.sub(r'\([^)]*\)|\[[^\]]*\]', ' ', n)
    n = re.sub(r'\bx\s?\d+\b', ' ', n)
    n = re.sub(r'\b(socketed|with|in|on)\b.*$', ' ', n)
    n = re.sub(r'[^a-z0-9\'+ ]', ' ', n)
    return re.sub(r'\s+', ' ', n).strip()

def in_main(item, main_set):
    """True when a main-table item name is contained in the variant item's canonical form (or equal)."""
    c = canon(item)
    if not c: return True
    for m in main_set:
        mc = canon(m)
        if mc and (mc == c or (len(mc) >= 4 and mc in c)): return True
    return False

NON_ITEMS = re.compile(r'battle (command|orders)|bind demon|pit lord|not an item|via call to arms|\brune\b.*sockets', re.I)

def main():
    write = '--write' in sys.argv
    ledger = json.load(open(LEDGER))
    files = sorted(glob.glob(os.path.join(VDIR, '*.json')))
    files = [f for f in files if os.path.basename(f) != 'index.json']
    index = {}          # item -> list of hits
    main_items = {}     # slug -> set of item names in main slots + merc table
    for slug, b in ledger.items():
        s = set()
        for items in b.get('slots', {}).values():
            for it in items: s.add(norm(it))
        merc = b.get('merc') or {}
        for slot in (merc.values() if isinstance(merc, dict) else []):
            for stage in (slot.values() if isinstance(slot, dict) else []):
                for it in (stage or []): s.add(norm(it))
        main_items[slug] = s
    loaded = 0
    for f in files:
        v = json.load(open(f))
        slug = v.get('slug') or os.path.basename(f)[:-5]
        if slug not in ledger:
            print('WARN: variant file for unknown build', slug, file=sys.stderr); continue
        loaded += 1
        b = ledger[slug]
        if write:
            b['variants'] = v.get('variants', [])
            b['prose_only_items'] = v.get('prose_only_items', [])
            b['variants_sources'] = v.get('sources', {})
            b['variants_notes'] = v.get('notes', '')
        def hit(item, variant, side, slot):
            item = norm(item)
            if not item: return
            index.setdefault(item, []).append({'build': slug, 'tier': b.get('tier'), 'class': b.get('class'),
                                               'variant': variant, 'side': side, 'slot': slot})
        for var in v.get('variants', []):
            vn = var.get('name', '?')
            for slot, items in (var.get('player') or {}).items():
                for it in items or []: hit(it, vn, 'player', slot)
            merc = var.get('merc') or {}
            for slot, items in merc.items():
                if slot == 'type' or not isinstance(items, list): continue
                for it in items: hit(it, vn, 'merc', slot)
        for it in v.get('prose_only_items', []) or []:
            hit(it, 'prose', 'player', 'prose')
    # new demand = items whose every hit comes from a build whose main tables do not list it
    groups = {}   # canonical key -> {'names': set, 'builds': {slug: set(variant/side)}}
    for item, hits in index.items():
        if NON_ITEMS.search(item): continue
        key = canon(item)
        if not key: continue
        for h in hits:
            if in_main(item, main_items.get(h['build'], set())): continue   # already counted by WP-A
            g = groups.setdefault(key, {'names': set(), 'builds': {}})
            g['names'].add(item)
            g['builds'].setdefault(h['build'], set()).add(f"{h['variant']}/{h['side']}")
    rows = []
    for key, g in groups.items():
        weight = sum(W.get(ledger[s].get('tier'), 1) for s in g['builds'])
        label = min(g['names'], key=len)
        rows.append((weight, label, g['builds'], sorted(g['names'])))
    rows.sort(key=lambda r: (-r[0], r[1].lower()))
    lines = [f"# WP-A variants — items named only in variant / merc / prose sections ({datetime.date.today()}; {loaded} guides merged)\n",
             "Weight = Σ S(2)/A(1) over builds whose MAIN gear tables do not already list the item. These are the demand signals appendix B missed.\n",
             "| weight | item | builds → variant/side |", "|--:|---|---|"]
    for w, item, builds, names in rows:
        cell = ' · '.join(f"{s} ({', '.join(sorted(v))})" for s, v in sorted(builds.items()))
        extra = '' if len(names) == 1 else ' <small>' + ' / '.join(n for n in names if n != item)[:160] + '</small>'
        lines.append(f"| {w} | {item}{extra} | {cell} |")
    report = '\n'.join(lines) + '\n'
    if write:
        bak = LEDGER + '.bak-' + datetime.date.today().strftime('%Y%m%d')
        if not os.path.exists(bak): open(bak, 'w').write(open(LEDGER).read())
        json.dump(ledger, open(LEDGER, 'w'), indent=2, ensure_ascii=False)
        json.dump(index, open(os.path.join(VDIR, 'index.json'), 'w'), indent=1, ensure_ascii=False)
        open(os.path.join(VDIR, 'new-demand.md'), 'w').write(report)
        print(f'merged {loaded} guides; {len(index)} distinct items; {len(rows)} new-demand items; backup {bak}')
    else:
        print(report)
if __name__ == '__main__': main()
