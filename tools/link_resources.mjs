import fs from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
const root=process.env.ROTAENO_WORKDIR || (()=>{throw Error('Set ROTAENO_WORKDIR before running this tool.');})();
const c=JSON.parse(fs.readFileSync(root+'/extracted/catalog.json','utf8'));
const k=Buffer.from(c.m_KeyDataString,'base64'),b=Buffer.from(c.m_BucketDataString,'base64'),e=Buffer.from(c.m_EntryDataString,'base64');
function key(p){const type=k[p++];if(type===0||type===1){const n=k.readInt32LE(p);p+=4;return k.subarray(p,p+n).toString(type===0?'ascii':'utf16le');}if(type===4)return k.readInt32LE(p);return {type,offset:p-1};}
let p=4;const buckets=[],map=new Map;
for(let i=0;i<b.readInt32LE(0);i++){const off=b.readInt32LE(p),n=b.readInt32LE(p+4);p+=8;const entries=[];for(let j=0;j<n;j++){entries.push(b.readInt32LE(p));p+=4;}const value=key(off);buckets.push({key:value,entries});if(typeof value==='string')map.set(value,entries);}
if(p!==b.length)throw Error('Bucket length mismatch');
const locations=[];for(let i=0;i<e.readInt32LE(0);i++){const p=4+i*28;const a=Array.from({length:7},(_,j)=>e.readInt32LE(p+4*j));locations.push({index:i,internal_id:c.m_InternalIds[a[0]],provider:c.m_ProviderIds[a[1]],dependency_key_index:a[2],primary_key:buckets[a[5]]?.key,resource_type:c.m_resourceTypes[a[6]]});}
const inventory=JSON.parse(fs.readFileSync(root+'/apk-inventory.json','utf8').replace(/^\uFEFF/,''));const stream=inventory.find(x=>(x.file_name||x.Apk).endsWith('split_UnityStreamingAssetsPack.apk'));const entries=new Set(stream.Entries.map(x=>x.Path));
function bundles(i,seen=new Set){if(seen.has(i))return [];seen.add(i);const l=locations[i],result=[];if(l.internal_id.endsWith('.bundle')){const entry=l.internal_id.replace('{UnityEngine.AddressableAssets.Addressables.RuntimePath}','assets/aa');result.push({entry,present_in_apk:entries.has(entry)});}if(l.dependency_key_index>=0)for(const dep of buckets[l.dependency_key_index]?.entries??[])result.push(...bundles(dep,seen));return result;}
const data=JSON.parse(fs.readFileSync(root+'/game-song-data.json','utf8')),resourceLinks=[];
for(const s of data.songs)for(const role of ['cover_hd','song_info_hd','preview','full']){const guid=s.resources[role].guid;if(!guid)continue;for(const idx of map.get(guid)??[]){resourceLinks.push({song_id:s.id,role,guid,...locations[idx],bundles:bundles(idx)});}}
fs.writeFileSync(root+'/resource-links.json',JSON.stringify(resourceLinks,null,2));
const db=new DatabaseSync(root+'/game-songs.sqlite');db.exec('DROP TABLE IF EXISTS resource_locations;CREATE TABLE resource_locations(song_id TEXT REFERENCES song_objects,role TEXT,guid TEXT,location_index INTEGER,internal_path TEXT,bundles_json TEXT,PRIMARY KEY(song_id,role,location_index))');const stmt=db.prepare('INSERT INTO resource_locations VALUES(?,?,?,?,?,?)');db.exec('BEGIN');for(const l of resourceLinks)stmt.run(l.song_id,l.role,l.guid,l.index,l.internal_id,JSON.stringify(l.bundles));db.exec('COMMIT');db.close();
console.log(JSON.stringify({resource_links:resourceLinks.length,unresolved_guids:data.songs.flatMap(s=>['cover_hd','preview','full'].filter(role=>s.resources[role].guid&&!map.has(s.resources[role].guid)).map(role=>({id:s.id,role}))),missing_bundles:resourceLinks.flatMap(x=>x.bundles).filter(x=>!x.present_in_apk).length,sample:resourceLinks.filter(x=>x.song_id==='after-rain')},null,2));
