import sys, dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.error import MethodBodyFormatError
from dncil.clr.token import Token, StringToken, InvalidToken
from dncil.cil.body.reader import CilMethodBodyReaderBase

class R(CilMethodBodyReaderBase):
    def __init__(self, pe, row):
        self.pe = pe; self.offset = pe.get_offset_from_rva(row.Rva)
    def read(self, n):
        d = self.pe.get_data(self.pe.get_rva_from_offset(self.offset), n); self.offset += n; return d
    def tell(self): return self.offset
    def seek(self, o): self.offset = o; return o

path, needles = sys.argv[1], sys.argv[2:]
pe = dnfile.dnPE(path)
md = pe.net.mdtables
types = list(md.TypeDef)
def owner(mi):
    # method index (1-based) -> type name
    name = '?'
    for i, t in enumerate(types):
        start = t.MethodList[0].row_index if t.MethodList else None
        if t.MethodList and any(m.row_index == mi for m in t.MethodList):
            return f'{t.TypeNamespace}.{t.TypeName}'
    return name
def us(tok):
    try: return pe.net.user_strings.get(tok.rid).value
    except Exception: return None
def member(tok):
    try:
        t = tok.table; rid = tok.rid
        if t == 0x06:
            m = md.MethodDef.rows[rid-1]; return f'{owner(rid)}::{m.Name}'
        if t == 0x0A:
            m = md.MemberRef.rows[rid-1]
            cls = m.Class.row
            cn = getattr(cls, 'TypeName', None) or getattr(cls, 'Name', '?')
            return f'{cn}::{m.Name}'
        if t == 0x04:
            f = md.Field.rows[rid-1]; return f'field {f.Name}'
        if t in (0x01, 0x02):
            r = (md.TypeRef if t == 1 else md.TypeDef).rows[rid-1]; return f'type {r.TypeName}'
    except Exception as e:
        return f'tok {tok}'
    return f'tok {tok}'
hits = []
bodies = {}
for i, row in enumerate(md.MethodDef, 1):
    if not row.Rva: continue
    try: body = CilMethodBody(R(pe, row))
    except MethodBodyFormatError: continue
    bodies[i] = (row, body)
    for ins in body.instructions:
        if ins.opcode.name == 'ldstr':
            s = us(ins.operand) if isinstance(ins.operand, StringToken) else None
            if s in needles: hits.append((i, s))
for i, s in hits:
    row, body = bodies[i]
    print(f'\n===== {owner(i)}::{row.Name}   (ldstr {s!r})')
    for ins in body.instructions:
        op = ins.operand
        if isinstance(op, StringToken): txt = repr(us(op))
        elif isinstance(op, Token): txt = member(op)
        else: txt = '' if op is None else str(op)
        print(f'   {ins.offset:04x} {ins.opcode.name:12} {txt}')
# who calls those methods
targets = {i for i, _ in hits}
print('\n===== callers')
for j, (row, body) in bodies.items():
    for ins in body.instructions:
        op = ins.operand
        if isinstance(op, Token) and not isinstance(op, StringToken) and op.table == 0x06 and op.rid in targets and ins.opcode.name in ('call', 'callvirt', 'ldftn', 'newobj'):
            print(f'   {owner(j)}::{row.Name} -> {member(op)} [{ins.opcode.name}]')
