import os,sys,pathlib,struct,json,sqlite3,zipfile,hashlib,collections
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from parse_game import ROOT,Reader,chart
import UnityPy
SOURCE_DIR=os.environ.get('ROTAENO_SOURCE_DIR', '')
if not SOURCE_DIR: raise SystemExit('Set ROTAENO_SOURCE_DIR before reading source APKs.')
source=pathlib.Path(SOURCE_DIR)
def manifest():
 with zipfile.ZipFile(source/'base.apk') as z:b=z.read('AndroidManifest.xml')
 strings=[];p=8;out={}
 def varlen(q):
  n=b[q];q+=1
  if n&128:n=((n&127)<<8)|b[q];q+=1
  return n,q
 while p<len(b):
  kind,header,size=struct.unpack_from('<HHI',b,p)
  if kind==1:
   count,styles,flags,start,style_start=struct.unpack_from('<IIIII',b,p+8)
   for i in range(count):
    q=p+start+struct.unpack_from('<I',b,p+header+4*i)[0]
    if flags&256:_,q=varlen(q);n,q=varlen(q);strings.append(b[q:q+n].decode('utf8'))
    else:n=struct.unpack_from('<H',b,q)[0];strings.append(b[q+2:q+2+2*n].decode('utf-16le'))
  elif kind==258:
   ns,name,astart,asz,n=struct.unpack_from('<IIHHH',b,p+16)
   if strings[name]=='manifest':
    for i in range(n):
     q=p+16+astart+i*asz;ans,aname,raw=struct.unpack_from('<III',b,q);vtype=b[q+15];data=struct.unpack_from('<I',b,q+16)[0]
     out[strings[aname]]=strings[raw] if raw!=0xffffffff else strings[data] if vtype==3 else data
  p+=size
 (ROOT/'manifest-info.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8');return out
db=sqlite3.connect(ROOT/'game-songs.sqlite');data=json.loads((ROOT/'game-song-data.json').read_text(encoding='utf8'))
full_charts=[]
for old in data['charts']:
 r=Reader((ROOT/'raw-objects'/f"{old['asset_file']}-{old['path_id']}.bin").read_bytes());r.header();c=chart(r);c.update({k:v for k,v in old.items() if k in ['asset_file','path_id','script_ref','byte_size','sha256','song_ids']})
 db.execute('UPDATE chart_objects SET raw_json=? WHERE asset_file=? AND path_id=?',(json.dumps({k:v for k,v in c.items() if k!='encrypted_chart'},ensure_ascii=False),c['asset_file'],c['path_id']))
 full_charts.append(c)
byref={(c['asset_file'],c['path_id']):c for c in full_charts}
for s in data['songs']:
 s['charts']=[{k:v for k,v in byref[(c['asset_file'],c['path_id'])].items() if k not in ['encrypted_chart','override_bytes']} for c in s['charts']]
 db.execute('UPDATE song_objects SET raw_json=? WHERE song_id=?',(json.dumps(s,ensure_ascii=False),s['id']))
data['charts']=[{k:v for k,v in c.items() if k not in ['encrypted_chart','override_bytes']} for c in full_charts]
data['manifest']=manifest()
env=UnityPy.load(str(ROOT/'extracted/datapack.unity3d'));songbyid={s['path_id']:s['id'] for s in data['songs']};packs=[];pack_errors=[]
for o in env.objects:
 if o.type.name!='MonoBehaviour':continue
 raw=o.get_raw_data()
 if struct.unpack_from('<iq',raw,16)!=(1,420):continue
 r=Reader(raw);r.header();candidates=[]
 for offset in range(r.p,len(raw)-4,4):
  n=struct.unpack_from('<i',raw,offset)[0]
  if not 1<=n<=100 or offset+4+12*n>len(raw):continue
  refs=[struct.unpack_from('<iq',raw,offset+4+i*12) for i in range(n)]
  if all(f==0 and pid in songbyid for f,pid in refs):candidates.append((n,offset,refs))
 if not candidates:pack_errors.append({'name':r.name,'path_id':o.path_id,'reason':'No nonempty all-song PPtr array found'});continue
 maxn=max(c[0] for c in candidates);chosen=[c for c in candidates if c[0]==maxn]
 if len(chosen)!=1:pack_errors.append({'name':r.name,'path_id':o.path_id,'reason':'Ambiguous song array'});continue
 n,offset,refs=chosen[0];packs.append({'pack_id':r.name,'asset_file':o.assets_file.name,'path_id':o.path_id,'song_ids':[songbyid[pid] for f,pid in refs],'song_array_offset':offset,'object_sha256':hashlib.sha256(raw).hexdigest(),'membership_evidence':'Unique maximal aligned length-prefixed PPtr array with every element resolving to a SongDataSO; pack class field songDatas observed in IL2CPP.'})
 (ROOT/'raw-objects'/f'{o.assets_file.name}-{o.path_id}.bin').write_bytes(raw)
db.executescript('DROP TABLE IF EXISTS pack_songs;DROP TABLE IF EXISTS pack_objects;CREATE TABLE pack_objects(pack_id TEXT PRIMARY KEY,asset_file TEXT,path_id INTEGER,raw_json TEXT);CREATE TABLE pack_songs(pack_id TEXT REFERENCES pack_objects,song_id TEXT REFERENCES song_objects,position INTEGER,PRIMARY KEY(pack_id,song_id))')
for p in packs:
 db.execute('INSERT INTO pack_objects VALUES(?,?,?,?)',(p['pack_id'],p['asset_file'],p['path_id'],json.dumps(p,ensure_ascii=False)))
 for i,sid in enumerate(p['song_ids']):db.execute('INSERT INTO pack_songs VALUES(?,?,?)',(p['pack_id'],sid,i))
db.commit();db.close();data['packs']=packs;data['pack_errors']=pack_errors
(ROOT/'game-song-data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'manifest':data['manifest'],'fully_parsed_chart_tails':len(full_charts),'packs':len(packs),'pack_memberships':sum(len(p['song_ids']) for p in packs),'pack_errors':pack_errors,'nonempty_chart_credit_overrides':sum(bool(c['override_info']['charter']['text']) for c in full_charts)},ensure_ascii=True,indent=2))
