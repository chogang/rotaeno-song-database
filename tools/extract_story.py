"""Read Naninovel managed-reference scripts without executing game code."""
import os,sys,pathlib,struct,re,json,hashlib,collections
root=pathlib.Path(os.environ['ROTAENO_WORKDIR'])
sys.path.insert(0,str(root/'tools/python-libs'))
import UnityPy
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
env=UnityPy.load(str(root/'extracted/datapack.unity3d'))
def string(b,p):
 n=struct.unpack_from('<i',b,p)[0]
 assert 0<=n<=len(b)-p-4
 return b[p+4:p+4+n].decode('utf8'),(p+4+n+3)&~3
def integer(b,p):return struct.unpack_from('<i',b,p)[0]
def long(b,p):return struct.unpack_from('<q',b,p)[0]
def records(b,start,count):
 rows=[]
 for m in re.finditer(rb'[\x01-\x7f]\x00\x00\x00[A-Za-z_][A-Za-z0-9_`+<>.]*',b[start:]):
  p=start+m.start()
  if p%4:continue
  try:
   name,q=string(b,p);ns,q=string(b,q);asm,q=string(b,q)
   if asm not in ['Elringus.Naninovel.Runtime','GW.NaninovelExtensions','Assembly-CSharp']:continue
   if not re.fullmatch(r'[A-Za-z0-9_.]+',ns):continue
   rid=long(b,p-8)
   if not 1000<=rid<10000000:continue
   rows.append(dict(rid=rid,type=name,start=p-8,payload=q))
  except (AssertionError,UnicodeError,struct.error):pass
 null_record=struct.pack('<qiii',-2,0,0,0)
 null_count=b[start:].count(null_record)
 assert len(rows)+null_count==count,(len(rows),null_count,count)
 assert len({r['rid'] for r in rows})==len(rows)
 for i,r in enumerate(rows):r['end']=rows[i+1]['start'] if i+1<len(rows) else len(b)
 return rows
docs=[];types=collections.Counter();samples={};unknown=[]
for o in env.objects:
 if o.type.name!='MonoBehaviour' or o.assets_file.name!='resources.assets':continue
 b=o.get_raw_data()
 if struct.unpack_from('<iq',b,16)!=(1,2017):continue
 name,p=string(b,28);n=integer(b,p);p+=4
 roots=[long(b,p+i*8) for i in range(n)];p+=n*8
 assert integer(b,p)==2;p+=4
 count=integer(b,p);p+=4
 try:rows=records(b,p,count)
 except AssertionError as e:raise AssertionError((name,o.path_id,str(e)))
 byid={r['rid']:r for r in rows};lines=[];header='';label=''
 for rid in roots:
  if rid<0:continue
  r=byid[rid];q=r['payload'];line=integer(b,q);h,q=string(b,q+4)
  data=dict(line=line+1,hash=h,type=r['type'],rid=rid)
  if r['type'] in ['CommentScriptLine','LabelScriptLine']:
   value,q=string(b,q);data['value']=value
   if line==0 and r['type']=='CommentScriptLine':header=value
   if r['type']=='LabelScriptLine':label=value
  elif r['type']=='CommandScriptLine':data['commands']=[long(b,q)]
  elif r['type']=='GenericTextScriptLine':data['commands']=[long(b,q+4+j*8) for j in range(integer(b,q))]
  else:assert r['type']=='EmptyScriptLine',r
  data['label']=label;lines.append(data)
 match=re.search(r'to [^<>]+ <([^>]+)> localization document',header)
 code=match[1] if match else 'zh-TW'
 entries=[];occurrences=collections.Counter()
 for line in lines:
  for j,rid in enumerate(line.get('commands',[])):
   if rid<0:continue
   r=byid[rid];types[r['type']]+=1
   # Command.playbackSpot contains script name followed by line/inline indexes.
   token=struct.pack('<i',len(name.encode()))+name.encode()
   found=b.find(token,r['payload'],r['end'])
   if found<0:
    unknown.append([name,code,r['type'],'missing playbackSpot']);continue
   _,q=string(b,found);assert integer(b,q)==line['line']-1
   q+=8
   if r['type'] not in samples:
    vals=[]
    for a in range(q,r['end']-4,4):
     try:
      v,k=string(b,a)
      if v and k<=r['end'] and all(ord(c)>=32 or c in '\n\r\t' for c in v):vals.append([a-q,v])
     except (AssertionError,UnicodeError,struct.error):pass
    samples[r['type']]=vals
   if r['type'] in ['OverridePrintCommand','PrintText','AddChoice','OverrideDisplayNameCommand']:
    field='text';speaker=''
    if r['type']=='OverrideDisplayNameCommand':
     speaker,q=string(b,q);q+=24;field='name'
    text,end=string(b,q);assert end<=r['end']
    if r['type'] in ['OverridePrintCommand','PrintText']:
     # PrinterId and AuthorId are serialized StringParameters after Text.
     try:speaker,_=string(b,end+52)
     except (AssertionError,UnicodeError,struct.error):speaker=''
    label=line['label'] if match else line['hash'];ordinal=occurrences[(label,field)];occurrences[(label,field)]+=1
    entries.append(dict(key=label+f'/{ordinal}/{field}',text=text,line=line['line'],label=label,command=r['type'],speaker=speaker,reference_id=rid,inline_index=j,field=field))
 doc=dict(script=name,code=code,language_basis='localization-header' if match else 'source-locale-configuration',source_asset='resources.assets',path_id=o.path_id,sha256=hashlib.sha256(b).hexdigest(),entries=entries)
 docs.append(doc)
print('DOCS',len(docs),'LANGS',collections.Counter(d['code'] for d in docs),'ENTRIES',collections.Counter({c:sum(len(d['entries']) for d in docs if d['code']==c) for c in {d['code'] for d in docs}}))
assert not unknown,unknown
assert len({(d['code'],d['script']) for d in docs})==len(docs)
for d in docs:assert len({e['key'] for e in d['entries']})==len(d['entries']),(d['code'],d['script'],collections.Counter(e['key'] for e in d['entries']).most_common(4))
docs.sort(key=lambda d:(d['code'],d['script']))
for d in docs:
 folder=out/'story'/d['code'];folder.mkdir(parents=True,exist_ok=True)
 (folder/(d['script']+'.txt')).write_text(''.join(e['key']+': '+e['text'].replace('\r\n','\\n').replace('\r','\\n').replace('\n','\\n')+'\n' for e in d['entries']),encoding='utf8')
(out/'story-scripts.json').write_text(json.dumps(dict(schemaVersion=1,documents=docs),ensure_ascii=False),encoding='utf8')
(out/'story-report.json').write_text(json.dumps(dict(objects=len(docs),source_asset='resources.assets',script_pointer=dict(file_id=1,path_id=2017),source_locale='zh-TW',source_locale_configuration_path_id=16077,languages={c:dict(documents=sum(d['code']==c for d in docs),entries=sum(len(d['entries']) for d in docs if d['code']==c)) for c in sorted({d['code'] for d in docs})},command_types=types,unknown=unknown,format_note='JSON and keyed TXT export of compiled dialogue and display-name fields; not original .nani source or a repackable Unity asset.'),ensure_ascii=False,indent=2),encoding='utf8')
