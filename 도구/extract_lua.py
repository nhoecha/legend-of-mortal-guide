import usf2, os, re, json, struct, collections, shutil
D=r"C:\Program Files (x86)\Steam\steamapps\common\LegendOfMortal\Mortal_Data"
OUT='lua'; LEGACY='lua_legacy'

# story/chinesetraditional 이 게임이 돌리는 전체 판이고 chinesesimplified 는 로직까지 다른 옛 일부 판이다
# (back_001 이 Back_02 로 안 간다). 어느 쪽인지는 ResourceManager 컨테이너에만 적혀 있다.
def story_locales():
    b=open(os.path.join(D,'globalgamemanagers'),'rb').read()
    loc={}
    for m in re.finditer(rb'story/([a-z]+)/([\x21-\x7e]+)',b):
        s=m.start()
        if struct.unpack_from('<I',b,s-4)[0]!=len(m.group()):
            continue
        fid,pid=struct.unpack_from('<iq',b,(s+len(m.group())+3)//4*4)
        loc[pid]=m.group(1).decode()
    return loc

LOC=story_locales()
for d in (OUT, LEGACY):
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d, exist_ok=True)   # OneDrive 가 빈 폴더를 쥐고 있을 때가 있다
sf=usf2.SF(os.path.join(D,'resources.assets'))
assets=[]
for pid,off,sz,cid in sf.objs:
    if cid!=49: continue
    r=sf.reader(off); nm=r.astr(); L=r.u32()
    assets.append((pid,nm,sf.data[r.o:r.o+L]))
has_trad={nm for pid,nm,_ in assets if LOC.get(pid)=='chinesetraditional'}

seen=collections.Counter(); m={}; n=0; legacy=0
for pid,nm,body in assets:
    safe=re.sub(r'[^0-9A-Za-z_.\-]','_',nm)[:110]
    if LOC.get(pid)=='chinesesimplified' and nm in has_trad:
        open(os.path.join(LEGACY,safe+'.lua'),'wb').write(body); legacy+=1
        continue
    seen[safe]+=1
    if seen[safe]>1: safe=f'{safe}__{pid}'
    open(os.path.join(OUT,safe+'.lua'),'wb').write(body)
    m[safe]=nm; n+=1
json.dump(m, open('lua_names.json','w',encoding='utf-8'), ensure_ascii=False)
print('추출',n,'파일',len(m),'· 간체 옛 판',legacy,'→',LEGACY)
dups=[k for k,v in seen.items() if v>1]
print('이름충돌',len(dups), dups[:5])
