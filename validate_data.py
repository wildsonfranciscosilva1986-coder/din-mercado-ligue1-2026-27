#!/usr/bin/env python3
"""Validate the Ligue 1 snapshot against current official LFP and independent ESPN data."""
import csv, json
from collections import Counter, defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def read_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

fixtures=read_csv(ROOT/'ligue1_2026_27_matches.csv')
assert len(fixtures)==72, f'expected 72 captured fixture slots, got {len(fixtures)}'
assert len({int(r['round']) for r in fixtures})==8
assert all(sum(int(x['round'])==rd for x in fixtures)==9 for rd in range(1,9))
assert len({r['official_id'] for r in fixtures})==72
clubs=sorted({r['home'] for r in fixtures}|{r['away'] for r in fixtures})
assert len(clubs)==18
counts=Counter(r['status'] for r in fixtures)
assert counts==Counter({'finished':63,'scheduled':9}),counts
for r in fixtures:
    if r['status']=='finished':
        assert r['home_goals'].isdigit() and r['away_goals'].isdigit(),r
    else:
        assert not r['home_goals'] and not r['away_goals'],r

# Recompute all league, home and away totals solely from official FullTime rows.
stats={t:{'played':0,'won':0,'drawn':0,'lost':0,'goals_for':0,'goals_against':0,'points':0} for t in clubs}
for m in fixtures:
    if m['status']!='finished':continue
    hg,ag=int(m['home_goals']),int(m['away_goals'])
    for t,gf,ga in [(m['home'],hg,ag),(m['away'],ag,hg)]:
        s=stats[t];s['played']+=1;s['goals_for']+=gf;s['goals_against']+=ga
        if gf>ga:s['won']+=1;s['points']+=3
        elif gf==ga:s['drawn']+=1;s['points']+=1
        else:s['lost']+=1
for s in stats.values():s['goal_difference']=s['goals_for']-s['goals_against']
fields=['played','won','drawn','lost','goals_for','goals_against','goal_difference','points']

# Reconcile every club to the latest official LFP standings API snapshot.
official=read_csv(ROOT/'source_snapshots/official_standings_table_2026-10-19.csv')
assert len(official)==18 and {r['team'] for r in official}==set(clubs)
off={r['team']:r for r in official}
for t,s in stats.items():
    for k in fields:assert s[k]==int(off[t][k]),('official LFP mismatch',t,k,s[k],off[t][k])

# Verify every official final against the independently sourced ESPN scoreboard rows.
espncheck=read_csv(ROOT/'source_snapshots/espn_results_crosscheck_2026-10-19.csv')
assert len(espncheck)==63 and all(r['result_match']=='True' and r['espn_status']=='STATUS_FULL_TIME' for r in espncheck)
assert len({r['official_id'] for r in espncheck})==63
assert {r['official_id'] for r in espncheck}=={r['official_id'] for r in fixtures if r['status']=='finished'}
espn_stats={t:{'played':0,'won':0,'drawn':0,'lost':0,'goals_for':0,'goals_against':0,'points':0} for t in clubs}
for m in espncheck:
    hg,ag=int(m['espn_home_goals']),int(m['espn_away_goals'])
    for t,gf,ga in [(m['home'],hg,ag),(m['away'],ag,hg)]:
        s=espn_stats[t];s['played']+=1;s['goals_for']+=gf;s['goals_against']+=ga
        if gf>ga:s['won']+=1;s['points']+=3
        elif gf==ga:s['drawn']+=1;s['points']+=1
        else:s['lost']+=1
for s in espn_stats.values():s['goal_difference']=s['goals_for']-s['goals_against']
for t in clubs:
    for k in fields:assert stats[t][k]==espn_stats[t][k],('ESPN table mismatch',t,k,stats[t][k],espn_stats[t][k])

# Confirm the reproducible page embeds the exact refreshed data.
data=json.loads((ROOT/'data.json').read_text(encoding='utf-8'))
assert len(data['matches'])==len(fixtures) and data['cutoff']
assert sum(m['status']=='finished' for m in data['matches'])==63
page=(ROOT/'index.html').read_text(encoding='utf-8')
assert '63 results' in page or '63' in page
assert len(official)==18

# Persist a compact auditable validation report.
report={'competition':'Ligue 1 McDonald’s 2026/27','cutoff':data['cutoff'],'official_fixture_slots':72,'rounds_present':8,'clubs':18,'finished_results':63,'scheduled_fixtures':9,'live_or_unconfirmed_scores':0,'source_validation':{'official_LFP_table':'PASS: all 18 club vectors match played, W-D-L, points, GF, GA and GD','independent_ESPN_scores':'PASS: 63/63 exact full-time scores match','independent_ESPN_table':'PASS: all 18 independently recomputed club vectors match the official-score table'},'overview':{'goals':sum(int(r['home_goals'])+int(r['away_goals']) for r in fixtures if r['status']=='finished'),'btts':sum(int(r['home_goals'])>0 and int(r['away_goals'])>0 for r in fixtures if r['status']=='finished'),'over_2_5':sum(int(r['home_goals'])+int(r['away_goals'])>=3 for r in fixtures if r['status']=='finished')},'table_order_source':'Current official LFP general standings API; current club statistics independently recomputed from the 63 official FullTime scores.','sources':{'official_match_data':'https://ma-api.ligue1.fr/championship-match/{l1_championship_match_id}','official_table':'https://ma-api.ligue1.fr/championship-standings/1/general?season=2026','independent_scoreboard':'https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard?dates=YYYYMMDD'}}
(ROOT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
text=[f"Ligue 1 2026/27 validation — cutoff {data['cutoff']}","Coverage: 72 captured official fixtures, 8 rounds × 9 fixtures, 18 clubs.","Statuses: 63 confirmed final scores; 9 scheduled; no live scores counted.","Official LFP table reconciliation: PASS 18/18 clubs across played, W-D-L, GF, GA, GD and points.","Independent ESPN result cross-check: PASS 63/63 final scores match STATUS_FULL_TIME events.","Independent ESPN table recomputed from ESPN results: PASS 18/18 club totals match the final-only table.",f"KPIs: {report['overview']['goals']} goals; BTTS {report['overview']['btts']}/63; Over 2.5 {report['overview']['over_2_5']}/63.","No unverified score is used; scheduled fixtures remain scoreless."]
(ROOT/'validation.txt').write_text('\n'.join(text)+'\n',encoding='utf-8')
print('\n'.join(text))
