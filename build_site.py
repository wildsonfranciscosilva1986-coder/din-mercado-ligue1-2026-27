#!/usr/bin/env python3
"""Build the interactive Ligue 1 site with current dynamic coverage metadata."""
import json
from datetime import datetime
from pathlib import Path
base=Path(__file__).resolve().parent
data=json.loads((base/'data.json').read_text(encoding='utf-8'))
template=(base/'index.template.html').read_text(encoding='utf-8')
inline=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</script>','<\\/script>')
finished=sum(m.get('status')=='finished' and m.get('home_goals') is not None and m.get('away_goals') is not None for m in data['matches'])
rounds=len({int(m['round']) for m in data['matches']})
cutoff=datetime.fromisoformat(data['cutoff']).strftime('%d/%m/%Y às %H:%M BRT')
for marker,value in {'__ROUND_COUNT__':str(rounds),'__FINISHED_COUNT__':str(finished),'__NONFINAL_COUNT__':str(len(data['matches'])-finished),'__CUTOFF__':cutoff,'__HOME_AWAY_NOTE__':data.get('homeAwayNote','')}.items():
    template=template.replace(marker,value)
page=template.replace('__DATA__',inline)
if '__' in page and any(token in page for token in ('__DATA__','__ROUND_COUNT__','__FINISHED_COUNT__','__NONFINAL_COUNT__','__CUTOFF__','__HOME_AWAY_NOTE__')):
    raise SystemExit('A dynamic dashboard placeholder was not replaced.')
(base/'index.html').write_text(page,encoding='utf-8')
print('index.html built; bytes=',(base/'index.html').stat().st_size,'fixtures=',len(data['matches']),'finals=',finished,'cutoff=',data['cutoff'])
