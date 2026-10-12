# -*- coding: utf-8 -*-
"""플래그를 세우는 자리마다, 그 자리에 닿으려면 무엇이 필요한지 모은다.

세이브 판정이 「이 플래그를 아직 만들 수 있는가」를 물으려면 한 단계로는 부족하다.
「공동 영전 - 소사매 참전」은 ch5_4_4 가 세우는데 그 자리가 M30026 안에 있고, M30026 은
lua 어디서도 세워지지 않는다. 그래서 그 값에 닿는 길은 「엽운주 참전」을 거쳐 2 를 만든 뒤
1 로 바꾸는 세 단계뿐이다 — 한 단계만 보면 놓친다.

lua 의 if/elseif 를 따라가며 각 SetFlag 를 감싸고 있는 분기의 조건을 모아 flagdep.json 으로 낸다.
읽는 쪽(save_read.py)이 이것으로 최소 고정점을 돌려 「이제 못 만드는 값」을 가려낸다.
"""
import json
import os
import re

RE_SWITCH = re.compile(r'local\s+(\w+)\s*=\s*checkpointmanager\.Switch\("([^"]+)"\)')
RE_IF = re.compile(r'^\s*if\s+(\w+)\s*==\s*(\d+)\s+then')
RE_ELIF = re.compile(r'^\s*elseif\s+(\w+)\s*==\s*(\d+)\s+then')
RE_IF_ANY = re.compile(r'\bif\b.*\bthen\b')
RE_LOOP = re.compile(r'\bfor\b.*\bdo\b|\bwhile\b.*\bdo\b|\bfunction\b')
RE_END = re.compile(r'^\s*end\b')
RE_SET = re.compile(r'statmodifymanager\.(SetFlag|AddFlag)\("([A-Za-z0-9_]+)",\s*(-?\d+)\)')
RE_CONDVAR = re.compile(r'local\s+(\w+)\s*=\s*checkpointmanager\.Condition\("([^"]+)"\)')
RE_NEWARR = re.compile(r'^\s*local\s+(\w+)\s*=\s*\{\s*\}')
RE_OPTLOCK = re.compile(r'^\s*(\w+)\[(\d+)\]\s*=\s*(?:(\w+)\s+and\s+)?"')
RE_CHOOSE = re.compile(r'local\s+(\w+)\s*=\s*choose\((\w+)\)')
GATE = 'cond:'
# 그 대화·장면 안에서만 뜻이 있는 값. 선택지 잠금에 섞여 있어도 회차 조건으로 못 박지 않는다.
RE_SCENE_LOCAL = re.compile(r'^(A0|B0|C0|TC)')
# 이름 없는 플래그는 'M30026 (설명)' 꼴로 적힌다. 뒤를 안 보면 S2503_Break_01_001 을 S2503 으로 읽는다.
RE_BAREID = re.compile(r'([A-Z]\d{4,6})(?=\s|$)')
RE_FLAGREQ = re.compile(r'\[플래그 ([^\]]+)\]\s*==\s*(-?\d+)')
RE_LOVERREQ = re.compile(r'\[마음에 둔 사람\]\s*==\s*(-?\d+)')


def enclosing(path, gates=False):
    """각 줄에서 그 줄을 감싸고 있는 (스위치 이름, 몇 번째 가지) 목록.

    gates 를 켜면 잠긴 선택지의 가지도 (GATE + 조건 이름, 0) 으로 싣는다. 대본은 선택지를
    `X = Condition("X")` → `opt[n] = X and "…" or "~…"` → `choose(opt)` 로 잠그는데, 스위치만
    따라가면 그 가지 안의 SetFlag 가 조건 없이 서는 것으로 보인다(풍#20 의 임시 플래그 2).
    """
    lines = open(path, encoding='utf-8', errors='replace').read().split('\n')
    var2sw = {}
    var2cond, lock, picked = {}, {}, {}     # 조건 변수, 배열별 잠금, choose 변수가 본 잠금
    stack = []          # (깊이, 스위치, 가지) — 가지가 None 이면 조건을 모른다
    depth = 0
    out = []

    def key(var, n):
        g = picked.get(var, {}).get(n) if gates else None
        return (GATE + g, 0) if g else (var2sw.get(var), n)

    for ln in lines:
        m = RE_SWITCH.search(ln)
        if m:
            var2sw[m.group(1)] = m.group(2)
        if gates:
            m = RE_CONDVAR.search(ln)
            if m:
                var2cond[m.group(1)] = m.group(2)
            m = RE_NEWARR.match(ln)
            if m:
                lock[m.group(1)] = {}       # 같은 이름의 배열을 다시 쓰는 대본이 있다
            m = RE_OPTLOCK.match(ln)
            if m:
                arr, n, var = m.group(1), int(m.group(2)), m.group(3)
                lock.setdefault(arr, {}).pop(n, None)
                if var:
                    lock[arr][n] = var2cond.get(var, var)
            m = RE_CHOOSE.search(ln)
            if m:
                picked[m.group(1)] = dict(lock.get(m.group(2)) or {})
        mi = RE_IF.match(ln)
        mе = RE_ELIF.match(ln)
        if mi:
            depth += 1
            stack.append((depth,) + key(mi.group(1), int(mi.group(2))))
        elif mе:
            if stack and stack[-1][0] == depth:
                stack.pop()
            stack.append((depth,) + key(mе.group(1), int(mе.group(2))))
        elif RE_IF_ANY.search(ln) and not re.search(r'\belseif\b', ln):
            depth += 1
            stack.append((depth, None, None))
        elif RE_LOOP.search(ln):
            depth += 1
            stack.append((depth, None, None))
        if RE_END.match(ln):
            while stack and stack[-1][0] >= depth:
                stack.pop()
            depth = max(0, depth - 1)
        out.append((ln, [(s, b) for _, s, b in stack if s]))
    return out


def main():
    G = json.load(open('graph.json', encoding='utf-8'))
    sw, cn = G['switch'], G['condition']
    DEAD = object()
    from flag_ko import FLAG_KO
    lab2id = {}
    for fid, lab in FLAG_KO.items():
        lab2id.setdefault(lab, fid)

    def reqs_of(name, branch):
        """그 가지가 성립하려면 필요한 (플래그 값, 심계 값)들. 모르면 None."""
        if name.startswith(GATE):
            items = cn.get(name[len(GATE):])
            if items is None:
                return DEAD                 # 게임 데이터에 없는 조건(XXX 등) — 그 선택지는 영영 잠겨 있다
            if len(items) != 1:
                return None
            txt = items[0] or ''
        else:
            items = sw.get(name)
            if not items or not (1 <= branch <= len(items)):
                return None                 # else 가지이거나 정의를 모른다
            txt = items[branch - 1] or ''
        if ' 또는 ' in txt or '아님' in txt:
            return None                     # 택일·부정은 못 박지 않는다
        out = []
        for v in RE_LOVERREQ.findall(txt):
            out.append(['@lover', int(v)])  # 심계도 같은 자리에 담는다
        for lab, v in RE_FLAGREQ.findall(txt):
            lab = lab.strip()
            fid = lab2id.get(lab)
            if not fid:
                # 한국어 이름이 없는 플래그는 조건 렌더러가 아이디를 그대로 적는다
                # (예: 'M30026 (觸發笙活雙俠分支)').
                mm = RE_BAREID.match(lab)
                fid = mm.group(1) if mm else None
            if fid:
                out.append([fid, int(v)])
        return out

    rev, mission = G.get('rev') or {}, G.get('mission') or {}
    ST = {'상순': 1, '중순': 2, '하순': 3}
    mis_cache = {}

    def wk_of(t):
        t = t or {}
        return (t['y'] * 1000 + t['m'] * 10 + ST.get(t.get('s'), 0)) if t.get('y') else None

    def _limit(c):
        hi, lo = wk_of(c.get('maxTime')), wk_of(c.get('time'))
        return None if hi is None or (lo is not None and hi < lo) else hi

    def mission_gate(sc):
        """그 스크립트를 여는 미션. (플래그 조건, 전부 꺼져 있나, 마지막 시점)

        lua 의 if 만 보면 사건 자체가 언제 열리는지가 빠진다. 「하후란을 스승으로 모심」은
        S0014_01_06 이 조건 없이 세우지만, 그 사건을 여는 미션이 공동파 탈백문을 요구한다.

        갈림이 있어도 위로 다 훑는다. 외길만 따라가면 들어오는 길이 여럿인 자리에서
        미션에 닿지 못한다 — 「엽운상 공략 중」이 그랬다. 그 플래그를 세우는 자리는
        이 빌드에서 꺼진 미션(S0208_01) 안에만 있는데 「아직 안 왔다」로 보였다.
        자유행동에서 바로 들어가는 장면은 미션이 안 열어도 나므로 관문을 걸지 않는다.
        """
        if sc in mis_cache:
            return mis_cache[sc]
        seen, stack, mis, free = set(), [sc], set(), False
        while stack and len(seen) <= 400:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            if cur in mission:
                # 꺼진 미션인데 다른 대본이 SetNextScript 로 그 장면을 직접 부르면, 미션은 관문이
                # 아니다. S0208_01 이 그렇다 — 미션은 _active False 지만 5장(ch5_4_1 · ch5_4_2)이
                # 곧장 넘긴다. 이걸 미션에서 멈춰 「엽운상 공략 중은 이 빌드에서 못 선다」고 막았었다.
                m0 = mission[cur]
                alive = any(c.get('active') is not False
                            for c in [m0] + list(m0.get('alts') or []))
                called = [p for p in (rev.get(cur) or [])
                          if p.get('from') and not p['from'].startswith('[')]
                if alive or not called:
                    mis.add(cur)
                    continue
            for p in (rev.get(cur) or []):
                f = p.get('from')
                if not f:
                    continue
                if f.startswith('['):
                    free = True          # 자유행동 진입 — 미션을 거치지 않는다
                else:
                    stack.append(f)
        need, dead, wk = [], False, None
        if mis and not free:
            def cands(k):
                m = mission[k]
                return [m] + list(m.get('alts') or [])

            # alts 는 「이 미션 대신 열리는 다른 미션」이다. 하나라도 살아 있으면 길은 있다.
            # ch7_5_6_1 은 conds 가 [항전 노선] 뿐이지만 alt 로 西武林盟 이 붙어 있다 —
            # main 만 읽으면 서무림맹 회차를 통째로 막아 버린다.
            dead = all(c.get('active') is False for k in mis for c in cands(k))

            # 마감이 적힌 것만 마감으로 쓴다. 하나라도 안 적혀 있으면 못 박지 않는다.
            # maxTime 이 time 보다 이른 미션이 69 개 있다(S2504_02 는 3년 7월인데 2년 7월).
            # 그 값은 마감이 아니므로 「모른다」로 본다 — 쓰면 설산행 전체를 막는다.
            lim = [_limit(c) for k in mis for c in cands(k)]
            wk = max(lim) if lim and None not in lim else None

            one = list(mis)[0]
            if len(mis) == 1 and not mission[one].get('alts'):
                for txt in (mission[one].get('conds') or []):
                    if ' 또는 ' in txt or '아님' in txt:
                        continue
                    for lab, v in RE_FLAGREQ.findall(txt):
                        lab = lab.strip()
                        fid2 = lab2id.get(lab)
                        if not fid2:
                            mm = RE_BAREID.match(lab)
                            fid2 = mm.group(1) if mm else None
                        if fid2:
                            need.append([fid2, int(v)])
        mis_cache[sc] = (need, dead, wk)
        return mis_cache[sc]

    up_cache = {}

    def entry_need(sc):
        """그 대본으로 들어오는 길이 하나뿐인 동안 거슬러 올라가며, 그 길의 갈림이 요구하는 것.

        SetFlag 를 감싼 if 만 보면 그 대본에 어떻게 들어왔는지가 빠진다. 「엽운상 무림대회 동행」은
        S0603_02 가 조건 없이 세우지만, 그 대본은 S0603_01 의 「엽운상 공략 중 == 1」 가지로만 온다.
        길이 둘 이상이면 어느 쪽으로 왔는지 모르므로 멈춘다. 미션이 직접 여는 대본에서도 멈춘다
        (그쪽은 mission_gate 가 본다).
        """
        if sc in up_cache:
            return up_cache[sc]
        out, dead, cur, seen = [], False, sc, {sc}
        for _ in range(24):
            ps = [p for p in rev.get(cur) or [] if p.get('from') != cur]    # 제자리로 돌아오는 대화 메뉴는 들어오는 길이 아니다
            if cur in mission or len(ps) != 1:
                break
            f = ps[0].get('from')
            if not f or f.startswith('[') or f in seen or ps[0].get('kind') != 'next':
                break
            for st in ps[0].get('path') or []:
                if st[0] == 'Switch' and isinstance(st[2], int):
                    r = reqs_of(st[1], st[2])
                elif st[0] == 'Choice' and len(st) > 5 and st[5]:
                    r = reqs_of(GATE + st[5], 0)
                else:
                    continue
                if r is DEAD:
                    dead = True
                elif r:
                    out += [x for x in r if x not in out and not RE_SCENE_LOCAL.match(x[0])]
            seen.add(f)
            cur = f
        up_cache[sc] = (out, dead)
        return up_cache[sc]

    dep = {}
    for fn in sorted(os.listdir('lua')):
        sc = fn[:-4].split('__')[0]
        for ln, encl in enclosing(os.path.join('lua', fn), gates=True):
            m = RE_SET.search(ln)
            if not m:
                continue
            kind, fid, val = m.group(1), m.group(2), m.group(3)
            e = dep.setdefault(fid, {})
            if kind == 'AddFlag':
                e['add'] = True
                continue
            need, unknown, why, gate, opt_dead = [], False, [], [], False
            for name, branch in encl:
                r = reqs_of(name, branch)
                if name.startswith(GATE):
                    # 선택지 잠금. 스위치와 달리 그 선택지를 누를 수 있느냐의 조건이라, 임시 플래그나
                    # 자기 자신(「이미 골랐나」 표시)에 대한 비교는 회차 조건이 아니다.
                    if r is DEAD:
                        opt_dead = True
                        continue
                    txt = (cn[name[len(GATE):]] or [''])[0] if len(cn[name[len(GATE):]]) == 1 else ''
                    if txt:
                        gate.append(txt)
                    if r is None:
                        unknown = True
                        if txt:
                            why.append(txt)
                    else:
                        need += [x for x in r if x[0] != fid and not RE_SCENE_LOCAL.match(x[0])]
                    continue
                if r is None:
                    unknown = True
                    # 못 박지는 못해도 무엇이 걸려 있는지는 알려 줄 수 있다. 택일 조건을
                    # 통째로 버리면 「조건 없음」으로 보인다 — 풍#20 이 그랬다. 그 항목은
                    # ch6_8_4 의 두 번째 선택지로만 열리고, 그 선택지가 열리려면
                    # 「위국 공략 중 또는 엽운상 무림대회 동행」이라야 한다.
                    items = sw.get(name)
                    if items and 1 <= branch <= len(items) and items[branch - 1]:
                        why.append(items[branch - 1])
                else:
                    need += r
            # 같은 값을 여러 자리에서 세운다. 자리마다 따로 담는다.
            gneed, gdead, gwk = mission_gate(sc)
            need = need + [x for x in gneed if x not in need]
            uneed, udead = entry_need(sc)
            uneed = [x for x in uneed if x not in need and x[0] != fid]
            need = need + uneed
            opt_dead = opt_dead or udead
            rec = {'sc': sc, 'need': need, 'unknown': unknown}
            if uneed:
                rec['up'] = uneed       # 그 대본으로 들어오는 외길에서 온 조건
            if gdead:
                rec['misDead'] = True     # 이 빌드에서 꺼진 미션 안에만 있는 자리
            if gwk:
                rec['misMax'] = gwk     # 그 사건을 여는 미션의 마감
            if why:
                rec['why'] = why
            if gate:
                rec['gate'] = gate      # 그 값을 세우는 선택지가 열리는 조건(원문)
            if opt_dead:
                rec['optDead'] = True   # 정의 없는 조건으로 잠긴 선택지 안에만 있는 자리
            e.setdefault(val, []).append(rec)
    json.dump(dep, open('flagdep.json', 'w', encoding='utf-8'), ensure_ascii=False)

    # 미션 키 -> 시점. 세이브가 들고 있는 것은 키뿐이라, 그것만 보여 주면
    # 「왜 이벤트가 안 뜨지」에 답이 안 된다.
    ST = {'상순': 1, '중순': 2, '하순': 3}
    mis = {}
    for sc, m in (G.get('mission') or {}).items():
        k = m.get('key')
        if not k:
            continue
        t = m.get('time') or {}
        rec = {'script': sc, 'desc': m.get('desc') or ''}
        if t.get('y'):
            rec['when'] = f"{t['y']}년차 {t['m']}월 {t.get('s') or ''}".strip()
            rec['wk'] = t['y'] * 1000 + t['m'] * 10 + ST.get(t.get('s'), 0)
        mis.setdefault(k, rec)
    json.dump(mis, open('missions.json', 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(G.get('summary') or {},
              open('summary.json', 'w', encoding='utf-8'), ensure_ascii=False)
    n = sum(len(v) for e in dep.values() for k, v in e.items() if k != 'add')
    print('플래그', len(dep), '개 / 세우는 자리', n, '곳')
    for k in ('M50010', 'M50009', 'M50011', 'M30026', 'E12100'):
        print(' ', k, json.dumps(dep.get(k), ensure_ascii=False)[:180])


if __name__ == '__main__':
    main()
