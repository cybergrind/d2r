#!/usr/bin/env python3
"""rune_ladder.py — WP-F: solve the empirical SC/NL/PC rune ladder (Ist = 1) from Traderie rune-for-rune asks.

  python3 pricing/tools/rune_ladder.py [--verbose] [--legacy]
      default: prints the pricing/data/wp-f-ladder.json hand-off shape to stdout ("_meta" + one object per rune with the keys
               wp_b_buckets.py / wp_g_build.py read: _meta.date and <Rune>.ist; plus ist_median/min/max, n_asks, n_sellers,
               prop1854_split, d2io_guide_band, dev_vs_guide_band, flag_gt30pct). diablo2.io fills are NOT computed here —
               the "fills"/"bids_active" arrays are emitted empty and must be merged from search-rune-*-sold.html by hand.
      --legacy: the original {"ladder": {...}, "iterations", "lem_fixed"} shape.  --verbose lists every listing used on stderr.

Input: pricing/raw/traderie/rune-<Name>.json (raw listings, already SC/NL/PC filtered by `traderie.py listings ID 2 --sc --nl --pc --json`).
Reading of a Traderie price (verified on the raw JSON, 2026-09-18):
  * listing.prices[] entries carry "group": entries sharing a group are ONE bundle (summed); different groups are ALTERNATIVE asks
    the seller accepts ("1x Jah OR 1x Zod"). "add" is False/None everywhere in the rune pulls (not used).
  * The ask is for the WHOLE STACK ("amount"): "Gul x7 | 1 Jah OR 1 Zod", "Mal x18 | 1 Zod". A minority price per unit
    ("Ber x3 | 2 Lo OR 1 Jah"). Every amount>1 listing is classified by which reading lands closer (log-distance) to the current
    solution; the per-stack reading feeds the ladder and per-unit-only listings are excluded (counted in the output).
  * Effective ask = the cheapest alternative at the current solution (a buyer pays the cheapest accepted bundle; single low runes
    are often listed "1 Ist OR 1 Mal OR 1 Um OR 2 Lem", where only the last alternative is a real price).
Solver: a per-rune median iteration diverges (Jah/Ber/Zod/Cham are quoted against each other and every seller asks a premium, so the
cycle inflates without bound). Instead: joint log-linear least squares, x_r = log(value in Ist), Ist pinned at 0; one equation per
listing: log(amount) + x_R = log(bundle value), multi-rune bundles linearised at the current solution; outer loop re-selects the
cheapest alternative / per-stack reading and repeats until no rune moves by >0.5 %. Seed = diablo2.io price guide (2026-08-28) band
midpoints; Lem is fixed at its guide midpoint (0.20 Ist, too few observations); bundles containing any other rune outside Pul..Zod are dropped.
Sellers multi-list (Zod: 41 of 61 listings from one seller): every listing is weighted 1/(listings of its seller) in the LS and in the median.
Output per rune: ist (joint solution), ist_median (seller-weighted) / min / max = spread of individual per-listing asks valued at the joint solution, n_asks, n_sellers.
"""
import json, sys, statistics, math
import numpy as np
RUNES=['Pul','Um','Mal','Ist','Gul','Vex','Ohm','Lo','Sur','Ber','Jah','Cham','Zod']
GUIDE={'Lem':(0.15,0.25),'Pul':(0.25,0.35),'Um':(0.35,0.5),'Mal':(0.55,0.7),'Ist':(1,1),'Gul':(1.4,1.7),'Vex':(2.5,3),'Ohm':(3.5,4),
       'Lo':(5,6),'Sur':(7,9),'Ber':(10,12),'Jah':(10,12),'Zod':(10,12),'Cham':(4,8)}  # Cham "offer" in NL column → seeded from its Ladder column 4-8
v={k:(a+b)/2 for k,(a,b) in GUIDE.items()}
UNK=[r for r in RUNES if r!='Ist']; IDX={r:i for i,r in enumerate(UNK)}
def load():
    data={}
    for r in RUNES:
        rows=[]
        for l in json.load(open(f'pricing/raw/traderie/rune-{r}.json')):
            pr=l.get('prices') or []
            if not pr or any(x.get('type')!='runes' for x in pr) or not l.get('amount'): continue
            g={}
            for x in pr: g.setdefault(x['group'],[]).append((x['name'].replace(' Rune',''),x.get('quantity') or 1))
            alts=[b for b in g.values() if all(n!=r and n in v for n,_ in b)]   # drop self-referencing / unknown-rune alternatives
            if alts: rows.append({'id':l['id'],'seller':l.get('seller_id'),'amount':l['amount'],'date':l['updated_at'][:10],'alts':alts})
        cnt={}
        for row in rows: cnt[row['seller']]=cnt.get(row['seller'],0)+1
        for row in rows: row['w']=1.0/cnt[row['seller']]        # one vote per seller (Zod: 41 of 61 listings are one seller's)
        data[r]=rows
    return data
def wmedian(pairs):
    pairs=sorted(pairs); tot=sum(w for _,w in pairs); acc=0
    for x,w in pairs:
        acc+=w
        if acc>=tot/2: return x
def bval(b): return sum(q*v[n] for n,q in b)
def solve(data):
    for it in range(100):
        A=[];y=[];W=[];used={r:[] for r in RUNES};perunit={r:[] for r in RUNES}
        for r in RUNES:
            for row in data[r]:
                b=min(row['alts'],key=bval); eff=bval(b); a=row['amount']
                if a>1 and abs(math.log(eff/v[r]))<abs(math.log(eff/a/v[r])): perunit[r].append((row,b,eff)); continue
                used[r].append((row,b,eff/a))
                # equation: log a + x_R = log(bundle) ; bundle linearised: log(sum q v) ≈ const + sum_i w_i x_i, w_i = q_i v_i / bundle
                coef=np.zeros(len(UNK)); const=math.log(eff)
                for n,q in b:
                    w=q*v[n]/eff
                    if n in IDX: coef[IDX[n]]+=w; const-=w*math.log(v[n])
                if r in IDX: coef[IDX[r]]-=1
                A.append(coef); y.append(const-math.log(a)); W.append(math.sqrt(row['w']))   # -coef·x = log(bundle_const) - log a
        A=np.array(A); y=np.array(y); W=np.array(W)
        x,*_=np.linalg.lstsq(-A*W[:,None],y*W,rcond=None)                                 # seller-weighted least squares
        new={r:math.exp(x[IDX[r]]) for r in UNK}
        delta=max(abs(new[r]/v[r]-1) for r in UNK); v.update(new)
        if delta<0.005: break
    return used,perunit,it+1
def main(a):
    data=load(); used,perunit,iters=solve(data)
    out={}
    for r in RUNES:
        u=[s for _,_,s in used[r]]; lo,hi=GUIDE[r]; val=v[r]
        wm=wmedian([(s,row['w']) for row,_,s in used[r]]) if u else None
        dev=(val/lo-1) if val<lo else ((val/hi-1) if val>hi else 0.0)
        out[r]={'ist':round(val,3),'ist_median':round(wm,3) if u else None,'ist_median_unweighted':round(statistics.median(u),3) if u else None,'n_sellers':len({row['seller'] for row,_,_ in used[r]}),'ist_min':round(min(u),3) if u else None,
                'ist_max':round(max(u),3) if u else None,'n_asks':len(u),'n_perunit_excluded':len(perunit[r]),
                'n_amount_gt1_perstack':sum(1 for row,_,_ in used[r] if row['amount']>1),'d2io_guide_band':[lo,hi],'dev_vs_guide':round(dev,3)}
    if '--legacy' in a:
        print(json.dumps({'ladder':out,'iterations':iters,'lem_fixed':v['Lem']},indent=1))
    else:
        # hand-off shape (pricing/data/wp-f-ladder.json): read by wp_b_buckets.py (_meta.date, <Rune>.ist) and wp_g_build.py (<Rune>.ist)
        dates=[row['date'] for r in RUNES for row in data[r]]; date=max(dates) if dates else ''
        hand={'_meta':{'date':date,'scope':'Softcore / Non-Ladder / PC / Reign of the Warlock economy','unit':'Ist Rune = 1.0',
              'asks_source':'Traderie JSON API, raw pricing/raw/traderie/rune-<Name>.json (client-filtered SC/NL/PC), asks paid purely in runes',
              'fills_source':'NOT computed by rune_ladder.py: merge diablo2.io activesold=1 rows (pricing/raw/d2io/search-rune-*-sold.html) by hand into fills/bids_active',
              'method':'pricing/tools/rune_ladder.py: cheapest accepted alternative per listing (prices[].group = OR), per-stack reading (divide by amount), per-unit-only listings excluded, one vote per seller, joint log-linear least squares with Ist pinned, seeded from the diablo2.io 2026-08-28 NL ladder; Lem fixed at %.2f'%v['Lem'],
              'which_number_to_use':'ist = joint solution (use for conversions); ist_median/min/max = seller-weighted median and spread of individual asks valued at that solution',
              'iterations':iters,'lem_fixed':v['Lem'],
              'per_stack_check':{'amount_gt1_listings_read_per_stack':sum(out[r]['n_amount_gt1_perstack'] for r in RUNES),
                                 'amount_gt1_listings_only_sensible_per_unit_excluded':sum(out[r]['n_perunit_excluded'] for r in RUNES)}}}
        for r in RUNES:
            o=out[r]; split={}
            for l in json.load(open(f'pricing/raw/traderie/rune-{r}.json')):
                gv=next((p.get('string') for p in (l.get('properties') or []) if p.get('property_id')==1854),None) or 'unset'
                split[gv]=split.get(gv,0)+1
            hand[r]={'ist':o['ist'],'ist_median':o['ist_median'],'ist_min':o['ist_min'],'ist_max':o['ist_max'],'n_asks':o['n_asks'],'n_sellers':o['n_sellers'],
                     'n_listings_sc_nl_pc':sum(split.values()),'n_perunit_excluded':o['n_perunit_excluded'],'n_amount_gt1_perstack':o['n_amount_gt1_perstack'],
                     'n_fills':0,'fills':[],'fills_ist_median':None,'bids_active':[],'d2io_guide_band':o['d2io_guide_band'],
                     'dev_vs_guide_band':o['dev_vs_guide'],'flag_gt30pct':abs(o['dev_vs_guide'])>0.30,'prop1854_split':split,'date':date}
        # Lem is not solved (too few observations): emitted fixed so wp_g_build.py can convert "Lem" fills through the same dict
        hand['Lem']={'ist':round(v['Lem'],3),'ist_median':None,'ist_min':None,'ist_max':None,'n_asks':0,'n_sellers':0,'n_listings_sc_nl_pc':0,
                     'n_perunit_excluded':0,'n_amount_gt1_perstack':0,'n_fills':0,'fills':[],'fills_ist_median':None,'bids_active':[],
                     'd2io_guide_band':list(GUIDE['Lem']),'dev_vs_guide_band':0.0,'flag_gt30pct':False,'prop1854_split':{},'date':date,
                     'note':'fixed at the diablo2.io 2026-08-28 NL band midpoint, not solved'}
        print(json.dumps(hand,indent=1))
    if '--verbose' in a:
        for r in RUNES:
            print(f'\n== {r}: ist={out[r]["ist"]} median={out[r]["ist_median"]} n={out[r]["n_asks"]}',file=sys.stderr)
            for row,b,s in sorted(used[r],key=lambda t:t[2]):
                print(f"  {r} x{row['amount']:<3} {row['date']} -> {s:7.3f} Ist/unit via {' & '.join(f'{q}x{n}' for n,q in b):18s} | all: "+' OR '.join(' & '.join(f'{q}x{n}' for n,q in bb) for bb in row['alts']),file=sys.stderr)
            for row,b,eff in perunit[r]:
                print(f"  EXCLUDED per-unit: {r} x{row['amount']} {row['date']} eff={eff:.2f} Ist (stack would be {eff/row['amount']:.3f}) | "+' OR '.join(' & '.join(f'{q}x{n}' for n,q in bb) for bb in row['alts']),file=sys.stderr)
if __name__=='__main__': main(sys.argv[1:])
