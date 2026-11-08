"""Export the embedded I2Languages table without contacting live services."""
import os,sys,pathlib,struct,json,hashlib,sqlite3,collections
WORKDIR=os.environ.get('ROTAENO_WORKDIR','')
if not WORKDIR:raise SystemExit('Set ROTAENO_WORKDIR before running extraction.')
ROOT=pathlib.Path(WORKDIR);sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tools/python-libs'))
from parse_game import Reader

def read_source():
 import UnityPy
 env=UnityPy.load(str(ROOT/'extracted/datapack.unity3d'))
 found=[o for o in env.objects if o.type.name=='MonoBehaviour' and o.assets_file.name=='resources.assets' and o.peek_name()=='I2Languages']
 assert len(found)==1,'Expected a unique I2Languages source'
 obj=found[0];raw=obj.get_raw_data()
 return raw,{'asset_file':obj.assets_file.name,'path_id':obj.path_id,'name':'I2Languages','sha256':hashlib.sha256(raw).hexdigest(),'byte_size':len(raw)}

def parse(raw):
 r=Reader(raw);r.p=28;assert r.s()=='I2Languages'
 prefix=[r.i() for _ in range(3)];n=r.i();assert 0<n<100000
 terms=[]
 for i in range(n):
  offset=r.p;key=r.s();typ=r.i();values=r.arr(r.s);nf=r.i();assert nf==len(values)
  flags=list(raw[r.p:r.p+nf]);r.p+=nf;r.align();touch=r.arr(r.s)
  assert key and len(values)==8
  terms.append({'entry_index':i,'key':key,'term_type':typ,'values':values,'flags':flags,'touch':touch,'byte_offset':offset})
 case_insensitive=r.flag();missing_policy=r.i();app_name_term=r.s();count=r.i();languages=[]
 for i in range(count):languages.append({'index':i,'name':r.s(),'code':r.s(),'flags':r.i()})
 assert count==8 and len({l['code'] for l in languages})==8
 assert [l['code'] for l in languages]==['china','zh-CN','zh-TW','en','ko','ja','id','th']
 return terms,languages,{'table_end_offset':r.p,'uninterpreted_configuration_bytes':len(raw)-r.p,'source_prefix_values':prefix,'case_insensitive_terms':case_insensitive,'missing_translation_policy':missing_policy,'app_name_term':app_name_term}

def save_db(db,terms,languages,source):
 db.execute('PRAGMA foreign_keys=ON')
 db.executescript('''
 DROP VIEW IF EXISTS localized_song_names;
 DROP VIEW IF EXISTS localization_canonical_terms;
 DROP TABLE IF EXISTS localization_values;
 DROP TABLE IF EXISTS localization_terms;
 DROP TABLE IF EXISTS languages;
 CREATE TABLE languages(code TEXT PRIMARY KEY,name TEXT NOT NULL,slot_index INTEGER UNIQUE NOT NULL,source_flags INTEGER NOT NULL);
 CREATE TABLE localization_terms(entry_index INTEGER PRIMARY KEY,term_key TEXT NOT NULL,term_type INTEGER NOT NULL,source_asset TEXT NOT NULL,source_path_id INTEGER NOT NULL,source_byte_offset INTEGER NOT NULL,touch_json TEXT NOT NULL);
 CREATE INDEX localization_term_keys ON localization_terms(term_key);
 CREATE TABLE localization_values(entry_index INTEGER REFERENCES localization_terms,language_code TEXT REFERENCES languages,text TEXT NOT NULL,source_flags INTEGER NOT NULL,PRIMARY KEY(entry_index,language_code));
 CREATE VIEW localization_canonical_terms AS SELECT * FROM localization_terms WHERE entry_index IN (SELECT MIN(entry_index) FROM localization_terms GROUP BY term_key);
 ''')
 db.executemany('INSERT INTO languages VALUES(?,?,?,?)',[(l['code'],l['name'],l['index'],l['flags']) for l in languages])
 db.executemany('INSERT INTO localization_terms VALUES(?,?,?,?,?,?,?)',[(t['entry_index'],t['key'],t['term_type'],source['asset_file'],source['path_id'],t['byte_offset'],json.dumps(t['touch'],ensure_ascii=False)) for t in terms])
 db.executemany('INSERT INTO localization_values VALUES(?,?,?,?)',[(t['entry_index'],l['code'],t['values'][l['index']],t['flags'][l['index']]) for t in terms for l in languages])
 if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='song_objects'").fetchone():
  db.execute('''CREATE VIEW localized_song_names AS SELECT s.song_id,s.title AS original_title,l.code AS language_code,t.term_key,v.text AS translated_title,ref.code AS reference_language,CASE WHEN ref.code IS NOT NULL THEN target.text ELSE v.text END AS resolved_translation,COALESCE(NULLIF(CASE WHEN ref.code IS NOT NULL THEN target.text ELSE v.text END,''),s.title) AS display_title,CASE WHEN ref.code IS NOT NULL THEN 'inferred_language_reference' WHEN v.text IS NULL OR v.text='' THEN 'original_title' ELSE 'localization_table' END AS display_title_source FROM song_objects s CROSS JOIN languages l LEFT JOIN localization_canonical_terms t ON t.term_key='db/song/'||s.song_id||'/name-translation' LEFT JOIN localization_values v ON v.entry_index=t.entry_index AND v.language_code=l.code LEFT JOIN languages ref ON ref.code=v.text LEFT JOIN localization_values target ON target.entry_index=t.entry_index AND target.language_code=ref.code''')
 db.commit();assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not db.execute('PRAGMA foreign_key_check').fetchall()

def main():
 raw,source=read_source();terms,languages,settings=parse(raw);out=ROOT/'localization';out.mkdir(exist_ok=True)
 def write(name,value):(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 text_terms=[t for t in terms if t['term_type']==0]
 write('languages.json',languages)
 write('all-terms.json',{'source':source,'languages':languages,'terms':terms})
 write('asset-references.json',{'languages':languages,'terms':[t for t in terms if t['term_type']!=0]})
 bykey={}
 for t in terms:bykey.setdefault(t['key'],t)
 grouped=collections.defaultdict(list)
 for t in terms:grouped[t['key']].append(t)
 duplicates={k:v for k,v in grouped.items() if len(v)>1}
 write('duplicate-terms.json',{'map_policy':'First serialized entry per key; runtime duplicate handling not asserted. All source entries preserved in all-terms.json and SQLite.','duplicates':duplicates})
 for l in languages:write(l['code']+'.json',{k:t['values'][l['index']] for k,t in bykey.items() if t['term_type']==0})
 songs=json.loads((ROOT/'game-song-data.json').read_text(encoding='utf8'))['songs'];names=[]
 codes={l['code']:l['index'] for l in languages}
 def resolve(t,code):
  chain=[];seen=set()
  while t:
   if code in seen:return {'text':None,'state':'cycle','reference_chain':chain}
   seen.add(code);value=t['values'][codes[code]]
   if value not in codes:return {'text':value,'state':'inferred_language_reference' if chain else 'literal' if value else 'empty','reference_chain':chain}
   chain.append(value);code=value
  return {'text':None,'state':'missing_term','reference_chain':chain}
 for s in songs:
  key='db/song/'+s['id']+'/name-translation';t=bykey.get(key)
  resolutions={l['code']:resolve(t,l['code']) for l in languages}
  names.append({'song_id':s['id'],'original_title':s['title'],'term_key':key,'term_present':t is not None,'translations':{l['code']:t['values'][l['index']] if t else None for l in languages},'resolution':resolutions,'display_titles':{l['code']:resolutions[l['code']]['text'] or s['title'] for l in languages}})
 write('song-names.json',names)
 # This mapping preserves override term keys when available, and reports absent
 # guessed keys rather than replacing them with a fabricated translation.
 packs=json.loads((ROOT/'game-song-data.json').read_text(encoding='utf8'))['packs'];pack_names=[]
 for p in packs:
  keys=[k for k in bykey if k.startswith('db/pack/'+p['pack_id']+'/')]
  rawfile=ROOT/'raw-objects'/f"{p['asset_file']}-{p['path_id']}.bin";overrides=[]
  if rawfile.exists():
   b=rawfile.read_bytes()
   for offset in range(0,len(b)-4,4):
    n=struct.unpack_from('<i',b,offset)[0]
    if 0<n<512 and offset+4+n<=len(b):
     try:k=b[offset+4:offset+4+n].decode('utf8')
     except UnicodeDecodeError:continue
     if k in bykey and k not in keys:keys.append(k);overrides.append({'key':k,'byte_offset':offset,'basis':'length-prefixed key observed in PackDataSO object'})
  pack_names.append({'pack_id':p['pack_id'],'additional_embedded_term_refs':overrides,'terms':{k:{l['code']:bykey[k]['values'][l['index']] for l in languages} for k in keys}})
 write('pack-texts.json',pack_names)
 report={'source':source,'term_count':len(terms),'unique_keys':len(bykey),'duplicate_keys':list(duplicates),'text_term_count':len(text_terms),'unique_text_keys':sum(t['term_type']==0 for t in bykey.values()),'asset_reference_term_count':len(terms)-len(text_terms),'language_slot_count':len(languages),'translation_cell_count':len(terms)*len(languages),'term_type_counts':dict(collections.Counter(t['term_type'] for t in terms)),'languages':[{**l,'nonempty_text_values':sum(bool(t['values'][l['index']]) for t in text_terms),'empty_text_values':sum(not t['values'][l['index']] for t in text_terms)} for l in languages],'song_name_keys_found':sum(n['term_present'] for n in names),'song_name_keys_missing':[n['song_id'] for n in names if not n['term_present']],'nonzero_term_flags':sum(bool(f) for t in terms for f in t['flags']),'touch_array_count':sum(bool(t['touch']) for t in terms),'parse_settings':settings,'integrity':'ok'}
 report['inferred_song_name_language_reference_cells']=sum(v['state']=='inferred_language_reference' for n in names for v in n['resolution'].values())
 report['song_name_reference_cycles']=sum(v['state']=='cycle' for n in names for v in n['resolution'].values())
 report['language_reference_policy']='A song-name cell equal to a known language code is interpreted as a reference to that slot. This is an analyst inference; raw cells are preserved. Empty resolved values use original_title in display_titles.'
 write('extraction-report.json',report)
 for dest in [ROOT/'game-songs.sqlite',out/'localization.sqlite']:
  db=sqlite3.connect(dest);save_db(db,terms,languages,source)
  if dest.name=='game-songs.sqlite':
   db.execute('INSERT OR REPLACE INTO analysis_metadata VALUES(?,?)',('localization',json.dumps(report,ensure_ascii=False)));db.commit()
  db.close()
 print(json.dumps(report,ensure_ascii=True,indent=2))

if __name__=='__main__':main()
