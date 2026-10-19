#!/usr/bin/env python3
"""Refresh the full official Ligue 1 season, cross-check every final with ESPN, fail closed."""
from __future__ import annotations
import csv, json, re, unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

ROOT=Path(__file__).resolve().parent
API='https://ma-api.ligue1.fr'
ESPN='https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard'
LFP_CALENDAR=f'{API}/championship-calendar/1?season=2026'
LFP_TABLE=f'{API}/championship-standings/1/general?season=2026'
LFP_MATCH='https://ligue1.com/en/match-sheet/{}'
CUT=datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(timespec='minutes')
PARIS=ZoneInfo('Europe/Paris')
HEADERS={'User-Agent':'Mozilla/5.0 DINMercadoLigue1Refresh/1.0','Origin':'https://ligue1.com','Referer':'https://ligue1.com/','Accept':'application/json'}

def get_json(url,params=None):
    response=requests.get(url,params=params,headers=HEADERS,timeout=40)
    response.raise_for_status()
    return response.json()

def norm(value):
    value=unicodedata.normalize('NFKD',value or '').encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+',' ',value).strip()

def parse_rounds():
    payload=get_json(LFP_CALENDAR)
    gameweeks=payload.get('gameWeeks') or {}
    if len(gameweeks)!=34 or set(map(int,gameweeks))!=set(range(1,35)):
        raise RuntimeError(f'Official LFP calendar must expose 34 rounds; got {len(gameweeks)}')
    fixtures=[];seen=set()
    for key,week in sorted(gameweeks.items(),key=lambda kv:int(kv[0])):
        rnd=int(key);ids=week.get('matchesIds') or []
        if int(week.get('gameWeekNumber',rnd))!=rnd or len(ids)!=9:
            raise RuntimeError(f'LFP calendar round {rnd} has unexpected coverage: {len(ids)} IDs')
        for full_id in ids:
            match=re.fullmatch(r'l1_championship_match_(\d+)',str(full_id))
            if not match or full_id in seen:raise RuntimeError(f'Invalid/duplicate official match ID: {full_id}')
            seen.add(full_id);fixtures.append((rnd,str(full_id),match.group(1)))
    if len(fixtures)!=306:raise RuntimeError(f'Expected 306 LFP fixture IDs, got {len(fixtures)}')
    return payload,fixtures

def fetch_match(item):
    rnd,full_id,short_id=item
    url=f'{API}/championship-match/{full_id}'
    m=get_json(url)
    if m.get('id')!=full_id or int(m.get('championshipId',-1))!=1 or int(m.get('season',-1))!=2026:
        raise RuntimeError(f'Official match identity/season mismatch: {full_id}')
    if int(m.get('gameWeekNumber',-1))!=rnd:
        raise RuntimeError(f'Official match round differs from calendar for {full_id}: {m.get("gameWeekNumber")} vs {rnd}')
    period=m.get('period')
    status_map={'fullTime':'finished','preMatch':'scheduled','inProgress':'in_progress','stopped':'in_progress','abandoned':'abandoned','postponed':'postponed','cancelled':'cancelled'}
    if period not in status_map:
        raise RuntimeError(f'Unknown official match period for {full_id}: {period!r}')
    status=status_map[period]
    home=m.get('home',{}).get('clubIdentity',{}).get('shortName','')
    away=m.get('away',{}).get('clubIdentity',{}).get('shortName','')
    if not home or not away or home==away:raise RuntimeError(f'Official fixture lacks valid clubs: {full_id}')
    if status=='finished':
        hg,ag=m.get('home',{}).get('score'),m.get('away',{}).get('score')
        if hg is None or ag is None or int(hg)<0 or int(ag)<0:raise RuntimeError(f'FullTime match has no valid score: {full_id}')
        hg,ag=str(int(hg)),str(int(ag))
    else:hg=ag=''
    raw_date=m.get('date')
    date_local=time_local=''
    if raw_date and not (m.get('dateTimeUnknown') and status!='finished'):
        dt=datetime.fromisoformat(raw_date.replace('Z','+00:00')).astimezone(PARIS)
        date_local=dt.strftime('%Y-%m-%d')
        if not m.get('dateTimeUnknown'):time_local=dt.strftime('%H:%M')
    return {'round':rnd,'home':home,'home_goals':hg,'away_goals':ag,'away':away,'status':status,
            'official_id':short_id,'official_url':LFP_MATCH.format(full_id),'date_local':date_local,
            'time_local':time_local,'schedule_note':'','official_time_display':time_local,
            '_source_url':url}

calendar_payload,fixture_ids=parse_rounds()
with ThreadPoolExecutor(max_workers=8) as pool:
    futures=[pool.submit(fetch_match,item) for item in fixture_ids]
    csv_rows=[f.result() for f in as_completed(futures)]
csv_rows.sort(key=lambda r:(int(r['round']),r['date_local'] or '9999-99-99',r['time_local'],int(r['official_id'])))
clubs=sorted({r['home'] for r in csv_rows}|{r['away'] for r in csv_rows})
if len(clubs)!=18:raise RuntimeError(f'Expected 18 LFP clubs, found {len(clubs)}: {clubs}')
if len({(r['round'],r['home'],r['away']) for r in csv_rows})!=306:raise RuntimeError('Duplicate or missing official round/home/away fixture key')
for rnd in range(1,35):
    current=[r for r in csv_rows if int(r['round'])==rnd]
    if len(current)!=9 or Counter([r['home'] for r in current]+[r['away'] for r in current])!=Counter(clubs):
        raise RuntimeError(f'Official LFP round {rnd} does not contain each of the 18 clubs exactly once')
for team in clubs:
    if sum(r['home']==team or r['away']==team for r in csv_rows)!=34:
        raise RuntimeError(f'Official LFP schedule does not give {team} 34 fixtures')
home_away_anomalies=[{'team':team,'home_fixtures':sum(r['home']==team for r in csv_rows),'away_fixtures':sum(r['away']==team for r in csv_rows)} for team in clubs if sum(r['home']==team for r in csv_rows)!=17 or sum(r['away']==team for r in csv_rows)!=17]
known_lfp_venue_anomaly=[{'team':'PSG','home_fixtures':16,'away_fixtures':18},{'team':'Rennes','home_fixtures':18,'away_fixtures':16}]
if home_away_anomalies not in ([],known_lfp_venue_anomaly):
    raise RuntimeError(f'Unexpected home/away fixture imbalance; halt for manual review: {home_away_anomalies}')
home_away_note=('Current LFP match-sheet API lists both PSG–Rennes fixtures at Roazhon Park: the R1 sheet and ESPN confirm Rennes 2–2 PSG, while the LFP season-calendar PDF lists PSG as R1 home. The R23 LFP sheet also lists Rennes home. Keep current match-sheet orientation; review if the LFP changes it.' if home_away_anomalies else 'All clubs have 17 home and 17 away fixtures in the current official calendar.')
counts={s:sum(r['status']==s for r in csv_rows) for s in sorted({r['status'] for r in csv_rows})}
finished=[r for r in csv_rows if r['status']=='finished']
if not finished:raise RuntimeError('LFP calendar returned no confirmed final scores')

# Current official standings snapshot; final-only stats must match exactly before any artifacts are written.
table_payload=get_json(LFP_TABLE)
standings=table_payload.get('standings') or {}
lfp_rows=[]
for rank,rec in sorted(standings.items(),key=lambda kv:int(kv[0])):
    ci=rec['clubIdentity'];team=ci['shortName']
    lfp_rows.append({'position':int(rec.get('rank',rank)),'team':team,'played':int(rec['played']),'won':int(rec['wins']),'drawn':int(rec['draws']),'lost':int(rec['losses']),'goals_for':int(rec['forGoals']),'goals_against':int(rec['againstGoals']),'goal_difference':int(rec['goalsDifference']),'points':int(rec['points'])})
if len(lfp_rows)!=18 or {x['team'] for x in lfp_rows}!=set(clubs):raise RuntimeError('LFP table club set does not match the official fixture calendar')
stats={t:{'played':0,'won':0,'drawn':0,'lost':0,'goals_for':0,'goals_against':0,'points':0} for t in clubs}
for match in finished:
    hg,ag=int(match['home_goals']),int(match['away_goals'])
    for team,gf,ga in ((match['home'],hg,ag),(match['away'],ag,hg)):
        s=stats[team];s['played']+=1;s['goals_for']+=gf;s['goals_against']+=ga
        if gf>ga:s['won']+=1;s['points']+=3
        elif gf==ga:s['drawn']+=1;s['points']+=1
        else:s['lost']+=1
for s in stats.values():s['goal_difference']=s['goals_for']-s['goals_against']
lfp_by={r['team']:r for r in lfp_rows};fields=['played','won','drawn','lost','goals_for','goals_against','goal_difference','points']
for team in clubs:
    diffs={field:(stats[team][field],lfp_by[team][field]) for field in fields if stats[team][field]!=lfp_by[team][field]}
    if diffs:raise RuntimeError(f'Final-only results do not reconcile with current LFP table for {team}: {diffs}. No files will be written.')

# Independent ESPN score check for every final; ESPN-derived table must independently agree too.
alias={'paris saint germain':'PSG','psg':'PSG','lille':'LOSC','losc':'LOSC','monaco':'AS Monaco','as monaco':'AS Monaco',
 'rennes':'Rennes','stade rennais':'Rennes','lyon':'OL','olympique lyonnais':'OL','paris fc':'Paris FC',
 'lens':'RC Lens','rc lens':'RC Lens','brest':'Brest','toulouse':'Toulouse FC','toulouse fc':'Toulouse FC',
 'lorient':'FC Lorient','fc lorient':'FC Lorient','nice':'OGC Nice','strasbourg':'Strasbourg','angers':'Angers SCO','marseille':'OM','om':'OM',
 'le mans':'LE Mans FC','le mans fc':'LE Mans FC','auxerre':'AJ Auxerre','aj auxerre':'AJ Auxerre','troyes':'Troyes','le havre ac':'Havre AC','havre ac':'Havre AC'}
if set(alias.values())!=set(clubs):raise RuntimeError(f'ESPN alias map does not cover official LFP roster: {set(clubs)^set(alias.values())}')
dates=set()
for match in finished:
    if not match['date_local']:raise RuntimeError(f'Finished fixture has no official local date: {match["official_id"]}')
    day=datetime.strptime(match['date_local'],'%Y-%m-%d').date()
    for delta in (-1,0,1):dates.add((day+timedelta(days=delta)).strftime('%Y%m%d'))
def fetch_espn(day):
    response=requests.get(ESPN,params={'dates':day},headers={'User-Agent':'Mozilla/5.0 DINMercadoLigue1Refresh/1.0'},timeout=40)
    response.raise_for_status();return day,response.json()
events={};queried=[]
with ThreadPoolExecutor(max_workers=8) as pool:
    futures=[pool.submit(fetch_espn,day) for day in sorted(dates)]
    for future in as_completed(futures):
        day,payload=future.result();queried.append(day)
        for event in payload.get('events',[]):
            comp=event.get('competitions',[{}])[0];teams_by_side={x.get('homeAway'):x for x in comp.get('competitors',[])}
            home,away=teams_by_side.get('home',{}),teams_by_side.get('away',{})
            home_name=alias.get(norm(home.get('team',{}).get('displayName','')));away_name=alias.get(norm(away.get('team',{}).get('displayName','')))
            if home_name not in clubs or away_name not in clubs:continue
            key=(home_name,away_name)
            record={'espn_event_id':event.get('id',''),'espn_status':comp.get('status',{}).get('type',{}).get('name',''),
                    'home_goals':str(home.get('score','')),'away_goals':str(away.get('score','')),
                    'espn_source_url':f'{ESPN}?dates={day}'}
            if key not in events or (record['espn_status']=='STATUS_FULL_TIME' and events[key]['espn_status']!='STATUS_FULL_TIME'):events[key]=record
cross=[]
for match in finished:
    event=events.get((match['home'],match['away']))
    if not event:raise RuntimeError(f'ESPN missing official final {match["home"]}–{match["away"]} ({match["date_local"]}); no files will be written')
    same=event['espn_status']=='STATUS_FULL_TIME' and event['home_goals']==str(match['home_goals']) and event['away_goals']==str(match['away_goals'])
    row={'official_id':match['official_id'],'round':match['round'],'home':match['home'],'official_home_goals':match['home_goals'],'espn_home_goals':event['home_goals'],
         'away':match['away'],'official_away_goals':match['away_goals'],'espn_away_goals':event['away_goals'],'espn_status':event['espn_status'],
         'result_match':str(same),'espn_event_id':event['espn_event_id'],'espn_source_url':event['espn_source_url']}
    if not same:raise RuntimeError(f'Official/ESPN score mismatch; no files will be written: {row}')
    cross.append(row)
espn_stats={t:{'played':0,'won':0,'drawn':0,'lost':0,'goals_for':0,'goals_against':0,'goal_difference':0,'points':0} for t in clubs}
for row in cross:
    hg,ag=int(row['espn_home_goals']),int(row['espn_away_goals'])
    for team,gf,ga in ((row['home'],hg,ag),(row['away'],ag,hg)):
        s=espn_stats[team];s['played']+=1;s['goals_for']+=gf;s['goals_against']+=ga
        if gf>ga:s['won']+=1;s['points']+=3
        elif gf==ga:s['drawn']+=1;s['points']+=1
        else:s['lost']+=1
for s in espn_stats.values():s['goal_difference']=s['goals_for']-s['goals_against']
for team in clubs:
    diffs={field:(stats[team][field],espn_stats[team][field]) for field in fields if stats[team][field]!=espn_stats[team][field]}
    if diffs:raise RuntimeError(f'Official-final table differs from independent ESPN-derived table for {team}: {diffs}. No files will be written.')

# All checks passed: atomically write the complete season, source snapshots and report.
SNAP=ROOT/'source_snapshots';SNAP.mkdir(exist_ok=True)
(SNAP/'calendar_latest.json').write_text(json.dumps({'url':LFP_CALENDAR,'retrieved_at_brt':CUT,'payload':calendar_payload},ensure_ascii=False,indent=2),encoding='utf-8')
(SNAP/'official_standings_latest.json').write_text(json.dumps({'url':LFP_TABLE,'retrieved_at_brt':CUT,'payload':table_payload},ensure_ascii=False,indent=2),encoding='utf-8')
with (SNAP/'official_standings_latest.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(lfp_rows[0]));writer.writeheader();writer.writerows(lfp_rows)
with (SNAP/'espn_results_crosscheck_latest.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(cross[0]));writer.writeheader();writer.writerows(cross)
espn_table=sorted([{'team':t,**s} for t,s in espn_stats.items()],key=lambda r:(-r['points'],-r['goal_difference'],-r['goals_for'],r['team']))
with (SNAP/'espn_table_recomputed_latest.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(espn_table[0]));writer.writeheader();writer.writerows(espn_table)
fields_csv=list(csv_rows[0])
with (ROOT/'ligue1_2026_27_matches.csv').open('w',encoding='utf-8',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=fields_csv);writer.writeheader();writer.writerows(csv_rows)
report={'competition':'Ligue 1 McDonald’s 2026/27','cutoff':CUT,'official_calendar_source':LFP_CALENDAR,'official_table_source':LFP_TABLE,
 'official_fixture_slots':len(csv_rows),'rounds_present':34,'clubs':len(clubs),'status_counts':counts,'home_away_schedule_anomalies':home_away_anomalies,'home_away_schedule_note':home_away_note,
 'finished_results':len(finished),'nonfinal_fixtures':len(csv_rows)-len(finished),'live_or_unconfirmed_scores_used':0,
 'official_table_reconciliation':{'clubs_compared':18,'all_stats_match':True,'mismatches':0},
 'independent_ESPN_score_check':{'finished_scores_checked':len(cross),'exact_STATUS_FULL_TIME_matches':len(cross),'mismatches':0,'queried_utc_dates':len(queried)},
 'independent_ESPN_table_reconciliation':{'clubs_compared':18,'all_stats_match':True,'mismatches':0},
 'overview':{'goals':sum(int(r['home_goals'])+int(r['away_goals']) for r in finished),'btts':sum(int(r['home_goals'])>0 and int(r['away_goals'])>0 for r in finished),'over_2_5':sum(int(r['home_goals'])+int(r['away_goals'])>=3 for r in finished)},
 'source_files':['ligue1_2026_27_matches.csv','source_snapshots/official_standings_latest.csv','source_snapshots/espn_results_crosscheck_latest.csv','source_snapshots/espn_table_recomputed_latest.csv']}
(ROOT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
source_info={'cutoff':CUT,'primary':[{'name':'Official LFP fixture calendar','url':LFP_CALENDAR,'coverage':f'34 matchdays, {len(csv_rows)} official fixture IDs.'},{'name':'Official LFP match-sheet API','url':'https://ma-api.ligue1.fr/championship-match/{l1_championship_match_id}','coverage':f'{len(finished)} FullTime scores, {len(csv_rows)-len(finished)} nonfinal fixtures.'},{'name':'Official LFP general standings','url':LFP_TABLE,'coverage':'18-club current table, reconciled against final-only scores.'}],'independent':[{'name':'ESPN scoreboard API','url':ESPN,'coverage':f'{len(cross)}/{len(finished)} exact STATUS_FULL_TIME result checks; independent table recomputed from ESPN scores.'}]}
(ROOT/'sources.json').write_text(json.dumps(source_info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'cutoff':CUT,'fixtures':len(csv_rows),'clubs':len(clubs),'status_counts':counts,'finals':len(finished),'LFP_table':'18/18 PASS','ESPN_scores':f'{len(cross)}/{len(finished)} PASS','ESPN_table':'18/18 PASS'},ensure_ascii=False,indent=2))
