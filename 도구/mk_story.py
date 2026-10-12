# -*- coding: utf-8 -*-
"""장면 안의 이야기 조각(AddStory)이 어느 가지에 있는지를 story.json 으로 낸다.

세이브의 StorySave 에는 「실제로 지나온 조각」이 남는다. 플래그는 결과만 말하지만
이것은 **어느 갈래로 갔는지**를 말한다. 대사형 완쾌(S0401_01)가 그 예다 — 지금 처세가
58 이라 조건이 다 맞아 보여도, 기록에 S0401_01_003 이 있으면 그 순간에는 60 이상이었고
완쾌 가지로 가지 않았다는 뜻이다. 값만 보면 통과로 잘못 읽는다.
"""
import glob
import json
import os
import re

from mk_flagdep import enclosing

RE_STORY = re.compile(r'statmodifymanager\.AddStory\("([A-Za-z0-9_]+)"\)')


def main():
    G = json.load(open('graph.json', encoding='utf-8'))
    SW = G['switch']
    have = {os.path.basename(p)[:-4] for p in glob.glob('lua/*.lua')}
    out = {}
    byscene = {}
    for p in sorted(glob.glob('lua/*.lua')):
        base = os.path.basename(p)[:-4]
        m0 = re.match(r'^(.*)__\d+$', base)
        if m0 and m0.group(1) in have:
            continue                      # 같은 장면의 다른 빌드본
        rows = enclosing(p)
        if not any(RE_STORY.search(ln) for ln, _ in rows):
            continue
        for ln, stack in rows:
            m = RE_STORY.search(ln)
            if not m:
                continue
            conds, unknown = [], False
            for sw, br in stack:
                items = SW.get(sw)
                txt = items[br - 1] if items and 1 <= br <= len(items) else None
                if txt is None:
                    unknown = True
                else:
                    conds.append(txt)
            key = m.group(1)
            # 같은 키가 여러 자리에 있으면 가지를 못 박을 수 없다. 그런 것은 조건을 비운다.
            if key in out and out[key]['sc'] != base:
                out[key] = {'sc': out[key]['sc'], 'conds': [], 'unknown': True, 'dup': True}
                continue
            out[key] = {'sc': base, 'conds': conds, 'unknown': unknown}
            byscene.setdefault(base, []).append(key)
    json.dump({'keys': out, 'scenes': byscene},
              open('story.json', 'w', encoding='utf-8'), ensure_ascii=False)
    top = sum(1 for v in out.values() if not v['conds'] and not v.get('unknown'))
    print(f'이야기 조각 {len(out)} 개 / 장면 {len(byscene)} 개')
    print(f'  가지 조건이 붙은 것 {sum(1 for v in out.values() if v["conds"])}'
          f' · 장면 최상위 {top} · 조건을 못 읽은 것 {sum(1 for v in out.values() if v.get("unknown"))}')


if __name__ == '__main__':
    main()
