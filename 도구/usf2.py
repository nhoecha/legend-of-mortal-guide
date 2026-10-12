import struct, os, collections

class R:
    def __init__(s,d,be=True,o=0): s.d=d; s.o=o; s.be=be
    def _u(s,f,n):
        v=struct.unpack_from(('>' if s.be else '<')+f,s.d,s.o)[0]; s.o+=n; return v
    def u32(s): return s._u('I',4)
    def i32(s): return s._u('i',4)
    def u64(s): return s._u('Q',8)
    def i64(s): return s._u('q',8)
    def u16(s): return s._u('H',2)
    def u8(s):
        v=s.d[s.o]; s.o+=1; return v
    def cstr(s):
        e=s.d.index(b'\x00',s.o); v=s.d[s.o:e].decode('utf-8','replace'); s.o=e+1; return v
    def align(s,n=4): s.o=(s.o+n-1)//n*n
    def astr(s):
        L=s.u32(); v=s.d[s.o:s.o+L].decode('utf-8','replace'); s.o+=L; s.align(4); return v
    def pptr(s): return (s.i32(), s.i64())

class SF:
    def __init__(s,path):
        d=open(path,'rb').read(); s.data=d; s.path=path
        r=R(d)
        meta=r.u32(); fsz=r.u32(); ver=r.u32(); doff=r.u32()
        endian=r.u8(); r.o+=3
        if ver>=22:
            meta=r.u32(); fsz=r.u64(); doff=r.u64(); r.u64()
        r.be = endian==1
        s.version=ver
        s.unity=r.cstr(); r.u32()
        ett=r.u8(); nt=r.u32(); types=[]
        for _ in range(nt):
            cid=r.i32(); r.u8(); r.u16()
            if cid==114: r.o+=16
            r.o+=16
            types.append(cid)
        nobj=r.u32(); r.align(4); objs=[]
        for _ in range(nobj):
            r.align(4)
            pid=r.i64(); off=r.u64() if ver>=22 else r.u32()
            sz=r.u32(); ti=r.i32()
            objs.append((pid, doff+off, sz, types[ti]))
        s.objs=objs
        ns=r.u32()
        for _ in range(ns): r.i32(); r.align(4); r.i64()
        ne=r.u32(); ext=[]
        for _ in range(ne):
            r.cstr(); r.o+=16; r.i32(); ext.append(r.cstr())
        s.externals=ext
        s.be=r.be
    def reader(s,off): return R(s.data,s.be,off)
    def by_pid(s):
        return {o[0]:o for o in s.objs}

def monoscripts(sf):
    """pathid -> (class, namespace, assembly)"""
    out={}
    for pid,off,sz,cid in sf.objs:
        if cid!=115: continue
        r=sf.reader(off)
        try:
            name=r.astr(); r.i32(); r.o+=16
            cls=r.astr(); ns=r.astr(); asm=r.astr()
            out[pid]=(cls,ns,asm)
        except Exception: pass
    return out

def mb_scripts(sf):
    """monobehaviour pathid -> (script_fileid, script_pathid, name, body_offset)"""
    out={}
    for pid,off,sz,cid in sf.objs:
        if cid!=114: continue
        r=sf.reader(off)
        try:
            r.pptr()          # m_GameObject
            r.u8(); r.align(4)  # m_Enabled
            sp=r.pptr()       # m_Script
            nm=r.astr()
            out[pid]=(sp[0],sp[1],nm,r.o,off+sz)
        except Exception: pass
    return out
