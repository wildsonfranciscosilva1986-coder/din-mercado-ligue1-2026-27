import json, re, os
from collections import defaultdict
BASE=os.path.dirname(__file__)
D=json.load(open(os.path.join(BASE,'data.json'),encoding='utf-8'))
M=D['matches']; finished=[m for m in M if m['status']=='finished']; scheduled=[m for m in M if m['status']=='scheduled']
assert D['cutoff']=='2026-10-18T14:12:13-03:00'
assert len(D['teams'])==18 and len(M)==72 and len(finished)==59 and len(scheduled)==13
assert len({m['official_id'] for m in M})==72 and all(sum(m['round']==r for m in M)==9 for r in range(1,9))
assert all(sum(m['status']=='finished' and m['round']==r for m in M)==9 for r in range(1,7))
assert sum(m['status']=='finished' and m['round']==7 for m in M)==5
assert sum(m['status']=='scheduled' and m['round']==7 for m in M)==4 and sum(m['status']=='scheduled' and m['round']==8 for m in M)==9
assert all((m['home_goals'] is not None and m['away_goals'] is not None) if m['status']=='finished' else (m['home_goals'] is None and m['away_goals'] is None) for m in M)
latest=next(m for m in M if m['official_id']=='73875')
assert (latest['round'],latest['home'],latest['home_goals'],latest['away_goals'],latest['away'],latest['status'])==(7,'Angers SCO',2,5,'OM','finished')
# Invariants over independently recomputed standings.
for s in D['standings']:
    assert s['played']==s['w']+s['d']+s['l'] and s['pts']==3*s['w']+s['d'] and s['gd']==s['gf']-s['ga']
assert sum(s['played'] for s in D['standings'])==2*len(finished)
assert sum(s['pts'] for s in D['standings'])==3*sum(m['home_goals']!=m['away_goals'] for m in finished)+2*sum(m['home_goals']==m['away_goals'] for m in finished)
# LFP standings page returned the table one result behind the latest confirmed match. Validate that full published table against the exact prior set.
lfp=[('PSG',14,7,4,2,1,14,9),('LOSC',14,7,4,2,1,10,5),('AS Monaco',14,6,4,2,0,10,5),('Rennes',13,6,4,1,1,12,10),('OL',11,6,3,2,1,11,4),('Paris FC',11,6,3,2,1,8,4),('RC Lens',10,7,3,1,3,14,11),('Brest',9,7,2,3,2,13,10),('Toulouse FC',9,7,2,3,2,12,11),('FC Lorient',8,6,2,2,2,6,6),('OGC Nice',8,6,2,2,2,5,7),('Strasbourg',7,7,2,1,4,12,15),('Angers SCO',7,6,2,1,3,7,10),('OM',6,6,2,0,4,9,8),('LE Mans FC',6,7,1,3,3,10,15),('AJ Auxerre',6,6,2,0,4,8,16),('Troyes',4,7,1,1,5,5,16),('Havre AC',2,6,0,2,4,4,8)]
def table(rows):
 c=defaultdict(lambda:{'played':0,'w':0,'d':0,'l':0,'gf':0,'ga':0,'pts':0})
 for m in rows:
  if m['status']!='finished': continue
  h,a,hg,ag=m['home'],m['away'],m['home_goals'],m['away_goals']
  c[h]['played']+=1;c[a]['played']+=1;c[h]['gf']+=hg;c[h]['ga']+=ag;c[a]['gf']+=ag;c[a]['ga']+=hg
  if hg>ag:c[h]['w']+=1;c[h]['pts']+=3;c[a]['l']+=1
  elif hg<ag:c[a]['w']+=1;c[a]['pts']+=3;c[h]['l']+=1
  else:c[h]['d']+=1;c[a]['d']+=1;c[h]['pts']+=1;c[a]['pts']+=1
 return c
pre=table([m for m in M if m['official_id']!='73875'])
for name,pts,mp,w,d,l,gf,ga in lfp:
 c=pre[name]; assert (c['pts'],c['played'],c['w'],c['d'],c['l'],c['gf'],c['ga'])==(pts,mp,w,d,l,gf,ga),(name,c)
current=table(M)
for name,*_ in lfp:
 s=next(x for x in D['standings'] if x['team']==name); c=current[name]
 assert (s['played'],s['w'],s['d'],s['l'],s['gf'],s['ga'],s['pts'])==(c['played'],c['w'],c['d'],c['l'],c['gf'],c['ga'],c['pts'])
# 16 unaffected records still match the LFP table; affected clubs update directly from the official sheet.
for name,pts,mp,w,d,l,gf,ga in lfp:
 if name in ('Angers SCO','OM'): continue
 c=current[name]; assert (c['pts'],c['played'],c['w'],c['d'],c['l'],c['gf'],c['ga'])==(pts,mp,w,d,l,gf,ga)
assert (current['Angers SCO']['pts'],current['Angers SCO']['played'],current['Angers SCO']['w'],current['Angers SCO']['d'],current['Angers SCO']['l'],current['Angers SCO']['gf'],current['Angers SCO']['ga'])==(7,7,2,1,4,9,15)
assert (current['OM']['pts'],current['OM']['played'],current['OM']['w'],current['OM']['d'],current['OM']['l'],current['OM']['gf'],current['OM']['ga'])==(9,7,3,0,4,14,10)
# Cross-check all 18 teams through round 6 against dated independent WorldFootball capture.
source=os.path.join(BASE,'source_snapshots/worldfootball_round6_2026-10-18.md')
text=open(source,encoding='utf-8').read(); alias={'Marseille':'OM','Paris SG':'PSG','Lyonnais':'OL','Lille':'LOSC','Stade Brest':'Brest','Toulouse':'Toulouse FC','Lorient':'FC Lorient','Nice':'OGC Nice','HAC':'Havre AC','Angers':'Angers SCO','Auxerre':'AJ Auxerre','ES Troyes AC':'Troyes','Le Mans':'LE Mans FC','Stade Rennais':'Rennes'}
ind=[]
for line in text.splitlines():
 if not re.match(r'^\|\s*\d+\s*\|',line):continue
 m=re.search(r'\|\s*(\d+)\s*\|.*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+):(\d+)\s*\|\s*(-?\d+)\s*\|\s*(\d+)\s*\|',line)
 if not m:continue
 names=re.findall(r'\[([^\]]+)\]\(https://www\.worldfootball\.net/teams/',line)
 if not names:continue
 name=alias.get(names[-1],names[-1]);ind.append((name,int(m.group(2)),int(m.group(3)),int(m.group(4)),int(m.group(5)),int(m.group(6)),int(m.group(7)),int(m.group(9))))
 if len(ind)==18:break
assert len(ind)==18,len(ind)
indcalc=table([m for m in M if m['round']<=6])
for name,mp,w,d,l,gf,ga,pts in ind:
 c=indcalc[name];assert (c['played'],c['w'],c['d'],c['l'],c['gf'],c['ga'],c['pts'])==(mp,w,d,l,gf,ga,pts),(name,c)
# Latest five J7 scores are checked against the registered independent result links/snapshots.
independent_r7={('Strasbourg','PSG'):(1,3),('LOSC','Brest'):(1,1),('Troyes','RC Lens'):(1,3),('LE Mans FC','Toulouse FC'):(0,3),('Angers SCO','OM'):(2,5)}
for pairing,score in independent_r7.items():
 row=next(m for m in finished if m['round']==7 and (m['home'],m['away'])==pairing);assert (row['home_goals'],row['away_goals'])==score
# Aggregate KPIs are independently recomputed with explicit final-match denominator.
total_goals=sum(m['home_goals']+m['away_goals'] for m in finished)
btts=sum(m['home_goals']>0 and m['away_goals']>0 for m in finished)
over25=sum(m['home_goals']+m['away_goals']>=3 for m in finished)
home_wins=sum(m['home_goals']>m['away_goals'] for m in finished);draws=sum(m['home_goals']==m['away_goals'] for m in finished);away_wins=sum(m['home_goals']<m['away_goals'] for m in finished)
assert (total_goals,btts,over25,home_wins,draws,away_wins)==(177,37,37,25,15,19)
assert home_wins+draws+away_wins==len(finished)
result={'cutoff':D['cutoff'],'teams':18,'official_fixtures_rounds_1_to_8':72,'completed_results':59,'scheduled_without_final':13,'matches_per_round':9,'all_ids_unique':True,'all_final_scores_parseable':True,'standings_recomputed_from_scores':True,'overview_metrics':{'goals':total_goals,'average_goals_per_final':round(total_goals/len(finished),2),'btts':[btts,len(finished)],'over_2_5':[over25,len(finished)],'home_wins_draws_away_wins':[home_wins,draws,away_wins]},'lfp_current_table_match':'LFP standings fetch at 14:11 BRT still reflects the 58-final table; all 18 exact against the pre-Angers 2-5 OM result snapshot, 16/18 unaffected clubs match the updated table, Angers SCO and OM updated from official LFP match sheet 73875.','independent_table_match':'18/18 club records match WorldFootball after round 6; five round-7 scores independently corroborated, including Angers SCO 2-5 OM (GFFN FT, OneFootball).','schedule_caveat':'Official and independent date/time labels conflict for some future fixtures; only shared round/opponents and 18 Oct where confirmed are shown.','rules_caveat':'LFP 2026/27 Europe allocation documented; not extrapolated as 2027/28 access. UEFA page showed no data. Specific LFP 2026/27 relegation regulation not located; relegation zone display is provisional.','pending_note':'Other J7 match pages at cutoff showed live status/in-progress minute or no independently confirmed final; not included.'}
json.dump(result,open(os.path.join(BASE,'validation.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=False,indent=2))
