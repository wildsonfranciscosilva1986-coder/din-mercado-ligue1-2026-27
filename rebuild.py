#!/usr/bin/env python3
"""Rebuild the Ligue 1 JSON and static page from the full validated official fixture CSV."""
import csv,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
with (ROOT/'ligue1_2026_27_matches.csv').open(encoding='utf-8-sig',newline='') as f:
    rows=list(csv.DictReader(f))
with (ROOT/'validation.json').open(encoding='utf-8') as f:
    report=json.load(f)
with (ROOT/'source_snapshots/official_standings_latest.csv').open(encoding='utf-8-sig',newline='') as f:
    official=list(csv.DictReader(f))
for row in rows:
    row['round']=int(row['round'])
    for key in ('home_goals','away_goals'):
        row[key]=int(row[key]) if row[key] else None
teams=sorted({m['home'] for m in rows}|{m['away'] for m in rows})
if len(rows)!=306 or len(teams)!=18 or len(official)!=18:
    raise SystemExit(f'Full-season inputs required: fixtures={len(rows)}, clubs={len(teams)}, table={len(official)}')

stats={t:{'team':t,'played':0,'w':0,'d':0,'l':0,'gf':0,'ga':0,'pts':0,'home_played':0,'away_played':0,'home_w':0,'home_d':0,'home_l':0,'home_gf':0,'home_ga':0,'away_w':0,'away_d':0,'away_l':0,'away_gf':0,'away_ga':0} for t in teams}
for match in rows:
    if match['status']!='finished':continue
    h,a=match['home'],match['away'];hg,ag=match['home_goals'],match['away_goals']
    if hg is None or ag is None:raise SystemExit(f'FullTime fixture has no score: {match}')
    for t in (h,a):stats[t]['played']+=1
    stats[h]['gf']+=hg;stats[h]['ga']+=ag;stats[a]['gf']+=ag;stats[a]['ga']+=hg
    stats[h]['home_played']+=1;stats[a]['away_played']+=1
    stats[h]['home_gf']+=hg;stats[h]['home_ga']+=ag;stats[a]['away_gf']+=ag;stats[a]['away_ga']+=hg
    if hg>ag:stats[h]['w']+=1;stats[a]['l']+=1;stats[h]['pts']+=3;stats[h]['home_w']+=1;stats[a]['away_l']+=1
    elif hg<ag:stats[a]['w']+=1;stats[h]['l']+=1;stats[a]['pts']+=3;stats[a]['away_w']+=1;stats[h]['home_l']+=1
    else:stats[h]['d']+=1;stats[a]['d']+=1;stats[h]['pts']+=1;stats[a]['pts']+=1;stats[h]['home_d']+=1;stats[a]['away_d']+=1
for s in stats.values():
    s['gd']=s['gf']-s['ga'];s['home_pts']=3*s['home_w']+s['home_d'];s['away_pts']=3*s['away_w']+s['away_d']
order=[r['team'] for r in sorted(official,key=lambda x:int(x['position']))]
order_index={t:i for i,t in enumerate(order)}
standings=sorted(stats.values(),key=lambda s:(-s['pts'],-s['gd'],-s['gf'],order_index.get(s['team'],999)))
for i,s in enumerate(standings,1):s['rank']=i
snapshot={'cutoff':report['cutoff'],'season':'2026/27','league':"Ligue 1 McDonald's",'teams':teams,'standings':standings,'matches':rows,'homeAwayNote':report.get('home_away_schedule_note','')}
(ROOT/'data.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
subprocess.run([sys.executable,str(ROOT/'build_site.py')],cwd=ROOT,check=True)
print(f"Built {len(teams)} clubs, {len(rows)} official fixture slots, {sum(m['status']=='finished' for m in rows)} confirmed finals; cutoff {report['cutoff']}.")
