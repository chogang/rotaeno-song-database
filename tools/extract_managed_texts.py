"""Export embedded Naninovel managed text documents and SDK locale strings."""
import os,sys,pathlib,json,re,hashlib,sqlite3
workdir=os.environ.get('ROTAENO_WORKDIR','')
if not workdir:raise SystemExit('Set ROTAENO_WORKDIR before running extraction.')
root=pathlib.Path(workdir);sys.path.insert(0,str(root/'tools/python-libs'))
import UnityPy
env=UnityPy.load(str(root/'extracted/datapack.unity3d'));out=root/'localization';documents=[];sdk=None
for obj in env.objects:
 if obj.type.name!='TextAsset':continue
 d=obj.parse_as_object()
 if d.m_Name not in ['DefaultUI','Locales','CharacterNames','AntiAddictionLocalization']:continue
 text=d.m_Script
 if isinstance(text,bytes):text=text.decode('utf8')
 source={'asset_file':obj.assets_file.name,'path_id':obj.path_id,'name':d.m_Name,'object_sha256':hashlib.sha256(obj.get_raw_data()).hexdigest()}
 if d.m_Name=='AntiAddictionLocalization':
  sdk={'source':source,'data':json.loads(text)};continue
 header=re.search(r'^; .*? <([^>]+)> to .*? <([^>]+)> localization document',text)
 code=header[2] if header else 'zh-TW'
 basis='explicit_document_header' if header else 'base_document; source locale inferred from translated sibling headers'
 folder=out/'naninovel'/code;folder.mkdir(parents=True,exist_ok=True)
 (folder/(d.m_Name+'.txt')).write_text(text,encoding='utf8')
 entries=[];unparsed=[]
 for i,line in enumerate(text.splitlines(),1):
  if not line.strip() or line.lstrip().startswith(';'):continue
  key,sep,value=line.partition(':')
  if not sep:unparsed.append({'line':i,'text':line});continue
  entries.append({'key':key,'text':value[1:] if value.startswith(' ') else value,'line':i})
 doc={'language_code':code,'language_basis':basis,'document':d.m_Name,'source':source,'entries':entries,'unparsed_lines':unparsed}
 (folder/(d.m_Name+'.json')).write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8');documents.append(doc)
index={'documents':[{k:v for k,v in d.items() if k not in ['entries','unparsed_lines']}|{'entry_count':len(d['entries']),'unparsed_line_count':len(d['unparsed_lines'])} for d in documents],'document_count':len(documents),'entry_count':sum(len(d['entries']) for d in documents),'language_codes':sorted({d['language_code'] for d in documents})}
(out/'managed-text-index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
if sdk:
 (out/'sdk-anti-addiction.json').write_text(json.dumps(sdk,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 folder=out/'sdk';folder.mkdir(exist_ok=True)
 for code,values in sdk['data'].get('items',{}).items():(folder/(code+'.json')).write_text(json.dumps(values,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
for filename in [root/'game-songs.sqlite',out/'localization.sqlite']:
 db=sqlite3.connect(filename);db.execute('DROP TABLE IF EXISTS managed_localization_values');db.execute('CREATE TABLE managed_localization_values(document TEXT,language_code TEXT,term_key TEXT,text TEXT,source_path_id INTEGER,source_line INTEGER,PRIMARY KEY(document,language_code,source_line))')
 db.executemany('INSERT INTO managed_localization_values VALUES(?,?,?,?,?,?)',[(d['document'],d['language_code'],e['key'],e['text'],d['source']['path_id'],e['line']) for d in documents for e in d['entries']]);db.commit();assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok';db.close()
print(json.dumps({'document_count':index['document_count'],'entry_count':index['entry_count'],'language_codes':index['language_codes'],'unparsed_lines':sum(len(d['unparsed_lines']) for d in documents),'sdk_language_keys':list(sdk['data'].get('items',{})) if sdk else []},ensure_ascii=True,indent=2))
