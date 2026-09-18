#!/usr/bin/env python3
"""WP-B bucketing of raw Traderie pulls (pricing/raw/traderie/<slug>.json, pulled 2026-09-18).
Scope filter: 799 softcore, 800 False (NL), 798 PC, 1854 not containing 'lord of destruction'/'classic' (unset kept).
Buckets: <sockets>os/<eth|noneth>/<rarity>[/15ed]; 'filled' sockets (934) go to a separate bucket suffix.
Ist conversion: §1.2 NL ladder midpoints (diablo2.io price guide 2026-08-28). Sub-Lem runes = 0.1 (flagged).
"""
import json, statistics, sys, os, glob, re
ROOT = '/mnt/extra/1000/games/d2r'
# Rune ladder: pricing/data/wp-f-ladder.json field "ist" (joint NL solution, Ist = 1.0, dated 2026-09-18) for Pul..Zod.
# Runes below Pul are not in the WP-F ladder: Lem = 0.2 = midpoint of the diablo2.io 2026-08-28 NL band (0.15-0.25).
_WPF = json.load(open(ROOT + '/pricing/data/wp-f-ladder.json'))
LADDER = {k: v['ist'] for k, v in _WPF.items() if k != '_meta'}
LADDER.setdefault('Lem', 0.20)
LADDER_SOURCE = f"pricing/data/wp-f-ladder.json (date {_WPF['_meta']['date']}), field ist; Lem 0.2 from the diablo2.io 2026-08-28 NL band"

SUBLEM = {'El','Eld','Tir','Nef','Eth','Ith','Tal','Ral','Ort','Thul','Amn','Sol','Shael','Dol','Hel','Io','Lum','Ko','Fal'}
SUBLEM_IST = 0.1  # below the ladder floor (< Lem 0.15); flagged 'sublem'
GEM_IST = {'Perfect Gem': 1/40, 'Perfect Amethyst': 1/12, 'Perfect Ruby': 1/40, 'Perfect Sapphire': 1/40, 'Perfect Topaz': 1/40,
           'Perfect Emerald': 1/40, 'Perfect Diamond': 1/40, 'Perfect Skull': 1/40}  # d2io: Ist ≈ 40 PGems / ≈ 12 PAmethyst
META = {797, 798, 799, 800, 1854, 932}

def props(l):
    d = {}
    for p in l.get('properties') or []:
        d[p['property_id']] = p['number'] if p['type'] == 'number' else (p['bool'] if p['type'] == 'bool' else p.get('string'))
    return d

def affix_str(l):
    out = []
    for p in l.get('properties') or []:
        if p['property_id'] in META or p['property_id'] in BASE_PROPS: continue
        v = p['number'] if p['type'] == 'number' else (p['bool'] if p['type'] == 'bool' else p.get('string'))
        out.append(f"{p['property'].replace('{{value}}', 'x')}={v}")
    return '; '.join(out)

def ask_str(l):
    pr = l.get('prices') or []
    groups = {}
    for x in pr: groups.setdefault(x.get('group', 0), []).append(x)
    s = ' OR '.join(' + '.join(f"{x.get('quantity', 1)}x {x['name']}" for x in e) for e in groups.values())
    if l.get('make_offer'): s = (s + ' (or offer)') if s else 'make offer'
    return s or '?'

def _group_ist(entries):
    """sum one price group (entries sharing prices[].group = paid together); None if any entry is not convertible"""
    tot = 0.0; flags = []
    for x in entries:
        q = x.get('quantity', 1) or 1; n = x['name']
        if x.get('type') == 'runes':
            r = n.replace(' Rune', '')
            if r in LADDER:
                tot += q * LADDER[r]
            elif r in SUBLEM:
                tot += q * SUBLEM_IST; flags.append('sublem')
            else:
                return None, ['unknown-rune:' + r]
        elif x.get('type') == 'gems' and n in GEM_IST:
            tot += q * GEM_IST[n]; flags.append('gems')
        else:
            return None, ['non-rune:' + n]
    return round(tot, 3), flags

def to_ist(l):
    """returns (ist or None, flags list). prices[].group: same group = summed, different groups = OR-alternatives
    (verified by WP-F on ~1,200 multi-group listings). Effective ask = cheapest convertible alternative; a listing
    whose alternatives are all non-rune counts as non-rune; no prices at all = offer."""
    pr = l.get('prices') or []
    if not pr: return None, ['offer' if l.get('make_offer') else 'noprice']
    groups = {}
    for x in pr: groups.setdefault(x.get('group', 0), []).append(x)
    best = None; bflags = []; nonrune = []
    for g, entries in groups.items():
        v, f = _group_ist(entries)
        if v is None: nonrune += f; continue
        if best is None or v < best[0]: best = (v, f)
    if best is None: return None, nonrune[:1] or ['noprice']
    flags = list(best[1])
    if len(groups) > 1: flags.append(f'alt{len(groups)}')
    return best[0], flags

def ask_str_chosen(l):
    """the alternative that priced the listing (for the cheapest-asks display)"""
    pr = l.get('prices') or []
    groups = {}
    for x in pr: groups.setdefault(x.get('group', 0), []).append(x)
    best = None
    for g, entries in groups.items():
        v, _ = _group_ist(entries)
        if v is not None and (best is None or v < best[0]): best = (v, entries)
    if best is None: return ask_str(l)
    s = ' + '.join(f"{x.get('quantity', 1)}x {x['name']}" for x in best[1])
    return s + (f' [1 of {len(groups)} alternatives]' if len(groups) > 1 else '')

BASE_PROPS = {402, 738, 425, 399, 937, 423, 510, 1855, 796, 1940, 934}  # sockets, eth, ED%, +def, max dur, +AR, EDmg%, def, req lvl, 'Base Item (Ranged)', filled sockets
RES_BASES = {'sacred-targe', 'sacred-rondache', 'targe'}  # 441 all-res is the paladin-shield auto-mod, not an affix, on these
BOW_BASES = {'grand-matron-bow', 'matriarchal-bow'}  # 454 +x Bow&Crossbow skills is the Amazon-bow auto-mod

def bucket_key(p, slug=''):
    s = p.get(402) or 0
    eth = 'eth' if p.get(738) else 'noneth'
    r = (p.get(797) or 'unset').lower()
    k = f"{int(s)}os/{eth}/{r}"
    if (p.get(425) or 0) >= 15 or (p.get(510) or 0) >= 15: k += '/15ed'
    if slug in RES_BASES:
        res = p.get(441)
        k += '/res?' if res is None else ('/res45' if res >= 45 else ('/res40-44' if res >= 40 else '/res<40'))
    if slug in BOW_BASES:
        sk = p.get(454)
        k += '/skill?' if sk is None else ('/skill3' if sk >= 3 else f'/skill{int(sk)}')
    base = BASE_PROPS | ({441} if slug in RES_BASES else set()) | ({454} if slug in BOW_BASES else set())
    if r in ('normal', 'superior', 'unset', 'low quality') and any(pid not in base and pid not in META for pid in p):
        k += '/affixed'  # white-labelled but carries affix/staff-mod properties -> not a clean base
    if p.get(934): k += '/filled'
    return k

def analyze(slug, item_id):
    f = f'{ROOT}/pricing/raw/traderie/{slug}.json'
    if not os.path.exists(f): return None
    ls = json.load(open(f))
    n_total = len(ls)
    gv_all = {}; gv_scope = {}
    scope = []
    for l in ls:
        p = props(l)
        gv = p.get(1854) or 'unset'
        gv_all[gv] = gv_all.get(gv, 0) + 1
        if p.get(799) == 'softcore' and p.get(800) is False and p.get(798) == 'PC':
            gv_scope[gv] = gv_scope.get(gv, 0) + 1
            if 'lord of destruction' not in gv and 'classic' not in gv: scope.append(l)  # excludes LoD/classic and combined values; 'unset' kept
    buckets = {}
    for l in scope:
        p = props(l)
        k = bucket_key(p, slug)
        ist, flags = to_ist(l)
        row = {'ask': ask_str_chosen(l), 'ask_full': ask_str(l), 'ist': ist, 'flags': flags, 'def': p.get(1855), 'ed': p.get(425), 'amount': l.get('amount'),
               'updated': l['updated_at'][:10], 'listing_id': l['id']}
        if (p.get(797) or '').lower() in ('magic', 'rare', 'crafted') or '/affixed' in k: row['affixes'] = affix_str(l)
        if slug in RES_BASES: row['res'] = p.get(441)
        if slug in BOW_BASES: row['bow_skills'] = p.get(454)
        buckets.setdefault(k, []).append(row)
    out = {}
    for k, rows in sorted(buckets.items()):
        priced = sorted([r for r in rows if r['ist'] is not None], key=lambda r: r['ist'])
        offers = [r for r in rows if r['ist'] is None and 'offer' in r['flags']]
        other = [r for r in rows if r['ist'] is None and 'offer' not in r['flags']]
        b = {'n': len(rows), 'n_priced': len(priced), 'n_offer': len(offers), 'n_nonrune': len(other),
             'thin': len(rows) < 3,
             'min_ist': priced[0]['ist'] if priced else None,
             'median_ist': round(statistics.median([r['ist'] for r in priced]), 3) if priced else None,
             'max_ist': priced[-1]['ist'] if priced else None,
             'amount_gt1': sum(1 for r in rows if (r['amount'] or 1) > 1),
             'cheapest': priced[:3]}
        if other: b['nonrune_asks'] = [r['ask_full'] for r in other][:3]
        if any('affixes' in r for r in rows): b['all_rows'] = rows  # magic/rare: keep everything for affix reading
        out[k] = b
    return {'item_id': item_id, 'pulled_pages': (n_total + 49) // 50, 'n_total': n_total, 'n_scope': len(scope),
            'game_version_dist_all': gv_all, 'game_version_dist_sc_nl_pc': gv_scope, 'buckets': out,
            'pulled': '2026-09-18', 'filter': 'SC/NL/PC (props 799/800/798) + 1854 not in {lord of destruction, classic} (unset kept), client-side; server: item id only'}

NAMES = {'archon-plate':'Archon Plate','mage-plate':'Mage Plate','dusk-shroud':'Dusk Shroud','wire-fleece':'Wire Fleece','monarch':'Monarch','sacred-targe':'Sacred Targe','sacred-rondache':'Sacred Rondache','phase-blade':'Phase Blade','berserker-axe':'Berserker Axe','colossus-blade':'Colossus Blade','thresher':'Thresher','giant-thresher':'Giant Thresher','cryptic-axe':'Cryptic Axe','great-poleaxe':'Great Poleaxe','colossus-voulge':'Colossus Voulge','flail':'Flail','crystal-sword':'Crystal Sword','grand-matron-bow':'Grand Matron Bow','matriarchal-bow':'Matriarchal Bow','matriarchal-javelin':'Matriarchal Javelin','greater-talons':'Greater Talons','runic-talons':'Runic Talons','diadem':'Diadem','tiara':'Tiara','circlet':'Circlet','coronet':'Coronet','blasphemous-grimoire':'Blasphemous Grimoire','possessed-grimoire':'Possessed Grimoire','grimoire':'Grimoire','legend-spike':'Legend Spike','fanged-knife':'Fanged Knife','mithril-point':'Mithril Point','bone-knife':'Bone Knife','vampirebone-gloves':'Vampirebone Gloves','sharkskin-gloves':'Sharkskin Gloves','heavy-bracers':'Heavy Bracers','demonhide-gloves':'Demonhide Gloves','chain-gloves':'Chain Gloves','vambraces':'Vambraces','bone-shield':'Bone Shield','sacred-armor':'Sacred Armor','targe':'Targe','mask':'Mask','preserved-head':'Preserved Head','mancatcher':'Mancatcher'}

def blues(out):
    def rows(slug, pred):
        res = []
        for k, v in out[slug]['buckets'].items():
            for x in v.get('all_rows', []):
                if pred(k, x): res.append({'bucket': k, 'ask': x['ask'], 'ask_full': x['ask_full'], 'ist': x['ist'], 'def': x['def'], 'updated': x['updated'], 'affixes': x.get('affixes', '')})
        res.sort(key=lambda r: (r['ist'] is None, r['ist'] or 0)); return res
    def summ(rs):
        v = sorted(r['ist'] for r in rs if r['ist'] is not None)
        return {'n': len(rs), 'n_priced': len(v), 'n_offer_or_nonrune': sum(1 for r in rs if r['ist'] is None), 'min_ist': v[0] if v else None,
                'median_ist': round(statistics.median(v), 3) if v else None, 'thin': len(rs) < 3, 'rows': rs[:12]}
    life = lambda a: int((re.search(r'\+x to Life=(\d+)', a) or [None, 0])[1] or 0)
    A = lambda x: x.get('affixes', '')
    b = {}
    b["Jeweler's Archon Plate of the Whale (4os magic, +life 90-100)"] = summ(rows('archon-plate', lambda k, x: k.startswith('4os') and 'magic' in k and 'filled' not in k and life(A(x)) >= 90))
    b["Archon Plate 4os magic, any affix (context)"] = summ(rows('archon-plate', lambda k, x: k.startswith('4os') and 'magic' in k and 'filled' not in k))
    b["Jeweler's Monarch of Deflecting (4os magic, 30 FBR/20 block)"] = summ(rows('monarch', lambda k, x: k.startswith('4os') and 'magic' in k and 'filled' not in k and 'Faster Block Rate=30' in A(x)))
    b["Monarch of Deflecting (magic, 30 FBR/20 block) with filled sockets"] = summ(rows('monarch', lambda k, x: 'magic' in k and 'filled' in k and 'Faster Block Rate=30' in A(x)))
    b["Monarch 4os magic, any affix (context)"] = summ(rows('monarch', lambda k, x: k.startswith('4os') and 'magic' in k and 'filled' not in k))
    b["Matriarchal Javelin magic +3 Jav / 40 IAS"] = summ(rows('matriarchal-javelin', lambda k, x: 'magic' in k and 'Javelin and Spear Skills (Amazon Only)=3' in A(x) and 'Attack Speed=40' in A(x)))
    b["Matriarchal Javelin magic +3 Jav / 30 IAS"] = summ(rows('matriarchal-javelin', lambda k, x: 'magic' in k and 'Javelin and Spear Skills (Amazon Only)=3' in A(x) and 'Attack Speed=30' in A(x)))
    b["Tiara magic 30 FRW (Artisan's of Speed = 3os + 30 FRW)"] = summ(rows('tiara', lambda k, x: 'magic' in k and 'Run/Walk=30' in A(x)))
    for g in ['vampirebone-gloves', 'sharkskin-gloves', 'heavy-bracers', 'demonhide-gloves', 'chain-gloves', 'vambraces']:
        b[f'{NAMES[g]} +2 Jav / 20 IAS (rare, any other affixes)'] = summ(rows(g, lambda k, x: 'rare' in k and 'Javelin and Spear Skills (Amazon Only)=2' in A(x) and 'Attack Speed=20' in A(x)))
        m = rows(g, lambda k, x: 'magic' in k and 'Javelin and Spear Skills' in A(x))
        if m: b[f'{NAMES[g]} magic +Jav skills (any IAS)'] = summ(m)
    return b

def final(out):
    import collections
    meta = {
        'pulled': '2026-09-18', 'regenerated': 'v2: OR-group price reading + WP-F ladder (same raw pulls)',
        'source': 'Traderie JSON API https://traderie.com/api/diablo2resurrected/listings?item=<id>&page=0..3 (50/page, page 0-based), via pricing/tools/traderie.py listings <id> 4 --json (no server filter); raw in pricing/raw/traderie/<slug>.json',
        'scope_filter': 'client-side: 799 Mode=softcore, 800 Ladder=false (Non-Ladder), 798 Platform=PC, 1854 Game version not containing "lord of destruction"/"classic" (unset kept, counted)',
        'ladder_ist': dict(LADDER, **{'sub-Lem runes (El..Fal)': SUBLEM_IST, 'Perfect Gem': 0.025, 'Perfect Amethyst': round(1/12, 4)}),
        'ladder_source': LADDER_SOURCE + '; sub-Lem runes 0.1 (below the guide floor, flagged "sublem"); PGem 1/40 Ist and PAmethyst 1/12 Ist from the guide line "Ist ~40 PGems or ~12 PAmethyst"',
        'bucket_key': '<sockets>os/<eth|noneth>/<rarity 797 or unset>[/15ed = 425 Enhanced Defense >=15 or 510 Enhanced Damage >=15][/res45|res40-44|res<40|res? on Sacred Targe/Rondache = prop 441][/skill3|skillN|skill? on Grand Matron/Matriarchal Bow = prop 454][/affixed = white-labelled but carries affix/staff-mod props -> not a clean base][/filled = 934 sockets contain runes/gems]',
        'price_reading': 'prices[] entries sharing a group value are summed; different group values are OR-alternatives (WP-F verified on ~1,200 multi-group listings). Effective ask = cheapest convertible (rune/pgem) alternative, flag "altN"; "ask" shows the chosen alternative, "ask_full" all alternatives joined by OR. Listings whose alternatives are all non-rune items (Small Charm, keys, shards...) are counted as n_nonrune but not priced; make_offer with no price = n_offer. Asks are ASKING prices, not fills; per whole stack (amount_gt1 counts listings with amount>1).',
        'prop_1076_note': 'The user URL filter prop_1076Min=1 = "+x to Dragon Flight (Assassin Only)". It is a real claw staff-mod (seen on 22 Greater Talons / 18 Runic Talons rows in this pull) and matches nothing on armor/weapon bases; WP-B priced bases with 402 Socketed + 738 Ethereal instead.',
        'thin': 'bucket with n<3 listings'}
    res = {'_meta': meta}; tot = sc = 0; gvall = collections.Counter(); gvsc = collections.Counter()
    for slug, d in out.items():
        tot += d['n_total']; sc += d['n_scope']; gvall.update(d['game_version_dist_all']); gvsc.update(d['game_version_dist_sc_nl_pc'])
        b = {}
        for k, v in d['buckets'].items():
            e = {x: v[x] for x in ('n', 'n_priced', 'n_offer', 'n_nonrune', 'thin', 'min_ist', 'median_ist', 'max_ist', 'amount_gt1')}
            e['cheapest'] = [{kk: c[kk] for kk in c if kk != 'listing_id'} for c in v['cheapest']]
            if 'nonrune_asks' in v: e['nonrune_asks'] = v['nonrune_asks']
            b[k] = e
        res[slug] = {'name': NAMES.get(slug, slug), 'item_id': d['item_id'], 'pulled_pages': d['pulled_pages'], 'n_total': d['n_total'], 'n_scope': d['n_scope'],
                     'game_version_dist_all': d['game_version_dist_all'], 'game_version_dist_sc_nl_pc': d['game_version_dist_sc_nl_pc'], 'buckets': b}
    meta.update({'n_total_all_bases': tot, 'n_scope_all_bases': sc, 'game_version_dist_all_listings': dict(gvall), 'game_version_dist_sc_nl_pc_listings': dict(gvsc)})
    res['_blues'] = blues(out)
    return res

if __name__ == '__main__':
    # usage: wp_b_buckets.py OUT.json [--raw]   (--raw dumps every bucket row incl. affix strings; default = the wp-b-prices.json shape)
    ids = dict(line.split() for line in open(os.path.dirname(os.path.abspath(__file__)) + '/wp_b_ids.txt') if line.strip())
    out = {}
    for slug, iid in ids.items():
        r = analyze(slug, iid)
        if r: out[slug] = r
    res = out if '--raw' in sys.argv else final(out)
    json.dump(res, open(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else '/dev/stdout', 'w'), indent=1)
