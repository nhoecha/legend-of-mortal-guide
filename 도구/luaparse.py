"""Parse the game's generated Lua story scripts into a branch tree."""
import re, os

RE_CP = re.compile(r'local\s+(\w+)\s*=\s*checkpointmanager\.(Switch|Dice|Condition|Position)\("([^"]*)"')
RE_IF = re.compile(r'^\s*(if|elseif)\s+(.*?)\s+then\s*$')
RE_ELSE = re.compile(r'^\s*else\s*$')
RE_END = re.compile(r'^\s*end\s*$')
RE_SCENE = re.compile(r'luamanager\.ChangeScene\("(\w+)",\s*"([^"]*)"')
RE_NEXT = re.compile(
    r'luamanager\.(SetNextScript|SetCurrentStoryScript|SetCurrentTravelScript|SetTempScript)'
    r'\(\s*(?:"([^"]*)"|(\w+))')
RE_SAY = re.compile(r'luamanager\.GetStoryText\("([^"]+)"\)')
RE_SAYLIT = re.compile(r'^\s*say\("(.*)"\)\s*$')
RE_ASSIGN = re.compile(r'^\s*(\w+)\s*=\s*"([^"]*)"\s*$')
RE_LOCAL = re.compile(r'^\s*local\s+(\w+)\s*=\s*"([^"]*)"\s*$')
RE_FLAG = re.compile(r'statmodifymanager\.\w*[Ff]lag\w*\(([^)]*)\)')
RE_OPTARR = re.compile(r'^\s*(\w+)\[(\d+)\]\s*=\s*"([^"]*)"')
# 선택지가 조건으로 잠기는 형태. 조건을 안 잡으면 못 고르는 선택지를 고를 수 있는 것처럼 보인다.
#   option_001[2] = Ch_2_4_8_4_001 and "O_2_4_8_4_002" or "~O_2_4_8_4_003"
RE_OPTARR_COND = re.compile(
    r'^\s*(\w+)\[(\d+)\]\s*=\s*(\w+)\s+and\s+"([^"]*)"\s+or\s+"([^"]*)"')
RE_CHOOSE = re.compile(r'local\s+(\w+)\s*=\s*choose\((\w+)\)')
RE_DICECALL = re.compile(r'checkpointmanager\.Dice\("([^"]*)"')
RE_INDEX = re.compile(r'^\s*--index:(\S+)')
RE_AWARD = re.compile(r'(endgamepanel\.Open|statmodifymanager\.AddAchievementLib|cgpanel\.Open)\("(\d+)"')

OPEN = re.compile(r'^\s*(if\b.*\bthen|for\b.*\bdo|while\b.*\bdo|function\b|do)\s*$')


def parse(text):
    """-> list of nodes; node = {'t': kind, ...} nested via 'body'"""
    lines = text.split('\n')
    pos = [0]
    checkpoints = {}          # varname -> (kind, name)
    arrays = {}               # option/dice array var -> {index: label}

    def block(depth=0):
        out = []
        while pos[0] < len(lines):
            i = pos[0]
            ln = lines[i]
            s = ln.strip()
            if RE_END.match(ln):
                pos[0] += 1
                return out
            if RE_ELSE.match(ln) or RE_IF.match(ln) and RE_IF.match(ln).group(1) == 'elseif':
                return out          # caller handles
            m = RE_CP.search(ln)
            if m:
                checkpoints[m.group(1)] = (m.group(2), m.group(3))
                if m.group(2) == 'Dice':
                    checkpoints['__lastdice'] = m.group(3)
                pos[0] += 1
                continue
            m = RE_OPTARR.match(ln)
            if m:
                arrays.setdefault(m.group(1), {})[int(m.group(2))] = m.group(3)
                pos[0] += 1
                continue
            m = RE_OPTARR_COND.match(ln)
            if m:
                arrays.setdefault(m.group(1), {})[int(m.group(2))] = m.group(4)
                cp = checkpoints.get(m.group(3))
                if cp and cp[0] == 'Condition':
                    checkpoints.setdefault('__optgate', {})[(m.group(1), int(m.group(2)))] = cp[1]
                pos[0] += 1
                continue
            m = RE_CHOOSE.search(ln)
            if m:
                checkpoints[m.group(1)] = ('Choice', m.group(2))
                pos[0] += 1
                continue
            if 'dicemenudialog.ResultSelection' in ln:
                mv = re.match(r'\s*local\s+(\w+)\s*=', ln)
                if mv:
                    arr = mv.group(1).replace('choice_', '')
                    checkpoints[mv.group(1)] = ('Dice', checkpoints.get('__lastdice', ''), arr)
                pos[0] += 1
                continue
            m = RE_IF.match(ln)
            if m and m.group(1) == 'if':
                cond = m.group(2)
                # 변수 이름은 한 파일 안에서 다시 쓰인다(가지 안에서 같은 switch_005_result 를 또 선언).
                # 끝까지 읽은 뒤에 풀면 바깥 if 가 안쪽 선언으로 풀리므로 이 줄에서 굳힌다.
                snap = dict(checkpoints)
                snap['__arrays'] = {k: dict(v) for k, v in arrays.items()}
                snap['__optgate'] = dict(checkpoints.get('__optgate') or {})
                pos[0] += 1
                lbl0 = _peek_index(lines, pos[0])
                body = block(depth + 1)
                branches = [(cond, body, lbl0)]
                resolved = [describe_cond(cond, snap)]
                while pos[0] < len(lines):
                    ln2 = lines[pos[0]]
                    m2 = RE_IF.match(ln2)
                    if m2 and m2.group(1) == 'elseif':
                        pos[0] += 1
                        lb = _peek_index(lines, pos[0])
                        resolved.append(describe_cond(m2.group(2), snap))
                        branches.append((m2.group(2), block(depth + 1), lb))
                    elif RE_ELSE.match(ln2):
                        pos[0] += 1
                        lb = _peek_index(lines, pos[0])
                        resolved.append(describe_cond(None, snap))
                        branches.append((None, block(depth + 1), lb))
                    else:
                        break
                if pos[0] < len(lines) and RE_END.match(lines[pos[0]]):
                    pos[0] += 1
                out.append({'t': 'if', 'branches': branches, 'resolved': resolved, 'line': i + 1})
                continue
            if OPEN.match(ln):        # for/while/function/do -> flatten
                pos[0] += 1
                out += block(depth + 1)
                continue
            m = RE_AWARD.search(ln)
            if m:
                out.append({'t': 'award',
                            'kind': ('ending' if 'endgamepanel' in m.group(1)
                                     else 'cg' if 'cgpanel' in m.group(1) else 'achievement'),
                            'id': m.group(2), 'line': i + 1})
                pos[0] += 1
                continue
            m = RE_SCENE.search(ln)
            if m:
                out.append({'t': 'scene', 'scene': m.group(1), 'arg': m.group(2), 'line': i + 1})
                pos[0] += 1
                continue
            m = RE_NEXT.search(ln)
            if m:
                out.append({'t': 'next', 'call': m.group(1), 'script': m.group(2),
                            'var': m.group(3), 'line': i + 1})
                pos[0] += 1
                continue
            m = RE_SAY.search(ln)
            if m:
                out.append({'t': 'say', 'key': m.group(1), 'line': i + 1})
                pos[0] += 1
                continue
            m = RE_LOCAL.match(ln) or RE_ASSIGN.match(ln)
            if m:
                out.append({'t': 'set', 'var': m.group(1), 'val': m.group(2), 'line': i + 1})
                pos[0] += 1
                continue
            pos[0] += 1
        return out

    tree = block()
    checkpoints['__arrays'] = arrays
    return tree, checkpoints


def _peek_index(lines, i):
    for k in range(i, min(i + 4, len(lines))):
        m = RE_INDEX.match(lines[k])
        if m:
            return m.group(1)
        if lines[k].strip():
            continue
    return None


def terminals(tree, checkpoints, path=()):
    """yield (path, node) for scene/next terminals; path = tuple of (kind, name, branchcond)"""
    for n in tree:
        if n['t'] == 'if':
            for k, (cond, body, lbl0) in enumerate(n['branches']):
                d = n['resolved'][k] if 'resolved' in n else describe_cond(cond, checkpoints)
                # 자리: (종류, 이름, 가지, 라벨, --index 라벨, 선택지 잠금조건)
                lbl = d[:4] + (lbl0, d[4])
                yield from terminals(body, checkpoints, path + (lbl,))
        elif n['t'] in ('scene', 'next', 'award'):
            yield path, n


def describe_cond(cond, checkpoints):
    """'switch1_1_result == 2' -> ('Switch','NAME',2)"""
    if cond is None:
        return ('else', None, None, None, None)
    for op, fmt in (('==', lambda v: int(v)), ('~=', lambda v: 'not ' + v)):
        m = re.match(r'(\w+)\s*' + re.escape(op) + r'\s*(-?\d+)', cond or '')
        if m and m.group(1) in checkpoints:
            cp = checkpoints[m.group(1)]
            k, nm = cp[0], cp[1]
            idx = fmt(m.group(2))
            arr = cp[2] if len(cp) > 2 else (nm if k == 'Choice' else None)
            label = None
            arrays = checkpoints.get('__arrays') or {}
            if arr and isinstance(idx, int):
                label = (arrays.get(arr) or {}).get(idx)
            gate = None
            if k == 'Choice' and isinstance(idx, int):
                gate = (checkpoints.get('__optgate') or {}).get((arr, idx))
            return (k, nm, idx, label, gate)
    return ('raw', cond, None, None, None)


def load_all(luadir='lua'):
    out = {}
    for fn in os.listdir(luadir):
        if not fn.endswith('.lua'):
            continue
        t = open(os.path.join(luadir, fn), encoding='utf-8', errors='replace').read()
        out[fn[:-4]] = t
    return out
