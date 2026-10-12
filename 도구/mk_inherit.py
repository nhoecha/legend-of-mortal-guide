"""Extract the 계승(inheritance) allocation table from the game files.

PlayerBonusStatData / SocialBonusStatData / FlagBonusStatData are the three tabs of the
계승 screen (속성 / 관계 / 문파). Each entry points at the stat it raises; the prefab it
points at groups entries into the same UI row type (= same step). The per-click point
cost lives inside the prefab, which is not in the asset files we parse, so the step and
the starting value are what we record.
"""
import sys, io, json, re, collections
import game, cond

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
g = game.Game()
R = cond.Renderer(g)

# step per prefab, read off the 계승 UI (the number under the +/- button)
STEP = {1520: 5, 1521: 10, 1522: 2500, 1523: 10, 1642: 10, 1643: 10, 1669: 2}

TAB = {'PlayerBonusStatData': '속성',
       'SocialBonusStatData': '관계',
       'FlagBonusStatData': '문파'}

out = {}
for cls, tab in TAB.items():
    for ref in g.byclass.get(cls, []):
        o = g.obj(ref, None)
        for e in o.get('_list') or []:
            sr = g.resolve(ref[0], e['_stat'])
            so = g.obj(sr, None) or {}
            nm = so.get('__name') or ''
            step = STEP.get(e['_prefab'][1])

            if tab == '속성':
                ko = R.stat_name(sr)
                if ko == '?':
                    ko = cond.STAT_KO.get(so.get('_name'), so.get('_name') or nm)
            elif tab == '관계':
                ko = R.rel_name(sr)
                if ko in ('?', ''):
                    zh = (nm.split('_')[-1] if '_' in nm else nm)
                    ko = cond.REL_KO.get(zh, zh)
                ko += ' 호감도'
            else:
                note = so.get('_devNote') or ''
                ko = re.sub('好感度$', ' 호감도', note)
                for zh, k in (('青城派', '청성파'), ('全真教', '전진교'), ('峨嵋派', '아미파'),
                              ('崆峒派', '공동파'), ('嵩山派', '숭산파'), ('點蒼派', '점창파'),
                              ('南宮世家', '남궁세가'), ('錦香宮', '금향궁'), ('丐幫', '개방'),
                              ('飛石幫', '비석방')):
                    ko = ko.replace(zh, k)

            out[ko] = {'tab': tab, 'step': step, 'start': so.get('_default'),
                       'max': so.get('_max'), 'raw': nm}

json.dump(out, open('inherit.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
by = collections.Counter(v['tab'] for v in out.values())
print('계승 가능 항목', len(out), dict(by))
for k, v in sorted(out.items(), key=lambda x: (x[1]['tab'], x[0])):
    print(f"  [{v['tab']}] {k:18} 시작 {str(v['start']):>5} · +{v['step']}씩 · 최대 {v['max']}")
