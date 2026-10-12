# -*- coding: utf-8 -*-
"""인물이 당문에 들어오고 나가는 자리를 모아 presence.json 으로 낸다.

영입 조건만 적어 두면 절반이다. 작성자의 회차는 엽운상·엽운주·용상을 전부 거두고도
셋 다 떠나보냈다 — 거둔 뒤에 지키는 쪽이 실제로는 더 어려웠다. 나가는 자리마다
시점과, 그 자리를 만든 선택지를 함께 싣는다.
"""
import glob
import json
import os
import re

from mk_flagdep import enclosing
from flag_ko import FLAG_KO

RE_SET = re.compile(r'statmodifymanager\.SetFlag\("([A-Za-z0-9_]+)",\s*(-?\d+)\)')
RE_INDEX = re.compile(r'^\s*--index:(\S+)')
RE_FLAGREQ = re.compile(r'\[플래그 ([^\]]+?)\]\s*==\s*(-?\d+)')

# 장면 안에도, 미션 조건에도 없는 관문. 들어오는 간선 위에 있어서 자동으로는 안 잡힌다.
# 확인한 것만 손으로 적는다.
LEAVE_NOTE = {
    ('엽운상', 'S0204_01_01_01'): '유학 선택 == 1(청성파) 회차만 붙잡을 수 있다',
    ('엽운주', 'S0204_01_01_01'): '유학 선택 == 1(청성파) 회차만 붙잡을 수 있다',
}


def main():
    import game
    g = game.Game()
    G = json.load(open('graph.json', encoding='utf-8'))
    SW = G['switch']
    MIS = G.get('mission') or {}
    rev = G.get('rev') or {}
    ST = {'상순': 1, '중순': 2, '하순': 3}

    # 「X가 당문에 있음」 계열 플래그만 본다.
    watch = {}
    for fid, lab in FLAG_KO.items():
        m = re.match(r'^(.+?)(?:이|가) 당문에 있음$', lab or '')
        if m:
            watch[fid] = m.group(1)

    def mission_of(sc, maxn=200):
        """그 스크립트를 여는 미션. 들어오는 길이 여럿이어도 전부 한 미션에 모이면 그것이다.

        엽가 남매가 떠나는 S0204_01_01_01 은 들어오는 길이 셋이라 외길 추적(when_of)으로는
        시점을 못 찾아 「시점 미상」으로 뒤로 밀렸고, 리더의 이탈 경고에서 잘려 나가고 있었다.
        셋 다 S0204_01 안이므로 3년 1월 상순이 맞다.
        """
        seen, stack, found = set(), [sc], set()
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            if len(seen) > maxn:
                return None
            seen.add(cur)
            if cur in MIS:
                found.add(cur)
                continue
            ps = rev.get(cur) or []
            if not ps:
                return None          # 미션에 닿지 않는 뿌리가 있으면 못 박지 못한다
            for p in ps:
                f = p.get('from')
                if not f:
                    return None
                stack.append(f)
        return found.pop() if len(found) == 1 else None

    def when_of(sc):
        """그 스크립트를 여는 미션의 시점. 갈림이 없는 동안만 거슬러 올라간다."""
        cur, seen = sc, {sc}
        for _ in range(12):
            mi = MIS.get(cur)
            if mi:
                t = mi.get('time') or {}
                if t.get('y'):
                    return (f"{t['y']}년차 {t['m']}월 {t.get('s') or ''}".strip(),
                            t['y'] * 1000 + t['m'] * 10 + ST.get(t.get('s'), 0))
                return None, None
            ps = rev.get(cur) or []
            if len(ps) != 1:
                return None, None
            nxt = ps[0].get('from')
            if not nxt or nxt in seen:
                return None, None
            seen.add(nxt)
            cur = nxt
        return None, None

    have = {os.path.basename(p)[:-4] for p in glob.glob('lua/*.lua')}
    out = {}
    for p in sorted(glob.glob('lua/*.lua')):
        base = os.path.basename(p)[:-4]
        m0 = re.match(r'^(.*)__\d+$', base)
        if m0 and m0.group(1) in have:
            continue                      # 같은 장면의 다른 빌드본
        rows = enclosing(p)
        if not any(RE_SET.search(ln) for ln, _ in rows):
            continue
        idx = None
        for ln, stack in rows:
            mi = RE_INDEX.match(ln)
            if mi:
                idx = mi.group(1)
            m = RE_SET.search(ln)
            if not m or m.group(1) not in watch:
                continue
            who, val = watch[m.group(1)], int(m.group(2))
            conds, unknown = [], False
            for sw, br in stack:
                items = SW.get(sw)
                txt = items[br - 1] if items and 1 <= br <= len(items) else None
                if txt is None:
                    unknown = True
                else:
                    conds.append(txt)
            when, wk = when_of(base)
            rec = {'sc': base, 'conds': conds, 'unknown': unknown}
            if when:
                rec['when'], rec['wk'] = when, wk
            else:
                mk = mission_of(base)
                mt = ((MIS.get(mk) or {}).get('time') or {}) if mk else {}
                if mt.get('y'):
                    rec['when'] = f"{mt['y']}년차 {mt['m']}월 {mt.get('s') or ''}".strip()
                    rec['wk'] = mt['y'] * 1000 + mt['m'] * 10 + ST.get(mt.get('s'), 0)
                    # 미션 자체가 아니라 그 안의 장면이므로 미션이 못박은 시점의 하한이다.
                    # ch7_5_6_3 처럼 미션 time 이 [시점 M7005] 로 미뤄지는 것도 있다.
                    rec['est'] = True
                    if mk and (MIS[mk].get('conds') or []):
                        rec['viaConds'] = MIS[mk]['conds']
            note = LEAVE_NOTE.get((who, base))
            if note:
                rec['note'] = note
            if idx and idx.startswith('O_'):
                rec['opt'] = g.t('Story/' + idx) or idx
            e = out.setdefault(who, {'flag': m.group(1), 'leave': [], 'join': []})
            e['leave' if val == 0 else 'join'].append(rec)

    json.dump(out, open('presence.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'인물 {len(out)}명')
    for who, e in sorted(out.items()):
        print(f'  {who:6} 들어오는 자리 {len(e["join"])} · 나가는 자리 {len(e["leave"])}')


if __name__ == '__main__':
    main()
