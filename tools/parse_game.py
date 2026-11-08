import os,sys,pathlib,struct,json,hashlib,sqlite3,re,collections
WORKDIR=os.environ.get('ROTAENO_WORKDIR', '')
if not WORKDIR: raise SystemExit('Set ROTAENO_WORKDIR before running extraction.')
ROOT=pathlib.Path(WORKDIR);sys.path.insert(0,str(ROOT/'tools/python-libs'))
import UnityPy
class Reader:
 def __init__(self,b):self.b=b;self.p=0
 def align(self):self.p=(self.p+3)&~3
 def i(self):v=struct.unpack_from('<i',self.b,self.p)[0];self.p+=4;return v
 def f(self):v=struct.unpack_from('<f',self.b,self.p)[0];self.p+=4;return v
 def s(self):
  n=self.i();assert 0<=n<=len(self.b)-self.p,(self.p,n,len(self.b));v=self.b[self.p:self.p+n].decode('utf8');self.p+=n;self.align();return v
 def ptr(self):f=self.i();p=struct.unpack_from('<q',self.b,self.p)[0];self.p+=8;return {'file_id':f,'path_id':p}
 def flag(self):v=self.b[self.p];self.p+=1;self.align();assert v in [0,1];return bool(v)
 def arr(self,func):n=self.i();assert 0<=n<100000;return [func() for _ in range(n)]
 def header(self):
  self.p=28;self.name=self.s();self.odin_format=self.i();n=self.i();assert 0<=n<1000000;self.odin_bytes=self.b[self.p:self.p+n];self.p+=n;self.align()
  self.odin_refs=self.arr(self.ptr);self.odin_string=self.s();self.prefab=self.ptr();self.arr(self.ptr);self.arr(self.s);self.arr(lambda:(self.s(),self.i(),self.s()))
 def local(self):
  use=self.flag();term=self.s();arabic=self.flag();maxline=self.i();numbers=self.flag();params=self.flag();constant=self.s();return {'use_term':use,'term':term,'text':constant}
 def ref(self):return {'guid':self.s(),'subobject':self.s(),'type':self.s()}
def resources(r):return {'cover_hd':r.ref(),'cover_blur':r.ptr(),'cover_downscale':r.ptr(),'song_info_hd':r.ref(),'song_info_downscale':r.ptr(),'preview':r.ref(),'full':r.ref()}
def sample():
 for id in [13827,13860,13825]:
  b=(ROOT/f'sample-{id}.bin').read_bytes();r=Reader(b);r.header();print('header',id,r.name,r.p,len(r.odin_bytes),r.odin_refs)
  for p in range(r.p,min(r.p+40,len(b)),4):print(p,struct.unpack_from('<i',b,p)[0])
def song(r):
 start=r.p
 # Some objects contain extra inherited serialized fields before the schedule.
 # Locate and verify the exact length-prefixed ID; retain the skipped bytes.
 marker=struct.pack('<i',len(r.name.encode('utf8')))+r.name.encode('utf8')
 matches=[m.start() for m in re.finditer(re.escape(marker),r.b[start:])]
 # A title can equal the ID. The ID precedes the info struct, so use the first
 # framed occurrence after the inherited prefix and validate the full layout.
 assert matches,('ID anchor missing',r.name)
 r.p=start+matches[0];id_offset=r.p
 id=r.s();assert id==r.name,(id,r.name,start)
 status=r.i();title=r.s();info={key:r.local() for key in ['artist','illustrator','charter','extra_credits','album']};hide=r.i();version=r.s()
 res=resources(r)
 # Locked resource override is Odin-serialized, not part of the Unity tail.
 charts=r.arr(r.ptr)
 return {'id':id,'title':title,'content_id_status':status,'info':info,'hide_type':hide,'release_version':version,'resources':res,'chart_refs':charts,'trailing_hex':r.b[r.p:].hex(),'parsed_until':r.p,'raw_size':len(r.b),'uninterpreted_prefix_hex':r.b[start:id_offset].hex(),'id_offset':id_offset}
def chart(r):
 level=r.i();cipher=r.s();storyboards=r.arr(r.ref);legacy=r.f();constant=r.f();prefix=r.s();override_level=r.s()
 offset=r.p;raw_override=r.b[offset:].hex();original=r.s();info={key:r.local() for key in ['title_translation','artist','illustrator','charter','extra_credits','album']};hide=r.i();version=r.s();res=resources(r)
 assert r.p==len(r.b),('Chart trailing bytes',r.name,r.p,len(r.b))
 return {'name':r.name,'level_id':level,'encrypted_chart':cipher,'storyboards':storyboards,'legacy_constant':legacy,'constant':round(constant,5),'override_prefix':prefix,'override_level':override_level,'override_info':{'title_original':original,**info,'hide_type':hide,'release_version':version},'override_resources':res,'override_offset':offset,'override_bytes':raw_override}
def extract_all():
 env=UnityPy.load(str(ROOT/'extracted/datapack.unity3d'));objects={};songs=[];charts=[];errors=[];rawdir=ROOT/'raw-objects';rawdir.mkdir(exist_ok=True)
 for obj in env.objects:
  if obj.type.name!='MonoBehaviour':continue
  raw=obj.get_raw_data();script=(struct.unpack_from('<i',raw,16)[0],struct.unpack_from('<q',raw,20)[0])
  if script not in [(1,1017),(1,1340)]:continue
  r=Reader(raw);meta={'asset_file':obj.assets_file.name,'path_id':obj.path_id,'script_ref':script,'byte_size':obj.byte_size,'sha256':hashlib.sha256(raw).hexdigest()}
  try:
   r.header();data=song(r) if script==(1,1017) else chart(r);data.update(meta)
   (songs if script==(1,1017) else charts).append(data)
   (rawdir/f'{obj.assets_file.name}-{obj.path_id}.bin').write_bytes(raw)
  except Exception as e:errors.append({**meta,'name':getattr(r,'name',None),'offset':r.p,'error':repr(e)})
 # Associate song/chart objects by exact serialized PPtr, never by display title.
 byref={(c['asset_file'],c['path_id']):c for c in charts}
 for s in songs:
  s['charts']=[]
  for ref in s['chart_refs']:
   c=byref.get((s['asset_file'],ref['path_id'])) if ref['file_id']==0 else None
   if c:s['charts'].append({k:v for k,v in c.items() if k not in ['encrypted_chart','override_bytes']});c.setdefault('song_ids',[]).append(s['id'])
   else:errors.append({'song_id':s['id'],'error':'Unresolved chart reference','ref':ref})
 payload={'unity_version':'2022.3.62f2c1','unitypy_version':UnityPy.__version__,'songs':songs,'charts':[{k:v for k,v in c.items() if k not in ['encrypted_chart']} for c in charts],'errors':errors}
 (ROOT/'game-song-data.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
 db=sqlite3.connect(ROOT/'game-songs.sqlite');db.executescript('''
 DROP TABLE IF EXISTS chart_objects;DROP TABLE IF EXISTS song_charts;DROP TABLE IF EXISTS song_objects;DROP TABLE IF EXISTS parse_errors;
 CREATE TABLE song_objects(song_id TEXT PRIMARY KEY,title TEXT,artist TEXT,illustrator TEXT,charter TEXT,album TEXT,release_version TEXT,asset_file TEXT,path_id INTEGER,object_sha256 TEXT,raw_json TEXT);
 CREATE TABLE chart_objects(asset_file TEXT,path_id INTEGER,name TEXT,level_id INTEGER,constant REAL,legacy_constant REAL,override_level TEXT,override_prefix TEXT,encrypted_chart TEXT,object_sha256 TEXT,raw_json TEXT,PRIMARY KEY(asset_file,path_id));
 CREATE TABLE song_charts(song_id TEXT REFERENCES song_objects,asset_file TEXT,path_id INTEGER,PRIMARY KEY(song_id,asset_file,path_id),FOREIGN KEY(asset_file,path_id) REFERENCES chart_objects);
 CREATE TABLE parse_errors(id INTEGER PRIMARY KEY,detail TEXT);
 ''')
 for s in songs:db.execute('INSERT INTO song_objects VALUES(?,?,?,?,?,?,?,?,?,?,?)',(s['id'],s['title'],*[s['info'][k]['text'] for k in ['artist','illustrator','charter','album']],s['release_version'],s['asset_file'],s['path_id'],s['sha256'],json.dumps(s,ensure_ascii=False)))
 for c in charts:
  db.execute('INSERT INTO chart_objects VALUES(?,?,?,?,?,?,?,?,?,?,?)',(c['asset_file'],c['path_id'],c['name'],c['level_id'],c['constant'],c['legacy_constant'],c['override_level'],c['override_prefix'],c['encrypted_chart'],c['sha256'],json.dumps({k:v for k,v in c.items() if k!='encrypted_chart'},ensure_ascii=False)))
  for sid in c.get('song_ids',[]):db.execute('INSERT INTO song_charts VALUES(?,?,?)',(sid,c['asset_file'],c['path_id']))
 for e in errors:db.execute('INSERT INTO parse_errors(detail) VALUES(?)',(json.dumps(e,ensure_ascii=False),))
 db.commit();report={'song_objects':len(songs),'chart_objects':len(charts),'linked_charts':sum(len(s['charts']) for s in songs),'errors':errors,'level_id_counts':dict(collections.Counter(c['level_id'] for c in charts)),'min_constant':min(c['constant'] for c in charts),'max_constant':max(c['constant'] for c in charts),'integrity_check':db.execute('PRAGMA integrity_check').fetchone()[0],'foreign_key_check':db.execute('PRAGMA foreign_key_check').fetchall()}
 db.close();(ROOT/'extraction-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=True,indent=2)[:10000])
def sample_parse():
 for id in [13827,13860,13825,13858]:
  r=Reader((ROOT/f'sample-{id}.bin').read_bytes());r.header()
  try:
   v=song(r) if id in [13827,13860] else chart(r)
   if 'encrypted_chart' in v:v['encrypted_chart']=v['encrypted_chart'][:30]+'...'
   print(id,json.dumps(v,ensure_ascii=False,indent=2))
  except Exception as e:print(id,'ERROR',r.p,repr(e));raise
if __name__=='__main__':extract_all() if '--all' in sys.argv else sample_parse()
