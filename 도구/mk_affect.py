# -*- coding: utf-8 -*-
"""인물 호감도가 오르내리는 자리를 전부 모아 affect.json 으로 낸다.

「서생 호감도 30 이상」 같은 조건을 두고 리더가 「1개 모자람」이라고만 적으면,
올릴 방법이 이 회차에 남아 있는지 없는지가 안 보인다. 서생은 자유행동에 아예
나오지 않아서 오르는 자리가 본편 사건의 특정 갈래뿐인데, 큰 폭(+20)이 전부
「공동 영전 - 서행 참전」에 걸려 있어 이 빌드에서는 닿지 않는다.

lua 의 statmodifymanager.Character 가 호감도를 움직이는 유일한 통로다
(SetCharacter 는 동행 해제용이고, 선물 계통은 lua 에 없다). 각 자리를 감싼
if/switch 조건을 mk_flagdep 의 것과 같은 방식으로 걷어 함께 싣는다.
"""
import glob
import json
import os
import re

from mk_flagdep import enclosing
from flag_ko import FLAG_KO

RE_INDEX = re.compile(r'^\s*--index:(\S+)')
RE_CH = re.compile(r'statmodifymanager\.Character\("([A-Za-z0-9_]+)",\s*(-?\d+),\s*(\d)\)')
RE_FLAG = re.compile(r'\[플래그 ([^\]]+?)\]\s*==\s*(-?\d+)')
RE_LOVER = re.compile(r'\[마음에 둔 사람\]\s*==\s*(-?\d+)')


def main():
    import game
    g = game.Game()
    G = json.load(open('graph.json', encoding='utf-8'))
    SW = G['switch']
    MIS = G.get('mission') or {}
    M = json.load(open('savemap.json', encoding='utf-8'))
    name_of = M['chars']
    lab2id = {}
    for fid, lab in FLAG_KO.items():
        lab2id.setdefault(lab, fid)

    have = {os.path.basename(p)[:-4] for p in glob.glob('lua/*.lua')}
    out = {}
    for p in sorted(glob.glob('lua/*.lua')):
        base = os.path.basename(p)[:-4]
        # ch2_2_5_1__973 같은 것은 같은 장면의 다른 빌드본이다. 기회가 하나 더
        # 있는 것이 아니므로 원본이 있으면 건너뛴다 — 안 그러면 상한이 부풀려진다.
        m0 = re.match(r'^(.*)__\d+$', base)
        if m0 and m0.group(1) in have:
            continue
        rows = enclosing(p)
        if not any(RE_CH.search(ln) for ln, _ in rows):
            continue
        # 그 줄을 지배하는 선택지. 「어느 선택지가 호감도를 움직이나」가 실제로 쓰는 정보다.
        idx = None
        for ln, stack in rows:
            mi = RE_INDEX.match(ln)
            if mi:
                idx = mi.group(1)
            m = RE_CH.search(ln)
            if not m:
                continue
            key, delta = m.group(1), int(m.group(2))
            who = name_of.get(key)
            if not who or not delta:
                continue
            need, unknown = [], False
            for sw, br in stack:
                items = SW.get(sw)
                txt = items[br - 1] if items and 1 <= br <= len(items) else None
                if txt is None or ' 또는 ' in txt or '아님' in txt:
                    unknown = True
                    continue
                hit = False
                for v in RE_LOVER.findall(txt):
                    need.append(['@lover', int(v)]); hit = True
                for lab, v in RE_FLAG.findall(txt):
                    fid = lab2id.get(lab) or lab.split(' ')[0]
                    need.append([fid, int(v)]); hit = True
                if not hit:
                    unknown = True          # 수치 조건 등 — 막지 않고 열어 둔다
            rec = {'d': delta, 'sc': base, 'need': need, 'unknown': unknown}
            if idx and idx.startswith('O_'):
                rec['opt'] = g.t('Story/' + idx) or idx
            m = MIS.get(base) or {}
            t = m.get('time') or {}
            if t.get('y'):
                rec['when'] = f"{t['y']}년 {t['m']}월 {t.get('s') or ''}".strip()
            out.setdefault(who, []).append(rec)

    json.dump(out, open('affect.json', 'w', encoding='utf-8'), ensure_ascii=False)

    # 위치별 결과 추첨표만 따로 뽑아 둔다. 리더가 매번 graph.json(1.8MB)을 열지 않게.
    json.dump(G['position'], open('pos.json', 'w', encoding='utf-8'), ensure_ascii=False)
    tot = sum(len(v) for v in out.values())
    print(f'인물 {len(out)}명 / 호감도가 움직이는 자리 {tot}곳')
    for who in sorted(out, key=lambda k: -sum(x['d'] for x in out[k] if x['d'] > 0))[:6]:
        up = sum(x['d'] for x in out[who] if x['d'] > 0)
        print(f'  {who} +{up} ({len(out[who])}곳)')


if __name__ == '__main__':
    main()
