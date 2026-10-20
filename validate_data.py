#!/usr/bin/env python3
"""Validate full-season Ligue 1 fixtures, official table, ESPN scores and embedded page."""
import csv,json
from datetime import datetime
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def read(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

fixtures=read(ROOT/'ligue1_2026_27_matches.csv')
assert len(fixtures)==306, f'expected 306 official fixture slots, got {len(fixtures)}'
assert len({int(r['round']) for r in fixtures})==34
assert all(sum(int(r['round'])==rnd for r in fixtures)==9 for rnd in range(1,35))
assert len({r['official_id'] for r in fixtures})==306
clubs=sorted({r['home'] for r in fixtures}|{r['away'] for r in fixtures})
assert len(clubs)==18
for team in clubs:
    assert sum(r['home']==team or r['away']==team for r in fixtures)==34,team
home_away_anomalies=[{'team':team,'home_fixtures':sum(r['home']==team for r in fixtures),'away_fixtures':sum(r['away']==team for r in fixtures)} for team in clubs if sum(r['home']==team for r in fixtures)!=17 or sum(r['away']==team for r in fixtures)!=17]
assert home_away_anomalies in ([],[{'team':'PSG','home_fixtures':16,'away_fixtures':18},{'team':'Rennes','home_fixtures':18,'away_fixtures':16}]),home_away_anomalies
allowed={'finished','scheduled','in_progress','abandoned','postponed','cancelled'}
counts=Counter(r['status'] for r in fixtures)
assert set(counts)<=allowed,counts
finished=[r for r in fixtures if r['status']=='finished']
assert finished
for row in fixtures:
    if row['status']=='finished':
        assert row['home_goals'].isdigit() and row['away_goals'].isdigit(),row
    else:
        assert not row['home_goals'] and not row['away_goals'],row

fields=['played','won','drawn','lost','goals_for','goals_against','goal_difference','points']
stats={t:{k:0 for k in fields} for t in clubs}
for m in finished:
    hg,ag=int(m['home_goals']),int(m['away_goals'])
    for team,gf,ga in ((m['home'],hg,ag),(m['away'],ag,hg)):
        s=stats[team];s['played']+=1;s['goals_for']+=gf;s['goals_against']+=ga
        if gf>ga:s['won']+=1;s['points']+=3
        elif gf==ga:s['drawn']+=1;s['points']+=1
        else:s['lost']+=1
for s in stats.values():s['goal_difference']=s['goals_for']-s['goals_against']

official=read(ROOT/'source_snapshots/official_standings_latest.csv')
assert len(official)==18 and {r['team'] for r in official}==set(clubs)
off={r['team']:r for r in official}
for team in clubs:
    for field in fields:assert stats[team][field]==int(off[team][field]),('LFP mismatch',team,field,stats[team][field],off[team][field])

espncheck=read(ROOT/'source_snapshots/espn_results_crosscheck_latest.csv')
final_ids={r['official_id'] for r in finished}
assert len(espncheck)==len(finished) and {r['official_id'] for r in espncheck}==final_ids
assert all(r['result_match']=='True' and r['espn_status']=='STATUS_FULL_TIME' for r in espncheck)
espn_stats={t:{k:0 for k in fields} for t in clubs}
for m in espncheck:
    hg,ag=int(m['espn_home_goals']),int(m['espn_away_goals'])
    for team,gf,ga in ((m['home'],hg,ag),(m['away'],ag,hg)):
        s=espn_stats[team];s['played']+=1;s['goals_for']+=gf;s['goals_against']+=ga
        if gf>ga:s['won']+=1;s['points']+=3
        elif gf==ga:s['drawn']+=1;s['points']+=1
        else:s['lost']+=1
for s in espn_stats.values():s['goal_difference']=s['goals_for']-s['goals_against']
for team in clubs:
    for field in fields:assert stats[team][field]==espn_stats[team][field],('ESPN table mismatch',team,field,stats[team][field],espn_stats[team][field])

source_report=json.loads((ROOT/'validation.json').read_text(encoding='utf-8'))
assert source_report.get('home_away_schedule_anomalies')==home_away_anomalies
assert source_report.get('home_away_schedule_note')
data=json.loads((ROOT/'data.json').read_text(encoding='utf-8'))
assert source_report['official_fixture_slots']==306 and source_report['finished_results']==len(finished)
assert len(data['matches'])==306 and data['cutoff']==source_report['cutoff']
assert len(data['matches'])==306 and sum(m['status']=='finished' for m in data['matches'])==len(finished)
assert data.get('homeAwayNote')==source_report['home_away_schedule_note']
page=(ROOT/'index.html').read_text(encoding='utf-8')
cutoff_dt=datetime.fromisoformat(data['cutoff'])
cutoff_label=cutoff_dt.strftime('%d/%m/%Y às %H:%M BRT')
cutoff_date=cutoff_dt.strftime('%d/%m/%Y')
cutoff_time=cutoff_dt.strftime('%H:%M')
assert '__DATA__' not in page and '__FINISHED_COUNT__' not in page and '__HOME_AWAY_NOTE__' not in page
assert cutoff_label in page and data['homeAwayNote'] in page
assert f'<div class="updated"><div class="live">Recorte verificado</div><div>{cutoff_date} · {cutoff_time} BRT</div></div>' in page
assert f"['Recorte de dados','{cutoff_date}','{cutoff_time} BRT · corte validado']" in page
assert '18/10/2026 · 14:12 BRT' not in page
source_report['dashboard_validation']={'fixture_slots':len(data['matches']),'embedded_final_scores':len(finished),'page_cutoff_matches_validation':True,'status':'PASS'}
source_report.setdefault('source_validation',{})
source_report['source_validation']['official_LFP_table']=f'PASS: {len(clubs)}/18 club vectors match across played, W-D-L, points, GF, GA and GD.'
source_report['source_validation']['independent_ESPN_scores']=f'PASS: {len(espncheck)}/{len(finished)} exact FullTime scores match.'
source_report['source_validation']['independent_ESPN_table']=f'PASS: {len(clubs)}/18 independently recomputed club vectors match.'
(ROOT/'validation.json').write_text(json.dumps(source_report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
text=[f"Ligue 1 2026/27 validation — cutoff {data['cutoff']}",f"Coverage: {len(fixtures)}/306 official fixtures; 34 rounds × 9 fixtures; 18 clubs.",f"Statuses: {counts['finished']} confirmed finals; {len(fixtures)-len(finished)} nonfinal fixtures, with no nonfinal scores used.","Official LFP standings reconciliation: PASS all 18 club-stat vectors.",f"Independent ESPN result cross-check: PASS {len(espncheck)}/{len(finished)} exact STATUS_FULL_TIME scores.",f"Independent ESPN-derived table: PASS all {len(clubs)}/18 club-stat vectors.",f"KPIs: {sum(int(r['home_goals'])+int(r['away_goals']) for r in finished)} goals; BTTS {sum(int(r['home_goals'])>0 and int(r['away_goals'])>0 for r in finished)}/{len(finished)}; Over 2.5 {sum(int(r['home_goals'])+int(r['away_goals'])>=3 for r in finished)}/{len(finished)}.","Full fixture calendar and cutoff are regenerated from official LFP API data; no unverified score or kickoff is inferred."]
(ROOT/'validation.txt').write_text('\n'.join(text)+'\n',encoding='utf-8')
print('\n'.join(text))
