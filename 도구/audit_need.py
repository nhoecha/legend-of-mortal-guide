# -*- coding: utf-8 -*-
"""미획득 항목마다, 그 수여 장면으로 들어오는 **모든** 길에 걸린 조건만 뽑아
data.json 이 싣고 있는 요구와 견준다. 도구가 한 갈래의 조건을 필수로 실은 것을 잡는다.

    python audit_need.py > audit.txt

플래그를 세우는 장면의 조건, 전투 안에서 서는 값은 보지 않는다.
"""
import io, json, os, re, sys
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
T = os.path.dirname(os.path.abspath(__file__))
g = json.load(open(os.path.join(T, 'graph.json'), encoding='utf-8'))
D = json.load(open(os.path.join(T, 'data.json'), encoding='utf-8'))
E, REV, MIS = g['edges'], g['rev'], g['mission']
SW, CD, DC = g['switch'], g['condition'], g['dice']


def pairs_of(path):
    out = []
    for p in path or []:
        if p[0] in ('Switch', 'Dice'):
            out.append((p[0], p[1], p[2]))
        elif p[0] == 'Choice' and len(p) > 5 and p[5]:
            out.append(('Gate', p[5], 1))
    return out


def text(pair):
    kind, name, idx = pair
    if kind == 'Switch':
        c = SW.get(name) or []
        if idx <= len(c):
            pre = ''.join(f'[아님: {x}] ' for x in c[:idx - 1])
            return pre + c[idx - 1]
        return '전부 아님: ' + ' / '.join(c)
    if kind == 'Gate':
        return '선택지 잠금: ' + (' / '.join(CD.get(name) or []) or name)
    if kind == 'Dice':
        d = DC.get(name) or {}
        props = ','.join((p.get('target') or p.get('type') or '?') for p in d.get('props', []))
        res = d.get('results') or []
        want = res[idx - 1]['cond'] if idx <= len(res) else '그 밖'
        return f'주사위 {name} 눈 {want} (보정: {props or "없음"})'
    if kind == 'Mission':
        m = MIS.get(name) or {}
        return f'미션 {m.get("key")} {json.dumps(m.get("time"), ensure_ascii=False)} ' + ' / '.join(m.get('conds') or [])
    if kind == 'Pos':
        return '자유행동 ' + name
    return str(pair)


def closure(target):
    seen, st = set(), [target]
    while st:
        s = st.pop()
        if s in seen:
            continue
        seen.add(s)
        for r in REV.get(s) or []:
            f = str(r.get('from'))
            if not f.startswith('['):
                st.append(f)
    return seen


def analyse(target):
    nodes = closure(target)
    roots, notes = {}, []
    for n in nodes:
        m = MIS.get(n)
        revs = REV.get(n) or []
        if m and m.get('active'):
            roots[n] = ('Mission', n, 1)
        elif any(str(r.get('from')).startswith('[') for r in revs):
            roots[n] = ('Pos', n, 1)
        elif not revs:
            if m:
                notes.append(f'꺼진 미션뿐인 입구: {n}')
            else:
                roots[n] = ('Unknown', n, 1)
    adj = defaultdict(list)
    allpairs = set()
    for n in nodes:
        for e in E.get(n) or []:
            if e['to'] in nodes and e.get('kind') != 'combat':
                ps = pairs_of(e.get('path'))
                adj[n].append((e['to'], ps))
                allpairs.update(ps)
    allpairs.update(roots.values())

    def reach(ban=None):
        st = [n for n, tag in roots.items() if tag != ban]
        seen = set()
        while st:
            s = st.pop()
            if s in seen:
                continue
            seen.add(s)
            if s == target:
                return True
            for to, ps in adj[s]:
                if ban not in ps:
                    st.append(to)
        return target in seen

    if not reach():
        return None, roots, notes
    need = [p for p in sorted(allpairs, key=str) if not reach(p)]
    return need, roots, notes


STAT = re.compile(r'\[([^\]]+)\]')
rows = []
for it in D['items']:
    if it.get('owned'):
        continue
    tag = f"{it['type'][0]}#{it['no']} {it['title']}"
    sites = it.get('paths') or []
    opts = it.get('opts') or []
    out = [f'=== {tag}  (id {it["id"]})  blocked={it.get("blocked")} {it.get("blockReason") or ""}']
    tool_stats = set()
    for o in opts:
        for r in o.get('reqs') or []:
            if 'stat' in r:
                tool_stats.add((r['stat'], ('아님 ' if r.get('neg') else '') + f"{r['op']} {r['val']}"))
            for a in r.get('any') or []:
                tool_stats.add((a['stat'], f"(또는) {a['op']} {a['val']}"))
    need_stats_all = []
    for p in sites:
        sc = p.get('script')
        need, roots, notes = analyse(sc)
        inside = [s.get('text', '') for s in p.get('steps') or []]
        out.append(f'  자리 {sc} via {p.get("via")}  입구 {len(roots)}개: ' + ', '.join(
            f'{k}({v[0]})' for k, v in list(roots.items())[:5]))
        for n in notes:
            out.append('    ! ' + n)
        if need is None:
            out.append('    ! 켜진 입구에서 닿지 않는다')
            need = []
        txts = [text(x) for x in need] + ['[장면 안] ' + t for t in inside if t]
        for t in txts:
            out.append('    필수: ' + t)
        need_stats_all.append(set(STAT.findall(' '.join(txts))))
    # a tool requirement is suspicious if its stat is absent from the necessary set of EVERY site
    sus = [f'{s} {c}' for s, c in sorted(tool_stats)
           if need_stats_all and all(s not in ns for ns in need_stats_all)]
    out.append('  도구 요구: ' + (', '.join(f'{s} {c}' for s, c in sorted(tool_stats)) or '없음'))
    if sus:
        out.append('  >>> 의심(필수 조건에 안 보임): ' + ', '.join(sus))
    rows.append(('\n'.join(out), bool(sus)))

print(f'미획득 {len(rows)}개, 의심 {sum(1 for _, s in rows if s)}개\n')
for t, s in rows:
    if s:
        print(t, '\n')
print('\n######## 의심 없음 ########\n')
for t, s in rows:
    if not s:
        print(t, '\n')
