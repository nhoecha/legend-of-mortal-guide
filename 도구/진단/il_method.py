import sys, dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.error import MethodBodyFormatError
from dncil.clr.token import Token, StringToken
from dncil.cil.body.reader import CilMethodBodyReaderBase
class R(CilMethodBodyReaderBase):
    def __init__(self, pe, row): self.pe = pe; self.offset = pe.get_offset_from_rva(row.Rva)
    def read(self, n):
        d = self.pe.get_data(self.pe.get_rva_from_offset(self.offset), n); self.offset += n; return d
    def tell(self): return self.offset
    def seek(self, o): self.offset = o; return o
path, tname, mname = sys.argv[1], sys.argv[2], sys.argv[3]
pe = dnfile.dnPE(path); md = pe.net.mdtables
own = {}
for t in md.TypeDef:
    for m in t.MethodList: own[m.row_index] = f'{t.TypeNamespace}.{t.TypeName}'
def member(tok):
    try:
        if tok.table == 0x06: return f'{own.get(tok.rid)}::{md.MethodDef.rows[tok.rid-1].Name}'
        if tok.table == 0x0A:
            m = md.MemberRef.rows[tok.rid-1]; c = m.Class.row
            return f'{getattr(c,"TypeName",None) or getattr(c,"Name","?")}::{m.Name}'
        if tok.table == 0x04: return f'field {md.Field.rows[tok.rid-1].Name}'
        if tok.table == 0x2B:
            return 'methodspec'
    except Exception: pass
    return str(tok)
for t in md.TypeDef:
    if tname and str(t.TypeName) != tname: continue
    names = [str(m.row.Name) for m in t.MethodList]
    if mname == '?': print(f'{t.TypeNamespace}.{t.TypeName}:', names); continue
    for m in t.MethodList:
        if str(m.row.Name) != mname or not m.row.Rva: continue
        print(f'===== {t.TypeNamespace}.{t.TypeName}::{m.row.Name}')
        try: body = CilMethodBody(R(pe, m.row))
        except MethodBodyFormatError as e: print('  (unreadable)'); continue
        for ins in body.instructions:
            op = ins.operand
            if isinstance(op, StringToken): txt = repr(pe.net.user_strings.get(op.rid).value)
            elif isinstance(op, Token): txt = member(op)
            else: txt = '' if op is None else str(op)
            print(f'   {ins.offset:04x} {ins.opcode.name:12} {txt}')
