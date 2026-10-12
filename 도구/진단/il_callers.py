import sys, os, dnfile
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
names = set(sys.argv[1:])
for dll in [f for f in os.listdir('.') if f.startswith('Mortal.') or f == 'Assembly-CSharp.dll']:
    pe = dnfile.dnPE(dll); md = pe.net.mdtables
    own = {}
    for t in md.TypeDef:
        for m in t.MethodList: own[m.row_index] = f'{t.TypeName}'
    for i, row in enumerate(md.MethodDef, 1):
        if not row.Rva: continue
        try: body = CilMethodBody(R(pe, row))
        except Exception: continue
        for ins in body.instructions:
            op = ins.operand
            if isinstance(op, Token) and not isinstance(op, StringToken) and ins.opcode.name in ('call', 'callvirt', 'ldftn', 'ldvirtftn'):
                tn = None
                try:
                    if op.table == 0x06: tn = (own.get(op.rid), str(md.MethodDef.rows[op.rid-1].Name))
                    elif op.table == 0x0A:
                        m = md.MemberRef.rows[op.rid-1]; c = m.Class.row
                        tn = (str(getattr(c, 'TypeName', '') or ''), str(m.Name))
                except Exception: pass
                if tn and tn[1] in names:
                    print(f'{dll}: {own.get(i)}::{row.Name}  --{ins.opcode.name}-->  {tn[0]}::{tn[1]}')
