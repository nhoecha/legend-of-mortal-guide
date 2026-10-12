"""Deserialize Unity MonoBehaviour bodies using field layouts recovered from .NET metadata."""
import struct
import clr

MANAGED = r"C:\Program Files (x86)\Steam\steamapps\common\LegendOfMortal\Mortal_Data\Managed"
ASMS = ['Mortal.Core.dll', 'Mortal.Story.dll', 'Mortal.Combat.dll', 'Mortal.Battle.dll',
        'Mortal.Free.dll', 'Assembly-CSharp.dll', 'OBB.Framework.dll', 'Fungus.dll']

PRIM = {'int': ('<i', 4), 'uint': ('<I', 4), 'float': ('<f', 4), 'long': ('<q', 8),
        'ulong': ('<Q', 8), 'double': ('<d', 8), 'short': ('<h', 2), 'ushort': ('<H', 2),
        'sbyte': ('<b', 1), 'byte': ('<B', 1), 'bool': ('<?', 1), 'char': ('<H', 2)}
SMALL = {'bool', 'byte', 'sbyte', 'short', 'ushort', 'char'}

# Unity built-in value types -> list of (name, primitive)
BUILTIN = {
    'UnityEngine.Vector2': [('x', 'float'), ('y', 'float')],
    'UnityEngine.Vector3': [('x', 'float'), ('y', 'float'), ('z', 'float')],
    'UnityEngine.Vector4': [('x', 'float'), ('y', 'float'), ('z', 'float'), ('w', 'float')],
    'UnityEngine.Quaternion': [('x', 'float'), ('y', 'float'), ('z', 'float'), ('w', 'float')],
    'UnityEngine.Color': [('r', 'float'), ('g', 'float'), ('b', 'float'), ('a', 'float')],
    'UnityEngine.Color32': [('r', 'byte'), ('g', 'byte'), ('b', 'byte'), ('a', 'byte')],
    'UnityEngine.Rect': [('x', 'float'), ('y', 'float'), ('w', 'float'), ('h', 'float')],
    'UnityEngine.Vector2Int': [('x', 'int'), ('y', 'int')],
    'UnityEngine.Vector3Int': [('x', 'int'), ('y', 'int'), ('z', 'int')],
    'UnityEngine.Bounds': [('cx', 'float'), ('cy', 'float'), ('cz', 'float'),
                           ('ex', 'float'), ('ey', 'float'), ('ez', 'float')],
    'UnityEngine.LayerMask': [('mask', 'int')],
}

UNITY_OBJECT_BASES = {'UnityEngine.Object', 'UnityEngine.ScriptableObject', 'UnityEngine.MonoBehaviour',
                      'UnityEngine.Component', 'UnityEngine.Behaviour', 'UnityEngine.GameObject',
                      'UnityEngine.Sprite', 'UnityEngine.Texture2D', 'UnityEngine.Transform',
                      'UnityEngine.AudioClip', 'UnityEngine.Material', 'UnityEngine.Texture',
                      'UnityEngine.Shader', 'UnityEngine.Mesh', 'UnityEngine.AnimationClip'}


def _subst(td, sub):
    if not isinstance(td, dict):
        return td
    if td.get('k') == 'var':
        return sub.get(td['n'], {'k': 'int'})
    t = dict(td)
    if 'elem' in t:
        t['elem'] = _subst(t['elem'], sub)
    if 'base' in t:
        t['base'] = _subst(t['base'], sub)
    if 'args' in t:
        t['args'] = [_subst(a, sub) for a in t['args']]
    return t


class World:
    """All game assemblies, with type lookup across them."""

    def __init__(self, asms=ASMS):
        import os
        self.metas = {}
        for a in asms:
            p = os.path.join(MANAGED, a)
            if os.path.exists(p):
                try:
                    self.metas[a] = clr.Meta(p)
                except Exception as e:
                    print('skip', a, e)
        self._attr_cache = {}
        self._layout_cache = {}

    def find(self, name):
        """-> (meta, typedef_row) for a full or short type name"""
        for a, m in self.metas.items():
            if name in m.types:
                return m, m.types[name]
        return None, None

    def field_attrs(self, m):
        """field row -> set of attribute type names (cached per assembly)"""
        key = id(m)
        if key in self._attr_cache:
            return self._attr_cache[key]
        out = {}
        for i in range(1, m.nrows(0x0c) + 1):
            r = m.row(0x0c, i)
            pt, pidx = m.coded('HasCustomAttribute', r['Parent'])
            if pt != 4:
                continue
            tt, tidx = m.coded('CustomAttributeType', r['Type'])
            nm = '?'
            if tt == 0x0a:      # MemberRef
                mr = m.row(0x0a, tidx)
                ct, cidx = m.coded('MemberRefParent', mr['Class'])
                if ct == 1:
                    nm = m.typeref_name(cidx)
                elif ct == 2:
                    nm = m.typedef_name(cidx)
            elif tt == 6:       # MethodDef -> find owning typedef
                nm = m.method_owner(tidx)
            out.setdefault(pidx, set()).add(nm)
        self._attr_cache[key] = out
        return out

    # ---------- layout ----------
    def layout(self, meta, ti, _depth=0, subst=None):
        """[(fieldname, typedesc)] in Unity serialization order (base first)"""
        key = (id(meta), ti, tuple(sorted((k, str(v)) for k, v in (subst or {}).items())))
        if key in self._layout_cache:
            return self._layout_cache[key]
        out = []
        base = meta.base_of(ti)
        if base and base[2] not in UNITY_OBJECT_BASES and base[2] not in (
                'System.Object', 'System.ValueType', 'System.Enum'):
            if base[0] == 'def':
                out += self.layout(meta, base[1], _depth + 1, subst)
            else:
                bm, bti = self.find(base[2])
                if bm is not None:
                    bsub = None
                    if base[0] == 'spec' and len(base) > 3 and base[3]:
                        bsub = {i: a for i, a in enumerate(base[3])}
                    out += self.layout(bm, bti, _depth + 1, bsub)
        attrs = self.field_attrs(meta)
        for nm, flags, sig, fi in meta.fields_of(ti):
            if flags & 0x0010 or flags & 0x0040:      # static / literal
                continue
            if flags & 0x0080:                        # NotSerialized
                continue
            acc = flags & 0x0007
            a = attrs.get(fi, set())
            if any('NonSerialized' in x for x in a):
                continue
            is_pub = acc == 0x0006
            has_sf = any('SerializeField' in x for x in a)
            if not (is_pub or has_sf):
                continue
            td = meta.parse_field_sig(sig)
            if subst:
                td = _subst(td, subst)
            out.append((nm, td))
        self._layout_cache[key] = out
        return out

    def enum_underlying(self, meta, ti):
        for nm, flags, sig, fi in meta.fields_of(ti):
            if flags & 0x0010 == 0:      # instance field = value__
                return meta.parse_field_sig(sig).get('k', 'int')
        return 'int'

    def is_enum(self, meta, ti):
        b = meta.base_of(ti)
        return bool(b) and b[2] == 'System.Enum'

    def is_unity_object(self, meta, ti, depth=0):
        b = meta.base_of(ti)
        if not b or depth > 12:
            return False
        if b[2] in UNITY_OBJECT_BASES or b[2].startswith('UnityEngine.'):
            return True
        if b[0] == 'def':
            return self.is_unity_object(meta, b[1], depth + 1)
        bm, bti = self.find(b[2])
        if bm is not None:
            return self.is_unity_object(bm, bti, depth + 1)
        return False


class Reader:
    def __init__(self, data, off, end):
        self.d = data
        self.o = off
        self.end = end

    def align(self):
        self.o = (self.o + 3) & ~3

    def prim(self, k):
        f, n = PRIM[k]
        v = struct.unpack_from(f, self.d, self.o)[0]
        self.o += n
        if k in SMALL:
            self.align()
        return v

    def string(self):
        L = struct.unpack_from('<i', self.d, self.o)[0]
        self.o += 4
        b = self.d[self.o:self.o + L]
        self.o += L
        self.align()
        return b.decode('utf-8', 'replace')

    def pptr(self):
        fid = struct.unpack_from('<i', self.d, self.o)[0]
        pid = struct.unpack_from('<q', self.d, self.o + 4)[0]
        self.o += 12
        return (fid, pid)


class Deser:
    def __init__(self, world):
        self.w = world

    def read_type(self, r, td, meta):
        k = td['k']
        if k in PRIM:
            return r.prim(k)
        if k == 'string':
            return r.string()
        if k == 'array':
            n = struct.unpack_from('<i', r.d, r.o)[0]
            r.o += 4
            el = td['elem']
            out = [self.read_type(r, el, meta) for _ in range(n)]
            if el.get('k') in SMALL:
                r.align()
            return out
        if k == 'generic':
            b = td['base']
            nm = b.get('name', '')
            if nm.startswith('System.Collections.Generic.List'):
                return self.read_type(r, {'k': 'array', 'elem': td['args'][0]}, meta)
            return None
        if k in ('class', 'value'):
            nm = td['name']
            if nm in BUILTIN:
                return {a: r.prim(b) for a, b in BUILTIN[nm]}
            if nm == 'System.String':
                return r.string()
            m2, ti = self.w.find(nm)
            if m2 is None:
                if nm.startswith('UnityEngine.'):
                    return r.pptr()
                raise KeyError('unknown type ' + nm)
            if self.w.is_enum(m2, ti):
                return r.prim(self.w.enum_underlying(m2, ti))
            if self.w.is_unity_object(m2, ti):
                return r.pptr()
            return self.read_obj(r, m2, ti)
        raise KeyError('unhandled ' + str(td))

    def read_obj(self, r, meta, ti):
        out = {}
        for nm, td in self.w.layout(meta, ti):
            out[nm] = self.read_type(r, td, meta)
        return out

    def read(self, data, off, end, typename):
        m, ti = self.w.find(typename)
        if m is None:
            raise KeyError(typename)
        r = Reader(data, off, end)
        v = self.read_obj(r, m, ti)
        return v, r.o, end
