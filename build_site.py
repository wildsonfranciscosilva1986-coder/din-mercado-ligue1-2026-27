import json, os
base=os.path.dirname(__file__)
data=json.load(open(os.path.join(base,'data.json'),encoding='utf-8'))
template=open(os.path.join(base,'index.template.html'),encoding='utf-8').read()
inline=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</script>','<\\/script>')
open(os.path.join(base,'index.html'),'w',encoding='utf-8').write(template.replace('__DATA__',inline))
print('index.html built; bytes=',os.path.getsize(os.path.join(base,'index.html')))
