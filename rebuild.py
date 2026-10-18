"""Recreate the JSON snapshot and standalone HTML using only this repo's verified CSV."""
import csv, json, os
from collections import defaultdict
BASE=os.path.dirname(__file__)
rows=[]
with open(os.path.join(BASE,'ligue1_2026_27_matches.csv'),encoding='utf-8') as f:
    for r in csv.DictReader(f):
        r['round']=int(r['round'])
        for k in ('home_goals','away_goals'):
            r[k]=int(r[k]) if r[k] else None
        rows.append(r)
teams=sorted(set([m['home'] for m in rows]+[m['away'] for m in rows]))
st={t:{'team':t,'played':0,'w':0,'d':0,'l':0,'gf':0,'ga':0,'pts':0,'home_played':0,'away_played':0,'home_w':0,'home_d':0,'home_l':0,'home_gf':0,'home_ga':0,'away_w':0,'away_d':0,'away_l':0,'away_gf':0,'away_ga':0} for t in teams}
for m in rows:
    if m['status']!='finished':continue
    h,a=m['home'],m['away'];hg,ag=m['home_goals'],m['away_goals']
    for t in (h,a):st[t]['played']+=1
    st[h]['gf']+=hg;st[h]['ga']+=ag;st[a]['gf']+=ag;st[a]['ga']+=hg
    st[h]['home_played']+=1;st[a]['away_played']+=1;st[h]['home_gf']+=hg;st[h]['home_ga']+=ag;st[a]['away_gf']+=ag;st[a]['away_ga']+=hg
    if hg>ag:st[h]['w']+=1;st[a]['l']+=1;st[h]['pts']+=3;st[h]['home_w']+=1;st[a]['away_l']+=1
    elif hg<ag:st[a]['w']+=1;st[h]['l']+=1;st[a]['pts']+=3;st[a]['away_w']+=1;st[h]['home_l']+=1
    else:st[h]['d']+=1;st[a]['d']+=1;st[h]['pts']+=1;st[a]['pts']+=1;st[h]['home_d']+=1;st[a]['away_d']+=1
for s in st.values():s['gd']=s['gf']-s['ga'];s['home_pts']=3*s['home_w']+s['home_d'];s['away_pts']=3*s['away_w']+s['away_d']
order=['PSG','LOSC','AS Monaco','Rennes','OL','Paris FC','RC Lens','Brest','Toulouse FC','FC Lorient','OGC Nice','Strasbourg','Angers SCO','OM','LE Mans FC','AJ Auxerre','Troyes','Havre AC']
idx={t:i for i,t in enumerate(order)}
standings=sorted(st.values(),key=lambda s:(-s['pts'],-s['gd'],-s['gf'],idx.get(s['team'],999)))
for i,s in enumerate(standings,1):s['rank']=i
snapshot={'cutoff':'2026-10-18T10:54:00-03:00','season':'2026/27','league':"Ligue 1 McDonald's",'teams':teams,'standings':standings,'matches':rows}
with open(os.path.join(BASE,'data.json'),'w',encoding='utf-8') as f:json.dump(snapshot,f,ensure_ascii=False,indent=2)
os.system(f'python3 "{os.path.join(BASE,"build_site.py")}"')
print(f"Built {len(teams)} clubs, {sum(m['status']=='finished' for m in rows)} results, {sum(m['status']=='scheduled' for m in rows)} scheduled fixtures.")
