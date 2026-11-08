import os,pathlib,json,sqlite3,hashlib,re,ast
workdir=os.environ.get('ROTAENO_WORKDIR','')
if not workdir:raise SystemExit('Set ROTAENO_WORKDIR before validation.')
root=pathlib.Path(workdir);out=root/'localization';data=json.loads((out/'all-terms.json').read_text(encoding='utf8'));terms=data['terms'];languages=data['languages']
assert len(terms)==2462 and len(languages)==8
assert len({t['key'] for t in terms})==2459
assert len({t['key'] for t in terms if t['term_type']==0})==2436
canonical={}
for t in terms:canonical.setdefault(t['key'],t)
for l in languages:
 values=json.loads((out/(l['code']+'.json')).read_text(encoding='utf8'))
 assert len(values)==2436
 for key,value in values.items():assert value==canonical[key]['values'][l['index']]
names=json.loads((out/'song-names.json').read_text(encoding='utf8'));assert len(names)==437
assert next(n for n in names if n['song_id']=='ai-li-ke2000')['display_titles']['ko']=='《Instant Luv 2000》'
assert next(n for n in names if n['song_id']=='after-rain')['display_titles']['ko']=='After Rain'
for filename in [root/'game-songs.sqlite',out/'localization.sqlite']:
 db=sqlite3.connect(filename);assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not db.execute('PRAGMA foreign_key_check').fetchall()
 assert db.execute('SELECT COUNT(*) FROM localization_terms').fetchone()[0]==2462
 assert db.execute('SELECT COUNT(*) FROM localization_values').fetchone()[0]==19696
 assert db.execute('SELECT COUNT(*) FROM managed_localization_values').fetchone()[0]==2415
 if filename.name=='game-songs.sqlite':
  assert db.execute('SELECT COUNT(*) FROM song_objects').fetchone()[0]==437
  assert db.execute('SELECT COUNT(*) FROM chart_objects').fetchone()[0]==1783
  rows=db.execute('SELECT song_id,language_code,display_title FROM localized_song_names').fetchall();assert len(rows)==3496
  indexed={n['song_id']:n for n in names}
  for sid,code,title in rows:assert title==indexed[sid]['display_titles'][code]
  (root/'schema.sql').write_text('\n\n'.join(r[0]+';' for r in db.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 ELSE 2 END,name")),encoding='utf8')
 db.close()
pattern=re.compile(rb'(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|\\\\[A-Za-z0-9._-]+\\[A-Za-z0-9_$.-]+\\|/(?:Users|home|tmp|private/var)/)')
files=0
for p in out.rglob('*'):
 if p.is_file():assert not pattern.search(p.read_bytes()),p.name;files+=1
report={'status':'ok','source_object_sha256':data['source']['sha256'],'source_entries':2462,'unique_keys':2459,'unique_text_keys':2436,'language_slots':8,'translation_cells':19696,'song_language_rows':3496,'managed_text_values':2415,'json_sqlite_parity':'ok','database_integrity':'ok','foreign_key_errors':0,'local_path_findings':0,'exported_files_scanned':files}
(out/'validation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,indent=2))
