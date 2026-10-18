import re, glob, os, json, csv
from collections import defaultdict
BASE='ligue1_2026_27_dashboard'
# Captured official LFP fixtures/results; only read the Ligue 1 pages gathered for this dashboard.
scored_re=re.compile(r'\[\((\d+)\)\\\\\s*\\\\\s*(.*?)\\\\\s*\\\\\s*!\[\]\(.*?\)\\\\\s*\\\\\s*(\d+)\s*-\s*(\d+)\\\\\s*\\\\\s*(.*?)\\\\\s*\\\\\s*!\[\]\(.*?\)\]\(https://ligue1\.com/fr/match-sheet/l1_championship_match_(\d+)\)',re.S)
card_re=re.compile(r'\[\((\d+)\)(.*?)\]\(https://ligue1\.com/fr/match-sheet/l1_championship_match_(\d+)\)',re.S)
paths={1:'web_fetches/2026-10-18T13-55-16_ligue1com_27eb0487.md',2:'web_fetches/2026-10-18T13-55-16_ligue1com_1f4a2380.md',3:'web_fetches/2026-10-18T13-55-17_ligue1com_dbf7ca92.md',4:'web_fetches/2026-10-18T13-55-16_ligue1com_45a14123.md',5:'web_fetches/2026-10-18T13-55-17_ligue1com_5d570841.md',6:'web_fetches/2026-10-18T13-55-17_ligue1com_070f42d4.md',7:'web_fetches/2026-10-18T13-54-25_ligue1com_b611b9f6.md',8:'web_fetches/2026-10-18T13-55-17_ligue1com_3165d662.md'}
rows=[]
for md,path in paths.items():
    text=open(path,encoding='utf-8').read()
    assert f'Journée {md}' in text, (md,path)
    if md<=6:
        matches=list(scored_re.finditer(text))
        assert len(matches)==9, (md,len(matches))
        for m in matches:
            home=m.group(2).strip()
            away=re.split(r'\\\\\s*\\\\\s*\(\d+\)',m.group(5))[0].strip()
            rows.append({'round':md,'home':home,'home_goals':int(m.group(3)),'away_goals':int(m.group(4)),'away':away,'status':'finished','official_id':m.group(6),'official_url':f'https://ligue1.com/fr/match-sheet/l1_championship_match_{m.group(6)}','date_local':None,'time_local':None,'schedule_note':None})
    else:
        cards=list(card_re.finditer(text))
        assert len(cards)==9,(md,len(cards))
        for card in cards:
            block=re.sub(r'!\[\]\([^)]*\)','',card.group(2)).replace('\\\\','\n')
            lines=[re.sub(r'\\+$','',x.strip()).strip() for x in block.splitlines()]
            lines=[x for x in lines if x and not re.fullmatch(r'\(\d+\)',x)]
            # Fixture card's first and third textual tokens are the team names; score/time sits between.
            home=lines[0]
            score=next((re.fullmatch(r'(\d+)\s*-\s*(\d+)',x) for x in lines if re.fullmatch(r'(\d+)\s*-\s*(\d+)',x)),None)
            if score:
                si=next(i for i,x in enumerate(lines) if re.fullmatch(r'\d+\s*-\s*\d+',x))
                away=lines[si+1]
                status='finished'; hg=int(score.group(1)); ag=int(score.group(2))
            else:
                timei=next(i for i,x in enumerate(lines) if re.fullmatch(r'\d{1,2}H\d{0,2}',x))
                away=lines[timei+1]; status='scheduled'; hg=ag=None
            official_display_time=next((x for x in lines if re.fullmatch(r'\d{1,2}H\d{0,2}',x)),None)
            if md==7:
                date_local='2026-10-18'
                note='LFP matchday-7 calendar labels the five remaining fixtures “today”; independent schedule agrees on 18 Oct. Kickoff differs by one hour; omitted.' if status=='scheduled' else None
            else:
                date_local=None
                note='LFP and independent schedule list this match on adjacent calendar dates (official calendar display timezone unclear); date/time withheld, pending reconciliation.'
            rows.append({'round':md,'home':home,'home_goals':hg,'away_goals':ag,'away':away,'status':status,'official_id':card.group(3),'official_url':f'https://ligue1.com/fr/match-sheet/l1_championship_match_{card.group(3)}','date_local':date_local,'time_local':None,'official_time_display':official_display_time,'schedule_note':note})
# Only publish completed matches through cutoff, plus the next scheduled matchday and the next round's verified opponents.
assert len(rows)==72, len(rows)
assert sum(r['status']=='finished' for r in rows)==58, sum(r['status']=='finished' for r in rows)
assert len({r['official_id'] for r in rows})==72
# Official roster independently derived from the 18-club schedule (each has nine R1 fixtures).
teams=sorted(set([r['home'] for r in rows]+[r['away'] for r in rows]))
assert len(teams)==18,(len(teams),teams)
# Validate complete single round-robin fixture counts for rounds 1-8 as listed by LFP.
for md in range(1,9): assert sum(r['round']==md for r in rows)==9, md
# Compute standings from confirmed final scores only.
st={t:{'team':t,'played':0,'w':0,'d':0,'l':0,'gf':0,'ga':0,'pts':0,'home_played':0,'away_played':0,'home_w':0,'home_d':0,'home_l':0,'home_gf':0,'home_ga':0,'away_w':0,'away_d':0,'away_l':0,'away_gf':0,'away_ga':0} for t in teams}
for m in rows:
 if m['status']!='finished': continue
 h,a=m['home'],m['away']; hg,ag=m['home_goals'],m['away_goals']
 for t in (h,a):st[t]['played']+=1
 st[h]['gf']+=hg; st[h]['ga']+=ag; st[a]['gf']+=ag; st[a]['ga']+=hg
 st[h]['home_played']+=1; st[a]['away_played']+=1
 st[h]['home_gf']+=hg;st[h]['home_ga']+=ag;st[a]['away_gf']+=ag;st[a]['away_ga']+=hg
 if hg>ag:
  st[h]['w']+=1;st[a]['l']+=1;st[h]['pts']+=3;st[h]['home_w']+=1;st[a]['away_l']+=1
 elif hg<ag:
  st[a]['w']+=1;st[h]['l']+=1;st[a]['pts']+=3;st[a]['away_w']+=1;st[h]['home_l']+=1
 else:
  st[h]['d']+=1;st[a]['d']+=1;st[h]['pts']+=1;st[a]['pts']+=1;st[h]['home_d']+=1;st[a]['away_d']+=1
for s in st.values():
 s['gd']=s['gf']-s['ga'];s['home_pts']=3*s['home_w']+s['home_d'];s['away_pts']=3*s['away_w']+s['away_d']
# Stats are computed from confirmed scores. Preserve the official LFP's displayed order only for otherwise identical numerical ties.
official_order=['PSG','LOSC','AS Monaco','Rennes','OL','Paris FC','RC Lens','Brest','Toulouse FC','FC Lorient','OGC Nice','Strasbourg','Angers SCO','OM','LE Mans FC','AJ Auxerre','Troyes','Havre AC']
order_index={t:i for i,t in enumerate(official_order)}
standings=sorted(st.values(),key=lambda s:(-s['pts'],-s['gd'],-s['gf'],order_index.get(s['team'],999)))
for i,s in enumerate(standings,1):s['rank']=i
json.dump({'cutoff':'2026-10-18T10:54:00-03:00','season':'2026/27','league':'Ligue 1 McDonald\'s','teams':teams,'standings':standings,'matches':rows},open(os.path.join(BASE,'data.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=2)
with open(os.path.join(BASE,'ligue1_2026_27_matches.csv'),'w',encoding='utf-8',newline='') as f:
 fields=list(dict.fromkeys(k for r in rows for k in r.keys()))
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print('Finished:',sum(r['status']=='finished' for r in rows),'Scheduled:',sum(r['status']=='scheduled' for r in rows),'Teams:',len(teams))
for s in standings:print(s['rank'],s['team'],s['played'],s['w'],s['d'],s['l'],s['gf'],s['ga'],s['pts'])
print('results IDs',len(set(r['official_id'] for r in rows)))
