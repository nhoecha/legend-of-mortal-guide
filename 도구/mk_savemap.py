# -*- coding: utf-8 -*-
"""세이브를 사람 말로 옮기는 데 필요한 이름표만 게임에서 뽑아 savemap.json 으로 굳힌다.

세이브 읽기 도구(save_read.py)가 게임 설치본 없이도 돌게 하려는 것이 목적이다.
게임을 여는 데 1분쯤 걸리므로 자주 돌릴 것은 아니다. 게임이 업데이트되면 다시 돌린다.
"""
import json
import game
from flag_ko import FLAG_KO

# 「변심의 꿈」 안내 문구에서 확인한 값. zh-cn 사본이 원문을 그대로 들고 있다.
#   0 唐默铃 / 1 瑞杏 / 2 叶云裳 / 3 虞小梅 / 4 上官萤 / 5 夏侯兰 / 7 魏菊 / 8 龙湘
# 6 은 lua 어디서도 세우지 않는다. 남은 자리가 욱죽뿐이라 그렇게 적어 둔다.
LOVER = {'0': '소사매', '1': '서행', '2': '엽운상', '3': '우소매', '4': '상관형',
         '5': '하후란', '6': '욱죽', '7': '위국', '8': '용상'}

STAGE = {'1': '상순', '2': '중순', '3': '하순'}

# 게임 로컬라이제이션(PlayerStat/*)에 이름이 없는 내부 스탯. UI 에는 안 뜨는데
# 조건문에는 나온다. 이름을 안 붙이면 리더가 「누적 연단 >=250 ?」 처럼 물음표로 두고
# 판정을 못 한다 — 생#39·한#9·한#10·한#11 이 그랬다.
# **이름은 cond.py 의 STAT_KO 와 정확히 같아야** 조건문과 이어진다.
EXTRA_STATS = {
    'total-poison-point': '누적 연단',      # 全毒藥點數
    'total-martial-point': '누적 무학',     # 全武學點數
    'total-weapon-point': '누적 단조',      # 全鍛造點數
    'total-contribution': '누적 공헌',      # 全貢獻度
    'faction-contribution': '문파 공헌',    # 門派貢獻
    'cook': '요리',
}


def main():
    g = game.Game()

    stats = {}
    for k, v in g.loc.items():
        if k.startswith('PlayerStat/'):
            stats[k.split('/', 1)[1]] = v

    for k, v in EXTRA_STATS.items():
        stats.setdefault(k, v)

    chars = {}
    for k, v in g.loc.items():
        if k.startswith('Character/'):
            chars[k.split('/', 1)[1]] = v

    books, miscs, specials, talents = {}, {}, {}, {}
    for pref, out in (('Book/Name/', books), ('Misc/Name/', miscs),
                      ('Special/Name/', specials), ('PlayerTalent/Name/', talents)):
        for k, v in g.loc.items():
            if k.startswith(pref):
                out[k[len(pref):]] = v
    # 접두사 형태가 다를 수 있어 한 번 더 훑는다
    for pref, out in (('Book/', books), ('Misc/', miscs), ('Special/', specials)):
        for k, v in g.loc.items():
            rest = k[len(pref):] if k.startswith(pref) else None
            if rest and '/' not in rest:
                out.setdefault(rest, v)

    out = {
        'stats': stats,
        'chars': chars,
        'flags': FLAG_KO,
        'lover': LOVER,
        'stage': STAGE,
        'books': books,
        'miscs': miscs,
        'specials': specials,
        'talents': talents,
    }
    json.dump(out, open('savemap.json', 'w', encoding='utf-8'), ensure_ascii=False)
    for k, v in out.items():
        print(k, len(v))


if __name__ == '__main__':
    main()
