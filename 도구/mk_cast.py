# -*- coding: utf-8 -*-
"""장면마다 누가 나오는지를 모아 cast.json 으로 낸다.

조건문에 안 적히는 요구가 하나 있다 — **그 인물이 이 회차에 있어야 한다**는 것.
생#98 「패자의 죽음」이 그랬다. 조건은 「결투 승패 == 0」뿐이라 도구가 「확실」이라고
불렀는데, 그 장면에는 엽운상이 나온다. 엽운상을 아직 거두지 않은 회차에서는 열릴 수
없는 자리다.

영입·이탈이 있는 인물(presence.json 의 열 명)만 센다. 당문에 늘 있는 사람은 조건이
되지 않는다.
"""
import glob
import json
import os
import re

from mk_flagdep import enclosing

RE_CHAR = re.compile(r'characters\.(?:Get|LoadCharacterAsset|Focus)\("([A-Za-z0-9_]+)"\)')


def main():
    M = json.load(open('savemap.json', encoding='utf-8'))
    P = json.load(open('presence.json', encoding='utf-8'))
    watch = set(P)                       # 영입·이탈이 있는 인물만
    ko = M['chars']

    out = {}
    for path in sorted(glob.glob('lua/*.lua')):
        sc = os.path.basename(path)[:-4]
        if '__' in sc:                   # zh-cn / zh-tw 중복본
            continue
        try:
            rows = enclosing(path)
        except Exception:
            continue
        sure, maybe = set(), set()
        for ln, stack in rows:
            for key in RE_CHAR.findall(ln):
                nm = ko.get(key)
                if nm in watch:
                    (sure if not stack else maybe).add(nm)
        maybe -= sure
        if sure or maybe:
            out[sc] = {'sure': sorted(sure), 'maybe': sorted(maybe)}

    json.dump(out, open('cast.json', 'w', encoding='utf-8'), ensure_ascii=False)
    n_sure = sum(1 for v in out.values() if v['sure'])
    print(f'cast.json  장면 {len(out)}개 (조건 없이 나오는 사람이 있는 장면 {n_sure}개)')


if __name__ == '__main__':
    main()
