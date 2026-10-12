"""Legend of Mortal (활협전) game-data index: assets, PPtr resolution, typed deserialization."""
import os, re, struct, collections
import usf2, unity_de

D = r"C:\Program Files (x86)\Steam\steamapps\common\LegendOfMortal\Mortal_Data"

ASSET_FILES = ['globalgamemanagers.assets', 'resources.assets',
               'sharedassets0.assets', 'sharedassets1.assets', 'sharedassets2.assets',
               'sharedassets3.assets', 'sharedassets5.assets', 'sharedassets6.assets'] + \
              [f'level{i}' for i in range(10)]


class Game:
    def __init__(self):
        self.w = unity_de.World()
        self.de = unity_de.Deser(self.w)
        self.sf = {}
        for f in ASSET_FILES:
            p = os.path.join(D, f)
            if os.path.exists(p):
                self.sf[f] = usf2.SF(p)
        # MonoScript table lives in globalgamemanagers.assets
        self.ms = usf2.monoscripts(self.sf['globalgamemanagers.assets'])
        self.mb = {}        # file -> {pathid: (fid, spid, name, bodyoff, end)}
        self.cls = {}       # (file, pathid) -> class name
        self.byclass = collections.defaultdict(list)   # class -> [(file, pathid)]
        for f, sf in self.sf.items():
            mb = usf2.mb_scripts(sf)
            self.mb[f] = mb
            for pid, (fid, spid, nm, bo, end) in mb.items():
                c = self._script_class(f, fid, spid)
                self.cls[(f, pid)] = c
                self.byclass[c].append((f, pid))
        self._cache = {}
        self.loc = {}
        self._load_loc()

    def _script_class(self, f, fid, spid):
        if fid == 0:
            ms = usf2.monoscripts(self.sf[f])
            return ms.get(spid, ('?',))[0]
        ext = self.sf[f].externals
        if fid - 1 < len(ext):
            tgt = ext[fid - 1]
            if tgt == 'globalgamemanagers.assets':
                return self.ms.get(spid, ('?',))[0]
            if tgt in self.sf:
                return usf2.monoscripts(self.sf[tgt]).get(spid, ('?',))[0]
        return '?'

    def resolve(self, f, pptr):
        """(fileID, pathID) inside file f -> (targetfile, pathid) or None"""
        fid, pid = pptr
        if pid == 0:
            return None
        if fid == 0:
            return (f, pid)
        ext = self.sf[f].externals
        if fid - 1 < len(ext):
            tgt = ext[fid - 1]
            tgt = os.path.basename(tgt)
            if tgt in self.sf:
                return (tgt, pid)
        return None

    def name(self, ref):
        if not ref:
            return None
        f, pid = ref
        e = self.mb.get(f, {}).get(pid)
        return e[2] if e else None

    def classof(self, ref):
        return self.cls.get(ref) if ref else None

    def obj(self, ref, typename=None):
        """deserialize the MonoBehaviour at ref"""
        if not ref:
            return None
        if ref in self._cache:
            return self._cache[ref]
        f, pid = ref
        e = self.mb.get(f, {}).get(pid)
        if not e:
            return None
        fid, spid, nm, bo, end = e
        tn = typename or self.cls.get(ref)
        if not tn or tn == '?':
            return None
        try:
            v, pos, endp = self.de.read(self.sf[f].data, bo, end, tn)
            v['__name'] = nm
            v['__ref'] = ref
            v['__exact'] = (pos == endp)
        except Exception as ex:
            v = {'__name': nm, '__ref': ref, '__error': f'{type(ex).__name__}: {ex}'}
        self._cache[ref] = v
        return v

    def all_of(self, clsname, typename=None):
        for ref in self.byclass.get(clsname, []):
            yield ref, self.obj(ref, typename)

    # ---------- localization ----------
    def _load_loc(self):
        """Korean localization from the CSV TextAssets."""
        for _fn, sf in self.sf.items():
          for pid, off, sz, cid in sf.objs:
            if cid != 49:
                continue
            r = sf.reader(off)
            nm = r.astr()
            L = r.u32()
            body = sf.data[r.o:r.o + L].decode('utf-8', 'replace')
            head = body[:4000]
            if len(re.findall(r'[가-힣]', head)) < 20:
                continue
            for line in body.split('\r\n'):
                if ' = ' not in line or line.startswith('//'):
                    continue
                k, _, v = line.partition(' = ')
                self.loc.setdefault(k.strip().lstrip('\ufeff'), v)

    def t(self, key, default=None):
        return self.loc.get(key, default)
