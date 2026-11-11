"""Extract WPF stream resources without loading any Acer code."""
from pathlib import Path
import struct, json, hashlib
src=Path('extracted/ui-analysis/Win32/NitroSense.exe'); b=src.read_bytes()
u16=lambda p:struct.unpack_from('<H',b,p)[0]
u32=lambda p:struct.unpack_from('<I',b,p)[0]
pe=u32(0x3c); opt=pe+24; secs=opt+u16(pe+20)
def offset(rva):
 for i in range(u16(pe+6)):
  p=secs+40*i; vs,va,rs,raw=struct.unpack_from('<IIII',b,p+8)
  if va <= rva < va+max(vs,rs): return raw+rva-va
 raise ValueError(rva)
base=offset(748156); size=u32(base); r=b[base+4:base+4+size]
assert hashlib.sha256(r).hexdigest()=='501a274df16fc191f9172fc1fbb3f86c1fba668e494e216eb464f86d01dc0f8b'
pos=0
def readint():
 global pos
 v=struct.unpack_from('<i',r,pos)[0];pos+=4;return v
def seven():
 global pos
 n=0;s=0
 while True:
  v=r[pos];pos+=1;n|=(v&127)<<s
  if v<128:return n
  s+=7
assert readint()==-1091581234
version=readint();skip=readint();pos+=skip
assert readint()==2
count=readint(); types=readint()
for _ in range(types):pos+=seven()
pos=(pos+7)//8*8
pos+=4*count
names=[readint() for _ in range(count)]
data=readint(); namestart=pos
out=Path('extracted/ui-analysis/resources');out.mkdir(exist_ok=True)
entries=[]
for n in names:
 pos=namestart+n; length=seven(); name=r[pos:pos+length].decode('utf-16le');pos+=length;dp=readint()
 pos=data+dp; typ=seven()
 if typ not in (32,33):
  entries.append({'name':name,'type':typ}); continue
 length=readint();payload=r[pos:pos+length]
 target=out/name
 if target.resolve().is_relative_to(out.resolve()):
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(payload)
 entries.append({'name':name,'type':typ,'bytes':length,'sha256':hashlib.sha256(payload).hexdigest()})
Path('evidence/ui-resource-index.json').write_text(json.dumps(entries,indent=2))
print('Extracted',len(entries),'resources')
