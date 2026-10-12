# -*- coding: utf-8 -*-
"""Minimal reader for .NET Binary Formatter streams (MS-NRBF).

활협전의 회차 세이브(Save_*.dat)가 이 형식이다. 도감 진행도(Save_universe)만 게임이
JSON 으로도 써 주고, 회차 상태는 이 이진 형식뿐이라 직접 읽어야 한다.

읽기 전용이고 표준 라이브러리만 쓴다.

    import nrbf
    root = nrbf.load('Save_auto_free.dat')     # dict / list / 스칼라로 이루어진 나무
    root['GameSave']['CurrentYear']

클래스 인스턴스는 dict 로 나오며 '__class' 키에 타입 이름이 들어간다.
List<T> 와 배열은 파이썬 리스트가 된다. 순환 참조는 그대로 유지되므로
json.dumps 를 바로 걸지 말고 필요한 가지만 꺼내 쓴다.
"""
import struct

# --- record types ---
SERIALIZED_STREAM_HEADER = 0
CLASS_WITH_ID = 1
SYSTEM_CLASS_WITH_MEMBERS = 2
CLASS_WITH_MEMBERS = 3
SYSTEM_CLASS_WITH_MEMBERS_AND_TYPES = 4
CLASS_WITH_MEMBERS_AND_TYPES = 5
BINARY_OBJECT_STRING = 6
BINARY_ARRAY = 7
MEMBER_PRIMITIVE_TYPED = 8
MEMBER_REFERENCE = 9
OBJECT_NULL = 10
MESSAGE_END = 11
BINARY_LIBRARY = 12
OBJECT_NULL_MULTIPLE_256 = 13
OBJECT_NULL_MULTIPLE = 14
ARRAY_SINGLE_PRIMITIVE = 15
ARRAY_SINGLE_OBJECT = 16
ARRAY_SINGLE_STRING = 17

# --- binary type enum ---
BT_PRIMITIVE = 0
BT_STRING = 1
BT_OBJECT = 2
BT_SYSTEM_CLASS = 3
BT_CLASS = 4
BT_OBJECT_ARRAY = 5
BT_STRING_ARRAY = 6
BT_PRIMITIVE_ARRAY = 7

# 원시 타입: 코드 -> (struct 포맷, 바이트 수). None 은 특수 처리.
_PRIM = {
    1: ('?', 1), 2: ('B', 1), 6: ('d', 8), 7: ('<h', 2), 8: ('<i', 4), 9: ('<q', 8),
    10: ('b', 1), 11: ('<f', 4), 12: ('<q', 8), 13: ('<q', 8),
    14: ('<H', 2), 15: ('<I', 4), 16: ('<Q', 8),
}


class _Ref:
    """나중에 메울 자리. 참조가 아직 안 읽힌 객체를 가리킬 때 쓴다."""
    __slots__ = ('id',)

    def __init__(self, i):
        self.id = i


class Reader:
    def __init__(self, data):
        self.b = data
        self.o = 0
        self.objects = {}      # id -> 값
        self.classes = {}      # metadata id -> (이름, 멤버이름들, 멤버타입들)
        self.libs = {}
        self.pending = []      # (컨테이너, 키, _Ref) — 다 읽고 나서 메운다

    # ---------- 낮은 수준 ----------
    def u8(self):
        v = self.b[self.o]
        self.o += 1
        return v

    def i32(self):
        v = struct.unpack_from('<i', self.b, self.o)[0]
        self.o += 4
        return v

    def prim(self, code):
        if code == 18:                       # String
            return self.string()
        if code == 3:                        # Char (UTF-8 한 글자)
            start = self.o
            for n in (1, 2, 3, 4):
                try:
                    s = self.b[start:start + n].decode('utf-8')
                except UnicodeDecodeError:
                    continue
                self.o = start + n
                return s
            raise ValueError('bad char')
        if code == 5:                        # Decimal 은 문자열로 실린다
            return self.string()
        if code == 17:                       # Null
            return None
        fmt, n = _PRIM[code]
        v = struct.unpack_from(fmt, self.b, self.o)[0]
        self.o += n
        return v

    def string(self):
        n = shift = 0
        while True:
            c = self.u8()
            n |= (c & 0x7f) << shift
            if not c & 0x80:
                break
            shift += 7
        s = self.b[self.o:self.o + n].decode('utf-8', 'replace')
        self.o += n
        return s

    # ---------- 클래스 서술 ----------
    def class_info(self):
        oid = self.i32()
        name = self.string()
        cnt = self.i32()
        members = [self.string() for _ in range(cnt)]
        return oid, name, members

    def member_types(self, count):
        kinds = [self.u8() for _ in range(count)]
        extra = []
        for k in kinds:
            if k in (BT_PRIMITIVE, BT_PRIMITIVE_ARRAY):
                extra.append(self.u8())
            elif k == BT_SYSTEM_CLASS:
                extra.append(self.string())
            elif k == BT_CLASS:
                extra.append((self.string(), self.i32()))
            else:
                extra.append(None)
        return list(zip(kinds, extra))

    # ---------- 값 ----------
    def value(self, kind, extra):
        if kind == BT_PRIMITIVE:
            return self.prim(extra)
        return self.record()

    def store(self, oid, val):
        if oid:
            self.objects[oid] = val
        return val

    def read_class(self, oid, name, members, types):
        obj = {'__class': name}
        self.store(oid, obj)
        for m, (k, extra) in zip(members, types):
            v = self.value(k, extra)
            obj[m] = v
            if isinstance(v, _Ref):
                self.pending.append((obj, m, v))
        return obj

    def record(self):
        t = self.u8()
        if t == OBJECT_NULL:
            return None
        if t == MEMBER_REFERENCE:
            i = self.i32()
            return self.objects.get(i, _Ref(i))
        if t == BINARY_OBJECT_STRING:
            oid = self.i32()
            return self.store(oid, self.string())
        if t == MEMBER_PRIMITIVE_TYPED:
            return self.prim(self.u8())
        if t == BINARY_LIBRARY:
            lid = self.i32()
            self.libs[lid] = self.string()
            return self.record()
        if t in (CLASS_WITH_MEMBERS_AND_TYPES, SYSTEM_CLASS_WITH_MEMBERS_AND_TYPES):
            oid, name, members = self.class_info()
            types = self.member_types(len(members))
            if t == CLASS_WITH_MEMBERS_AND_TYPES:
                self.i32()                    # LibraryId
            self.classes[oid] = (name, members, types)
            return self.read_class(oid, name, members, types)
        if t in (CLASS_WITH_MEMBERS, SYSTEM_CLASS_WITH_MEMBERS):
            oid, name, members = self.class_info()
            if t == CLASS_WITH_MEMBERS:
                self.i32()
            # 타입 정보가 없으면 값을 레코드로 읽는 수밖에 없다
            types = [(BT_OBJECT, None)] * len(members)
            self.classes[oid] = (name, members, types)
            return self.read_class(oid, name, members, types)
        if t == CLASS_WITH_ID:
            oid = self.i32()
            meta = self.i32()
            name, members, types = self.classes[meta]
            return self.read_class(oid, name, members, types)
        if t == ARRAY_SINGLE_PRIMITIVE:
            oid = self.i32()
            n = self.i32()
            code = self.u8()
            return self.store(oid, [self.prim(code) for _ in range(n)])
        if t in (ARRAY_SINGLE_OBJECT, ARRAY_SINGLE_STRING):
            oid = self.i32()
            n = self.i32()
            return self.store(oid, self.items(n))
        if t == BINARY_ARRAY:
            oid = self.i32()
            atype = self.u8()
            rank = self.i32()
            lens = [self.i32() for _ in range(rank)]
            if atype in (3, 4, 5):
                for _ in range(rank):
                    self.i32()
            kind = self.u8()
            extra = None
            if kind in (BT_PRIMITIVE, BT_PRIMITIVE_ARRAY):
                extra = self.u8()
            elif kind == BT_SYSTEM_CLASS:
                extra = self.string()
            elif kind == BT_CLASS:
                extra = (self.string(), self.i32())
            total = 1
            for x in lens:
                total *= x
            if kind == BT_PRIMITIVE:
                return self.store(oid, [self.prim(extra) for _ in range(total)])
            return self.store(oid, self.items(total))
        if t == MESSAGE_END:
            return None
        raise ValueError(f'알 수 없는 레코드 {t} (offset {self.o - 1})')

    def read_stream(self):
        """스트림은 레코드의 나열이다. 루트가 앞선 레코드를 앞으로 참조할 수 있으므로
        MessageEnd 까지 전부 읽은 뒤에 루트를 꺼낸다."""
        if self.b[self.o] != SERIALIZED_STREAM_HEADER:
            raise ValueError('NRBF 헤더가 아니다')
        self.o += 1
        root_id = self.i32()
        self.i32(); self.i32(); self.i32()
        while self.o < len(self.b):
            if self.b[self.o] == MESSAGE_END:
                break
            self.record()
        return self.objects.get(root_id)

    def items(self, n):
        """배열 원소들. null 반복 레코드가 섞여 나온다."""
        out = []
        while len(out) < n:
            save = self.o
            t = self.u8()
            if t == OBJECT_NULL_MULTIPLE_256:
                out += [None] * self.u8()
                continue
            if t == OBJECT_NULL_MULTIPLE:
                out += [None] * self.i32()
                continue
            self.o = save
            v = self.record()
            out.append(v)
            if isinstance(v, _Ref):
                self.pending.append((out, len(out) - 1, v))
        return out


def _resolve(r):
    for holder, key, ref in r.pending:
        holder[key] = r.objects.get(ref.id)


def _unwrap(node, seen=None):
    """List<T> 는 _items/_size 를 가진 클래스로 실린다. 파이썬 리스트로 바꾼다."""
    seen = seen if seen is not None else set()
    if id(node) in seen:
        return node
    if isinstance(node, dict):
        seen.add(id(node))
        cls = node.get('__class') or ''
        if cls.startswith('System.Collections.Generic.List`1') and '_items' in node:
            n = node.get('_size') or 0
            items = node.get('_items') or []
            return [_unwrap(x, seen) for x in items[:n]]
        for k, v in list(node.items()):
            if k != '__class':
                node[k] = _unwrap(v, seen)
        return node
    if isinstance(node, list):
        seen.add(id(node))
        return [_unwrap(x, seen) for x in node]
    return node


def loads(data):
    r = Reader(data)
    root = r.read_stream()
    _resolve(r)
    return _unwrap(root)


def load(path):
    with open(path, 'rb') as f:
        return loads(f.read())
