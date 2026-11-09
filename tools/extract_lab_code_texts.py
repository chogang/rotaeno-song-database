"""Recover Lab name literals from a pinned Rotaeno 2.99.0 ARM64 build.

Static ADRP/ADD/LDR slices and ELF relative relocations only; no target execution.
Methods without a recognized literal load remain explicitly unresolved.
"""
import hashlib,json,os,pathlib,struct,sys

def extract(metadata, binary, methods):
 b=binary.read_bytes();m=metadata.read_bytes()
 assert hashlib.sha256(m).hexdigest()=='91c74f933e83904e0b642515fb2b0a9fad4ef07893f1edd10965d5c9a1e64a0a', 'Unsupported metadata build.'
 assert hashlib.sha256(b).hexdigest()=='257941c2ea1be78980721f4b7005ddab7bc0d9610fe0290ede36e220f7823d23', 'Unsupported native build.'
 assert b[:6]==b'\x7fELF\x02\x01'
 o,n,d,_=struct.unpack_from('<IIII',m,8)
 literals=[]
 for i in range(0,n,8):
  size,pos=struct.unpack_from('<II',m,o+i);literals.append(m[d+pos:d+pos+size].decode('utf8'))
 phoff=struct.unpack_from('<Q',b,32)[0];phsize,phcount=struct.unpack_from('<HH',b,54);segments=[]
 for i in range(phcount):
  kind,_,off,va,_,size,_,_=struct.unpack_from('<IIQQQQQQ',b,phoff+i*phsize)
  if kind==1:segments.append((va,off,size))
 def offset(va):
  for start,off,size in segments:
   if start<=va<start+size:return off+va-start
  raise ValueError('Unmapped native address.')
 relocs={};shoff=struct.unpack_from('<Q',b,40)[0];shsize,shcount=struct.unpack_from('<HH',b,58)
 for i in range(shcount):
  sh=struct.unpack_from('<IIQQQQIIQQ',b,shoff+i*shsize)
  if sh[1]==4:
   for pos in range(sh[4],sh[4]+sh[5],sh[9]):
    addr,info,addend=struct.unpack_from('<QQq',b,pos)
    if info&0xffffffff==1027:relocs[addr]=addend
 def read(va):return relocs[va] if va in relocs else struct.unpack_from('<Q',b,offset(va))[0]
 entries={};unresolved=[]
 for row in methods:
  start=int(row['address'],16);regs={};found=[]
  for pc in range(start,start+160,4):
   word=struct.unpack_from('<I',b,offset(pc))[0];rd=word&31;rn=(word>>5)&31
   if word&0x9f000000==0x90000000:
    imm=(((word>>5)&0x7ffff)<<2)|((word>>29)&3)
    if imm&(1<<20):imm-=1<<21
    regs[rd]=(pc&~4095)+(imm<<12)
   elif word&0xffc00000==0xf9400000 and rn in regs:
    addr=regs[rn]+(((word>>10)&4095)*8)
    try:value=read(addr);regs[rd]=value
    except ValueError:continue
    if value>>29==5 and value&1:
     index=(value&0x1fffffff)>>1;assert index<len(literals)
     context={**row,'load_address':hex(pc),'literal_slot_address':hex(addr)}
     entries.setdefault(index,dict(literal_index=index,text=literals[index],contexts=[]))['contexts'].append(context);found.append(index)
   elif word&0x7f000000==0x11000000 and rn in regs:regs[rd]=regs[rn]+(((word>>10)&4095)<<(12 if word&(1<<22) else 0))
   if word==0xd65f03c0:break
  if not found:unresolved.append(row)
 result={'schemaVersion':1,'source':{'metadata_file':'global-metadata.dat','metadata_sha256':hashlib.sha256(m).hexdigest(),'binary_file':'libil2cpp.so','binary_sha256':hashlib.sha256(b).hexdigest(),'metadata_version':struct.unpack_from('<I',m,4)[0]},'entries':sorted(entries.values(),key=lambda e:e['literal_index']),'unresolved_methods':unresolved,'key_policy':'App IDs lab/code/<literal_index> are analysis identifiers, not original I2 translation keys. Korean edits are separate review proposals, not a native code patch.'}
 assert {'DJ SPIN','DJ Scratch','Funky','Mine Fun','Rectangle','Relativity','VTuber','VTuber (Easy)','Weeeeeeeee'} <= {e['text'] for e in result['entries']}
 assert len(result['entries'])==18 and len(unresolved)==9
 return result

if __name__=='__main__':
 root=pathlib.Path(os.environ['ROTAENO_WORKDIR']);binary=pathlib.Path(os.environ['ROTAENO_NATIVE_BINARY'])
 methods=json.loads(pathlib.Path(__file__).with_name('lab-name-methods.json').read_text(encoding='utf8'))
 data=extract(root/'extracted/global-metadata.dat',binary,methods)
 pathlib.Path(sys.argv[1]).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'code_texts':len(data['entries']),'texts':[e['text'] for e in data['entries']],'unresolved_methods':len(data['unresolved_methods'])}))
