"""Minimal .NET (ECMA-335) metadata reader: tables, strings, blobs, field signatures."""
import struct

CODED = {
 'TypeDefOrRef': (2, [2, 1, 0x1b]),
 'HasConstant': (2, [4, 8, 0x17]),
 'HasCustomAttribute': (5, [6, 4, 1, 2, 8, 9, 0x0a, 0, 0x0e, 0x17, 0x14, 0x11,
                            0x1a, 0x1b, 0x20, 0x23, 0x26, 0x27, 0x28, 0x2a, 0x2c, 0x2b]),
 'HasFieldMarshal': (1, [4, 8]),
 'HasDeclSecurity': (2, [2, 6, 0x20]),
 'MemberRefParent': (3, [2, 1, 0x1a, 6, 0x1b]),
 'HasSemantics': (1, [0x14, 0x17]),
 'MethodDefOrRef': (1, [6, 0x0a]),
 'MemberForwarded': (1, [4, 6]),
 'Implementation': (2, [0x26, 0x23, 0x27]),
 'CustomAttributeType': (3, [-1, -1, 6, 0x0a, -1]),
 'ResolutionScope': (2, [0, 0x1a, 0x23, 1]),
 'TypeOrMethodDef': (1, [2, 6]),
}

S, G, B = 'S', 'G', 'B'

SCHEMA = {
 0x00: [('Generation', 2), ('Name', S), ('Mvid', G), ('EncId', G), ('EncBaseId', G)],
 0x01: [('ResolutionScope', 'ResolutionScope'), ('Name', S), ('Namespace', S)],
 0x02: [('Flags', 4), ('Name', S), ('Namespace', S), ('Extends', 'TypeDefOrRef'),
        ('FieldList', 'T04'), ('MethodList', 'T06')],
 0x03: [('Field', 'T04')],
 0x04: [('Flags', 2), ('Name', S), ('Signature', B)],
 0x05: [('Method', 'T06')],
 0x06: [('RVA', 4), ('ImplFlags', 2), ('Flags', 2), ('Name', S), ('Signature', B), ('ParamList', 'T08')],
 0x07: [('Param', 'T08')],
 0x08: [('Flags', 2), ('Sequence', 2), ('Name', S)],
 0x09: [('Class', 'T02'), ('Interface', 'TypeDefOrRef')],
 0x0a: [('Class', 'MemberRefParent'), ('Name', S), ('Signature', B)],
 0x0b: [('Type', 1), ('Pad', 1), ('Parent', 'HasConstant'), ('Value', B)],
 0x0c: [('Parent', 'HasCustomAttribute'), ('Type', 'CustomAttributeType'), ('Value', B)],
 0x0d: [('Parent', 'HasFieldMarshal'), ('NativeType', B)],
 0x0e: [('Action', 2), ('Parent', 'HasDeclSecurity'), ('PermissionSet', B)],
 0x0f: [('PackingSize', 2), ('ClassSize', 4), ('Parent', 'T02')],
 0x10: [('Offset', 4), ('Field', 'T04')],
 0x11: [('Signature', B)],
 0x12: [('Parent', 'T02'), ('EventList', 'T14')],
 0x13: [('Event', 'T14')],
 0x14: [('EventFlags', 2), ('Name', S), ('EventType', 'TypeDefOrRef')],
 0x15: [('Parent', 'T02'), ('PropertyList', 'T17')],
 0x16: [('Property', 'T17')],
 0x17: [('Flags', 2), ('Name', S), ('Type', B)],
 0x18: [('Semantics', 2), ('Method', 'T06'), ('Association', 'HasSemantics')],
 0x19: [('Class', 'T02'), ('MethodBody', 'MethodDefOrRef'), ('MethodDeclaration', 'MethodDefOrRef')],
 0x1a: [('Name', S)],
 0x1b: [('Signature', B)],
 0x1c: [('MappingFlags', 2), ('MemberForwarded', 'MemberForwarded'), ('ImportName', S), ('ImportScope', 'T1a')],
 0x1d: [('RVA', 4), ('Field', 'T04')],
 0x1e: [('Token', 4), ('FuncCode', 4)],
 0x1f: [('Token', 4)],
 0x20: [('HashAlgId', 4), ('Major', 2), ('Minor', 2), ('Build', 2), ('Rev', 2),
        ('Flags', 4), ('PublicKey', B), ('Name', S), ('Culture', S)],
 0x21: [('Processor', 4)],
 0x22: [('OSPlatformID', 4), ('OSMajor', 4), ('OSMinor', 4)],
 0x23: [('Major', 2), ('Minor', 2), ('Build', 2), ('Rev', 2), ('Flags', 4),
        ('PublicKeyOrToken', B), ('Name', S), ('Culture', S), ('HashValue', B)],
 0x24: [('Processor', 4), ('AssemblyRef', 'T23')],
 0x25: [('OSPlatformID', 4), ('OSMajor', 4), ('OSMinor', 4), ('AssemblyRef', 'T23')],
 0x26: [('Flags', 4), ('Name', S), ('HashValue', B)],
 0x27: [('Flags', 4), ('TypeDefId', 4), ('Name', S), ('Namespace', S), ('Implementation', 'Implementation')],
 0x28: [('Offset', 4), ('Flags', 4), ('Name', S), ('Implementation', 'Implementation')],
 0x29: [('NestedClass', 'T02'), ('EnclosingClass', 'T02')],
 0x2a: [('Number', 2), ('Flags', 2), ('Owner', 'TypeOrMethodDef'), ('Name', S)],
 0x2b: [('Method', 'MethodDefOrRef'), ('Instantiation', B)],
 0x2c: [('Owner', 'T2a'), ('Constraint', 'TypeDefOrRef')],
}

# ELEMENT_TYPE
ET = {0x01: 'void', 0x02: 'bool', 0x03: 'char', 0x04: 'sbyte', 0x05: 'byte',
      0x06: 'short', 0x07: 'ushort', 0x08: 'int', 0x09: 'uint', 0x0a: 'long',
      0x0b: 'ulong', 0x0c: 'float', 0x0d: 'double', 0x0e: 'string', 0x18: 'IntPtr',
      0x19: 'UIntPtr', 0x1c: 'object'}


class Meta:
    def __init__(self, path):
        d = open(path, 'rb').read()
        self.d = d
        self.path = path
        pe = struct.unpack_from('<I', d, 0x3c)[0]
        nsec = struct.unpack_from('<H', d, pe + 6)[0]
        optsz = struct.unpack_from('<H', d, pe + 20)[0]
        opt = pe + 24
        magic = struct.unpack_from('<H', d, opt)[0]
        ddoff = opt + (96 if magic == 0x10b else 112)
        cli_rva = struct.unpack_from('<I', d, ddoff + 14 * 8)[0]
        secs = []
        so = opt + optsz
        for i in range(nsec):
            b = so + i * 40
            vsz, va, rsz, ra = struct.unpack_from('<IIII', d, b + 8)
            secs.append((va, vsz, ra, rsz))
        self.secs = secs
        cli = self.rva(cli_rva)
        md_rva = struct.unpack_from('<I', d, cli + 8)[0]
        md = self.rva(md_rva)
        self.mdoff = md
        vlen = struct.unpack_from('<I', d, md + 12)[0]
        p = md + 16 + ((vlen + 3) // 4) * 4
        p += 2
        nstreams = struct.unpack_from('<H', d, p)[0]
        p += 2
        self.streams = {}
        for _ in range(nstreams):
            off, size = struct.unpack_from('<II', d, p)
            p += 8
            e = d.index(b'\x00', p)
            nm = d[p:e].decode()
            p = e + 1
            p = md + ((p - md + 3) // 4) * 4
            self.streams[nm] = (md + off, size)
        self.strings = self.streams.get('#Strings')
        self.blob = self.streams.get('#Blob')
        self._tables()
        self._typedef_index()

    def rva(self, r):
        for va, vsz, ra, rsz in self.secs:
            if va <= r < va + max(vsz, rsz):
                return ra + (r - va)
        raise KeyError(hex(r))

    def s(self, i):
        o = self.strings[0] + i
        e = self.d.index(b'\x00', o)
        return self.d[o:e].decode('utf-8', 'replace')

    def blobv(self, i):
        o = self.blob[0] + i
        b0 = self.d[o]
        if b0 & 0x80 == 0:
            L = b0; o += 1
        elif b0 & 0xc0 == 0x80:
            L = ((b0 & 0x3f) << 8) | self.d[o + 1]; o += 2
        else:
            L = ((b0 & 0x1f) << 24) | (self.d[o + 1] << 16) | (self.d[o + 2] << 8) | self.d[o + 3]; o += 4
        return self.d[o:o + L]

    def _tables(self):
        d = self.d
        o = self.streams['#~'][0]
        heapsz = d[o + 6]
        valid = struct.unpack_from('<Q', d, o + 8)[0]
        p = o + 24
        self.rows = {}
        for t in range(64):
            if valid >> t & 1:
                self.rows[t] = struct.unpack_from('<I', d, p)[0]
                p += 4
        self.sstr = 4 if heapsz & 1 else 2
        self.sguid = 4 if heapsz & 2 else 2
        self.sblob = 4 if heapsz & 4 else 2

        def colsize(c):
            if c == S: return self.sstr
            if c == G: return self.sguid
            if c == B: return self.sblob
            if isinstance(c, int): return c
            if len(c) == 3 and c[0] == 'T':
                return 4 if self.rows.get(int(c[1:], 16), 0) >= 65536 else 2
            bits, tabs = CODED[c]
            mx = max([self.rows.get(t, 0) for t in tabs if t >= 0] + [0])
            return 4 if mx >= (1 << (16 - bits)) else 2

        self.tab = {}
        for t in sorted(self.rows):
            cols = SCHEMA[t]
            sizes = [colsize(c) for _, c in cols]
            rowsz = sum(sizes)
            self.tab[t] = (p, rowsz, sizes, cols)
            p += rowsz * self.rows[t]

    def row(self, t, i):
        p, rowsz, sizes, cols = self.tab[t]
        o = p + (i - 1) * rowsz
        out = {}
        for (name, c), sz in zip(cols, sizes):
            out[name] = int.from_bytes(self.d[o:o + sz], 'little')
            o += sz
        return out

    def nrows(self, t):
        return self.rows.get(t, 0)

    def coded(self, c, v):
        bits, tabs = CODED[c]
        tag = v & ((1 << bits) - 1)
        idx = v >> bits
        return (tabs[tag] if tag < len(tabs) else -1), idx

    # ---------- higher level ----------
    def _typedef_index(self):
        self.types = {}      # full name -> row index
        self.typerow = {}    # row index -> (ns, name)
        for i in range(1, self.nrows(0x02) + 1):
            r = self.row(0x02, i)
            ns, nm = self.s(r['Namespace']), self.s(r['Name'])
            full = f'{ns}.{nm}' if ns else nm
            self.typerow[i] = (ns, nm, r)
            self.types.setdefault(full, i)
            self.types.setdefault(nm, i)
        self.nested = {}
        for i in range(1, self.nrows(0x29) + 1):
            r = self.row(0x29, i)
            self.nested[r['NestedClass']] = r['EnclosingClass']

    def typeref_name(self, i):
        r = self.row(0x01, i)
        ns, nm = self.s(r['Namespace']), self.s(r['Name'])
        return f'{ns}.{nm}' if ns else nm

    def typedef_name(self, i):
        ns, nm, _ = self.typerow[i]
        return f'{ns}.{nm}' if ns else nm

    def fields_of(self, ti):
        """list of (name, flags, sigblob) in declaration order"""
        r = self.typerow[ti][2]
        start = r['FieldList']
        if ti + 1 <= self.nrows(0x02):
            end = self.row(0x02, ti + 1)['FieldList']
        else:
            end = self.nrows(0x04) + 1
        out = []
        for fi in range(start, end):
            fr = self.row(0x04, fi)
            out.append((self.s(fr['Name']), fr['Flags'], self.blobv(fr['Signature']), fi))
        return out

    def base_of(self, ti):
        r = self.typerow[ti][2]
        t, idx = self.coded('TypeDefOrRef', r['Extends'])
        if idx == 0:
            return None
        if t == 2:
            return ('def', idx, self.typedef_name(idx))
        if t == 1:
            return ('ref', idx, self.typeref_name(idx))
        if t == 0x1b:
            blob = self.blobv(self.row(0x1b, idx)['Signature'])
            td = self.parse_type_sig(blob)
            if td.get('k') == 'generic':
                b = td['base']
                return ('spec', idx, b.get('name', '?'), td.get('args', []))
            return ('spec', idx, td.get('name', '?'), [])
        return ('spec', idx, '?', [])

    # ---------- signatures ----------
    def parse_field_sig(self, blob):
        p = [0]

        def u():
            b0 = blob[p[0]]
            if b0 & 0x80 == 0:
                p[0] += 1; return b0
            if b0 & 0xc0 == 0x80:
                v = ((b0 & 0x3f) << 8) | blob[p[0] + 1]; p[0] += 2; return v
            v = ((b0 & 0x1f) << 24) | (blob[p[0] + 1] << 16) | (blob[p[0] + 2] << 8) | blob[p[0] + 3]
            p[0] += 4
            return v

        def typ():
            e = blob[p[0]]; p[0] += 1
            if e in ET:
                return {'k': ET[e]}
            if e in (0x11, 0x12):  # VALUETYPE / CLASS
                tok = u()
                tag = tok & 3
                idx = tok >> 2
                if tag == 0:
                    nm = self.typedef_name(idx); kind = 'def'
                elif tag == 1:
                    nm = self.typeref_name(idx); kind = 'ref'
                else:
                    nm = '?'; kind = 'spec'
                return {'k': 'value' if e == 0x11 else 'class', 'name': nm, 'ref': kind, 'row': idx}
            if e == 0x1d:  # SZARRAY
                while blob[p[0]] in (0x1f, 0x20):  # modifiers
                    p[0] += 1; u()
                return {'k': 'array', 'elem': typ()}
            if e == 0x14:  # ARRAY
                el = typ(); u(); n = u()
                for _ in range(n): u()
                n2 = u()
                for _ in range(n2): u()
                return {'k': 'array', 'elem': el}
            if e == 0x15:  # GENERICINST
                base = typ()
                n = u()
                args = [typ() for _ in range(n)]
                return {'k': 'generic', 'base': base, 'args': args}
            if e == 0x13:  # VAR (generic type param)
                return {'k': 'var', 'n': u()}
            if e == 0x1e:  # MVAR
                return {'k': 'var', 'n': u()}
            if e in (0x1f, 0x20):  # CMOD
                u(); return typ()
            if e == 0x45:  # PINNED etc
                return typ()
            return {'k': f'et{e:#x}'}

        if blob[0] == 0x06:
            p[0] = 1
        else:
            p[0] = 0
        while blob[p[0]] in (0x1f, 0x20):
            p[0] += 1; u()
        return typ()

    def parse_type_sig(self, blob):
        return self.parse_field_sig(blob)

    def method_owner(self, mi):
        if not hasattr(self, '_mowner'):
            self._mowner = {}
            for i in range(1, self.nrows(0x02) + 1):
                r = self.row(0x02, i)
                start = r['MethodList']
                end = self.row(0x02, i + 1)['MethodList'] if i + 1 <= self.nrows(0x02) else self.nrows(0x06) + 1
                for k in range(start, end):
                    self._mowner[k] = i
        ti = self._mowner.get(mi)
        return self.typedef_name(ti) if ti else '?'
