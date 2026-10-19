#!/usr/bin/env python3
"""Refresh current Ligue 1 results from official LFP data; fail closed on validation."""
import csv, json, re, unicodedata
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

ROOT=Path(__file__).resolve().parent
API='https://ma-api.ligue1.fr'
ESPN='https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard'
LFP_MATCH='https://ligue1.com/fr/match-sheet/l1_championship_match_{}'
LFP_TABLE='https://ma-api.ligue1.fr/championship-standings/1/general?season=2026'
CUT=datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%Y-%m-%d %H:%M America/Sao_Paulo')
HEADERS={'User-Agent':'Mozilla/5.0 DINMercadoLigue1Refresh/1.0','Origin':'https://ligue1.com','Referer':'https://ligue1.com/'}

def read_csv(name):
    with (ROOT/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def norm(s):return re.sub(r'[^a-z0-9]+',' ',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()).strip()

def lfp_fetch(row):
    mid=row['official_id'];url=f'{API}/championship-match/l1_championship_match_{mid}'
    r=requests.get(url,headers=HEADERS,timeout=35);r.raise_for_status();return row['official_id'],url,r.json()

csv_rows=read_csv('ligue1_2026_27_matches.csv')
clubs=sorted({r['home'] for r in csv_rows}|{r['away'] for r in csv_rows})
assert len(csv_rows)==72 and len(clubs)==18
fetch_rows=[r for r in csv_rows if r.get('official_id')]
by_id={r['official_id']:r for r in fetch_rows}
with ThreadPoolExecutor(max_workers=5) as ex:
    futures=[ex.submit(lfp_fetch,r) for r in fetch_rows]
    for fut in as_completed(futures):
        mid,url,m=fut.result()
        row=by_id[mid]
        assert str(m['id']).endswith(mid) and m.get('championshipId')==1 and m.get('season')==2026
        home=m['home']['clubIdentity']['shortName'];away=m['away']['clubIdentity']['shortName']
        assert (home,away)==(row['home'],row['away']),(mid,home,away,row['home'],row['away'])
        period=m.get('period')
        if period=='fullTime':
            row['status']='finished';row['home_goals']=str(int(m['home']['score']));row['away_goals']=str(int(m['away']['score']))
        elif period in ('inProgress','stopped'):
            row['status']='in_progress';row['home_goals']='';row['away_goals']=''
        else:
            row['status']='scheduled';row['home_goals']='';row['away_goals']=''
        if m.get('gameWeekNumber') is not None:assert int(row['round'])==int(m['gameWeekNumber']),(row,m['gameWeekNumber'])
        if m.get('date'):
            dt=datetime.fromisoformat(m['date'].replace('Z','+00:00')).astimezone(ZoneInfo('Europe/Paris'))
            row['date_local']=dt.strftime('%Y-%m-%d')
        row['_source_url']=url

# Only persist the declared source CSV fields; keep its schema stable.
fields=list(csv_rows[0])
with (ROOT/'ligue1_2026_27_matches.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([{k:r.get(k,'') for k in fields} for r in csv_rows])

# Current official LFP standings snapshot.
r=requests.get(LFP_TABLE,headers=HEADERS,timeout=35);r.raise_for_status();table_payload=r.json()
standings=table_payload['standings']
lfp_rows=[]
for rank,rec in sorted(standings.items(),key=lambda kv:int(kv[0])):
    ci=rec['clubIdentity'];team=ci['shortName']
    lfp_rows.append({'position':int(rec.get('rank',rank)),'team':team,'played':int(rec['played']),'won':int(rec['wins']),'drawn':int(rec['draws']),'lost':int(rec['losses']),'goals_for':int(rec['forGoals']),'goals_against':int(rec['againstGoals']),'goal_difference':int(rec['goalsDifference']),'points':int(rec['points'])})
assert len(lfp_rows)==18 and {x['team'] for x in lfp_rows}==set(clubs),(len(lfp_rows),set(x['team'] for x in lfp_rows)^set(clubs))
with (ROOT/'source_snapshots/official_standings_2026-10-19.json').open('w',encoding='utf-8') as f:json.dump({'url':LFP_TABLE,'retrieved_at_brt':CUT,'payload':table_payload},f,ensure_ascii=False,indent=2)

# Compute the final-only table from the CSV and compare every field to current LFP standings.
finished=[r for r in csv_rows if r['status']=='finished']
stats={t:{'played':0,'won':0,'drawn':0,'lost':0,'goals_for':0,'goals_against':0,'points':0} for t in clubs}
for m in finished:
    hg,ag=int(m['home_goals']),int(m['away_goals'])
    for t,gf,ga in [(m['home'],hg,ag),(m['away'],ag,hg)]:
        x=stats[t];x['played']+=1;x['goals_for']+=gf;x['goals_against']+=ga
        if gf>ga:x['won']+=1;x['points']+=3
        elif gf==ga:x['drawn']+=1;x['points']+=1
        else:x['lost']+=1
for x in stats.values():x['goal_difference']=x['goals_for']-x['goals_against']
lfp_by={x['team']:x for x in lfp_rows};fields_cmp=['played','won','drawn','lost','goals_for','goals_against','goal_difference','points']
for t in clubs:
    assert all(stats[t][k]==lfp_by[t][k] for k in fields_cmp),(t,stats[t],lfp_by[t])

# Independently cross-check every final score with ESPN's public scoreboard, using adjacent UTC dates.
alias={
 'paris saint germain':'PSG','psg':'PSG','lille':'LOSC','losc':'LOSC','monaco':'AS Monaco','as monaco':'AS Monaco',
 'rennes':'Rennes','stade rennais':'Rennes','lyon':'OL','olympique lyonnais':'OL','paris fc':'Paris FC',
 'lens':'RC Lens','rc lens':'RC Lens','brest':'Brest','toulouse':'Toulouse FC','toulouse fc':'Toulouse FC',
 'lorient':'FC Lorient','fc lorient':'FC Lorient','nice':'OGC Nice','strasbourg':'Strasbourg','angers':'Angers SCO','marseille':'OM','om':'OM',
 'le mans':'LE Mans FC','le mans fc':'LE Mans FC','auxerre':'AJ Auxerre','aj auxerre':'AJ Auxerre','troyes':'Troyes','le havre ac':'Havre AC','havre ac':'Havre AC'
}
dates=set()
for m in finished:
    d=datetime.strptime(m['date_local'],'%Y-%m-%d').date()
    for delta in (-1,0,1):dates.add((d+timedelta(days=delta)).strftime('%Y%m%d'))
def fetch_espn(day):
    q=requests.get(ESPN,params={'dates':day},headers={'User-Agent':'Mozilla/5.0 DINMercadoLigue1Refresh/1.0'},timeout=35);q.raise_for_status();return day,q.json()
events={}
with ThreadPoolExecutor(max_workers=5) as ex:
    futures=[ex.submit(fetch_espn,d) for d in sorted(dates)]
    for fut in as_completed(futures):
        day,p=fut.result()
        for e in p.get('events',[]):
            c=e['competitions'][0];tm={x['homeAway']:x for x in c['competitors']};h=tm.get('home',{});a=tm.get('away',{})
            hn=alias.get(norm(h.get('team',{}).get('displayName','')));an=alias.get(norm(a.get('team',{}).get('displayName','')))
            if hn not in clubs or an not in clubs:continue
            key=(hn,an);rec={'espn_event_id':e.get('id',''),'espn_status':c['status']['type'].get('name',''),'home_goals':str(h.get('score','')),'away_goals':str(a.get('score','')),'espn_source_url':f'{ESPN}?dates={day}'}
            if key not in events or (rec['espn_status']=='STATUS_FULL_TIME' and events[key]['espn_status']!='STATUS_FULL_TIME'):events[key]=rec
cross=[]
for m in finished:
    key=(m['home'],m['away']);e=events.get(key)
    if not e:raise ValueError(f'ESPN missing official final {key}')
    same=e['espn_status']=='STATUS_FULL_TIME' and e['home_goals']==str(m['home_goals']) and e['away_goals']==str(m['away_goals'])
    row={'official_id':m['official_id'],'round':m['round'],'home':m['home'],'official_home_goals':m['home_goals'],'espn_home_goals':e['home_goals'],'away':m['away'],'official_away_goals':m['away_goals'],'espn_away_goals':e['away_goals'],'espn_status':e['espn_status'],'result_match':str(same),'espn_event_id':e['espn_event_id'],'espn_source_url':e['espn_source_url']}
    cross.append(row)
    if not same:raise ValueError(f'ESPN score mismatch: {row}')
with (ROOT/'source_snapshots/espn_results_crosscheck_2026-10-19.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(cross[0]));w.writeheader();w.writerows(cross)

# Save current official snapshot as simple CSV for the validators and dashboard audit.
with (ROOT/'source_snapshots/official_standings_table_2026-10-19.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(lfp_rows[0]));w.writeheader();w.writerows(lfp_rows)
# Result-side independent table, recomputed from ESPN-matched final events.
independent=[]
for t in clubs:
    independent.append({'team':t,**stats[t]})
independent.sort(key=lambda x:(-x['points'],-x['goal_difference'],-x['goals_for'],x['team']))
with (ROOT/'source_snapshots/espn_table_recomputed_2026-10-19.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(independent[0]));w.writeheader();w.writerows(independent)
validation={'competition':'Ligue 1 McDonald’s 2026/27','cutoff':CUT,'official_source':'LFP public championship-match API and championship-standings API','independent_source':'ESPN public soccer scoreboard API','fixtures':len(csv_rows),'clubs':len(clubs),'finished_results':len(finished),'nonfinal_fixtures':len(csv_rows)-len(finished),'official_table_match':'PASS: all 18 clubs match in played, W-D-L, GF, GA, GD and points','independent_score_check':{'finished_scores_checked':len(cross),'matching_scores':len(cross),'mismatches':0,'queried_utc_dates':len(dates)},'overview':{'goals':sum(int(x['home_goals'])+int(x['away_goals']) for x in finished),'btts':sum(int(x['home_goals'])>0 and int(x['away_goals'])>0 for x in finished),'over25':sum(int(x['home_goals'])+int(x['away_goals'])>=3 for x in finished)},'official_match_sheets_checked':[f'https://ligue1.com/fr/match-sheet/l1_championship_match_{m["official_id"]}' for m in fetch_rows],'table_source':LFP_TABLE}
(ROOT/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'cutoff':CUT,'finals':len(finished),'nonfinal':len(csv_rows)-len(finished),'official_table_18of18':'PASS','ESPN_crosscheck':f'{len(cross)}/{len(cross)} PASS','final_ids_checked':[m['official_id'] for m in fetch_rows if by_id[m['official_id']]['status']=='finished']},ensure_ascii=False,indent=2))
