"""Assemble the 생사부 dataset (game files + save + community sheet) into data.json."""
import glob, json, os, re, collections
import game
from scene_ko import SCENE_KO
from combat_ko import combat_ko

# 세이브 폴더는 Steam ID 로 한 단계 더 들어간다. ID 를 코드에 남기지 않는다
SAVE = next(iter(sorted(glob.glob(os.path.join(
    os.environ.get('USERPROFILE', ''), 'AppData', 'LocalLow', 'Obb Studio', 'Mortal',
    '*', 'Save_universe.json')))), '')

PLACE = {
    'spa': 'Spa', 'back': 'BackMountain', 'girlroom': 'Room2', 'room': 'Room1',
    'center': 'Center', 'door': 'Door', 'alchemy': 'Alchemy', 'study': 'Study',
    'forge': 'Forge', 'kitchen': 'Kitchen', 'farm': 'Farm', 'pharmacy': 'Pharmacy',
    'teashop': 'Teashop', 'tower': 'Tower', 'downtown': 'Downtown',
    'fortress': 'Fortress', 'secret': 'Secret', 'mall': 'Mall',
}
KIND_KO = {'大失敗': '대실패', '失敗': '실패', '正常': '정상', '特殊': '특수', '成功': '성공',
           '大成功': '대성공', '其他': '기타', '事件': '이벤트'}


def kind_ko(k):
    base = re.sub(r'_\d+$', '', k or '')
    return KIND_KO.get(base, base or '?')


def main():
    g = game.Game()
    G = json.load(open('graph.json', encoding='utf-8'))
    sw, dice = G['switch'], G['dice']
    rev, deaths, combat = G['rev'], G['deaths'], G['combat']
    mission, hub = G.get('mission', {}), G.get('hub', {})
    summary = G.get('summary', {})
    summary.update(SCENE_KO)   # hand-written summaries beat the first-two-lines quote

    # 꺼진 미션(active: false)은 입구가 아니다. 그 날짜와 조건을 실으면 생#103 처럼
    # 「2년차 10월 중순 · 강릉대전 참전」이라는 없는 관문이 생긴다(실제 입구는 3년 5월 ch5_4_1).
    for _sc in list(mission):
        _defs = [d for d in [mission[_sc]] + (mission[_sc].get('alts') or [])
                 if d.get('active') is not False]
        if not _defs:
            del mission[_sc]
            continue
        _mi = dict(_defs[0])
        _mi['alts'] = [dict(d, alts=[]) for d in _defs[1:]]
        mission[_sc] = _mi

    # --- save ---
    sv = json.load(open(SAVE, encoding='utf-8'))
    owned = set()
    for k in ('LibraryData1', 'LibraryData2', 'LibraryData3', 'LibraryData4'):
        owned |= {int(e['Name']) for e in sv.get(k, [])}

    # --- community sheet ---
    sheet = {}
    try:
        P = json.load(open('parsed.json', encoding='utf-8'))
        for tab, base in (('생사부', 9999), ('한청서', 19999), ('풍운사', 29999)):
            for rn, hidden, cells in P.get(tab, []):
                m = {c[0]: (c[1], c[2]) for c in cells}
                num = (m.get(1) or ('', 0))[0].strip()
                if not re.fullmatch(r'\d+(\.0)?', num):
                    continue
                n = int(float(num))
                sheet[base + n] = {
                    'no': n,
                    'name': (m.get(2) or ('', 0))[0].strip(),
                    'cond': (m.get(3) or ('', 0))[0].strip(),
                    'struck': any(v[1] for v in m.values()),
                    'hidden': hidden,
                }
    except Exception as e:
        print('sheet skip', e)

    # --- position (free action) label lookup ---
    pos_label = {}
    for pr in G['position']:
        nm = pr['name']
        head = nm.split('_')[0].lower()
        key = PLACE.get(head)
        place = g.t(f'Position/Name/{key}') if key else None
        typ = 'work' if '_work' in nm.lower() else ('free' if '_free' in nm.lower() else None)
        typ_ko = g.t(f'Position/type/{typ}') if typ else None
        pos_label[nm] = ' '.join(x for x in [place, typ_ko] if x) or nm
    for pr in G['position']:                 # 먼저 굴리는 특수 사건 표는 그 행동의 이름을 쓴다
        if pr.get('then') in pos_label:
            pos_label[pr['name']] = pos_label[pr['then']]

    def step_text(s):
        kind = s[0]
        name = s[1]
        idx = s[2] if len(s) > 2 else None
        lbl = s[3] if len(s) > 3 else None
        ilbl = s[4] if len(s) > 4 else None
        key = ilbl or (lbl.split('|')[0] if isinstance(lbl, str) else None)
        text = g.t(f'Story/{key}') if key else None
        if kind == 'Choice':
            out = {'k': '선택지', 'text': text or key or '?', 'raw': key}
            gate = s[5] if len(s) > 5 else None
            if gate:
                # 이 선택지는 조건이 맞아야 고를 수 있다. 안 맞으면 회색으로 잠긴다.
                out['lock'] = ' / '.join(G['condition'].get(gate) or []) or gate
            return out
        if kind == 'Dice':
            th = ''
            if isinstance(lbl, str) and '|' in lbl:
                th = lbl.split('|', 1)[1]
            d = dice.get(name) or {}
            props = ', '.join(f"{p['target'] or p['type']}"
                              for p in (d.get('props') or []) if p.get('target'))
            return {'k': '주사위', 'text': (text or key or '?'), 'th': th, 'props': props, 'raw': name,
                    'pr': d.get('props') or []}
        if kind == 'Switch':
            conds = sw.get(name) or []
            if isinstance(idx, int) and 1 <= idx <= len(conds):
                return {'k': '조건', 'text': conds[idx - 1] or '(무조건)', 'raw': name, 'idx': idx}
            if isinstance(idx, int) and conds and idx == len(conds) + 1:
                return {'k': '조건', 'text': '위 조건 불만족 (' + (conds[0] or '?') + ' 아님)', 'raw': name,
                        'idx': idx}
            return {'k': '조건', 'text': f'{name} (분기 {idx})', 'raw': name, 'idx': idx}
        if kind == 'else':
            return {'k': '그 외', 'text': '위 조건 모두 불만족'}
        if kind == 'Condition':
            return {'k': '조건', 'text': ' / '.join(G['condition'].get(name) or []) or name, 'raw': name}
        if kind == 'raw':
            m = re.match(r'choice_(dice|option)\w*\s*==\s*(-?\d+)', str(name) or '')
            if m:
                return {'k': '주사위' if m.group(1) == 'dice' else '선택지',
                        'text': f'{m.group(2)}번째 결과'}
        return {'k': '기타', 'text': str(name)}


    # 자유행동 허브: 한 구역의 모든 이벤트가 되돌아오는 지점. 여기를 지나 위로 올라가면
    # "이 장면에 오기까지 필요한 것"이 아니라 "그 구역 전체 이벤트의 조건"을 긁게 된다.
    HUB_STOP = {sc for sc, v in rev.items() if len(v) >= 8}

    STAGE_N = {'상순': 1, '중순': 2, '하순': 3}

    def fmt_time(t):
        if not t:
            return ''
        return f"{t['y']}년차 {t['m']}월" + (f" {t['s']}" if t.get('s') else '')

    def mission_defs(mi):
        return [mi] + (mi.get('alts') or [])

    def merged_conds(mi):
        """정의가 여럿이면 서로 택일이다. 하나라도 무조건이면 제약이 없다.

        모든 정의에 공통인 조건은 따로 빼내 그대로 남긴다. 통째로 묶어 택일로 만들면
        양쪽에서 다 요구하는 것(용지단취의 용상 호감도 60 같은)까지 선택 사항처럼 보인다.
        """
        atoms = []
        for d in mission_defs(mi):
            cs = d.get('conds') or []
            if not cs:
                return []
            atoms.append([a.strip() for c in cs for a in c.split(' 그리고 ') if a.strip()])
        if len(atoms) == 1:
            return mi.get('conds') or []
        common = [a for a in atoms[0] if all(a in g for g in atoms[1:])]
        rest = [' 그리고 '.join(a for a in g if a not in common) for g in atoms]
        out = [' 그리고 '.join(common)] if common else []
        uniq = list(dict.fromkeys(r for r in rest if r))
        if len(uniq) == 1:
            out.append(uniq[0])
        elif uniq and len(uniq) == len(rest):
            out.append('(' + ') 또는 ('.join(uniq) + ')')
        # 남은 것이 비어 있는 정의가 있으면 그쪽은 공통 조건만으로 성립한다 -> 추가 제약 없음
        return out

    def def_times(d):
        """이 정의가 실제로 쓰는 시점. 나머지 필드는 버려진 값이다.

        타입이 특정이면 _specificTime, 구간이면 _minTime~_maxTime 이다. 두 필드가 서로
        어긋나는 정의가 흔한데, 나무위키 타임라인과 대조해 이 규칙으로 맞는 것을 확인했다
        (설산행 S2500_01 은 특정 3년 5월 하순이 맞고, 청성 수련 S3001_01 은 구간
        2년 8월 하순~9월 하순이 맞다).
        """
        # dayCheck 가 False 면 시점 필드를 아예 안 본다. 조건에 적힌 것만 유효하다.
        if d.get('dayCheck') is False:
            return []
        if d.get('timeType') == '區間':
            return [t for t in (d.get('minTime'), d.get('maxTime')) if t]
        return [t for t in (d.get('time'),) if t]

    def _tkey(t):
        return (t['y'], t['m'], STAGE_N.get(t.get('s', ''), 0))

    def merged_when(mi):
        """정의가 여럿이면 가장 이른 것부터 늦은 것까지로 적는다.

        9년차 12월 하순은 상한이 없다는 표시다(5곳). 그대로 적으면 없는 연도가 보인다.
        """
        raw = [t for d in mission_defs(mi) for t in def_times(d)]
        openended = any(t['y'] >= 9 for t in raw)
        ts = sorted({(_tkey(t), fmt_time(t)) for t in raw if t['y'] < 9})
        if not ts:
            return ''
        if openended:
            return f'{ts[0][1]} 이후'
        if len(ts) > 1:
            return f'{ts[0][1]} ~ {ts[-1][1]}'
        return ts[0][1]

    def origin_of(script, depth=0, seen=None):
        """walk up to the nearest mission entry or free-action hub"""
        seen = seen or set()
        if script in mission:
            mi = mission[script]
            # merged_when 이 비면 정말로 시점이 없는 것이다(dayCheck False).
            # 예전에는 여기서 min/max 로 되돌아갔는데, 그게 바로 안 봐야 할 값이다.
            when = merged_when(mi)
            return {'kind': '사건', 'when': when, 'where': mi.get('place') or '',
                    'conds': merged_conds(mi), 'via': script, 'hops': depth,
                    'summary': summary.get(script, ''),
                    'timeType': mi.get('timeType') or '', 'stage': mi.get('stage') or ''}
        if script in hub:
            return {'kind': '자유행동', 'when': '', 'where': hub[script] or '',
                    'conds': [], 'via': script, 'hops': depth, 'timeType': '', 'stage': '',
                    'summary': summary.get(script, '')}
        if script in HUB_STOP:
            return {'kind': '자유행동', 'when': '', 'where': hub.get(script, ''),
                    'conds': [], 'via': script, 'hops': depth, 'timeType': '', 'stage': '',
                    'summary': summary.get(script, ''), 'viaHub': True}
        if depth > 6 or script in seen:
            return None
        seen = seen | {script}
        best = None
        for p in rev.get(script, []):
            if p['kind'] == 'position':
                src = p['from'].replace('[자유행동] ', '')
                tw = TRAVEL_WHEN.get(src)
                cand = {'kind': '자유행동', 'when': tw[0] if tw else '',
                        'where': pos_label.get(src, src),
                        'conds': [x for x in [p.get('cond')] if x], 'via': src,
                        'hops': depth, 'timeType': '', 'stage': ''}
                if tw:
                    cand['travel'] = tw[1]
                if best is None or cand['hops'] < best['hops']:
                    best = cand
                continue
            r = origin_of(p['from'], depth + 1, seen)
            if r and (best is None or r['hops'] < best['hops']):
                best = r
        return best

    # 여행 자리는 SetCurrentTravelScript 로 켜져서 그래프에 들어오는 간선이 없다. 그래서
    # 시점도 갈래도 통째로 비어 「경로 N가지 중 하나」만 남는다. 여행을 여는 자리를 찾아
    # 손으로 적는다 — 조건은 적지 않는다. 여행 조우는 실제로 조건 없는 추첨이다.
    TRAVEL_WHEN = {
        'Travel_001':      ('1년차 10월 중순', '남궁가 연회 가는 길 (ch2_2_3_1)'),
        'Travel_002':      ('1년차 11월 상순', 'ch2_2_4_1 여행'),
        'Travel_302':      ('2년차 8월 상순',  '공동파 유학 가는 길 (ch3_2_1) · 공동파 회차 전용'),
        'Travel_310':      ('2년차 10월 상순', 'ch3_15 여행'),
        'Travel_401':      ('3년차 1월 중순',  '대사형 하산 길 (ch4_7_6) · 따라간 회차 전용'),
        'Travel_601_01':   ('3년차 9월 상순',  'ch6_3_2 여행'),
        'Travel_601_02':   ('3년차 9월 상순',  'ch6_3_2 여행'),
        'Travel_S2501_01': ('3년차 6월 중순 출발',
                            '설산행 여행 (당문 회의 meeting_option_502_01 에서 출발) · 탈백문 회차 전용'),
        'Travel_S2503_01': ('3년차 6~7월',     '설산 체류 중 (S2503) · 탈백문 회차 전용'),
    }

    def origin_root(script, depth=0, seen=None):
        """last resort: topmost ancestor script, so at least the flow is visible"""
        seen = seen or set()
        if depth > 8 or script in seen:
            return None
        seen = seen | {script}
        ups = [p for p in rev.get(script, []) if p['kind'] != 'position']
        if not ups:
            return {'kind': '스토리 진행', 'when': '', 'where': '', 'conds': [],
                    'via': script, 'hops': depth, 'timeType': '', 'stage': '', 'rootOnly': True,
                    'summary': summary.get(script, '')}
        for p in ups:
            r = origin_root(p['from'], depth + 1, seen)
            if r:
                return r
        return None

    def origin_guess(script):
        """fallback: nearest mission whose name is a prefix of this script"""
        parts = script.split('_')
        for k in range(len(parts) - 1, 1, -1):
            cand = '_'.join(parts[:k])
            if cand in mission:
                o = origin_of(cand)
                if o:
                    o = dict(o, guess=True)
                    return o
        return None

    def entry_of(script, depth=0, seen=None):
        """walk up rev; return list of entry descriptions"""
        seen = seen or set()
        if script in seen or depth > 3:
            return []
        seen = seen | {script}
        out = []
        for p in rev.get(script, [])[:6]:
            if p['kind'] == 'position':
                out.append({'type': 'free', 'label': pos_label.get(p['from'].replace('[자유행동] ', ''), p['from']),
                            'result': kind_ko(p.get('outcomeKind')), 'rate': p.get('rate'),
                            'cond': p.get('cond') or '', 'src': p['from']})
            else:
                ups = entry_of(p['from'], depth + 1, seen)
                node = {'type': 'script', 'label': p['from'], 'kind': p['kind'],
                        'summary': summary.get(p['from'], ''),
                        'steps': [step_text(s) for s in (p.get('path') or [])], 'up': ups}
                out.append(node)
        return out


    # ---- route tags: which characters / factions this item involves ----
    CAST = ['소사매', '대사형', '이사형', '삼사형', '사사형', '장문인', '서행',
            '엽운주', '엽운상', '용상', '용연', '우소매', '하후란', '욱죽', '위국',
            '상관형', '복운', '남궁심', '남궁천', '남궁원', '윤지평', '송비', '조규',
            '단하자', '신도룡', '번소천', '금오상인', '당교교', '당삼', '당대경',
            '만리붕정', '해무진', '이부귀', '화중선', '조활', '마부귀', '석공원']
    FACTION = ['공동파', '청성파', '아미파', '숭산파', '점창파', '금향궁', '남궁세가',
               '상관세가', '개방', '비석방', '서무림맹', '무림맹', '전진교', '당문']

    def tags_of(item):
        blob = json.dumps(item, ensure_ascii=False)
        out = [c for c in CAST if c in blob]
        out += [f for f in FACTION if f in blob]
        return out

    TYPE = {1: '생사부', 2: '한청서', 3: '풍운사'}
    ids = sorted(int(x) for x in (G.get('library') or []) if str(x).isdigit())
    if not ids:
        ids = list(range(10000, 10105)) + list(range(20000, 20054)) + list(range(30000, 30020))
    items = []
    for i in ids:
        sid = str(i)
        typ = TYPE.get(i // 10000, '기타')
        title = g.t(f'Library/Title/{sid}') or ''
        desc = g.t(f'Library/Desc/{sid}') or ''
        paths = []
        for d in deaths.get(sid, []):
            paths.append({
                'script': d['script'],
                'via': d['via'],
                'combat': d.get('combat'),
                # 전투 이름은 개발자 메모라 중국어다. 읽는 사람이 한국어라 옮겨서 싣는다.
                'combatDesc': combat_ko((combat.get(d.get('combat')) or {}).get('desc', '')),
                'steps': [step_text(s) for s in d['path']],
                'entries': entry_of(d['script']),
                'summary': summary.get(d['script'], ''),
                'origin': (origin_of(d['script']) or origin_guess(d['script'])
                           or origin_root(d['script'])),
            })
        items.append({
            'id': i,
            'type': typ,
            'no': i - (i // 10000) * 10000 + 1,
            'title': title,
            'desc': desc,
            'owned': i in owned,
            'reachable': bool(paths),
            'paths': paths,
            'sheet': sheet.get(i),
        })

    for it in items:
        it['tags'] = tags_of(it)


    # ---- 도달 불가 판정: 아무데서도 세팅되지 않는 플래그를 요구하는 항목 ----
    import os as _os
    from flag_ko import FLAG_KO
    setv = collections.defaultdict(set)
    addf = set()
    # 자유행동 자리를 여는 스크립트. Position("X") 를 부르는 쪽이 그 자리의 입구다.
    POS_CALLER = {}
    for fn in sorted(_os.listdir('lua')):
        t = open(_os.path.join('lua', fn), encoding='utf-8', errors='replace').read()
        for mm in re.finditer(r'statmodifymanager\.SetFlag\("([A-Za-z0-9_]+)",\s*(-?\d+)\)', t):
            setv[mm.group(1)].add(int(mm.group(2)))
        for mm in re.finditer(r'statmodifymanager\.AddFlag\("([A-Za-z0-9_]+)"', t):
            addf.add(mm.group(1))
        if '__' not in fn:      # zh-cn/zh-tw 사본은 그래프에 노드가 없다
            for mm in re.finditer(r'checkpointmanager\.Position\("([A-Za-z0-9_]+)"\)', t):
                POS_CALLER.setdefault(mm.group(1), fn[:-4])
    for ref, o in g.all_of('MissionCheckData', 'Mortal.Core.MissionCheckData'):
        if '__error' in o:
            continue
        f = ref[0]
        for key in ('_modifyFlagsWhenTrue', '_modifyFlagsWhenFalse'):
            for fm in (o.get(key) or []):
                fl = g.resolve(f, fm.get('_data')) if fm.get('_data') else None
                nm2 = g.name(fl) if fl else None
                if nm2:
                    setv[nm2].add(fm.get('_value'))
    default = {}
    for ref, o in g.all_of('FlagData', 'Mortal.Core.FlagData'):
        if '__error' not in o:
            default[o['__name']] = o.get('_default', 0)
    label2id = {}
    for fid, ko in FLAG_KO.items():
        label2id.setdefault(ko, fid)
    for fid in default:
        label2id.setdefault(fid, fid)

    # 꺼진 미션 안에서만 세워지는 값은 이 빌드에서 아무도 만들 수 없다.
    # (「엽운상 공략 중」을 여기에 넣었던 것은 틀렸다 — S0208_01 미션은 꺼져 있지만 5장이
    #  그 장면을 직접 부른다. mk_flagdep.mission_gate 가 이제 그 경우를 관문으로 치지 않는다.)
    try:
        _dep = json.load(open('flagdep.json', encoding='utf-8'))
    except OSError:
        _dep = {}
    DEAD_SET = {(f, int(v)) for f, e in _dep.items() for v, pl in e.items()
                if v != 'add' and isinstance(pl, list) and pl
                and all(x.get('misDead') or x.get('optDead') for x in pl)}

    # 세우는 자리가 있어도 그 자리의 전제가 끝내 못 서면 못 만든다. 공동 영전 서행 참전(M50010)은
    # M30026 == 1(세우는 곳 없음) 이나 M50010 == 2(M50010 == 1 이 전제) 뒤에서만 1 이 된다.
    # 기본값에서 출발해 전제가 다 서는 setter 만 받아들이는 고정점으로 그런 고리를 찾는다.
    # 못 읽은 조건이 있는 setter(unknown)는 열린 것으로 본다 — 못 한다고 잘못 말하는 쪽이 더 나쁘다.
    def _cands(f):
        return {int(v) for v, pl in (_dep.get(f) or {}).items() if v != 'add' and isinstance(pl, list) and pl}
    _ok = {(f, v) for f, v in default.items()}
    _grow = True
    while _grow:
        _grow = False
        for f, e in _dep.items():
            for v in _cands(f):
                if (f, v) in _ok:
                    continue
                for x in e[str(v)]:
                    if x.get('misDead') or x.get('optDead'):
                        continue
                    if x.get('unknown') or all(
                            nf.startswith('@') or nf in addf or nf not in default or (nf, int(nv)) in _ok
                            or (int(nv) in setv.get(nf, ()) and str(int(nv)) not in (_dep.get(nf) or {}))
                            for nf, nv in x.get('need') or []):
                        _ok.add((f, v)); _grow = True
                        break
    UNSAT = {(f, v) for f in _dep for v in _cands(f) if (f, v) not in _ok and (f, v) not in DEAD_SET
             and f not in addf}

    def _reach(flag, val):
        if flag in addf: return True
        if (flag, val) in DEAD_SET or (flag, val) in UNSAT: return False
        if flag not in default: return None
        if val == default[flag]: return True
        return val in setv.get(flag, set())

    RE_FLAGEQ = re.compile(r'\[플래그 ([^\]]+)\]\s*==\s*(-?\d+)')

    def _blockers(text):
        out = []
        for lab, v in RE_FLAGEQ.findall(text or ''):
            fid = label2id.get(lab.strip())
            if fid and _reach(fid, int(v)) is False:
                if f'[플래그 {lab.strip()}] == {v} 아님' in text:
                    continue
                out.append((fid, lab.strip(), int(v)))
        return out

    def _path_blockers(it):
        res, nb = [], 0
        for p in it['paths']:
            b = _blockers(' '.join(x['text'] for x in p['steps']))
            if b:
                nb += 1
                res += b
        return nb, res

    # 1차 판정 -> 이미 획득한 항목을 막는 플래그는 엔진이 쓰는 것이므로 화이트리스트
    engine_written = set()
    for it in items:
        if not it['owned'] or not it['paths']:
            continue
        nb, res = _path_blockers(it)
        if nb == len(it['paths']):
            engine_written |= {r[0] for r in res}

    def _blockers2(text):
        return [b for b in _blockers(text) if b[0] not in engine_written]

    # ---- 현재 빌드에서 도달할 수 없는 경로 ----
    # 근거 두 가지(18장).
    #  ① lua 가 부르는 Condition 이름 중 게임 데이터에 없는 것이 5개 있다(XXX 등 자리표시자).
    #     그런 조건으로 잠긴 대화 선택지는 항상 "~x"(비활성)라 영구히 고를 수 없다.
    #  ② act* 는 전투 desc 가 活動(활동) 모드이고, lua·미션·자유행동·C# 어디에도 진입점이 없다.
    RE_DEADOPT = re.compile(
        r'local\s+(\w+)\s*=\s*checkpointmanager\.Condition\("([^"]+)"\)\s*\n'
        r'\s*\w+\[\d+\]\s*=\s*\1\s+and\s+"[^"+]+\+([^+"]+)\+')
    RE_DEADXXX = re.compile(r'\w+\[\d+\]\s*=\s*XXX\s+and\s+"[^"+]+\+([^+"]+)\+')
    _known_cond = set(G.get('condition', {}))
    DEAD_OPT = set()
    for _fn in os.listdir('lua'):
        if not _fn.endswith('.lua') or '__' in _fn:
            continue
        _t = open(os.path.join('lua', _fn), encoding='utf-8', errors='replace').read()
        for _v, _c, _o in RE_DEADOPT.findall(_t):
            if _c not in _known_cond:
                DEAD_OPT.add(_o)
        # Condition 을 거치지 않고 XXX 를 바로 쓰는 줄도 있다. 정의가 없으니 늘 거짓이다.
        # ch6_3_5 의 「홀로 강릉으로 간다」가 이 모양이라, 금향궁 방문이 강제인 것을 못 보고 있었다.
        DEAD_OPT.update(RE_DEADXXX.findall(_t))

    def _edge_dead(e):
        for st in (e.get('path') or []):
            if st and st[0] == 'Choice' and len(st) > 4 and st[4] in DEAD_OPT:
                return True
        return False

    _pos_scripts = {o['script'] for pr in G['position'] for o in pr['outcomes'] if o.get('script')}
    UNREACHABLE = {s for s in G['scripts'] if s.startswith('act')}   # 活動 모드
    _grew = True
    while _grew:
        _grew = False
        for _s in G['scripts']:
            if _s in UNREACHABLE or _s in mission or _s in _pos_scripts or _s in hub:
                continue
            _ins = rev.get(_s) or []
            if not _ins:
                continue          # 진입점 없음은 신호가 약하다(메뉴에서 부르는 것이 많다)
            for _e in _ins:
                _src = _e.get('from')
                if not isinstance(_src, str) or _src.startswith('['):
                    break         # 자유행동에서 들어옴 = 살아있음
                if _src in UNREACHABLE:
                    continue
                if any(not _edge_dead(x) for x in G['edges'].get(_src, []) if x.get('to') == _s):
                    break
            else:
                UNREACHABLE.add(_s)
                _grew = True

    for it in items:
        it['blocked'] = False
        it['blockReason'] = []
        if not it['paths']:
            continue
        nb, res = 0, []
        for p in it['paths']:
            b = _blockers2(' '.join(x['text'] for x in p['steps']))
            p['blocked'] = bool(b)
            if b:
                nb += 1
                res += b
        if nb == len(it['paths']) and res:
            it['blocked'] = True
            it['blockReason'] = sorted({
                f'{lab}({fid}) == {v} 를 세우는 사건이 이 빌드에서 꺼져 있음'
                if (fid, v) in DEAD_SET else
                f'{lab}({fid}) == {v} 를 세우는 자리가 전부 이 빌드에서 못 서는 값을 전제로 함'
                if (fid, v) in UNSAT else
                f'{lab}({fid}) == {v} 를 만드는 곳이 게임 어디에도 없음'
                for fid, lab, v in res})
        # 도달 불가 장면만 남은 항목도 막힌 것이다(18장)
        _un = [p for p in it['paths'] if p.get('script') in UNREACHABLE]
        for p in _un:
            p['blocked'] = True
        if _un and len(_un) == len(it['paths']):
            it['blocked'] = True
            _why = ('活動(이벤트) 모드라 현재 빌드에 진입점이 없음'
                    if it['paths'][0].get('script', '').startswith('act')
                    else '그 장면으로 가는 선택지가 게임에 없는 조건으로 잠겨 있음')
            it['blockReason'] = sorted(set(it['blockReason']) | {_why})

    # 게임 파일로 불가를 확인했는데 위의 자동 판정이 못 잡는 항목. 근거를 같이 적는다.
    # 시트가 「불가」라고만 한 것은 여기 넣지 않는다 — 생#82 는 시트가 불가라 했지만
    # 하후란 갈래가 열려 있었다. 우리가 확인한 것만 막는다.
    CONFIRMED_BLOCK = {
        10076: '무림대회 전투 다섯 곳은 deadEnd 가 아니라 져도 스크립트가 다른 결과를 준다. deadEnd 인 CL_1618_01(금향궁 화중선 도전)은 [M60019] == 1 로 잠겨 있고, 그 전제 M40048 을 세우는 곳이 없다',
        10082: 'ch8_2_1 에서 「우소매 공략 중(G11004) == 1」 가지로만 가는데 G11004 를 1 로 만드는 곳이 없다',
        10089: '[결투 범용 이벤트 플래그 5] 가 ch8_3_2_3_1 시작에서 0 으로 깔리고, 1 로 만드는 가지는 「상관형 공략 중 == 1」뿐인데 상관형 공략 중은 이 빌드에서 안 선다',
    }
    for it in items:
        why = CONFIRMED_BLOCK.get(it['id'])
        if why and not it.get('owned'):
            it['blocked'] = True
            it['blockReason'] = sorted(set(it.get('blockReason') or []) | {why})

    # ---- run planner: per-path route requirement + sortable time ----
    # 부정형은 뺀다. 그대로 실으면 화면 쪽이 == N 으로 읽어 값을 거꾸로 못박는다.
    # 부정은 절 전체에 걸리므로(A 그리고 B 아님) 숫자 바로 뒤만 보면 앞쪽 비교를 놓친다.
    # 덩어리에 '아님'이 있으면 통째로 버린다.
    RE_FLAGCHUNK = re.compile(r'\[플래그[^\]]{2,80}\]\s*(?:==|>=)\s*-?\d+')
    RE_POS = re.compile(r'\[플래그 (\S+) 공략 중\] == 1(?! 아님)')
    RE_NEG = re.compile(r'\[플래그 (\S+) 공략 중\] == 1 아님')

    def when_key(w):
        mm = re.match(r'(\d+)년차 (\d+)월(?: (상순|중순|하순))?', w or '')
        if not mm:
            return None
        return int(mm.group(1)) * 1000 + int(mm.group(2)) * 10 + STAGE_N.get(mm.group(3) or '', 0)

    # 조건이 **선택지를 여는 자리**에 걸려 있으면 경로 조건으로 안 잡힌다. 경로가 요구하는 값이 그 장면
    # 안에서 서는 임시 플래그이고 그 값을 세우는 자리가 잠긴 선택지뿐이면, 그 잠금(flagdep 의 gate)을
    # 경로 조건으로 올린다. 잠금이 요구하는 플래그를 세우는 자리가 전부 어떤 루트를 전제로 하면 그것도 싣는다.
    # 풍#20: ch6_8_4 의 「엽운상과 함께 간다」(임시 플래그 2 = 2)는 Condition Ch_6_8_4_002
    #   = [위국 공략 중] == 0 그리고 [엽운상 무림대회 동행] == 1 일 때만 눌린다. 그 동행 플래그는
    #   S0603_02 에서 서는데, S0603_01 이 [엽운상 공략 중] == 1 일 때만 그리로 넘긴다.
    def gate_conds(p):
        out = []
        for x in p['steps']:
            if ' 또는 ' in x['text'] or '아님' in x['text']:
                continue
            for lab, v in RE_FLAGEQ.findall(x['text']):
                fid = label2id.get(lab.strip())
                if not fid or not fid.startswith('A0'):
                    continue
                gates = {tuple(r.get('gate') or ()) for r in (_dep.get(fid) or {}).get(v, [])
                         if r.get('sc') == p['script']}
                if len(gates) != 1:
                    continue        # 그 장면에서 안 서거나, 자리마다 잠금이 다르다
                for g in gates.pop():
                    if ' 또는 ' in g or '아님' in g:
                        continue
                    out.append(g)
                    for lab2, v2 in RE_FLAGEQ.findall(g):
                        fid2 = label2id.get(lab2.strip())
                        e2 = _dep.get(fid2) or {}
                        places = [r for r in e2.get(v2, []) if not r.get('misDead') and not r.get('optDead')]
                        if not places or e2.get('add') or default.get(fid2) == int(v2):
                            continue
                        common = set.intersection(*[{(a, b) for a, b in r.get('need') or []} for r in places])
                        out += [f'[플래그 {FLAG_KO[a]}] == 1' for a, b in sorted(common)
                                if b == 1 and a.startswith('G110') and a in FLAG_KO]
        return out

    # 위 추출이 못 따라가는 것을 대본을 읽고 손으로 적는 자리 (항목 id → 조건 조각).
    EXTRA_COND = {}

    for it in items:
        # 막힌 경로는 판정에서 뺀다. 남겨 두면 생#42 처럼 못 서는 「서행 참전」 경로가 갈래 조건 없이 「가능」으로 남는다.
        if any(p.get('blocked') for p in it['paths']) and not all(p.get('blocked') for p in it['paths']):
            it['deadPaths'] = [p for p in it['paths'] if p.get('blocked')]
            it['paths'] = [p for p in it['paths'] if not p.get('blocked')]
        opts = []
        for p in it['paths']:
            txt = ' '.join(x['text'] for x in p['steps'])
            o = p.get('origin') or {}
            for c in (o.get('conds') or []):
                txt += ' ' + c
            txt += ' ' + ' '.join(gate_conds(p) + EXTRA_COND.get(it['id'], []))
            req = sorted(set(RE_POS.findall(txt)) - set(RE_NEG.findall(txt)))
            kinds = sorted({x['k'] for x in p['steps']})
            opts.append({
                'req': req,
                'when': o.get('when', ''), 'wk': when_key(o.get('when', '')),
                'where': o.get('where', ''), 'kind': o.get('kind', ''),
                'script': p['script'], 'kinds': kinds,
                'save': bool({'선택지', '주사위'} & set(kinds)),
            })
        it['opts'] = opts
        it['anyFree'] = any(not o['req'] for o in opts)
        it['reqRoutes'] = sorted({r for o in opts for r in o['req']})


    # ---- 위상정렬로 시점 추정 (미션 시점이 없는 장면) ----
    import sys as _sys
    _sys.setrecursionlimit(20000)
    known_wk = {}
    known_last = {}     # 구간 미션은 끝이 따로 있다. 「마지막 기회」는 이쪽으로 잰다
    for sc, mi in mission.items():
        # 정의가 여럿이면 가장 이른 시점을 쓴다 (가장 빠르게 도달할 수 있는 때)
        ks = [t['y'] * 1000 + t['m'] * 10 + STAGE_N.get(t.get('s', ''), 0)
              for d in mission_defs(mi) for t in def_times(d) if t['y'] < 9]
        if ks:
            known_wk[sc] = min(ks)
            known_last[sc] = max(ks)
    edges_g = G.get('edges', {})
    _me, _ml = {}, {}

    def _earliest(sc, stack=frozenset()):
        if sc in known_wk: return known_wk[sc]
        if sc in HUB_STOP: return None
        if sc in _me: return _me[sc]
        if sc in stack: return None
        _me[sc] = None
        vals = []
        for p in rev.get(sc, []):
            if p['kind'] == 'position':
                continue
            v = _earliest(p['from'], stack | {sc})
            if v is not None: vals.append(v)
        _me[sc] = max(vals) if vals else None
        return _me[sc]

    def _latest(sc, stack=frozenset()):
        if sc in known_wk: return known_wk[sc]
        if sc in _ml: return _ml[sc]
        if sc in stack: return None
        _ml[sc] = None
        vals = []
        for e in edges_g.get(sc, []):
            v = _latest(e['to'], stack | {sc})
            if v is not None: vals.append(v)
        _ml[sc] = min(vals) if vals else None
        return _ml[sc]

    def _is_free(sc, depth=0, seen=None):
        """자유행동에서 출발하는 장면인가"""
        seen = seen or set()
        if depth > 6 or sc in seen: return False
        seen = seen | {sc}
        for p in rev.get(sc, []):
            if p['kind'] == 'position': return True
            if _is_free(p['from'], depth + 1, seen): return True
        return False

    # 미션으로 시점이 확인된 것만 모아 챕터별 범위를 낸다. 범위가 6개월을 넘으면
    # 추정이라 부르기 어려우므로 버린다(ch2_ 는 12개월, ch7_ 은 13개월이라 빠진다).
    def _chapter_of(sc):
        m = re.match(r'(ch\d+)_', sc or '')
        return m.group(1) if m else None

    _span = {}
    for _sc, _mi in mission.items():
        _c = _chapter_of(_sc)
        _ks = [t['y'] * 1000 + t['m'] * 10
               for x in mission_defs(_mi) for t in def_times(x) if t['y'] < 9]
        if not _ks or not _c:
            continue
        lo, hi = _span.get(_c, (min(_ks), max(_ks)))
        _span[_c] = (min(lo, *_ks), max(hi, *_ks))
    def _months(k):
        return (k // 1000) * 12 + (k % 1000) // 10

    # 범위가 6개월을 넘으면 추정이라 부르기 어렵다. ch2_(12개월)와 ch7_(13개월)이 여기서 빠진다.
    CHAPTER_SPAN = {c: v for c, v in _span.items()
                    if _months(v[1]) - _months(v[0]) <= 6}

    def _fmt_wk(k):
        if k is None: return ''
        return f'{k // 1000}년차 {(k % 1000) // 10}월'

    for it in items:
        for o in it['opts']:
            if o['wk'] is not None:
                o['timeKind'] = '확정'
                continue
            sc = o['script']
            a, b = _earliest(sc), _latest(sc)
            ch = CHAPTER_SPAN.get(_chapter_of(sc))
            # 챕터는 순서대로 흐르므로, 그 챕터가 시작하기 전에는 일어날 수 없다.
            # 그래프 하한만 쓰면 ch5 사건이 "2년차 10월 이후"로 보여 곧 올 것처럼 읽힌다.
            if ch and not _is_free(sc):
                a = ch[0] if a is None else max(a, ch[0])
                b = ch[1] if b is None else min(b, ch[1])
            if a is None and b is None:
                if ch and not _is_free(sc):
                    o['wkEst'] = ch[0]
                    o['wkMax'] = ch[1]
                    o['timeKind'] = '챕터 추정'
                    o['estText'] = f'{_fmt_wk(ch[0])} ~ {_fmt_wk(ch[1])} 사이 (챕터 추정)'
                    continue
                o['timeKind'] = '상시' if _is_free(sc) else '미상'
                continue
            o['wkEst'] = a if a is not None else b
            # 상한도 싣는다. 하한만 있으면 창이 이미 닫힌 항목이 「아직 가능」으로 남는다.
            if b is not None:
                o['wkMax'] = b
            o['timeKind'] = '추정'
            lo, hi = _fmt_wk(a), _fmt_wk(b)
            if lo and hi and lo == hi: o['estText'] = lo + ' 무렵'
            elif lo and hi: o['estText'] = f'{lo} 이후 ~ {hi} 이전'
            elif lo: o['estText'] = f'{lo} 이후'
            else: o['estText'] = f'{hi} 이전'


    # ---- 수치 요구 추출 ----
    RE_STAT = re.compile(r'\[([^\]\[]+)\]\s*(>=|<=|==|!=|>|<)\s*(-?\d+)')
    SKIP_PREFIX = ('플래그', '기술', '비급', '잡물', '귀중품', '시점', '도감', '서적', '개발', '난수')

    def stat_reqs(texts):
        out = []
        for t in texts:
            # 「행동력 N 이하」는 맞춰야 하는 조건이 아니라 시점 표기다. 행동력은 행동마다
            # 1 씩 자동으로 줄고 더 쓰거나 아낄 수 없어서, 그 순의 끝자락을 가리킬 뿐이다.
            # 미션 209개 중 17개가 쓰는데 전부 <=1 또는 <=2 다.
            t = re.sub(r'\[행동력\]\s*<=\s*[12]', '(그 순의 끝 무렵)', t)
            neg = ' 아님' in t
            found = [(n, op, int(v)) for n, op, v in RE_STAT.findall(t)
                     if not n.startswith(SKIP_PREFIX)]
            # 'A 또는 B' 는 택일이다. 부정형은 드모르간으로 전부 필요가 되므로 그대로 편다.
            if found and not neg and ' 또는 ' in t and len(found) > 1:
                out.append({'any': [{'stat': n, 'op': op, 'val': v, 'neg': False}
                                    for n, op, v in found]})
                continue
            # '위 조건 불만족 (...)' 은 괄호 안 전체를 부정한다. 안에 비교가 둘 이상이면
            # 드모르간 때문에 "각각을 부정"이 아니므로, 그 사실을 solo 로 남겨 소비 쪽이 판단하게 한다.
            for n, op, v in found:
                out.append({'stat': n, 'op': op, 'val': v, 'neg': neg,
                            'solo': len(RE_STAT.findall(t)) == 1})
        # 중복 제거
        seen, uniq = set(), []
        for r in out:
            if 'any' in r:
                k = ('any',) + tuple(sorted((a['stat'], a['op'], a['val']) for a in r['any']))
            else:
                k = (r['stat'], r['op'], r['val'], r['neg'], r.get('solo'))
            if k not in seen:
                seen.add(k); uniq.append(r)
        return uniq

    # ---- 경로가 어느 갈래(유학 선택)에 속하는가 ----
    # ch2_4 라인은 M20008 을 아예 읽지 않아 조건 텍스트로는 갈래를 알 수 없다.
    # 미션 _desc(唐門留學 / 崆峒留學 / 青城)를 씨앗으로 접두사 규칙을 세우고
    # 그래프 전방 도달성 · 경로 혼합 · desc 세 가지로 모순 0건을 확인했다(17장).
    BRANCH_PREFIX = (
        # ch2_6_ 남궁기 고문, ch2_8_ 사사형 귀환. 둘 다 잔류 라인에서만 미션이 켜지고
        # 공동파 라인에서 들어오는 길이 없다. 나무위키 타임라인도 잔류 표에만 싣는다.
        (('ch2_4_', 'ch3_3_', 'ch3_1_', 'ch2_6_', 'ch2_8_', 'section_02_'), '0'),
        (('ch2_5_', 'ch3_2_', 'section_01_'), '2'),        # 공동파 유학
    )

    # 청성행은 유학 선택 플래그를 건드리지 않는다. 잔류 라인 안에서 ch2_4_9_2 가
    # [엽운상 당문에 있음] + [마음에 둔 사람 == 엽운상] 으로 갈라, 참이면 ch3_3_→ch3_1_,
    # 거짓이면 ch2_4_10_ 으로 간다. 그래서 둘은 같은 회차에 못 담긴다.
    QC_PREFIX = (
        # section_02_ 는 청성 체류 자유행동이다. 들어오는 곳이 S3001~S3006 과 ch3_1_*,
        # ch3_3_2_2_4 뿐이라 전부 청성 라인이다. 전에 "양쪽에서 닿는다"고 뺐던 것은 틀렸다.
        (('ch3_3_', 'ch3_1_', 'section_02_'), '1'),        # 청성으로 떠남
        # ch2_6_ 은 미션 M2010_03 으로만 열리고 그 미션을 켜는 곳은 ch2_4_10_3 하나뿐이다.
        # ch2_8_ 은 진입로가 둘이라(ch2_4_5_3 과 ch2_6_3_*) 청성행 여부를 못 박지 않는다.
        (('ch2_4_10_', 'ch2_6_'), '0'),                    # 당문에 그대로
    )

    def branch_of(path):
        """이 경로의 장면 자체가 어느 갈래에 있는가.

        상류까지 훑으면 안 된다. 조상 사슬이 허브를 넘어 엉뚱한 라인에 닿으면
        (예: 당문 포위전 항목이 ch2_4_ 조상을 갖게 되면) 갈래가 뒤집힌다.
        장면 스크립트와 그 직전 출처만 본다.
        """
        return _by_prefix(path, BRANCH_PREFIX)

    def qc_of(path):
        """청성행 여부. 갈래와 같은 규칙이되 접두사 표만 다르다."""
        return _by_prefix(path, QC_PREFIX)

    # 8장은 미션이 둘로 갈린다 — M7001_01 圍攻唐門(ch8_1_1_1 → ch8_6_*) 과
    # M7002_01 東西武林盟(ch8_1_2 → ch8_2_*·ch8_3_*·ch8_4_*). 두 하류는 거의 안 겹친다.
    # 갈림이 미션 시퀀스에 있어서 조건문으로는 안 잡히므로 접두사로 적는다.
    # ch8_6_3_2 는 연인별 후일담이 전부 모인 자리라(한청서 37~46) 이 한 줄이 크다.
    # 한때 (('ch8_6_','ch8_1_1_'), 'league', '4') 를 넣었다가 뺐다. 「너의 결정 == 4」 만으로는
    # 이 라인이 닫히지 않는다 — ch7_5_6_1 이 서무림맹을 고른 뒤에도 **문파를 하나도 못 모으면**
    # 임시 플래그 1 을 세워 圍攻唐門(M7001_01) 으로 보낸다. 작성자가 「결성이 실패하는 거 아니냐」고
    # 물어 드러났다. 조건이 네 문파의 설득 결과에 걸려 있어 접두사 한 줄로는 못 적으므로,
    # save_read 의 BRANCHED 「8장 라인 갈림」이 조건을 그대로 보여 주는 쪽으로 옮겼다.
    NOT_BRANCH = ()

    # 플래그가 서려면 갈래·심계가 먼저 정해져 있어야 하는 것 (청성행, 그 시점의 심계). 엽운주는 3년 1월에 떠나
    # 청성 회차만 붙잡는다. 심계는 reqs 에 안 넣는다 — 청성행(엽운상)과 겹쳐 플래너가 불가로 읽는데 실제로는 변심으로 된다.
    FLAG_IMPLIES = {
        '[플래그 공동 영전 - 엽운주 참전] == 1': ('1', None),
        '[플래그 공동 영전 - 소사매 참전] == 1': (None, '3년차 5월 상순 공동 영전(ch5_4_4) 때 심계 소사매 · 엽운상 루트로 넘어가면 공동 영전을 건너뛴다'),
    }

    def not_branch(path):
        """이 경로가 「그 갈래를 고르지 않았을 때만」 열리는가. {fork: 안 되는 값}"""
        out = {}
        for v in (path.get('script'), (path.get('origin') or {}).get('via')):
            if not isinstance(v, str):
                continue
            for pres, fork, bad in NOT_BRANCH:
                if v.lower().startswith(pres):
                    out[fork] = bad
        return out

    def _by_prefix(path, table):
        got = set()
        for v in (path.get('script'), (path.get('origin') or {}).get('via')):
            if not isinstance(v, str):
                continue
            # 자유행동 자리는 Section_01_02_Start 처럼 대문자로 적힌다. 표는 스크립트
            # 이름을 소문자로 담고 있어서, 탈백 숲 항목들이 갈래를 잃고 있었다.
            v = v.lower()
            for pres, b in table:
                if v.startswith(pres):
                    got.add(b)
        return got.pop() if len(got) == 1 else None

    def flat_reqs(rs):
        """택일 그룹을 펼쳐 (스탯, 연산자, 값) 집합으로."""
        return {(a['stat'], a['op'], a['val'])
                for r in rs for a in (r['any'] if 'any' in r else [r])}

    # ---- 모든 길에 걸린 조건만 필수다 ----
    # 들어오는 길이 여럿이면 길마다 스위치가 다르다. 그것을 전부 모아 요구로 실으면
    # 생#96 처럼 「엽운상 호감도 30 미만」이라는 없는 조건이 생긴다 — 30 이상인 갈래도
    # 같은 선택지로 다시 모인다. 스위치 가지 하나를 그래프에서 빼 보고, 그래도 켜진 입구에서
    # 닿으면 그 가지는 필수가 아니다.
    edges_all = G['edges']
    _need_cache = {}

    def need_of(script):
        if script in _need_cache:
            return _need_cache[script]
        nodes, st = set(), [script]
        while st:
            x = st.pop()
            if x in nodes:
                continue
            nodes.add(x)
            for r in rev.get(x) or []:
                f = str(r.get('from'))
                if not f.startswith('['):
                    st.append(f)
        roots = set()
        for x in nodes:
            rs = rev.get(x) or []
            if x in mission or not rs or any(str(r.get('from')).startswith('[') for r in rs):
                roots.add(x)
        adj, pairs = {}, set()
        for x in nodes:
            for e in edges_all.get(x) or []:
                if e['to'] not in nodes or e.get('kind') == 'combat':
                    continue
                ps = {(q[0], q[1], q[2]) for q in (e.get('path') or []) if q[0] in ('Switch', 'Dice')}
                adj.setdefault(x, []).append((e['to'], ps))
                pairs |= ps

        def reach(ban):
            st2, seen = list(roots), set()
            while st2:
                x = st2.pop()
                if x in seen:
                    continue
                seen.add(x)
                if x == script:
                    return True
                for to, ps in adj.get(x, []):
                    if ban not in ps:
                        st2.append(to)
            return False

        if not reach(None):         # 입구를 못 찾은 자리. 걸러 낼 근거가 없으니 전부 둔다.
            _need_cache[script] = None
            return None
        need = {p for p in pairs if not reach(p)}
        _need_cache[script] = need
        return need

    # ---- 임시 플래그를 앞 장면이 세우는 경우 ----
    # 생#99 의 조건은 「임시 플래그 2 == 1」 하나로 보이지만 그 값은 앞 장면 ch2_6_2_3 에서만 선다.
    # 그 장면에 닿는 길의 조건(수양 · 성정 · 도덕 · 구력 주사위)이 진짜 조건인데, 항목 장면으로
    # 들어오는 길이 넷이라 need_of 는 그것들을 「어느 한 길에만 걸린 조건」으로 내렸다.
    # 그래서 그 값을 세우는 장면을 **반드시 거치는** 길만 놓고 필수 조건을 다시 센다.
    _TMP_SET, _TMP_ADD = {}, {}
    for _fn in os.listdir('lua'):
        if not _fn.endswith('.lua'):
            continue
        _txt = open(os.path.join('lua', _fn), encoding='utf-8', errors='ignore').read()
        for _fid, _v in re.findall(r'SetFlag\("(A0000\d)",\s*(-?\d+)\)', _txt):
            _TMP_SET.setdefault((_fid, int(_v)), set()).add(_fn[:-4])
        for _fid in re.findall(r'AddFlag\("(A0000\d)"', _txt):
            _TMP_ADD.setdefault(_fid, set()).add(_fn[:-4])

    def _ancestors(script):
        nodes, st = set(), [script]
        while st:
            x = st.pop()
            if x in nodes:
                continue
            nodes.add(x)
            for r in rev.get(x) or []:
                f = str(r.get('from'))
                if not f.startswith('['):
                    st.append(f)
        return nodes

    def need_via(script, setters):
        """setters 중 하나를 거쳐 script 에 닿는 길만 놓고, 모든 길에 걸린 걸음을 고른다.

        (필수 걸음 집합, 필수 선택지 [(장면, 라벨)], 필수 주사위 [(이름, 문턱 라벨)]). 길이 없으면 None.
        """
        nodes = _ancestors(script)
        roots = set()
        for x in nodes:
            rs = rev.get(x) or []
            if x in mission or not rs or any(str(r.get('from')).startswith('[') for r in rs):
                roots.add(x)
        adj, pairs, lab = {}, set(), {}
        for x in nodes:
            for e in edges_all.get(x) or []:
                if e['to'] not in nodes or e.get('kind') == 'combat':
                    continue
                ps = set()
                for q in (e.get('path') or []):
                    if q[0] in ('Switch', 'Dice'):
                        ps.add((q[0], q[1], q[2]))
                        if q[0] == 'Dice':
                            lab[(q[0], q[1], q[2])] = q[3] if len(q) > 3 else ''
                    elif q[0] == 'Choice':
                        t = ('Choice', x, q[1], q[2])
                        ps.add(t)
                        lab[t] = (q[4] if len(q) > 4 and q[4] else q[3]) or ''
                adj.setdefault(x, []).append((e['to'], ps))
                pairs |= ps

        def walk(start, ban, goal=None):
            st2, seen = list(start), set()
            while st2:
                x = st2.pop()
                if x in seen:
                    continue
                seen.add(x)
                if x == goal:
                    return True, seen
                for to, ps in adj.get(x, []):
                    if ban not in ps:
                        st2.append(to)
            return False, seen

        def reach(ban):
            _, seen = walk(roots, ban)
            hit, _ = walk([s_ for s_ in setters if s_ in seen], ban, script)
            return hit

        if not reach(None):
            return None
        need = {p for p in pairs if not reach(p)}
        choices = [(p[1], lab.get(p)) for p in sorted(need) if p[0] == 'Choice']
        dices = [(p[1], lab.get(p)) for p in sorted(need) if p[0] == 'Dice']
        return need, choices, dices

    RE_TMPREQ = re.compile(r'\[플래그 (임시 플래그 \d)\]\s*==\s*(\d+)')

    def via_setter(script, sure):
        """sure 에 임시 플래그 요구가 있고 그 값을 앞 장면이 세우면 (라벨, 값, 세우는 장면들, need_via 결과)."""
        for t in sure:
            if ' 또는 ' in t or '아님' in t:
                continue
            for lab_, v in RE_TMPREQ.findall(t):
                fid, v = label2id.get(lab_), int(v)
                if not fid or v == 0:
                    continue
                anc = _ancestors(script)
                here = _TMP_SET.get((fid, v), set())
                if script in here or (_TMP_ADD.get(fid, set()) & anc):
                    continue        # 그 장면 안에서 서는 값은 temp_flag_why 가 맡는다. 더하는 값은 못 가린다
                cands = (here & anc) - {script}
                if not cands:
                    continue
                r = need_via(script, cands)
                if r:
                    return lab_, v, sorted(cands), r
        return None

    def _kept(x, need):
        # 이 걸음의 조건이 모든 길에 걸려 있는가. 스위치가 아니면 그대로 둔다.
        if need is None or x.get('k') != '조건' or 'idx' not in x:
            return True
        return ('Switch', x.get('raw'), x.get('idx')) in need

    def entry_texts(entries, depth=0, need=None, dropped=None):
        out = []
        for e in entries or []:
            if depth > 2:
                break
            if e.get('type') == 'free':
                if e.get('cond'):
                    out.append(e['cond'])
                continue
            for x in (e.get('steps') or []):
                if _kept(x, need):
                    out.append(x['text'])
                elif dropped is not None:
                    dropped.append(x['text'])
            out += entry_texts(e.get('up') or [], depth + 1, need, dropped)
        return out

    sw_idx = G.get('switch', {})
    cond_idx = G.get('condition', {})

    def upstream_pairs(script, maxd=6, need=None):
        """이 장면까지 오는 길에 걸려 있던 (조건, 그 조건을 보는 장면).

        장면을 함께 싣는 것은 이미 지나간 조건과 앞으로 올 조건을 가르기 위해서다.
        지나간 자리의 조건은 그때 값으로 이미 판가름났고, 지금 값으로 대조하면
        틀린 답이 나온다 — 생#42 의 「구력 <50」은 5장 조건인데 4년차 값을 댔다.

        순서형 스위치는 갈래가 아니라 순서다. 마지막 가지에는 대응하는 문장이 없어
        (else 라서) 그 길로 온 경우 아무 조건도 실리지 않는데, 형제 가지의 조건은
        그대로 남아 필수처럼 보인다. 한#49 가 그랬다 — 단합 >=80 으로 오는 길
        (ch8_3_1_1_1) 과 <80 으로 오는 길 (ch8_3_1_1_2) 이 같은 곳으로 합류하는데
        「단합 <80」만 남아 「단합이 넘쳐서 못 딴다」가 되었다. 그래서 마지막 가지로도
        올 수 있는 스위치는 그 스위치가 실은 문장을 전부 뺀다.
        """
        out, seen, stack = [], set(), [(script, 0)]
        by_sw = {}          # 스위치 -> 그 스위치가 실은 문장들
        elsed = set()       # 마지막(조건 없는) 가지로도 올 수 있는 스위치
        while stack:
            sc, d = stack.pop()
            if sc in seen or d > maxd:
                continue
            seen.add(sc)
            mi = mission.get(sc)
            if mi:
                out += [(t, sc) for t in merged_conds(mi)]
            if sc in HUB_STOP and sc != script:
                continue
            for p in rev.get(sc, []):
                # 조건을 실제로 읽는 곳은 갈림이 있는 부모 장면이다.
                at = p['from']
                if p['kind'] == 'position':
                    if p.get('cond'):
                        out.append((p['cond'], sc))
                    continue
                for step in (p.get('path') or []):
                    k, nm2, idx = step[0], step[1], (step[2] if len(step) > 2 else None)
                    if k == 'Switch' and isinstance(idx, int):
                        if need is not None and ('Switch', nm2, idx) not in need:
                            continue        # 다른 길로도 올 수 있는 가지
                        lst = sw_idx.get(nm2) or []
                        if 1 <= idx <= len(lst):
                            out.append((lst[idx - 1], at))
                            by_sw.setdefault(nm2, set()).add(lst[idx - 1])
                        else:
                            elsed.add(nm2)
                    elif k == 'Condition':
                        out += [(t, at) for t in (cond_idx.get(nm2) or [])]
                stack.append((p['from'], d + 1))
        drop = set()
        for nm2 in elsed:
            drop |= by_sw.get(nm2, set())
        return [(t, a) for t, a in out if t not in drop]

    def upstream_texts(script, maxd=6):
        return [t for t, _ in upstream_pairs(script, maxd)]

    def _at_wk(sc):
        """그 조건을 읽는 장면이 벌어지는 가장 이른 시점. 모르면 None.

        읽는 쪽은 이것을 세이브의 현재 시점과 견준다. 이미 지나간 자리의 조건은
        그때 값으로 판가름이 끝났으므로, 지금 값으로 대조하면 안 된다.
        """
        a = _earliest(sc)
        ch = CHAPTER_SPAN.get(_chapter_of(sc))
        if ch and not _is_free(sc):
            a = ch[0] if a is None else max(a, ch[0])
        return a

    def up_reqs(script, direct, need=None):
        """상류 조건에 그것을 읽는 장면(at)을 붙여 모은다.

        같은 조건이 여러 자리에 있으면 제일 나중 자리를 남긴다. 한 자리라도 아직
        안 지나갔으면 지금 값으로 따져야 하기 때문이다. 장을 못 읽는 자리(자유행동
        등)는 지나갔다고 단정할 수 없으므로 그쪽을 남긴다.
        """
        best, order = {}, []
        for txt, at in upstream_pairs(script, need=need):
            for r in stat_reqs([txt]):
                if flat_reqs([r]) <= direct:
                    continue
                if 'any' in r:
                    k = ('any',) + tuple(sorted((a['stat'], a['op'], a['val'])
                                                for a in r['any']))
                else:
                    k = (r['stat'], r['op'], r['val'], r['neg'], r.get('solo'))
                r = dict(r, at=at, atWk=_at_wk(at))
                if k not in best:
                    best[k] = r
                    order.append(k)
                    continue
                w0, w1 = best[k]['atWk'], r['atWk']
                if w0 is not None and (w1 is None or w1 > w0):
                    best[k] = r
        return [best[k] for k in order]

    # talk_<인물키>_* 는 그 인물과 나누는 대화라 그 인물이 당문에 있어야 한다.
    # 조건문에는 대화 플래그만 적혀 있어서, 없는 인물의 대화가 조건 없이 가능해 보였다.
    # 이름의 번호는 인물 번호가 아니다. talk_girl5_* 는 열아홉 편 중 열여덟에
    # 하후란이 나오고 우소매는 한 번도 안 나온다. talk_girl2·talk_special3 은
    # 그런 스크립트 자체가 없다. 하후란 쪽 잠금은 자리 잠금이라 pos_gate 가 댄다.
    TALK_NEEDS = {
        'talk_girl4': '상관형이 당문에 있음',
    }

    def talk_needs(script):
        for pre, lab in TALK_NEEDS.items():
            if (script or '').startswith(pre + '_') or script == pre:
                return [f'[플래그 {lab}] == 1']
        return []

    def pos_gate(via):
        """그 자유행동 자리로 갈 수 있는가.

        자리 자체가 지도에서 잠겨 있을 수 있는데, 그 잠금은 자리를 여는 스크립트에
        있어서 항목 쪽 조건문에는 흔적이 없다. 한#23 은 탈백 숲에서만 나는데 그 숲의
        이동 버튼이 [하후란을 스승으로 모심] 으로 잠겨 있다(= 탈백문 가입 회차 전용).
        talk_girl5_02 는 부모가 둘이라 linear_texts 가 첫 걸음에서 멈춰 이걸 못 봤다.
        """
        sc = POS_CALLER.get(via)
        return linear_texts(sc) if sc else []

    def linear_texts(script, maxd=24):
        """부모가 하나뿐인 동안 거슬러 올라가며 만나는 조건.

        갈림이 없으니 전부 반드시 거치는 조건이다. entries 는 3단까지만 보고
        upstream_texts 는 여러 부모를 합쳐서 플래그에는 못 쓴다. 그 사이에 낀
        긴 외길이 통째로 안 보였다 — 한#22 는 여덟 단 위에서
        「하후란을 스승으로 모심」을 요구하는데 잔류 회차에서도 가능해 보였다.
        """
        out, sc, seen = [], script, {script}
        for _ in range(maxd):
            ps = rev.get(sc) or []
            if len(ps) != 1:
                break
            p = ps[0]
            f = p.get('from')
            if not f or f in seen or p['kind'] == 'position':
                break
            seen.add(f)
            for step in (p.get('path') or []):
                k, nm2, idx = step[0], step[1], (step[2] if len(step) > 2 else None)
                if k == 'Switch' and isinstance(idx, int):
                    lst = sw_idx.get(nm2) or []
                    if 1 <= idx <= len(lst):
                        out.append(lst[idx - 1])
                elif k == 'Condition':
                    out += (cond_idx.get(nm2) or [])
                elif k == 'Choice' and len(step) > 5 and step[5]:
                    # 잠긴 선택지로만 들어오는 자리. 들어오는 길이 하나뿐인 동안만
                    # 훑으므로 이 잠금은 반드시 거치는 조건이다.
                    out += (cond_idx.get(step[5]) or [])
            mi = mission.get(f)
            if mi:
                out += merged_conds(mi)
            sc = f
        return out

    for it in items:
        for o, p in zip(it['opts'], it['paths']):
            def _locks_one(e):
                # up 까지 파고들면 그 위 장면의 대화 항목이 통째로 딸려 온다.
                # 한 항목의 잠금 조건은 그 항목을 골랐을 때만 조건이다.
                return [x['lock'] for x in (e.get('steps') or []) if x.get('lock')]

            def locks(es):
                """잠긴 선택지의 조건 중, 어느 길로 와도 걸리는 것만.

                들어오는 길이 여럿이면 길마다 열리는 대화 항목이 다르다. 한#16 은
                네 길의 잠금 조건이 통째로 합쳐져 「서행·소사매·엽운주 참전이 전부
                필요」해 보였다. 실제로는 누가 참전했느냐에 따라 물어볼 수 있는
                항목이 달랐을 뿐이다. 그래서 전부에 공통인 것만 남긴다.
                """
                es = es or []
                if not es:
                    return []
                sets = [set(_locks_one(e)) for e in es]
                return sorted(set.intersection(*sets))

            # 반드시 거치는 조건. 들어오는 길이 하나뿐인 자리에서만 모은다.
            sure = [x['text'] for x in p['steps']]
            sure += [x['lock'] for x in p['steps'] if x.get('lock')]
            sure += locks(p.get('entries'))
            sure += gate_conds(p) + EXTRA_COND.get(it['id'], [])
            org = p.get('origin') or {}
            sure += (org.get('conds') or [])
            if org.get('kind') == '자유행동':
                sure += pos_gate(org.get('via'))
            sure += linear_texts(p['script'])
            sure += talk_needs(p['script'])
            # entries 는 부모가 여럿이면 서로 다른 길의 조건을 한데 모은다. 그것을 전부
            # 필수로 읽으면 한#16 처럼 「서행 참전이 필요하다」는 없는 조건이 생긴다.
            need = need_of(p['script'])
            via = via_setter(p['script'], sure)
            if via:
                need = {q for q in via[3][0] if q[0] != 'Choice'}
            dropped = []
            texts = sure + entry_texts(p.get('entries') or [], need=need, dropped=dropped)
            # 분기 플래그 비교는 stat_reqs 가 걸러내므로 원문 조각을 따로 실어 보낸다.
            # 이게 없으면 화면 쪽 분기 추출기가 고른 경로에서 플래그를 아예 못 본다.
            # 택일('또는')이 든 덩어리는 통째로 뺀다. 화면 쪽은 == N 을 전부 필수로 읽어서,
            # 둘 중 하나면 되는 플래그를 둘 다 못박아 버린다.
            # 플래그는 판정에 바로 쓰이므로 확실한 것만 싣는다.
            o['flags'] = sorted({m for t in sure
                                 if ' 또는 ' not in t and '아님' not in t
                                 for m in RE_FLAGCHUNK.findall(t)})
            o['reqs'] = stat_reqs(texts)
            direct = flat_reqs(o['reqs'])
            o['upReqs'] = up_reqs(p['script'], direct, need=need)
            # 어느 한 길에만 걸린 조건. 판정에는 안 쓰고 「길에 따라」로만 보여 준다.
            alt = [r for r in stat_reqs(dropped) if not flat_reqs([r]) <= direct]
            if via:
                # 그 장면을 안 거치는 길의 조건은 대안이 아니라 틀린 길이다. 「길에 따라」로도 안 보인다.
                o['via'] = {
                    'flag': via[0], 'val': via[1], 'at': via[2],
                    'choices': [g.t(f'Story/{lb}') or lb for _sc, lb in via[3][1] if lb],
                    'dice': [dict(step_text(['Dice', nm_, 0, lb]), at=nm_) for nm_, lb in via[3][2]],
                }
            elif alt:
                o['pathReqs'] = alt
            b = branch_of(p)
            if b is not None:
                o['branch'] = b
            q = qc_of(p)
            # 「유학 선택」 하나만 보는 스위치가 모든 길에 걸려 있으면 그것이 갈래다.
            # 생#102 는 S0028_01 이 [유학 선택] != 1 의 나머지 가지(= 청성행)로만 넘긴다.
            for _k, _nm, _ix in (need or ()):
                _cs = sw_idx.get(_nm) or []
                if _k != 'Switch' or len(_cs) != 1 or q is not None:
                    continue
                _m = re.fullmatch(r'\[플래그 유학 선택[^\]]*\] (==|!=) 1', _cs[0])
                if _m:
                    q = '1' if (_m.group(1) == '==') == (_ix == 1) else '0'
            for chunk, (fq, later) in FLAG_IMPLIES.items():
                if any(chunk in f for f in o['flags']):
                    q = fq if fq is not None else q
                    if later:
                        o['loverLater'] = later
            if q is not None:
                o['qc'] = q
            n = not_branch(p)
            # 엽운상 루트(S0208_*)는 3년 5월 상순 ch5_4_1 이 「엽운상이 당문에 있음」일 때 넘긴다.
            # 3년 1월 상순 S0204_01(조건: 엽운주가 당문에 있음)에서 남매를 붙잡는 가지는 「유학 선택 == 1」뿐이고,
            # 그 값은 청성행(ch3_3_1_1)만 세운다. 그래서 공동파 유학도, 청성행 없는 잔류도 거기 닿지 못한다.
            # 잔류를 열어 두었던 것은 엽운주가 ch2_4_10_3(2년 8월)에서 먼저 빠지기 때문인데, 그 사슬이
            # 반드시 2년 10월 중순 ch2_8_2 로 이어져 그를 되돌려 놓는다 — S0204_01 은 그대로 뜬다.
            ys_route = any('[플래그 엽운상 공략 중] == 1' in f for f in o['flags'])
            if (p['script'] or '').startswith('S0208_') or ys_route:
                o['qc'] = '1'
            if n:
                o['notBranch'] = n

    # ---- 플래그를 언제 세울 수 있는가 ----
    # 「엽운상이 당문에 있음 == 1」 같은 조건을 세이브와 맞대려면, 그 값을 만드는 곳이
    # 아직 앞에 남아 있는지 알아야 한다. 지나갔으면 그 항목은 이 회차에서 끝난 것이다.
    # 값을 더하는 AddFlag 는 어디로 갈지 몰라 별도로 표시하고 판정에서 뺀다.
    flag_when = {}
    for fn in _os.listdir('lua'):
        t = open(_os.path.join('lua', fn), encoding='utf-8', errors='replace').read()
        sc = fn[:-4].split('__')[0]
        # 미션이 못박은 시점만 쓴다. _earliest 는 하한 추정이라 "마지막 기회"로 읽으면
        # 아직 오지도 않은 사건을 지났다고 말하게 된다(공동 영전이 그랬다).
        wk = known_wk.get(sc)
        # 판정에는 못 쓰지만 「언제쯤 오는가」를 보여 주기엔 쓸 만한 하한 추정.
        # 회의처럼 여러 자리에서 공유되는 스크립트는 이것도 실제보다 이르게 나오므로,
        # 읽는 쪽이 「그 무렵부터」로 적어야 한다. 판정에 쓰면 안 된다.
        est = _at_wk(sc)
        for mm in re.finditer(r'statmodifymanager\.SetFlag\("([A-Za-z0-9_]+)",\s*(-?\d+)\)', t):
            e = flag_when.setdefault(mm.group(1), {'set': {}, 'add': False})
            # 최소는 시작, 최대는 끝으로 싣는다. 전에는 둘 다 시작이라 구간 미션(S2402_01, 2년 4월~7월)이
            # 세우는 값의 「마지막 기회」가 2년 4월로 잡혔다.
            e['set'].setdefault(mm.group(2), []).append((wk, known_last.get(sc, wk)))
            e.setdefault('est', []).append(est)
        for mm in re.finditer(r'statmodifymanager\.AddFlag\("([A-Za-z0-9_]+)"', t):
            flag_when.setdefault(mm.group(1), {'set': {}, 'add': False})['add'] = True
    for e in flag_when.values():
        ests = [w for w in (e.pop('est', None) or []) if w is not None]
        e['estMin'] = min(ests) if ests else None
        e['estMax'] = max(ests) if ests else None
        for v, ws in e['set'].items():
            known = [w for w in ws if w[0] is not None]
            # 시점을 모르는 자리가 하나라도 있으면 "언제든 가능"으로 본다(보수적).
            e['set'][v] = {'min': min(w[0] for w in known) if known else None,
                           'max': max(w[1] for w in known) if known else None,
                           'unknown': len(known) < len(ws)}

    # ---- bundle map: divergence scenes that yield 2+ items ----
    def decider_of(steps):
        k = [x['k'] for x in steps]
        if '선택지' in k: return '선택지'
        if '주사위' in k: return '주사위'
        if '조건' in k or '그 외' in k: return '조건'
        return '무조건'

    bmap = collections.defaultdict(list)
    for it in items:
        for p in it['paths']:
            bmap[p['script']].append((it, p))

    bundles = []
    for sc, lst in bmap.items():
        seen_ids = {}
        for it, p in lst:
            cur = seen_ids.get(it['id'])
            txt = ' · '.join(x['text'] for x in p['steps']) or '(무조건)'
            if cur is None:
                seen_ids[it['id']] = {'id': it['id'], 'type': it['type'], 'no': it['no'],
                                      'title': it['title'], 'owned': it['owned'],
                                      'blocked': it.get('blocked', False),
                                      'conds': [txt], 'decider': decider_of(p['steps'])}
            elif txt not in cur['conds']:
                cur['conds'].append(txt)
        rows = sorted(seen_ids.values(), key=lambda x: (x['type'], x['no']))
        if len(rows) < 2:
            continue
        kinds = collections.Counter(r['decider'] for r in rows)
        o = origin_of(sc) or origin_guess(sc) or origin_root(sc) or {}
        bundles.append({
            'script': sc,
            'summary': summary.get(sc, ''),
            'when': o.get('when', ''), 'where': o.get('where', ''),
            'kinds': dict(kinds),
            'saveable': bool(kinds.get('선택지') or kinds.get('주사위')),
            'total': len(rows),
            'miss': sum(1 for r in rows if not r['owned'] and not r['blocked']),
            'blocked': sum(1 for r in rows if r['blocked']),
            'items': rows,
        })
    bundles.sort(key=lambda b: (-b['miss'], -b['total']))

    bytype = collections.Counter(x['type'] for x in items)
    stats = {
        'byType': dict(bytype),
        'ownedByType': dict(collections.Counter(x['type'] for x in items if x['owned'])),
        'total': len(items),
        'owned': sum(1 for x in items if x['owned']),
        'reachable': sum(1 for x in items if x['reachable']),
        'unreachable': [x['id'] for x in items if not x['reachable']],
        'blocked': sum(1 for x in items if x.get('blocked')),
        'engineFlags': sorted(engine_written),
        'withOrigin': sum(1 for x in items for p in x['paths'] if p.get('origin')),
        'paths': sum(len(x['paths']) for x in items),
    }
    json.dump({'items': items, 'stats': stats, 'bundles': bundles,
               'flagWhen': flag_when, 'flagKo': FLAG_KO,
               # 어디서도 세워지지 않는 플래그는 기본값에서 움직이지 않는다.
               # 그것을 요구하는 조건은 이 빌드에서 성립할 수 없다.
               'flagDefault': default},
              open('data.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print(stats)
    print('paths total', sum(len(x['paths']) for x in items))
    print('bundles', len(bundles), '| 미획득 2개 이상', sum(1 for b in bundles if b['miss'] >= 2),
          '| 같은 세이브 분기 가능', sum(1 for b in bundles if b['saveable']))


if __name__ == '__main__':
    main()
