#!/usr/bin/env python3
"""d2io_search.py — diablo2.io trade search (phpBB search.php, plain GET, no login). Verified 2026-09-18.

  d2io_search.py KEYWORDS [filter=value ...] [--out FILE] [--parse FILE]

Filters (values decoded from the search page's data-param buttons, 2026-09-18):
  ladder=2 Non-ladder | ladder=1 Ladder          hc=2 Softcore | hc=1 Hardcore        plat_pc=1 (also plat_switch/plat_playstation/plat_xbox)
  activesold=2 Active only | activesold=1 Sold in the last 3 days (FILLS, not asks)     wtbs=1 WTS | wtbs=2 WTB
  legacy_resu=2 Reign of the Warlock | legacy_resu=1 Resurrected (pre-RotW)             xc=1 Expansion | xc=2 Non-expansion
  irarity: 1 Unique 2 Runeword 3 Set 4 Base 5 Crafted 6 Rare 7 Magic 8 Misc(runes/gems/keys) 9 Player services
  charm=1 Small 2 Large 3 Grand      skiller=1 resists=1 life=1 mana=1 magicfind=1 extragold=1 ias=1 fcr=1 frw=1 fhr=1 ed=1 mmd=1 ar=1
  eth=1 Ethereal | eth=2 Non-eth     super=1 Superior | super=2 Non-superior     unid=1 Unidentified | unid=2 Identified
  imaxsockets=1..6 (exact socket count) | imaxsockets=7 No sockets     perfect=1 Perfect roll     online=1 seller online     region=1 Americas 2 Europe 3 Asia
  iitemtype=Jewels|Rings|Amulets|Body%20Armor|Helms|Shields|Grimoires|Targes|Katars|Daggers|Swords|Axes|Polearms|Bows|Javelins|Orbs|Staves|Wands|...
  iclassspec=1..8 class-specific, imercspec=1..5 merc-specific
KEYWORDS ARE REQUIRED: a search with empty keywords and only filters returns "Found 0 matches" (tested 2026-09-18).
Behaviour: ~30 trades per page ("Page 1 of N"); a SECOND search within ~20 s returns an empty result (phpBB flood control for guests) —
space requests ≥ 30 s apart (26 s still produced an empty page once) and retry once on an empty result. Rows carry markers: title="Non-Ladder character" / "Hardcore character", "Windows PC", region, "Want to Sell"/"Want to Buy",
class zi-tinylogrotw = RotW listing, text "SOLD" for completed trades. Prices are free text in the title/body ("LF 2 Ist", "Offer: PUL ...").
The item tooltip is inside [quote]...[/quote]. Example:
  d2io_search.py jewel ladder=2 hc=2 plat_pc=1 activesold=1 legacy_resu=2 --out pricing/raw/d2io/search-jewel-sold.html
"""
import re, subprocess, sys, html
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
BASE='https://diablo2.io/search.php?fid%5B%5D=16&terms=all&sc=0&sf=titleonly&sr=on&sk=t&sd=d&st=0&ch=300&t=0&submit=Search'
def parse(t):
    rows=[]
    parts=re.split(r'(?=<a[^>]+href="/trade/[^"]+\.html")',t)
    seen=set()
    for part in parts[1:]:
        m=re.match(r'<a[^>]+href="(/trade/[^"]+\.html)"',part); slug=m.group(1)
        if slug in seen: continue
        seen.add(slug)
        blk=part[:6000]
        nl='NL' if 'Non-Ladder character' in blk else ('L' if 'Ladder character' in blk else '?')
        hc='HC' if 'Hardcore character' in blk else 'SC'
        plat='PC' if 'Windows PC' in blk else ('console' if re.search(r'Switch|Playstation|Xbox',blk) else '?')
        rotw='RotW' if 'zi-tinylogrotw' in blk else ''
        sold='SOLD' if re.search(r'>\s*SOLD\s*<',blk) else ''
        txt=re.sub(r'<[^>]+>',' ',blk); txt=html.unescape(re.sub(r'\s+',' ',txt)).strip()
        txt=txt.split('Listed ')[0][:400]
        rows.append((slug,nl,hc,plat,rotw,sold,txt))
    return rows
def main(a):
    if '--parse' in a:
        t=open(a[a.index('--parse')+1],errors='ignore').read()
    else:
        skip={a[i+1] for i,x in enumerate(a) if x in('--out','--parse') and i+1<len(a)}
        kw=[x for x in a if '=' not in x and not x.startswith('--') and x not in skip]
        fl=[x for x in a if '=' in x]
        import urllib.parse
        url=BASE+'&keywords='+urllib.parse.quote_plus(' '.join(kw))+''.join('&'+f for f in fl)
        t=subprocess.run(['curl','-s','-A',UA,'--max-time','60',url],capture_output=True,text=True).stdout
        if '--out' in a: open(a[a.index('--out')+1],'w').write(t)
        print('#',url,file=sys.stderr)
    pg=re.search(r"Page\s*(?:<[^>]+>\s*)*1\s*(?:<[^>]+>\s*)*of\s*(?:<[^>]+>\s*)*(\d+)",t); print('# pages:',pg.group(1) if pg else '?',file=sys.stderr)
    fm=re.search(r'Found\s*(?:<[^>]+>\s*)*(\d+)\s*(?:<[^>]+>\s*)*matches',t); print('# matches:',fm.group(1) if fm else '?',file=sys.stderr)
    rows=parse(t)
    if not rows: print('# 0 rows — flood control? wait 30 s and retry',file=sys.stderr)
    for r in rows: print(' | '.join(r))
if __name__=='__main__': main(sys.argv[1:])
