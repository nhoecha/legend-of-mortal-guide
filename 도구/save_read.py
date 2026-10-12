# -*- coding: utf-8 -*-
"""활협전 세이브 읽기 — 지금 상태와, 이 회차에서 아직 딸 수 있는 도감을 보여준다.

    python save_read.py               가장 최근 세이브를 읽고 보고서 출력
    python save_read.py --watch       세이브가 바뀔 때마다 다시 그린다 (Ctrl+C 로 종료)
    python save_read.py --list        세이브 슬롯 목록
    python save_read.py Save_005      특정 세이브
    python save_read.py --flags 유학  이름/설명에 그 말이 든 플래그를 모두 출력
    python save_read.py --all         이 회차에서 못 하는 항목까지 전부 출력

세이브는 읽기만 한다. 쓰지 않는다.

필요한 것: nrbf.py, savemap.json(mk_savemap.py 로 생성), data.json, forks.json, route_forks.json.
게임 설치본은 필요 없다.
"""
import json, os, re, sys, time, glob, subprocess, threading

HERE = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(os.environ.get('USERPROFILE', ''),
                        r'AppData\LocalLow\Obb Studio\Mortal')

sys.path.insert(0, HERE)
import nrbf
try:
    from mission_ko import mission_ko
except Exception:
    mission_ko = lambda d: d


# ---------------------------------------------------------------- 꾸미기
_C = os.name != 'nt' or os.environ.get('WT_SESSION') or os.environ.get('TERM')
try:
    if os.name == 'nt':
        os.system('')          # ANSI 활성화
except Exception:
    pass


def c(s, code):
    return f'\033[{code}m{s}\033[0m' if _C else str(s)


def bold(s): return c(s, '1')
def dim(s): return c(s, '2')
def ok(s): return c(s, '32')
def bad(s): return c(s, '31')
def warn(s): return c(s, '33')
def acc(s): return c(s, '36')


RE_ANSI = re.compile(r'\[[0-9;]*m')


def wide(s):
    """한글은 두 칸을 차지한다. 색 코드는 폭이 없다."""
    s = RE_ANSI.sub('', str(s))
    return sum(2 if ord(ch) > 0x1100 and not 0x2000 <= ord(ch) <= 0x206f else 1 for ch in s)


def pad(s, n):
    s = re.sub(r'\\n|[\r\n]', ' ', str(s))   # 제목에 줄바꿈이 들어 있으면 표가 깨진다
    return s + ' ' * max(0, n - wide(s))


def rule(title=''):
    line = '─' * 66
    if title:
        return '\n' + bold(f'■ {title}') + '\n'
    return dim(line)


# ---------------------------------------------------------------- 인물 색
# 게임 데이터에는 인물별 색이 없다. 작성자가 캐릭터 그림을 보고 고른 것(하후란 남색, 소사매 분홍)과
# 내가 이름의 뜻·설정으로 고른 것이 섞여 있다. 다르면 이 표만 고치면 된다.
#   욱죽(郁竹) 대나무 초록, 위국(魏菊) 국화 노랑, 상관형(上官螢) 반딧불 연두,
#   서행(瑞杏) 살구, 우소매(虞小梅) 매화, 엽운상은 담비털옷과 병약함.
# 당문 사형들은 한 갈래로 보이도록 푸른 계열로 묶었다.
CHAR_COLOR = {
    # 공략 대상
    '당묵령': 218, '엽운상': 183, '용상': 153, '우소매': 196, '상관형': 156,
    '하후란': 26, '욱죽': 35, '위국': 222, '서행': 247,
    # 당가는 한 집안으로 보이게 하늘색 하나로. 소사매(당묵령)만 분홍으로 따로 둔다.
    '당중령': 117, '당포의': 117, '당쟁': 117, '당승': 117, '당유원': 117,
    # 조건문은 관계 이름(소사매·대사형…)을, 세이브는 본명(당묵령·당포의…)을 쓴다
    '소사매': 218, '장문인': 117, '대사형': 117, '이사형': 117, '삼사형': 117, '사사형': 117,
    '당삼': 103, '당교교': 139,
    # 엽가 남매도 같은 색 (당가 하늘색과 겹치지 않게 연보라로)
    '엽운주': 183, '엽운추': 183,
    # 그 밖
    '서생': 180, '남궁심': 145, '남궁천': 152, '복온': 187, '송비': 137,
    '윤지평': 108, '신도룡': 151, '해무진': 143, '이부귀': 179, '왕이장': 138,
    '번소천': 131, '유악': 102, '용연': 132, '조규': 101, '단하자': 146,
    '차헌원': 130, '만리붕정': 172, '석공원': 95, '하령서': 176, '금오상인': 209,
}


def cname(name):
    """인물 이름에 그 인물의 색을 입힌다."""
    c = CHAR_COLOR.get(name)
    if c is None or not _C:
        return name
    return f'\033[38;5;{c}m{name}\033[0m'


RE_AFF = re.compile(r'^(.+?) 호감도$')


def paint(text):
    """조건 문구 안의 인물 이름에도 색을 입힌다."""
    if not _C:
        return text
    for nm in sorted(CHAR_COLOR, key=len, reverse=True):
        if nm in text:
            text = text.replace(nm, cname(nm))
    return text


# ---------------------------------------------------------------- 자료
def load_json(name):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding='utf-8'))


def find_saves():
    """계정 폴더별 세이브 파일. 최근 수정 순."""
    out = []
    for acct in sorted(glob.glob(os.path.join(SAVE_DIR, '*'))):
        if not os.path.isdir(acct):
            continue
        for f in glob.glob(os.path.join(acct, '*.dat')):
            base = os.path.basename(f)
            # Save_universe 는 도감, Legend_* 는 열전 기록이라 GameSave 가 없다
            if base.startswith('Save_universe') or base.startswith('Legend_'):
                continue
            out.append(f)
    out.sort(key=os.path.getmtime, reverse=True)
    return out


def universe_owned():
    """도감 획득 상태는 게임이 JSON 으로도 써 준다. 세이브보다 이쪽이 최신이다."""
    got = set()
    for acct in glob.glob(os.path.join(SAVE_DIR, '*')):
        p = os.path.join(acct, 'Save_universe.json')
        if not os.path.exists(p):
            continue
        try:
            sv = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        for k in ('LibraryData1', 'LibraryData2', 'LibraryData3', 'LibraryData4'):
            got |= {int(e['Name']) for e in sv.get(k, [])}
    return got


def universe_paths():
    return [os.path.join(a, 'Save_universe.json')
            for a in glob.glob(os.path.join(SAVE_DIR, '*'))]


def universe_mtime():
    """도감 JSON 이 마지막으로 바뀐 시각. 없으면 0."""
    return max((os.path.getmtime(p) for p in universe_paths()
                if os.path.exists(p)), default=0)


def bake_web(full):
    """웹 공략기 다시 굽기. 감시 스레드에서 부른다."""
    err = rebuild_guide(full)
    if err:
        print(bad('   ' + err))
    elif full:
        print(ok('   웹 공략기 갱신 완료'))


def rebuild_guide(full=True):
    """도감을 딴 직후 웹 공략기를 다시 굽고, 열려 있으면 새로고침한다.

    HTML 은 정적이라 획득 여부가 구울 때 박힌다. 감시 중에 이걸 대신 돌려 주지
    않으면 작성자가 매번 손으로 build_site.py 를 부르게 된다.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    # data.json 은 세이브와 무관하다. 세이브만 바뀌었으면 굽기만 다시 하면 되고,
    # 그쪽은 몇 초면 끝난다. build_site.py 는 1분이 넘게 걸린다.
    for script in (('build_site.py', 'gen_html.py') if full else ('gen_html.py',)):
        r = subprocess.run([sys.executable, script], cwd=here, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if r.returncode:
            return f'{script} 실패: {r.stderr.decode("utf-8", "replace").strip()[:120]}'
    ps = os.path.join(here, 'refresh-page.ps1')
    if os.path.exists(ps):
        subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                        '-File', ps, '-Title', '도감 공략기'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return None


# ---------------------------------------------------------------- 세이브 해석
STAGE_KO = {1: '상순', 2: '중순', 3: '하순'}

# 게임의 「불러오기」 화면에 뜨는 이름. 자동 저장은 이야기·육성·전투 셋이 따로 돈다.
KIND_KO = {'Save_auto': '자동 · 이야기', 'Save_auto_free': '자동 · 육성',
           'Save_auto_battle': '자동 · 전투'}


def save_kind(path):
    base = os.path.basename(path)[:-4]
    return KIND_KO.get(base, '수동 ' + base.replace('Save_', ''))


class Run:
    """세이브 하나를 사람이 읽을 수 있는 모양으로."""

    def __init__(self, path, M):
        self.path = path
        self.M = M
        root = nrbf.load(path)
        # 오토세이브는 AutoGameSave 껍데기 안에 GameSave 가 들어 있고,
        # 수동 세이브는 GameSave 가 곧 루트다.
        gs = root.get('GameSave') if isinstance(root, dict) else None
        if gs is None and isinstance(root, dict) and 'CurrentYear' in root:
            gs = root
        if gs is None:
            raise ValueError('GameSave 를 찾지 못했다')
        self.slot = root.get('Slot') or ''
        self.gs = gs
        self.stats = {s['Key']: s['Value'] for s in gs.get('Stats') or []}
        self.flags = {f['Name']: f['State'] for f in gs.get('EventFlags') or []}
        self.rel = {r['Key']: r for r in gs.get('Relationships') or []}
        self.year = gs.get('CurrentYear') or 0
        self.month = gs.get('CurrentMonth') or 0
        st = gs.get('CurrentStage')
        self.stage = st.get('value__') if isinstance(st, dict) else (st or 0)
        mm = gs.get('MainMission') or {}
        self.mission = mm.get('Key') or ''
        self.script = gs.get('StartStoryScript') or gs.get('CurrentSceneKey') or ''

    @property
    def wk(self):
        return self.year * 1000 + self.month * 10 + self.stage

    def when(self):
        return f'{self.year}년차 {self.month}월 {STAGE_KO.get(self.stage, "")}'.strip()

    def stat_ko(self, key):
        return self.M['stats'].get(key, key)

    def char_ko(self, key):
        return self.M['chars'].get(key, key)

    # 조건문은 서열로, 세이브는 이름으로 부른다. 이어 주지 않으면 「이사형 호감도 < 30」이
    # 「확인 못 함」으로 떠서, 남은 여유가 2점뿐인 것을 못 보고 지나친다.
    ALIAS = {'대사형': '당포의', '이사형': '당쟁', '삼사형': '당승', '사사형': '당유원',
             '장문인': '당중령', '소사매': '당묵령'}

    def affection(self, ko):
        """한글 이름으로 호감도를 찾는다. 한 인물에 키가 여럿인 경우가 있어(우소매 girl5*)
        가장 큰 값을 쓴다."""
        ko = self.ALIAS.get(ko, ko)
        vals = [r.get('Value') for k, r in self.rel.items()
                if self.M['chars'].get(k) == ko and r.get('Value') is not None]
        return max(vals) if vals else None

    def flag_ko(self, fid):
        return self.M['flags'].get(fid, fid)


# 분기 플래그 찾기 — forks.json 의 라벨은 FLAG_KO 라벨의 앞부분이다
def fork_values(run, forks):
    lab2id = {}
    for fid, lab in run.M['flags'].items():
        lab2id.setdefault(lab, fid)
    out = {}
    for f in forks:
        fid = None
        for lab, i in lab2id.items():
            if lab == f['flag'] or lab.startswith(f['flag'] + ' '):
                fid = i
                break
        if fid is None or fid not in run.flags:
            continue
        out[f['id']] = (fid, str(run.flags[fid]))
    return out


def run_forks(run, forks):
    """이 회차가 이미 확정한 분기 값. 플래너의 분기 id 기준."""
    raw = fork_values(run, forks)
    got = {k: v[1] for k, v in raw.items()}
    # 유학 선택 1 은 별개 갈래가 아니라 잔류(0)에서 청성행을 탄 상태다
    if got.get('study') == '1':
        got['study'] = '0'
        got['qingcheng'] = '1'
    # 「청성행」은 실제 플래그 이름이 아니라 우리가 붙인 갈래라 fork_values 가 못 찾는다.
    # 잔류 중이면 아직 안 정해진 것으로 놓아 선택지 비교에 나오게 한다.
    if got.get('study') == '0':
        got.setdefault('qingcheng', '0')
    return got, raw



# ---------------------------------------------------------------- 조건 대조
OPTX = {'>=': '\u2265', '<=': '\u2264', '>': '>', '<': '<', '==': '=', '!=': '\u2260'}
FLIP = {'>=': '<', '<=': '>', '>': '<=', '<': '>=', '==': '!=', '!=': '=='}


def cur_value(run, name):
    """조건에 적힌 이름으로 지금 값을 찾는다. 못 찾으면 None."""
    if name == '마음에 둔 사람':
        return run.stats.get('lover')
    if name.endswith(' 호감도'):
        return run.affection(name[:-4].strip())
        return None
    for key, ko in run.M['stats'].items():
        if ko == name:
            return run.stats.get(key)
    # 소지품과 재능은 Stats 가 아니라 저마다 다른 목록에 있고, 세는 칸도 다르다.
    # 「비급 등급」이 「비급」보다 먼저 걸려야 한다 — 접두사가 겹친다.
    for pre, sec in (('기술 ', 'talents'), ('비급 등급 ', 'bookrank'),
                     ('비급 ', 'books'), ('잡물 ', 'miscs'), ('귀중품 ', 'specials')):
        if name.startswith(pre):
            return item_value(run, sec, name[len(pre):].strip())
    return None


# 목록 이름 -> (세이브의 칸, 세는 값). 개수는 더하고 등급은 제일 높은 것을 본다.
ITEM_SEC = {
    'talents': ('Talents', 'Level', 'max'),
    'books': ('Books', 'Count', 'sum'),
    'bookrank': ('Books', 'MartialLevel', 'max'),
    'miscs': ('Miscs', 'Count', 'sum'),
    'specials': ('SpecialItems', 'Count', 'sum'),
}


def item_value(run, sec, ko):
    """소지품·재능의 지금 값.

    안 가지고 있으면 0 이다. 이름 자체를 모를 때만 None 을 준다 — 그 둘을 섞으면
    「안 가진 것」이 「우리가 못 읽은 것」으로 보여 조건이 조용히 통과한다.
    """
    field, key, how = ITEM_SEC[sec]
    names = run.M.get('books' if sec == 'bookrank' else sec) or {}
    ids = {i for i, n in names.items() if n == ko}
    if not ids:
        return None
    vals = [r.get(key) or 0 for r in (run.gs.get(field) or []) if r.get('Id') in ids]
    return (max(vals) if how == 'max' else sum(vals)) if vals else 0


def _holds(op, cur, val):
    return {'>=': cur >= val, '<=': cur <= val, '>': cur > val,
            '<': cur < val, '==': cur == val, '!=': cur != val}[op]


def _atoms(o):
    """경로가 요구하는 (이름, 연산자, 값) 들. 상류 조건도 포함한다.

    부정은 solo 일 때만 뒤집는다. 여러 비교가 한 덩어리로 부정된 것은 어느 쪽을
    뒤집어야 하는지 알 수 없어 버린다.
    """
    out = []
    # 상류 조건은 「이 항목의 조건」이 아닐 수 있다. 그 장면까지 오는 길에 있던 다른
    # 분기의 조건이 딸려 오기도 한다 — 한#49 의 「남궁심 20 이상」이 그랬다.
    # 그래서 어디서 왔는지를 같이 실어, 화면이 구분해 보여 줄 수 있게 한다.
    out = []
    for up, src in ((False, o.get('reqs') or []), (True, o.get('upReqs') or [])):
        for r in src:
            r = dict(r, __up=up)
            if 'any' in r:
                grp = [(a['stat'], a['op'], a['val']) for a in r['any']]
                if grp:
                    out.append(('any', grp))
                continue
            if r.get('neg'):
                if r.get('solo') is False:
                    continue
                out.append(('one', (r['stat'], FLIP[r['op']], r['val'], up, r.get('atWk'))))
            else:
                out.append(('one', (r['stat'], r['op'], r['val'], up, r.get('atWk'))))
    return out


def passed(atwk, now):
    """그 조건을 읽는 자리를 이미 지났는가.

    지난 자리의 조건은 그때 값으로 이미 판가름났다. 지금 값으로 대조하면 틀린다 —
    생#39 의 「누적 연단 >=250」은 3년차 1월 자리인데 4년차 값을 대고 있었다.
    실린 시점은 순(旬)이 없는 그 달 기준이라, 같은 달이면 아직 안 지난 것으로 본다.
    """
    return atwk is not None and now is not None and now // 10 > atwk // 10


def _tighten(items):
    """같은 스탯의 같은 방향 조건은 제일 빡센 것만 남긴다."""
    best = {}
    order = []
    for name, op, val, *rest in items:
        up = rest[0] if rest else False
        aw = rest[1] if len(rest) > 1 else None
        side = '>' if op in ('>=', '>') else ('<' if op in ('<=', '<') else op)
        k = (name, side)
        if k not in best:
            best[k] = (name, op, val, up, aw)
            order.append(k)
            continue
        _, op0, v0, up0, aw0 = best[k]
        if side == '>' and val > v0:
            best[k] = (name, op, val, up and up0, aw)
        elif side == '<' and val < v0:
            best[k] = (name, op, val, up and up0, aw)
    return [best[k] for k in order]


# 이벤트가 도는 동안에만 값이 있는 플래그. 세이브에 있는 값으로 판정하면 안 된다.
FLAG_RUNTIME = ('범용', '임시 플래그')
RE_FLAGCMP = re.compile(r'\[플래그 ([^\]]+)\]\s*(==|>=)\s*(-?\d+)')


def flag_met(cur, op, want):
    """세이브의 값이 조건을 채웠는가. 값이 없으면 못 채운 것으로 본다."""
    if cur is None:
        return False
    return cur >= want if op == '>=' else cur == want


def flag_label(short, op, want):
    if op == '>=':
        return f'{short} {want} 이상'
    return short if want == 1 else (short + ' 아님' if want == 0 else f'{short} {want}')


def pathof(it, o):
    """opt 와 짝인 path. 둘은 같은 순서로 들어 있다."""
    for a, b in zip(it.get('opts') or [], it.get('paths') or []):
        if a is o:
            return b
    return None


def need_line(o, got, fmap):
    """이 항목이 어느 갈래를 타야 하는가. 아직 그 갈래로 안 서 있을 때만 적는다.

    갈래 요구는 조건문에 안 적히고 장면 접두사로만 드러난다(ch3_1_* = 청성 라인).
    그래서 생#98 「패자의 죽음」이 「조건 없음 - 그 장면이 오면 발생」으로만 보였다.
    작성자가 「저번 런에 아예 안 떴다」고 알려 주어 드러났다 - 그 회차는 심계가 소사매라
    청성행 자체를 못 탔다.
    """
    out = []
    for key, want in (('study', o.get('branch')), ('qingcheng', o.get('qc'))):
        if want is None or got.get(key) == want:
            continue
        f = fmap.get(key) or {}
        nm = next((x['name'] for x in (f.get('options') or []) if x['v'] == want), None)
        if nm:
            out.append(f'{f.get("flag", key)}: {nm}')
    # 「고르지 않아야」 열리는 갈래도 적는다. 안 적으면 「수치 조건 없음」으로 보여서
    # 서무림맹 회차에서도 딸 수 있을 것처럼 읽힌다(작성자가 한청서 43 에서 잡았다).
    for key, bad in (o.get('notBranch') or {}).items():
        f = fmap.get(key) or {}
        nm = next((x['name'] for x in (f.get('options') or []) if x['v'] == bad), None)
        if nm:
            out.append(f'{f.get("flag", key)}: {nm} 아님')
    if o.get('loverLater'):
        out.append(o['loverLater'])
    return ' · '.join(out)


def route_line(it, o):
    """이 항목을 어디서 어떻게 만나는지 한 줄로.

    조건만 적으면 「조건 없음 — 그 장면이 오면 발생」으로 끝나서, 정작 어느 사건을
    타야 하는지가 안 보인다. 장면 요약과 마지막 전투/죽음 방식을 붙인다.
    """
    p = pathof(it, o) or {}
    og = p.get('origin') or {}
    # 원점 요약이 비는 경로가 있다(GameOver 로 빠지는 자리). 그때는 바로 위 장면을 쓴다.
    # 단, 들어오는 길이 여럿이면 첫 번째가 이 경로의 것이라는 보장이 없다.
    # 한#23 이 실제로는 우소매와의 대화인데 「설산 숲 · 하후란」으로 보였다.
    ents = p.get('entries') or []
    ent = ents[0].get('summary') or '' if len(ents) == 1 else ''
    bits = []
    for s in (og.get('summary'), ent, p.get('summary')):
        s = (s or '').strip()
        if s and s not in bits:
            bits.append(s if len(s) <= 58 else s[:57] + '…')
    if not bits:
        return ''
    tail = ''
    if p.get('combatDesc'):
        tail = f' · 전투 {p["combatDesc"]} 에서 패배'
    elif p.get('via') == 'GameOver':
        # GameOver 가 전부 전투 패배는 아니다. 생#99 · #100 은 선택지와 주사위로 죽는다.
        fought = any('승패' in (s.get('text') or '') or '전투 결과' in (s.get('text') or '')
                     for s in (p.get('steps') or []))
        tail = ' · 그 장면의 전투에서 패배' if fought else ' · 그 장면의 선택 · 주사위로 사망'
    n = len(it.get('opts') or [])
    more = f'  (경로 {n}가지 중 하나)' if n > 1 else ''
    # 여행 조우는 조건이 없어 「경로 N가지 중 하나」만 남는다. 어느 여행인지와 언제인지는
    # 손으로 적어 두었으므로(build_site.TRAVEL_WHEN) 그것을 앞에 붙인다.
    if og.get('travel'):
        head = og.get('when') or ''
        more += chr(10) + ' ' * 19 + dim('↳ ' + (head + ' · ' if head else '') + og['travel'])
    body = ' → '.join(bits) + tail
    if wide(body) > 96:
        while bits and wide(' → '.join(bits) + tail) > 96:
            bits.pop()
        body = (' → '.join(bits) + tail) if bits else tail.lstrip(' ·')
    return body + more


def flag_bits(run, o, pending=None):
    """조건에 적힌 플래그를 요구사항으로만 적는다.

    ✓/✗ 를 붙이지 않는 이유: 플래그가 지금 0 인 것은 대개 「아직 안 왔다」이지
    「못 한다」가 아니다. 실제로 못 하는 경우는 갈래 판정이 따로 잡아 준다.
    이벤트가 도는 동안에만 값이 있는 것(범용·임시)은 아예 버린다.
    """
    out = []
    pending = pending if pending is not None else [0]
    for chunk in (o.get('flags') or []):
        m = RE_FLAGCMP.match(chunk)
        if not m:
            continue
        lab, op, want = m.group(1).strip(), m.group(2), int(m.group(3))
        if any(k in lab for k in FLAG_RUNTIME):
            continue
        short = re.sub(r'\s*\(.*', '', lab)
        fid = None
        for i, l in run.M['flags'].items():
            if l == lab:
                fid = i
                break
        cur = run.flags.get(fid) if fid else None
        label = flag_label(short, op, want)
        if flag_met(cur, op, want):
            out.append(dim(label) + ok(' ✓'))
        else:
            out.append(warn('아직 ') + dim(label))
            pending[0] += 1
    return out


def step_bits(path):
    """스탯도 플래그도 아닌 것 — 무엇을 고르고 무엇에 지면 되는가."""
    out = []
    for st in (path.get('steps') or []):
        t = re.sub(r'\\n|[\r\n]', ' ', st.get('text') or '')
        if st['k'] == '선택지':
            # 잠긴 선택지는 조건이 맞아야 뜬다. 판정에는 안 넣더라도 보여는 준다.
            lk = f" ({st['lock']} 이라야 뜸)" if st.get('lock') else ''
            out.append((acc('고르기: ') + t[:34] + dim(lk), 0))
        elif st['k'] == '주사위':
            th = f" 기준 {st['th']}" if st.get('th') else ''
            out.append((acc('주사위: ') + t[:26] + dim(th), 0))
    if path.get('combatDesc'):
        out.append((acc('전투에서 패배: ') + path['combatDesc'][:30], 0))
    return out


# 작성자의 게임에는 주사위 범위를 통째로 옮기는 옵션(수렴)이 있다. 작성자 말로는 범위가
# -50 ~ 50 또는 50 ~ 150 까지 간다(2026-10-04). 그래서 눈은 -50 에서 150 사이로 본다.
DICE_LO, DICE_HI = -50, 150


def dice_blocked(run, path):
    """보정을 더하면 범위를 옮겨도 못 넘는 주사위. 보정을 다 읽은 것만 판정한다.

    생#99 가 이것이다 — 눈 + 이사형 호감도 < 20 인데 호감도가 83 이면 눈이 -50 이어도 33.
    """
    out = []
    for st in ((path or {}).get('steps') or []):
        m = re.fullmatch(r'\s*(<|>=)\s*(-?\d+)\s*', st.get('th') or '')
        prs = st.get('pr')
        if st.get('k') != '주사위' or not m or not prs:
            continue
        bonus, names = 0, []
        for p in prs:
            tgt = p.get('target')
            name = (tgt + ' 호감도') if p.get('type') == '好感度' and tgt else tgt
            cur = cur_value(run, name) if name else None
            if not isinstance(cur, (int, float)):
                bonus = None
                break
            bonus += (p.get('rate') or 1) * cur * (-1 if p.get('neg') else 1)
            names.append(f'{name} {cur}')
        if bonus is None:
            continue
        op, th = m.group(1), int(m.group(2))
        best = (DICE_LO if op == '<' else DICE_HI) + bonus
        if (op == '<' and not best < th) or (op == '>=' and not best >= th):
            out.append(f'주사위 {op}{th} 불가 — 보정 {", ".join(names)}, 범위를 끝까지 옮겨도 {best:g}')
    return out


def prereq_hint(run, o, PQ):
    """이 경로가 아직 없는 인물 플래그를 요구하면, 그 인물을 어떻게 들이는지 한 줄로."""
    lab2id = {}
    for fid, lab in run.M['flags'].items():
        lab2id.setdefault(lab, fid)
    byflag = {}
    for name, d in (PQ.get('chars') or {}).items():
        for fid in re.split(r'\s*/\s*', d.get('flag') or ''):
            if fid:
                byflag[fid] = (name, d)
    out = []
    for chunk in (o.get('flags') or []):
        m = RE_FLAGCMP.match(chunk)
        if not m or int(m.group(3)) != 1:
            continue
        fid = lab2id.get(m.group(1).strip())
        if not fid or fid not in byflag or run.flags.get(fid) == 1:
            continue
        name, d = byflag[fid]
        if name in [x[0] for x in out]:
            continue
        out.append((name, d))
    return out


def temp_flag_why(run, o):
    """그 장면 안에서 세워지는 플래그를 요구할 때, 그 값을 세우는 자리의 조건.

    조건문에는 「임시 플래그 2 == 2」만 적혀 있어 「조건 없음」으로 보인다. 실제로는 그
    장면의 두 번째 선택지라야 그 값이 되고, 그 선택지가 열리는 조건이 따로 있다.
    풍#20 「악은 악으로」가 그랬다 — 작성자가 「엽운상 루트였던 것 같다」고 짚어 주었고,
    ch6_8_4 의 그 선택지는 「위국 공략 중 또는 엽운상 무림대회 동행」이라야 열린다.

    택일(「또는」)이라 못 박지는 못한다. 그래서 값으로 대조하지 않고 문장만 보여 주며,
    이런 항목을 「확실」이라고 부르지 않는다.
    """
    # scene_group() 은 ch6_8_4 처럼 짧은 이름에 None 을 준다(다른 용도로 만든 함수다).
    # 여기서는 같은 스크립트이거나 한쪽이 다른 쪽의 앞자락일 때만 같은 자리로 본다.
    sc0 = o.get('script') or ''
    if not sc0:
        return []

    def same(a):
        return bool(a) and (a == sc0 or a.startswith(sc0 + '_') or sc0.startswith(a + '_'))

    lab2ids = {}
    for fid, lab in run.M['flags'].items():
        lab2ids.setdefault(lab, []).append(fid)
    out = []
    for chunk in (o.get('flags') or []):
        m = re.match(r'\[플래그 ([^\]]+?)\]\s*==\s*(-?\d+)', chunk)
        if not m:
            continue
        lab, val = m.group(1).strip(), m.group(2)
        for fid in lab2ids.get(lab, []):
            for r in ((DEPG.get(fid) or {}).get(val) or []):
                if same(r.get('sc')):
                    out += r.get('why') or []
    return sorted(set(out))


# 대본에 조건 없이 나오지만, 그 사람이 없어도 장면이 도는 것을 세이브로 확인한 자리.
# 작성자의 4년차 세이브(Save_003·004)는 상관형·위국이 당문에 없는데 ch8_1_2 와 ch8_2_6_2 를
# 그대로 지나갔다 — 게임이 없는 사람도 연출로 세운다. ch8_2_6_2_5 는 그 다음 장면인데,
# 들어가는 갈림(Ch_8_2_6_2_005)이 금향궁 지원·단하자만 보고 인물 유무는 보지 않는다.
# ch7_5_6_3 · ch7_5_6_3_1(수라장)은 공략 중인 사람에 따라 갈래가 나뉠 뿐, 대본의 다른 인물은 문을 막지 않는다.
CAST_NOT_GATE = {'ch8_1_2', 'ch8_2_6_2', 'ch8_2_6_2_5', 'ch7_5_6_3', 'ch7_5_6_3_1',
                 'ch2_6_3_1'}   # 상관형이 이야기 속 손님으로 조건 없이 등장한다(생#99, 작성자 2026-10-07)

# 시트는 「현재 달성 불가능」이라 했지만 게임 파일로 길이 열려 있는 것을 확인한 항목.
# 생#82: ch7_5_6_3_1 의 하후란 갈래는 [하후란 공략 중] + 패배 + [임시 플래그 2] == 0 이면 준다.
# 임시 플래그 2 를 1 로 만드는 자리는 ch7_5_6_3 의 「하후란 + 엽운상 공략 중」뿐인데, 하후란은
# 공동파 유학 회차에서만 켜지고 엽운상은 그 회차에서 못 켜므로(3년 1월에 떠난다) 늘 0 이다.
# 시트와 작성자의 시도는 용상 갈래(임시 플래그 1 == 3, 못 만듦)였다.
SHEET_WRONG = {10081}


def jhg_state(run):
    """만리붕정(ch8_2_6_2_5)을 막는 금향궁 지원이 어떤 상태인가. ('bad'|'ok'|'pend', 문장)

    지원은 [가는 길에 들름]==2 · [쫓겨나지 않음] · [지지 대상]==2 셋이 다 맞아야 선다.
    값 0 은 아직 안 고른 것일 수 있어 「끊겼다」로 치지 않는다 — Save_009 의 들름 0 을
    끊긴 것으로 읽었다가, 작성자가 그 뒤 금향궁에 들르고 지지해서 막혔다.
    """
    f = run.flags
    if f.get('M80009') == 1:
        return 'bad', '금향궁 지원 1 — 「대문을 굳게 닫는다」가 만리붕정으로 안 간다'
    if f.get('M60038') == 1 or f.get('M60041') == 1:
        return 'ok', ''
    # 용상을 받아들이면(M60036) 지지 선택지가 「용상의 의견을 묻는다」 하나만 남아 지지가 2 로 굳는다.
    # 작성자가 「Save_011 은 용상을 받아들인 뒤라 늦었다」고 잡아 주었다.
    if f.get('M60016') == 2 and f.get('M60036') == 1 and not f.get('M60041'):
        return 'bad', '금향궁에 들렀고 용상을 받아들여 지지가 금향궁으로 굳는다 — 만리붕정으로 안 간다'
    # 무림대회가 지났고 셋이 전부 지원 쪽으로 굳었으면 4년 2월 ch8_1_2 에서 1 이 선다.
    if run.wk > 3102 and f.get('M60016') == 2 and f.get('M60038') == 2 and not f.get('M60041'):
        return 'bad', '금향궁에 들르고 지지해서 4년 2월에 금향궁 지원이 선다 — 만리붕정으로 안 간다'
    if run.wk > 3102 and f.get('M60038') != 2:
        return 'ok', ''                  # 무림대회가 지났고 금향궁을 안 골랐다
    if run.wk > 4022 and f.get('M80009') == 0:
        return 'ok', ''
    return 'pend', '금향궁 지원 끊기 (무림대회에서 용상 거절 → 정파 또는 수수방관)'


def cast_missing(run, o, path=None):
    """이 경로에 나오는 사람 중, 지금 이 회차에 없는 사람.

    조건문에 안 적히는 요구다. 생#98 「패자의 죽음」은 조건이 「결투 승패 == 0」뿐이라
    「확실」로 나왔는데, 그 장면에는 엽운상이 나온다 — 아직 거두지 않은 회차에서는
    열릴 수 없는 자리다. 작성자가 잡아 주었다.

    상류 한 단계까지 본다. 그 장면 자체에는 조건부로만 나오고, 바로 위 장면에서
    조건 없이 나오는 경우가 있다 (ch3_1_7_5_1 과 ch3_1_7_4 가 그랬다).
    """
    if not CAST or not PRES:
        return []
    # 조건 없이 나오는 사람(sure)만 센다. 조건부로 나오는 사람은 없어도 그 장면은
    # 열린다 — maybe 까지 세면 생#68 하나에 다섯 명이 붙어 전부 「대기」가 되어 버린다.
    # 들어오는 길이 여럿인 entries 는 보지 않는다. 그 길 중 하나만 타면 되기 때문이다.
    p = path or {}
    # 엔딩·업적 장면은 그때 살아 있는 사람을 전부 부른다. 특정 인물이 조건인 것이
    # 아니라 결과를 함께 보여 주는 것이라, 여기서는 세지 않는다.
    if p.get('via') in ('ending', 'achievement', 'cg'):
        return []
    scs = {o.get('script'), (p.get('origin') or {}).get('via')} - CAST_NOT_GATE
    need = set()
    for sc in scs:
        need |= set((CAST.get(sc) or {}).get('sure') or [])
    out = []
    for who in sorted(need):
        fid = (PRES.get(who) or {}).get('flag')
        if fid and not run.flags.get(fid):
            out.append(who)
    return out


def req_line(run, o, path=None, width=5):
    """이 경로의 조건을 한 줄로. 지금 값과 대조해 표시한다.

    스탯 조건이 제일 쓸모 있어 앞에 두고, 없으면 플래그와 선택지/주사위/전투로 채운다.
    비어 있는 줄은 「조건 없음」이지 「모른다」가 아니어야 한다.
    """
    singles, groups, gone = [], [], []
    for kind, payload in _atoms(o):
        if kind == 'any':
            groups.append(payload)
        elif passed(payload[4], run.wk):
            gone.append(payload)          # 이미 판가름난 자리 — 대조하지 않는다
        else:
            singles.append(payload)
    bits, unmet, unknown = [], 0, 0
    for name, op, val, up, _aw in _tighten(singles):
        cur = cur_value(run, name)
        show = cname(LOVER_SHOW(run, val)) if name == '마음에 둔 사람' else val
        # 오는 길에서 주운 조건은 이 항목의 조건이 아닐 수 있다. 흐리게 적는다.
        label = (dim('경로 ') if up else '') + f'{paint(name)} {OPTX[op]}{show}'
        if cur is None:
            unknown += 1
            bits.append((dim(label + ' ?'), 2))
            continue
        curshow = cname(LOVER_SHOW(run, cur)) if name == '마음에 둔 사람' else cur
        if _holds(op, cur, val):
            # 아슬아슬한 조건은 여유를 적어 준다. 「이사형 호감도 <30」에 28 로 서 있으면
            # 통과 표시만 봐서는 한 번만 더 올라도 닫힌다는 것을 모른다.
            slack = ''
            if isinstance(cur, int) and isinstance(val, int) and name != '마음에 둔 사람':
                room = {'<': val - cur - 1, '<=': val - cur,
                        '>': cur - val - 1, '>=': cur - val}.get(op)
                if room is not None and room <= 3:
                    slack = warn(f' 여유 {room}')
            bits.append((ok(f'{label} \u2713') + slack, 1 if slack else 0))
        else:
            unmet += 1
            bits.append((bad(f'{label} \u2717{curshow}'), 1))
    for grp in groups:
        met = any(cur_value(run, n) is not None and _holds(op, cur_value(run, n), v)
                  for n, op, v in grp)
        label = ' 또는 '.join(f'{paint(n)} {OPTX[op]}{v}' for n, op, v in grp)
        bits.append((ok(label + ' \u2713') if met else bad(label + ' \u2717'), 0 if met else 1))
        unmet += 0 if met else 1
    # 그 장면에 나오는 사람이 아직 없으면, 수치를 다 맞춰도 그 자리는 오지 않는다.
    # bits 를 자르기 전에 넣어야 한다 — 이것 하나뿐인 경우가 있고, 그때 「조건 없음」
    # 으로 빠져나가면 생#98 처럼 「확실」이 되어 버린다.
    # 그 장면 안에서 정해지는 플래그의 조건. 못 박을 수 없으니 문장만 보여 준다.
    for msg in dice_blocked(run, path):
        unmet += 1
        bits.append((bad(msg), 1))
    for t in temp_flag_why(run, o):
        unknown += 1
        bits.append((dim('그 자리 조건: ') + warn(t.replace('[플래그 ', '').replace(']', '')), 2))
    gone_cast = cast_missing(run, o, path)
    if gone_cast:
        show = '  '.join(cname(w) for w in gone_cast[:3])
        more = f' +{len(gone_cast) - 3}' if len(gone_cast) > 3 else ''
        bits.append((bad(show) + bad(' 없음' + more), 2))
    # 지난 자리의 조건은 판정에서 뺀다. 무엇이 있었는지는 맨 뒤에 흐리게 남긴다.
    for name, op, val, up, _aw in _tighten(gone):
        bits.append((dim(f'{name} {OPTX[op]}{val} 지남'), -1))
    # 못 맞춘 것부터. 스탯만 판정 대상이라 여기서 자른다.
    bits.sort(key=lambda b: -b[1])
    head = [b[0] for b in bits[:width]]
    more = len(bits) - len(head)
    if more > 0:
        head.append(dim(f'+{more}'))
    # 행동(고르기·주사위·전투)은 판정이 아니라 방법이다. 그 다음에 붙인다.
    if path is not None:
        head += [t for t, _ in step_bits(path)][:2]
    pend = [len(gone_cast)]
    if o.get('script') == 'ch8_2_6_2_5':
        st, why = jhg_state(run)
        if st == 'pend':
            pend[0] += 1
            head.append(warn('아직 ') + dim(why))
    allfl = flag_bits(run, o, pend)
    fl = sorted(allfl, key=lambda t: 0 if '아직' in t else 1)[:3]
    if fl:
        head.append(dim('· ') + '  '.join(fl))
    if not head:
        return dim('조건 없음 — 그 장면이 오면 발생'), 0, 0, 0, 0
    return '  '.join(head), unmet, unknown, len(bits), pend[0]


def LOVER_SHOW(run, v):
    return run.M['lover'].get(str(v), v)


def lover_of(run):
    """지금 심계. 아직 정해지지 않았으면 None.

    변심의 꿈으로 비운 직후 세이브에는 99 가 들어 있다 - 표에 없는 값이다. 이것을
    그냥 값으로 다루면 「심계가 엽운상 여야 한다 (지금 99)」 같은 말이 나오고, 아직
    아무 쪽도 안 닫혔는데 심계 조건이 붙은 항목이 전부 「심계를 바꿔야」로 빠진다.
    """
    lv = run.stats.get('lover')
    return lv if str(lv) in run.M['lover'] else None


def lover_tally(run, D, got, rf, owned, fmap, PQ, DEP):
    """심계를 누구로 두면 무엇이 열리는가. 한 회차에 한 명이라는 전제에서의 비교표."""
    items = D['items']
    have = owned or {x['id'] for x in items if x.get('owned')}
    reach = make_reachable(run, D, PQ, DEP, got, make_decided(run, got))
    cnt, names = {}, {}
    for it in items:
        if it['id'] in have or it.get('blocked') or not it.get('reachable'):
            continue
        for o in it['opts']:
            lv = opt_lover(o)
            if lv is None:
                continue
            saved = run.stats.get('lover')
            run.stats['lover'] = lv               # 그 심계였다면 어떻게 되는가
            v, _ = opt_verdict(run, it, o, got, rf, lv, fmap, D, PQ, reach)
            run.stats['lover'] = saved
            if v == '가능':
                cnt[lv] = cnt.get(lv, 0) + 1
                names.setdefault(lv, []).append(it['type'][0] + '#' + str(it['no']))
                break
    if not cnt:
        return []
    L = [rule('심계별로 열리는 항목')]
    L.append(dim('   한 회차 안에서 심계를 바꾸지 않는다고 보고 센 것이다.'))
    L.append(dim('   지금 심계로 되는 것은 위 목록에 이미 들어 있다.'))
    now = run.stats.get('lover')
    for lv, n in sorted(cnt.items(), key=lambda x: -x[1]):
        who = run.M['lover'].get(str(lv), lv)
        tag = cname(who) + (ok(' (지금)') if lv == now else '')
        L.append(f'   {pad(tag, 18)} {n}개   '
                 + dim(' '.join(sorted(set(names[lv])))[:60]))
    return L


# ---------------------------------------------------------------- 보고서
# ---------------------------------------------------------------- 자유행동 확률
# 위치마다 결과 후보가 가중치로 뽑힌다. 사람을 거둘수록 후보가 늘어 분모가 커지므로,
# 같은 인물 이벤트라도 회차가 갈수록 덜 나온다 — 작성자가 「엽남매가 거의 안 나와」라고
# 한 것이 이것이다. 그래서 확률을 세어 보여 준다.
POS_KO = {
    'Door_Free_001': '대문 · 자유', 'Door_Work_001': '대문 · 업무', 'Door_02': '대문 · 들어설 때',
    'Fortress_Work_001': '외성 · 업무', 'Back_Free_001': '뒷산 · 자유', 'Back_Work_001': '뒷산 · 업무',
    'Center_Free_001': '정심당 · 자유', 'Center_Work_001': '정심당 · 업무',
    'Alchemy_Work_001': '연단방 · 업무', 'Kitchen_Work_001': '부엌 · 업무',
    'Forge_Work_001': '대장간 · 업무',
    'Farm_Work_001': '농장 · 업무', 'Study_Work_001': '강경당 · 업무',
    'Room_Work_001': '남제자방 · 업무', 'GirlRoom_Free_001': '여제자방 · 자유',
    'GirlRoom_Work_001': '여제자방 · 업무', 'Mall_Free_001': '저잣거리 · 자유',
    'Mall_Work_001': '저잣거리 · 업무', 'Spa_Free_001': '온천 · 자유',
    'Pharmacy_Work_001': '약방 · 업무', 'Teashop_Work_001': '찻집 · 업무',
    'Fish_01': '낚시', 'Walk_01': '산책', 'Chess_01': '바둑', 'Casino_01': '도박',
    'Chess_02': '바둑 2', 'Chess_03': '바둑 3',
}
# Back_02 · Back_03 · Forge_01 · Fortress_02 는 따로 고르는 행동이 아니다. 업무·자유를 누르면 먼저
# 굴리는 특수 사건 표라서 이름은 두 번째 표(then)에서 빌리고, 확률은 pos_elig 가 두 단계를 곱한다.
POS_SKIP = ('Ch_', 'Section_', 'Travel_')


def pos_name(name):
    return POS_KO.get(name) or name


def pos_elig(run, t, bytab):
    """그 행동을 한 번 했을 때 지금 조건에서 뽑힐 수 있는 결과와 확률. [(p, script)]"""
    def roll(tab):
        elig = []
        for o in tab['outcomes']:
            if not cond_ok(run, o['cond']):
                continue
            r = o['rate'] + sum(ri['rate'] for ri in o.get('rateItems') or []
                                if cond_ok(run, ri['cond']))
            elig.append((r, o))
        tot = sum(r for r, _ in elig) or 1
        return [(r / tot, o) for r, o in elig]
    saved = run.flags
    run.flags = {**saved, **(t.get('sets') or {})}
    try:
        out = []
        for p, o in roll(t):
            inner = roll(bytab[t['then']]) if o.get('forward') and t.get('then') in bytab else []
            if inner:
                out += [(p * q, oo['script']) for q, oo in inner]
            else:
                out.append((p, o['script']))
        return out
    finally:
        run.flags = saved


def pos_tables(tabs):
    """행동 하나당 표 하나. 첫 단계 표가 있으면 그 표로 두 단계를 함께 세고, 이름은 두 번째 표를 쓴다."""
    bytab = {t['name']: t for t in tabs or []}
    inner = {t['then'] for t in bytab.values() if t.get('then')}
    for t in bytab.values():
        if t['name'].startswith(POS_SKIP) or t['name'] in inner:
            continue
        yield t, pos_name(t.get('then') or t['name']), bytab
RE_COND = re.compile(r'\[([^\]]+?)\]\s*(==|!=|>=|<=|>|<)\s*(\[[^\]]+\]|-?\d+)')
CMP = {'==': lambda a, b: a == b, '!=': lambda a, b: a != b, '>=': lambda a, b: a >= b,
       '<=': lambda a, b: a <= b, '>': lambda a, b: a > b, '<': lambda a, b: a < b}


def wk_of(text):
    m = re.match(r'(\d+)년차 (\d+)월 (상순|중순|하순)', text or '')
    if not m:
        return None
    return (int(m.group(1)) * 1000 + int(m.group(2)) * 10
            + {'상순': 1, '중순': 2, '하순': 3}[m.group(3)])


def cond_ok(run, cond):
    """조건문이 지금 성립하는가. 못 읽은 조각은 막지 않는다."""
    if not cond or ' 또는 ' in cond:
        return True
    lab2fid = {}
    for fid, lab in run.M['flags'].items():
        lab2fid.setdefault(lab, fid)
    lab2st = {}
    for k, lab in run.M['stats'].items():
        lab2st.setdefault(lab, k)
    for part in cond.split(' 그리고 '):
        m = RE_COND.search(part)
        if not m:
            continue
        lhs, op, rhs = m.group(1), m.group(2), m.group(3)
        if rhs.startswith('['):
            w = wk_of(rhs[1:-1].replace('시점 ', ''))
            if w is None:
                continue
            cur, val = run.wk, w
        else:
            val = int(rhs)
            if lhs.startswith('플래그 '):
                lab = re.sub(r'\s*\(.*\)$', '', lhs[4:]).strip()
                fid = lab2fid.get(lab) or (lab if re.match(r'^[A-Z]', lab) else None)
                if fid is None:
                    continue
                cur = run.flags.get(fid, 0)
            elif lhs.endswith(' 호감도'):
                cur = run.affection(lhs[:-4].strip()) or 0
            elif lhs.startswith('시점') or lhs.startswith('잡물'):
                continue
            else:
                k = lab2st.get(lhs)
                if k is None:
                    continue
                cur = run.stats.get(k, 0)
        if not CMP[op](cur, val):
            return False
    return True


def where_section(run, G, AF, who, down=False):
    """그 인물 호감도가 오르는(또는 내리는) 자리를 지금 세이브 기준 확률과 함께.

    내리는 쪽도 필요하다. 「이사형 호감도 < 30」처럼 넘기면 닫히는 조건이 있어서,
    이미 넘겼을 때 되돌릴 자리가 어디인지가 곧 그 항목을 살리는 길이 된다.
    """
    who = Run.ALIAS.get(who, who)          # 「이사형」처럼 서열로 물어도 찾아 준다
    best = {}
    for g in AF.get(who) or []:
        if (g['d'] < 0) if down else (g['d'] > 0):
            cur = best.get(g['sc'])
            v = abs(g['d'])
            best[g['sc']] = v if cur is None else max(cur, v)
    L = [rule(f'{who} 호감도 — 지금 어디서 {"내려가나" if down else "오르나"}')]
    L.append(dim('   위치마다 결과가 가중치로 뽑힌다. 지금 조건이 맞는 후보만 세었다.'))
    L.append(dim('   사람을 거둘수록 후보가 늘어 같은 이벤트도 덜 나온다.'))
    L.append('')
    rows = []
    for t, nm, bytab in pos_tables(G['position']):
        elig = pos_elig(run, t, bytab)
        exp, hits = 0.0, []
        for p, sc in elig:
            # 결과 스크립트가 다시 갈라지는 경우가 있다(fortress_work_201 -> _201_01).
            # 그 아래에서 오르는 것도 그 결과가 뽑혀야 볼 수 있으니 같이 센다.
            d = max([v for k, v in best.items()
                     if k == sc or k.startswith(sc + '_')] or [0])
            if not d:
                continue
            exp += p * d
            hits.append(f'{"-" if down else "+"}{d} {int(p * 100)}%')
        if hits:
            rows.append((exp, nm, len(elig), hits))
    if not rows:
        L.append(dim(f'   지금 조건에서는 {who} 이벤트가 뜨는 자리가 없다'))
        return L
    for exp, nm, n, hits in sorted(rows, key=lambda x: -x[0]):
        L.append(f'   {pad(nm, 18)} {bold(f"회당 {chr(45) if down else chr(43)}{exp:.2f}")}   '
                 + dim(f'후보 {n}개 · ') + acc('  '.join(hits)))
    return L


def pos_odds(run, POS, AF, names=None):
    """장소·행동마다, 지금 조건에서 각 인물 호감도가 회당 얼마나 오르는가."""
    idx = {}
    for who, gs in (AF or {}).items():
        if names and who not in names:
            continue
        for g in gs:
            if g['d'] > 0:
                k = (who, g['sc'])
                idx[k] = max(idx.get(k, 0), g['d'])
    rows = []
    for t, nm, bytab in pos_tables(POS):
        elig = pos_elig(run, t, bytab)
        per = {}
        for p, sc in elig:
            for (who, gsc), d in idx.items():
                if gsc == sc or gsc.startswith(sc + '_'):
                    per[who] = per.get(who, 0.0) + p * d
        if per:
            rows.append((nm, len(elig), per))
    rows.sort(key=lambda x: -max(x[2].values()))
    return rows


# 심계 이름과 인물 이름이 다른 경우. 도감·조건은 「소사매」로, 세이브는 「당묵령」으로 부른다.
LOVER_AS_CHAR = {'소사매': '당묵령'}


def odds_section(run, POS, AF, lover_ko):
    L = [rule('자유행동 — 지금 어디서 누구 호감도가 오르나')]
    L.append(dim('   결과는 가중치 추첨이다. 사람을 거둘수록 후보가 늘어 같은 이벤트도 덜 뜬다.'))
    L.append(dim('   숫자는 회당 기대치. 한 사람만 보려면 --where <이름>'))
    L.append('')
    mine = LOVER_AS_CHAR.get(lover_ko, lover_ko)
    rows = pos_odds(run, POS, AF)
    if not rows:
        L.append(dim('   지금 조건에서 오르는 자리가 없다'))
        return L
    for nm, n, per in rows[:8]:
        top = sorted(per.items(), key=lambda x: -x[1])[:4]
        bits = '  '.join(
            (bold if w == mine else str)(f'{cname(w)} +{v:.2f}') for w, v in top)
        L.append(f'   {pad(nm, 18)} {bits}   {dim(f"후보 {n}")}')
    return L


def event_moves(run, AF, who, down=False):
    """자유행동 말고 사건 안에서 호감도가 움직이는 자리. 어느 선택지인지까지."""
    who = Run.ALIAS.get(who, who)
    rows = []
    for g in AF.get(who) or []:
        d = g['d']
        if ((d >= 0) if down else (d <= 0)):
            continue
        if not g.get('opt') and not g.get('when'):
            continue
        when = g.get('when') or ''
        m = re.match(r'(\d+)년 (\d+)월 (상순|중순|하순)', when)
        if m:
            wk = (int(m.group(1)) * 1000 + int(m.group(2)) * 10
                  + {'상순': 1, '중순': 2, '하순': 3}[m.group(3)])
            if wk < run.wk:
                continue                  # 이미 지난 자리는 알려 봐야 소용없다
        rows.append((when, abs(d), g['sc'], g.get('opt') or ''))
    seen, out = set(), []
    for r in sorted(rows, key=lambda x: (x[0] == '', x[0])):
        k = (r[2], r[3], r[1])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    if not out:
        return []
    sign = '-' if down else '+'
    L = [rule(f'{who} 호감도 — 사건에서 {"내려가는" if down else "올라가는"} 자리')]
    L.append(dim('   한 번뿐인 자리다. 선택지가 적힌 것은 그 선택지를 골라야 한다.'))
    L.append('')
    for when, d, sc, opt in out[:20]:
        tag = ok(f'{sign}{d}')
        L.append(f'   {pad(tag, 6)}{pad(when or dim("시점 미상"), 16)} {pad(dim(sc), 30)} '
                 + (acc(opt) if opt else ''))
    return L


# ---------------------------------------------------------------- 서무림맹
# 「우리도 무림맹을 결성한다」를 고르는 것과, 실제로 문파들이 합류하는 것은 다르다.
# 문파마다 사신을 보냈는지(파견)와 설득 결과가 따로 기록된다.
ALLY = [
    ('아미파',  'M70026', 'M70046', {1: '성공', 2: '실패', 3: '중립'},
     'M70029', '복운을 사신으로 보냄'),
    ('청성파',  'M70024', 'M70048', {1: '성공', 2: '실패'},
     'M70058', '당방을 사신으로 보냄'),
    ('공동파',  'M70025', 'M70050', {1: '성공', 2: '실패'},
     'M70034', '당문 제자를 사신으로 보냄'),
    ('개방',    'M70027', 'M70045', {1: '마부귀가 도움', 2: '실패', 3: '개방이 당문에 합류'},
     'E13011', '마부귀가 당문에 있음'),
]


# ch7_5_6_2 는 「공략 중」 값의 합만 본다. 상관형 2 를 세우는 ch7_5_4_9 는 입구가 「상관형 공략 중 == 1」인데
# 1 을 세우는 곳이 없어 이 빌드에서는 열리지 않는다. 실제로 짝이 되는 것은 하후란 + 용상 또는 소사매다.
ASURA_ROUTES = (('G11000', '소사매'), ('G11001', '상관형'), ('G11002', '엽운상'),
                ('G11003', '용상'), ('G11005', '하후란'))
ASURA_WK = 4022                       # 4년차 2월 중순


def asura_section(run, owned=()):
    """수라장 경보. 켜지고 나면 손쓸 데가 없어서 미리 말해야 의미가 있다."""
    on = run.flags.get('M70059')
    hit = run.flags.get('M70054')
    live = [(who, run.flags.get(f) or 0) for f, who in ASURA_ROUTES
            if (run.flags.get(f) or 0) > 0]
    total = sum(v for _, v in live)
    if not live and not on:
        return []
    L = [rule('수라장 — 공략 중인 사람')]
    L.append('   ' + ('  '.join(f'{cname(w)} {dim(str(v))}' for w, v in live)
                      or dim('아무도 없음'))
             + f'   합계 {bold(str(total))}')
    if hit:
        L.append(bad('   이미 발생했다.') + dim(' 용상·하후란은 공략 중이 2 가 되어 결말이 닫혔다.'))
    elif on:
        L.append(bad('   시작 플래그가 켜졌다 — 다음 순에 발생한다. 피할 자리가 없다.'))
    elif total >= 2:
        L.append(bad('   합계가 2 이상이다 — 8장 갈림(ch7_5_6_2)에서 수라장이 켜진다.'))
    elif run.wk < ASURA_WK:
        L.append(ok('   아직 안전하다.') + dim(' 합계가 2 가 되는 순간 확정된다.'))
    if not hit and run.flags.get('G11005') == 1 and (on or total >= 2) and 10081 not in owned:
        L.append(acc('   하후란 공략 중이라 수라장 결투 상대는 하후란이다. 지면 생사부 82 「봉인된 흑암대법사」.'))
    return L


def league_section(run):
    """서무림맹 결성 현황. 결정만 하고 문파를 못 모으면 이름뿐이다."""
    dec = run.flags.get('M70015')
    if dec is None:
        return []
    NAMES = {1: '강호 은퇴', 2: '끝까지 싸움', 3: '무림맹에 호응', 4: '서무림맹 결성'}
    L = [rule('서무림맹 — 결성 현황')]
    L.append(f'   {pad("너의 결정", 20)} '
             + (ok(NAMES.get(dec, f'값 {dec}')) if dec else dim('아직 안 정해짐')))
    if dec != 4:
        L.append(dim('   서무림맹 노선이 아니라 문파 설득은 일어나지 않는다.'))
        return L
    L.append(dim('   문파마다 사신을 보내야 설득 장면이 열린다. 보내지 않으면 결과가 0 으로 남는다.'))
    L.append('')
    for who, sent, res, names, extra, extra_ko in ALLY:
        v = run.flags.get(res)
        sv = run.flags.get(sent)
        if v in names:
            st = ok(names[v]) if v == 1 else warn(names[v])
        elif sv == 1:
            st = warn('사신은 보냈고 결과는 아직')
        elif sv == 0:
            st = bad('사신 안 보냄')
        elif sv == -1:
            # ch7_5_4_7 이 「대사형을 따라감」 노선에서 -1 을 박는다. 보낼 사람이 없다는 뜻.
            st = bad('보낼 사람이 없었다')
        else:
            st = dim(f'파견 플래그 {sv} — 뜻을 모른다')
        tail = ''
        if run.flags.get(extra) == 1:
            tail += dim(f'   {extra_ko} ✓')
        L.append(f'   {pad(who, 10)}{st}{tail}')
    # 금향궁은 설득이 아니라 무림대회 지지와 출격 결과로 갈린다
    g = run.flags.get('M80009')
    o = run.flags.get('M80010')
    OUT = {1: '금향궁이 서무림맹 합류', 2: '되받아 고함', 3: '고함당함', 4: '문 열고 맞서 싸움'}
    # 그 플래그는 4년 2월 중순 동서무림맹 대전(ch8_1_2)이 세운다. 그 전에는 0 인 것이 정상인데
    # 「지원 없음」이라고만 적어 두면 실패한 것으로 읽힌다.
    ready = all(run.flags.get(f) == v for f, v in
                (('M60016', 2), ('M60041', 0), ('M60038', 2)))
    if g == 1:
        st = ok('당문을 지원')
    elif run.wk <= 4022:
        st = (acc('조건 충족 — 4년차 2월 중순 동서무림맹 대전 에서 붙는다') if ready
              else warn('아직 그 사건이 안 왔다'))
    else:
        st = bad('지원 없음')
    L.append(f'   {pad("금향궁", 10)}{st}'
             + (dim('   출격 결과: ') + (ok(OUT[o]) if o == 1 else warn(OUT[o])) if o in OUT else ''))
    if g != 1 and not ready:
        L.append(dim('      ch8_1_2 조건 — 금향궁에 손님으로 감 · 쫓겨나지 않음 · 무림대회에서 금향궁 지지'))
    return L


# 한 번뿐인 판정. 그 순이 지나면 회차 안에서 다시 오지 않는데, 조건이 조건문 한 줄에
# 모여 있지 않아(중첩된 switch 를 걷어야 한다) 항목 조건으로는 잡히지 않는다.
# 게임 파일에서 확인한 것만 손으로 적는다.
ONESHOT = (
    {
        'wk': 3011, 'name': '대사형 완쾌', 'flag': 'M40010', 'sc': 'S0401_01',
        'note': '미션 조건은 없지만 자리가 연단방이다 — 그 순에 **연단방에 가야** 뜬다. '
                '시간만 흘리면 그냥 지나간다. 처세가 높으면 오히려 막힌다. '
                '얻는 것: 와운강 결전(ch4_6_2)에서 대사형이 주사위 없이 정식으로 이긴다. 완쾌가 아니면 '
                '1~99 주사위로 절초를 고른다 — 50 이상 「조금 위험한 절초」는 똑같이 이기고, 50 미만 '
                '「안전한 절초」는 죽은 척해서 일부러 져 준다(명성 -4 · 동행자 복운). 이기는 쪽에서만 '
                '석공원 부부 화해를 도움(M40049) · 동행자 용상 · 명성 +5 가 붙는다. '
                '완쾌 자체를 조건으로 거는 도감은 없다.',
        'need': [('처세', '<', 60), ('대사형 호감도', '>=', 40),
                 ('기술 의술', '>=', 4), ('누적 연단', '>=', 200)],
        # 그 장면이 어느 갈래로 갔는지가 StorySave 에 남는다. 플래그보다 진단이 정확하다.
        'story': [('S0401_01_004', True, '완쾌 갈래를 탔다'),
                  ('S0401_01_003', False, '처세가 60 이상이라 그 앞에서 갈라졌다'),
                  ('S0401_01_005', False, '의술 4 또는 누적 연단 200 이 모자랐다'),
                  ('S0401_01_002', None, '처세 80 미만 · 대사형 호감도 40 이상은 통과했다')],
    },
    {
        'wk': 3053, 'name': '설산행 발동', 'flag': 'M10017', 'sc': 'S2500_01',
        'note': '3년 5월 하순 S2500_01(雪山行前置). 켜지면 6월 중순 출발 → 여행 끝에 '
                '플래그가 서고 7월의 因果·決勝日이 열린다.',
        'need': [('하후란 호감도', '>=', 40)],
        'needFlag': [('S0014_02', 1, '하후란을 스승으로 모심')],
    },
)

# 라인이 갈리고 **라인마다 보는 값이 아예 다른** 관문. 한 표에 담으면 「조건 셋 중 하나」로
# 읽혀 엉뚱한 값을 올리게 된다 — 대사형 생존이 그랬다. 작성자가 실제 플레이로 짚어 주었다.
BRANCHED = (
    {
        'wk': 3102, 'name': '금향궁 지원 끊기 (만리붕정)', 'flag': 'M80009_OFF',
        'note': '금향궁 지원(M80009)은 4년 2월 중순 ch8_1_2 에서 아래 셋이 **모두** 맞을 때만 1 이 된다. '
                '1 이면 당문 포위전의 「대문을 굳게 닫는다」가 만리붕정(ch8_2_6_2_5) 대신 ch8_2_6_2_7 로 가서 '
                '생사부 68·84 가 닫힌다. 셋 중 **하나만** 어긋나면 된다 — 아래 「된다」가 하나라도 뜨면 안전하다. '
                '주의: 값 0 은 「아직 안 정함」일 수 있다. 지지 대상은 무림대회(3년 10월 중순)에서 정해진다. '
                '가는 길의 금향궁 방문(M60016 = 2)은 **강제**다 — ch6_3_5 의 「홀로 강릉으로 간다」는 조건이 XXX(정의 없음)라 영영 잠겨 있다(작성자 확인). '
                '「용상의 의견을 묻는다」는 금향궁 지지와 같은 2 를 세우는 함정이다. '
                '**용상을 받아들이면(ch6_7_1, M60036) 지지 선택지가 그것 하나만 남는다** — 그래서 금향궁에 들른 회차라면 '
                '무림대회에서 「정세가 불확실하니 일단 입장을 밝히지 않는다」로 용상을 거절해야 한다.',
        'lines': [
            {
                'name': '하나만 깨면 된다 (가는 길의 금향궁 방문은 강제라 못 깬다)',
                'where': '용상을 거절하고 지지를 정파 또는 수수방관으로 두는 것이 현실적인 길이다',
                'any': [
                    {'flag': [('M60038', 2, '무림대회 지지 대상 ≠ 금향궁', '!=')],
                     'then': '「정파와 같은 진영」 또는 「수수방관」 (아직 0 이면 안 고른 것일 수 있음)'},
                    {'flag': [('M60036', 1, '무림대회에서 용상을 받아들이지 않음', '!=')],
                     'then': 'ch6_7_1 「정세가 불확실하니 일단 입장을 밝히지 않는다」 (용상 호감도 30 미만이면 선택지 없이 자동)'},
                    {'flag': [('M60041', 0, '금향궁행에서 쫓겨남', '!=')],
                     'then': 'ch6_4_4_2 「개소리는 집어치워라」(수양 < 40 · 성정 ≥ 60) → 「이딴 곳에선 당장 나가주지」'},
                ],
            },
        ],
    },
    {
        'wk': 3051, 'name': '금오상인 사망', 'flag': 'M50018',
        'note': '3년 5월 상순 ch5_4_8_2 의 결투에서 이긴 뒤, 그 자리에서 두 번 더 갈린다. '
                '첫 관문의 열쇠는 4장에서만 만들어지므로 5장에 와서는 손쓸 데가 없다. '
                'M50018 은 6~8장에서 여러 곳이 읽는다(회의의 직접 제안 조건도 그중 하나).',
        'lines': [
            {
                'name': '① 4장에서 열쇠 만들기 (둘 중 하나)',
                'where': '이게 없으면 이겨도 ch5_4_8_3 으로 빠져 죽일 자리에 못 간다',
                'any': [
                    {'flag': [('M40046', 1, '삼문 회담에서 금오상인과 겨룸')],
                     'then': '간병 라인 ch4_6_13_3 — 「공력을 거둔다」 → 습격 → 「응한다」 → CL_1409_04 승리'},
                    {'flag': [('M40020', 0, '와운강 귀환 결과 ≠ 0', '!=')],
                     'then': '하산 라인 ch4_8_8 — 1 은 금오상인에게 머리 맞음, 2 는 신도룡에게 내력 흡수'},
                ],
            },
            {
                'name': '② 5장 결투 (3년 5월 상순 ch5_4_8_2)',
                'where': '첫 결투에서 이겨야 한다. 지면 ch5_4_8_3 으로 간다',
                'any': [
                    {'flag': [('M50017', 1, '금오상인 첫 결투 = 승')]},
                ],
            },
            {
                'name': '③ ch5_4_8_8_1 의 주사위 — 마지막 갈림',
                'where': '여기서 금오상인이 죽느냐 도망치느냐가 갈린다',
                'any': [
                    {'flag': [('M50009', 1, '공동 영전 - 소사매 참전')],
                     'then': '1 이면 주사위가 어느 쪽으로 굴러도 ch5_4_8_8_3 에 닿아 죽는다'},
                ],
                'then': '소사매 참전이 0 이면 주사위에 **성공할 때 ch5_4_8_8_4 로 새어 살아서 도망간다** — '
                        '일부러 실패해야 ch5_4_8_8_2 를 거쳐 죽는다. '
                        '작성자가 「이기고 회피도 했는데 안 죽었다」고 한 자리가 이것이다.',
            },
        ],
    },
    {
        'wk': 4012, 'name': '8장 라인 갈림', 'flag': 'M7001_MARK',
        'note': '회의 결과와 문파 설득 결과로 8장이 둘 중 하나로 정해진다. 항전은 4년 1월 중순, '
                '서무림맹은 4년 2월 중순에 갈린다. 두 라인은 이어지는 장면이 거의 안 겹치므로 '
                '한 회차에 한쪽 결말만 볼 수 있다. 「서무림맹 결성」을 골라도 네 문파를 하나도 '
                '못 모으면 A 로 간다 — 작성자가 짚어 준 자리다. '
                '다만 복운이 합류해 있으면(회의 직전 ch7_3_3 에서 복운 호감도 20 이상 · 생존) '
                '3년 12월 하순에 아미파 사절이 저절로 나가고(ch7_5_4_3) 주사위 없이 성공한다'
                '(ch7_5_5_3 첫 가지) — 그 회차의 서무림맹은 늘 B 다. 대본 확인, 게임 미확인. '
                '(대본: ch7_5_6_1 이 정하고 ch7_5_6_2 가 메인 미션 M7001_01 / M7002_01 을 고른다)',
        'lines': [
            {
                'name': 'A · 당문 포위전 — 당문 혼자 무림맹을 맞는다',
                'where': '한청서 37~46 연인별 후일담이 전부 이 라인에 있다 (ch8_1_1_1 → ch8_6_*)',
                'any': [
                    {'flag': [('M70052', 1, '항전 노선')],
                     'then': '회의가 「끝까지 싸운다」로 끝난 경우'},
                    {'flag': [('M70015', 4, '너의 결정 = 서무림맹'),
                              ('M70045', 1, '개방 설득 ≠ 마부귀 도움', '!='),
                              ('M70046', 1, '아미파 설득 ≠ 성공', '!='),
                              ('M70048', 1, '청성파 설득 ≠ 성공', '!='),
                              ('M70050', 1, '공동파 설득 ≠ 성공', '!=')],
                     'need': [('복온 호감도', '<', 20)],
                     'then': '또는 서무림맹 결성을 선언하고 네 문파를 하나도 못 모은 경우 '
                             '(복운 호감도 20 이상이면 아미파가 저절로 성공해 이 길은 닫힌다)'},
                ],
            },
            {
                'name': 'B · 동서무림맹 대전 — 서무림맹을 이끌고 무림맹과 싸운다',
                'where': '상갓집 개·비협귀환·대원 결전이 이 라인이다 (ch8_1_2 → ch8_2_* ch8_3_* ch8_4_*)',
                'then': 'A 의 두 경우가 모두 아니면 이쪽이다. 서무림맹을 결성하고 문파를 하나라도 모으면 여기로 간다.',
            },
        ],
    },
    {
        'wk': 3121, 'name': '회의 선택지 갈림', 'flag': 'M70004',
        'note': '3년 12월 상순 회의(ch7_4_2_break_start_01). [서무림맹 결성 가능](M70004)이 1 이면 '
                '「서무림맹 결성」만 뜨고 「강호 은퇴 = 당문 해체」와 「끝까지 싸운다」가 통째로 잠긴다. '
                '0 이면 반대로 서무림맹이 안 뜨고, 그때만 투표(ch7_4_3_1)가 열려 은퇴와 항전을 가른다. '
                '복운만 20 이상이면 복운만 합류하고 이 값은 안 켜진다. 아래 넷 중 하나라도 걸리면 1 이다. '
                '①만 플레이어가 고르는 것이고 ②③④ 는 조건이 맞으면 저절로 켜진다 — '
                '②는 그 대화를 끝내는 순간 지나가므로 피할 길이 없다 — 이부귀를 20 밑으로 두는 것이 '
                '유일한 방법이다. 작성자의 회차가 그것으로 켜졌다(①은 위국·심상 조건에 막혀 뜨지도 않았다). '
                '「무림맹에 호응」은 조건이 XXX(정의 없음)라 이 빌드에서는 회의에 영영 안 뜬다.',
        'lines': [
            {
                'name': '① 소국의 편지',
                'where': 'ch7_3_2 대화의 7번 항목 → ch7_3_2_6. 고를 때만 켜진다',
                'any': [{'flag': [('Talk_Option_06', 0, 'Talk_Option_06 == 0'),
                                  ('E12002', 1, '위국이 당문에 있음')],
                         'need': [('심상', '>', 20)],
                         'then': '이 셋이 다 맞아야 항목이 뜬다(아니면 ~x 로 잠긴다)'}],
            },
            {
                'name': '② 개방이 제안',
                'where': 'ch7_3_3 — 그 대화의 「나가기」(exit) 목적지라 피할 수 없다',
                'any': [{'need': [('이부귀 호감도', '>=', 20)]}],
            },
            {
                'name': '③ 직접 제안 · 전술',
                'where': 'ch7_4_1',
                'any': [{'flag': [('M50018', 1, '금오상인 사망')],
                         'need': [('기술 전술', '>=', 8)]}],
            },
            {
                'name': '④ 직접 제안 · 학문',
                'where': 'ch7_4_1',
                'any': [{'flag': [('M50018', 1, '금오상인 사망')],
                         'need': [('학문', '>=', 60), ('기술 전술', '>=', 5)]}],
            },
        ],
    },
    {
        'wk': 3013, 'name': '대사형 생존', 'flag': 'M40034',
        'note': '3년 1월 중순 ch4_6_3 에서 라인이 갈린다. 두 라인은 만나지 않는다 — '
                '하산했으면 의술·연단·남궁호심결·내력을, 남았으면 운명·명성·도덕을 안 본다.',
        'lines': [
            {
                'name': 'A · 하산 라인',
                'where': 'ch4_6_3 → ch4_7_1 → ch4_8_10_1',
                'any': [
                    {'need': [('운명', '>=', 10)],
                     'then': '선택지 두 번째 「어떻게든 대사형이 살아 있기를 바란다」'},
                    {'flag': [('M40020', 2, '와운강 귀환 결과 2')],
                     'need': [('명성', '>=', 50), ('도덕', '>=', 80)]},
                    {'flag': [('M40020', 2, '와운강 귀환 결과 2'), ('G30003', 1, '신도룡과 아는 사이')],
                     'need': [('신도룡 호감도', '>=', 30)]},
                ],
            },
            {
                'name': 'B · 당문 간병 라인',
                'where': 'M3004_01/02 → ch4_6_9 → ch4_6_13 → ch4_6_15',
                'any': [
                    {'need': [('기술 의술', '>=', 5)], 'then': '① 전승 사건 진입 (둘 중 하나면 된다)'},
                    {'need': [('누적 연단', '>=', 250)], 'then': '① 전승 사건 진입 (둘 중 하나면 된다)'},
                ],
                'then': '② ch4_6_13 에서 생존 점수(M40033)를 쌓아 ch4_6_15 에서 2 이상이라야 한다. '
                        '남궁호심결 3 이상이면 내력 50/35/25 에 +3/+2/+2, 없으면 기본 +1 에 내력 50 으로 +1 뿐이다. '
                        '우소매가 없으면 그 뒤 선택지에서 반드시 「공력을 거둔다」를 고른다 — 점수 -1 과 수명·내력 -1 을 '
                        '치르고 습격 전투(CL_1409_01~04, 전부 즉사)를 이겨야 하지만, 「공력을 거두지 않는다」는 '
                        '싸울 기회도 없이 검에 꿰뚫려 대사형이 그 자리에서 죽는다(E10000=1, 심상 -20, 공동·청성과 교전). '
                        '그래서 감점을 메우려면 내력 50 이 필요하다. '
                        '남궁호심결은 비급 《남궁심법》(7012, 2500) 을 끝까지 익히면 3 이 된다(상점 2-11 이후).',
                'extra': [('기술 남궁호심결', '>=', 3), ('내력', '>=', 50)],
            },
        ],
    },
)


def _need_line(run, indent, lab, op, val):
    cur = cur_value(run, lab)
    hit = cur is not None and CMP[op](cur, val)
    shown = '?' if cur is None else str(cur)
    body = f'{indent}{pad(lab, 14)}{pad(op + " " + str(val), 8)}지금 {shown}'
    return dim(body) + (ok('  ✓') if hit else warn('  ✗')), hit


def branched_section(run):
    """라인마다 보는 값이 다른 관문. 라인을 나눠 보여 주고 각 줄을 세이브와 맞댄다."""
    L = []
    for c in BRANCHED:
        done = run.flags.get(c['flag']) == 1
        gone = run.wk > c['wk'] and not done
        if not L:
            L = [rule('갈래마다 조건이 다른 관문')]
            L.append(dim('   라인을 먼저 정하고 그 라인의 값을 맞춘다. 다른 라인 값은 판정에 안 쓰인다.'))
            L.append('')
        state = (ok('이미 켜졌다 ✓') if done
                 else bad('지났다 — 이 회차에서는 끝') if gone else warn('아직 앞에 있다'))
        L.append(f'   {pad(c["name"], 16)}{pad(wk_stage_ko(c["wk"]), 16)}' + state)
        for ln in c['lines']:
            L.append(f'      {ln["name"]}   ' + dim(ln.get('where') or ''))
            for grp in ln.get('any') or []:
                rows, all_ok = [], True
                for ent in (grp.get('flag') or []):
                    fid, want, lab = ent[0], ent[1], ent[2]
                    op = ent[3] if len(ent) > 3 else '=='
                    h = CMP[op](run.flags.get(fid) or 0, want)
                    all_ok = all_ok and h
                    rows.append(dim(f'         {pad(lab, 22)}') + (ok('✓') if h else warn('✗')))
                for lab, op, val in (grp.get('need') or []):
                    row, h = _need_line(run, '         ', lab, op, val)
                    all_ok = all_ok and h
                    rows.append(row)
                L.append(f'         {ok("· 된다") if all_ok else dim("·")}'
                         + (dim('  → ' + grp['then']) if grp.get('then') else ''))
                L += rows
            if ln.get('extra'):
                # 「어느 하나」(any) 를 넘은 다음에 또 넘어야 하는 줄이다. 같은 모양으로
                # 이어 놓으면 OR 그룹의 한 줄로 읽힌다 — 작성자가 「이거 하나만 하면 되냐」고
                # 물은 자리다. 단을 나눠 두 번째 관문임을 밝힌다.
                L.append(dim('         ── 그 다음 관문 (위를 넘긴 뒤 또 본다)'))
                for lab, op, val in ln['extra']:
                    L.append(_need_line(run, '         ', lab, op, val)[0])
            if ln.get('then'):
                L.append(dim('         ' + ln['then']))
            L.append('')
        if c.get('note'):
            L.append(dim('      ' + c['note']))
        L.append('')
    return L


def seen_story(run):
    """이 회차에서 실제로 지나온 장면 조각(AddStory). 어느 갈래를 탔는지가 여기 남는다."""
    if getattr(run, '_story', None) is None:
        run._story = {e.get('Key') for e in (run.gs.get('StorySave') or []) if e.get('Key')}
    return run._story


def story_report(run, needle):
    """장면 하나가 어느 가지로 갔는지 세이브 기록으로 읽는다.

    플래그는 결과만 말한다. 이야기 조각(AddStory)은 **지나온 가지**를 말하므로,
    지금 수치가 조건에 맞아도 그때는 아니었다는 것을 잡아낸다 — 대사형 완쾌가 그랬다.
        python save_read.py --story S0401_01
    """
    ST = load_json('story.json') or {}
    KEYS, SCENES = ST.get('keys') or {}, ST.get('scenes') or {}
    if not KEYS:
        return warn('story.json 이 없다. python mk_story.py 를 먼저 돌린다.')
    seen = seen_story(run)
    scs = [sc for sc in SCENES if needle.lower() in sc.lower()]
    if not scs:
        return warn(f'「{needle}」 이 든 장면을 story.json 에서 못 찾았다.')
    L = [rule(f'이야기 조각으로 본 갈래 — {needle}')]
    L.append(dim('   ●  지나온 조각   ·  ○  안 지난 조각. 조건은 그 조각을 감싼 가지다.'))
    L.append('')
    for sc in sorted(scs)[:12]:
        keys = SCENES[sc]
        any_seen = any(k in seen for k in keys)
        L.append(f'   {sc}   ' + (ok('이 장면은 지났다') if any_seen
                                  else dim('이 장면의 기록이 없다 — 아직 안 지났거나 다른 길로 갔다')))
        for k in keys:
            e = KEYS.get(k) or {}
            mark = ok('  ● ') if k in seen else dim('  ○ ')
            cond = ' · '.join(e.get('conds') or []) or '(가지 조건 없음 — 장면 최상위)'
            if e.get('unknown'):
                cond += '  ' + warn('(못 읽은 조건 있음)')
            L.append(mark + pad(k, 26) + dim(cond[:78]))
        L.append('')
    return chr(10).join(L)


def oneshot_section(run):
    """한 번뿐인 판정이 아직 앞에 있는지, 지금 값으로 통과하는지."""
    rows = []
    for c in ONESHOT:
        done = run.flags.get(c['flag']) == 1
        gone = run.wk > c['wk'] and not done
        rows.append((c, done, gone))
    if not rows:
        return []
    L = [rule('한 번뿐인 판정 — 그 순을 놓치면 회차 안에서 끝')]
    L.append(dim('   조건이 여러 겹으로 나뉘어 있어 항목 조건으로는 안 잡히는 것들이다.'))
    L.append('')
    for c, done, gone in rows:
        mi = (load_json('graph.json') or {}).get('mission', {}).get(c['sc']) or {}
        where = mi.get('place') or ''
        head = (f'   {pad(c["name"], 12)}{pad(wk_stage_ko(c["wk"]), 16)}{pad(dim(c["sc"]), 12)}'
                + pad(warn(where + ' 에서') if where else '', 12))
        if mi and not mi.get('active', True):
            L.append(head + bad('이 빌드에서는 꺼져 있다 — 안 뜬다'))
            continue
        if done:
            L.append(head + ok('이미 켜졌다 ✓'))
            continue
        L.append(head + (bad('지났다 — 이 회차에서는 끝') if gone else warn('아직 앞에 있다')))
        for lab, op, val in (c.get('need') or []):
            cur = cur_value(run, lab)
            hit = cur is not None and CMP[op](cur, val)
            shown = '?' if cur is None else str(cur)
            line = f'      {pad(lab, 14)}{pad(op + " " + str(val), 8)}지금 {shown}'
            L.append(dim(line) + (ok('  ✓') if hit else warn('  ✗')))
        for fid, want, lab in (c.get('needFlag') or []):
            hit = run.flags.get(fid) == want
            L.append(dim(f'      {pad(lab, 22)}') + (ok('✓') if hit else warn('✗')))
        for key, good, lab in (c.get('story') or []):
            if key not in seen_story(run):
                continue
            paint = ok if good else (dim if good is None else bad)
            L.append(dim(f'      기록 {pad(key, 18)}') + paint(lab))
        if c.get('note'):
            L.append(dim('      ' + c['note']))
        L.append('')
    return L


def wk_stage_ko(w):
    st = {1: '상순', 2: '중순', 3: '하순'}.get(w % 10, '')
    return f'{w // 1000}년차 {(w % 1000) // 10}월 {st}'.strip()


def leave_section(run, PRES):
    """지금 당문에 있는 사람이 떠나게 되는 자리.

    영입 조건만 적어 두면 절반이다. 작성자는 엽운상·엽운주·용상을 다 거두고도
    셋 다 떠나보냈고, 그때마다 그 항목들이 통째로 닫혔다.
    """
    if not PRES:
        return []
    rows = []
    for who, e in PRES.items():
        if run.flags.get(e.get('flag')) != 1:
            continue                      # 이미 없는 사람은 경고할 것이 없다
        for r in e.get('leave') or []:
            wk = r.get('wk')
            if wk is not None and wk < run.wk:
                continue
            rows.append((wk if wk is not None else 999999, who, r))
    if not rows:
        return []
    L = [rule('인물 이탈 주의 — 지금 당문에 있는 사람')]
    L.append(dim('   여기에 걸리면 그 인물이 필요한 항목이 통째로 닫힌다.'))
    L.append(dim('   선택지가 적힌 줄은 그 선택지를 고르면 떠난다는 뜻이다.'))
    L.append('')
    # 시점과 이름이 같으면 그 다음에 dict 를 비교하려 들어 터진다. 키를 못 박는다.
    for _, who, r in sorted(rows, key=lambda x: (x[0], x[1], x[2].get('sc') or ''))[:14]:
        cond = ' · '.join(r.get('conds') or [])[:44]
        when = r.get('when')
        when = (when + (' 무렵' if r.get('est') else '')) if when else dim('시점 미상')
        L.append(f'   {pad(cname(who), 8)}{pad(when, 21)}'
                 f'{pad(dim(r["sc"]), 30)} '
                 + (bad(r['opt']) if r.get('opt') else dim(cond)))
        # 장면에도 미션 조건에도 안 적힌 관문(간선 위의 조건). 손으로 확인한 것만 온다.
        if r.get('note'):
            L.append(f'   {pad("", 8)}{warn("└ " + r["note"])}')
    return L


# 값 0 이 「그렇게 정했다」가 아니라 「아직 안 정했다」인 갈래들.
# study 는 여기 넣지 않는다. meeting_option_01 이 M20008 에 1 이나 2 만 쓰므로 0 은
# 미정과 「안 감」이 겹치지만, 회의 시점(2년 2월 상순)이 지나면 「안 감」으로 굳는다.
# 그 구분은 make_decided() 가 시점으로 한다 — 여기 넣으면 회의를 지나고도 영영
# 「아직 안 정해짐」이 되어 버린다 (작성자가 회의 시점을 알려 주어 드러났다).
UNDECIDED = ('sect', 'snow', 'league', 'tourney', 'banquet',
             'runaway', 'qingcheng')

STUDY_WK = 2021        # 당문 회의 = 2년차 2월 상순 (작성자가 플레이로 확인)


def obtainable(run, D, got, rf, lover, fmap, have, PQ, reach):
    """그 갈래에서 아직 딸 수 있는 항목. (갈래가 열린 것, 그중 지금 수치로도 되는 것)

    「가능」은 갈래가 안 닫혔다는 뜻일 뿐이고 수치 조건은 안 본다. 작성자의 회차는
    도덕이 높아서 낮은 도덕을 요구하는 쪽이 대부분 막혀 있었는데, 그게 개수에
    안 잡혀서 갈래 비교가 실제보다 후하게 나왔다. 그래서 둘을 갈라 센다.
    """
    out, ready = set(), set()
    for it in D['items']:
        if it['id'] in have or it.get('blocked') or not it.get('reachable'):
            continue
        tag = it['type'][0] + '#' + str(it['no'])
        for o in it.get('opts') or []:
            v, _ = opt_verdict(run, it, o, got, rf, lover, fmap, D, PQ, reach)
            if v != '가능':
                continue
            out.add(tag)
            _, unmet, _, _, _ = req_line(run, o, pathof(it, o))
            if not unmet:
                ready.add(tag)
                break
    return out, ready


def wk_ko(w):
    return f'{w // 1000}년차 {(w % 1000) // 10}월' if w else ''


def when_fork(D, fid):
    """그 갈래가 정해지는 무렵. **하한 추정이라 「그 무렵부터」로 읽어야 한다.**

    회의처럼 여러 자리가 같은 스크립트를 쓰면 실제보다 이르게 나온다. 유학 선택이
    「1년차 8월 ~ 2년차 8월」로 잡히는 것이 그 예다 — 실제 회의는 그 창 안 어딘가다.
    판정에는 쓰지 않는다.
    """
    e = (D.get('flagWhen') or {}).get(fid) or {}
    a, b = e.get('estMin'), e.get('estMax')
    if not a:
        return ''
    return wk_ko(a) if not b or b == a else f'{wk_ko(a)} ~ {wk_ko(b)}'


def fork_lines(run, D, forks, rf, got, lover, fmap, have, PQ, reach):
    """아직 안 정해진 갈래마다, 각 선택지에서 몇 개를 딸 수 있는지.

    작성자가 매번 갈림길에서 이걸 물었다 — 회의에서 유학을 갈지, 가출해서 어디에
    묵을지. 숫자만으로는 안 되고 「이쪽에만 있는 것」이 무엇인지가 결정 근거다.
    """
    L = []
    raw = fork_values(run, forks)
    decided = make_decided(run, got)
    for f in forks:
        fid = f['id']
        if fid not in got:
            continue
        p = f.get('parent')
        if p and got.get(p['fork']) != p['v']:
            continue
        v = got[fid]
        name = next((o['name'] for o in f['options'] if o['v'] == v), None)
        # 0 은 「안 함」이자 「아직 안 정함」이다. 어느 쪽인지는 판정과 같은 규칙으로 가른다.
        if not decided(fid):
            name = None
        # 0 이 뜻하는 쪽을 같이 적는다. 「아직 안 정해짐」만 있으면 지금 어느 라인에
        # 서 있는지가 안 보인다 — 정해지기 전에도 그 라인의 사건은 벌어진다.
        zero = next((o['name'] for o in f['options'] if o['v'] == '0'), '')
        undecided = dim(f'아직 안 정해짐 (값 {v})') + (dim(f' · 지금은 {zero}') if zero else '')
        # 언제 정해지는지를 같이 적는다. 확인된 값은 그대로, 추정은 「무렵」을 붙인다.
        sure_w = f.get('when')
        w = sure_w or when_fork(D, (raw.get(fid) or (None,))[0])
        tail = dim(f'   {w}' + ('' if sure_w else ' 무렵')) if w else ''
        L.append(f'   {pad(f["flag"], 26)} ' + (ok(name) if name else undecided) + tail)
        if name:
            continue
        sets = {}
        for o in f['options']:
            if o['v'] == v:
                continue
            # 그 값을 세우는 자리가 전부 잠긴 선택지·꺼진 사건 안에 있으면 고를 수 없는 갈래다.
            # 「무림맹에 호응」이 그렇다 — 회의의 그 선택지는 조건 XXX(정의 없음)로 잠겨 있다.
            places = (DEPG.get((raw.get(fid) or (None,))[0]) or {}).get(o['v']) or []
            if places and all(p.get('optDead') or p.get('misDead') for p in places):
                sets[o['name']] = (None, dim('이 빌드에서는 고를 수 없다 (선택지가 잠겨 있다)'))
                continue
            need = o.get('needLover')
            if need is not None and lover is not None and int(need) != lover:
                # 못 여는 갈래라도 개수는 세어 준다. 다음 회차를 짤 때 그 숫자가 필요하다.
                # 그 심계로 바꿨다고 치고, 이 갈래를 타는 쪽과 안 타는 쪽을 견준다.
                who = run.M['lover'].get(str(need), need)
                g = dict(got)
                g[fid] = o['v']
                on, on_ready = obtainable(run, D, g, rf, int(need), fmap, have, PQ, reach)
                g[fid] = v
                off, _ = obtainable(run, D, g, rf, int(need), fmap, have, PQ, reach)
                gain = sorted(on - off)
                lose = sorted(off - on)
                tail = f'심계가 {cname(who)} 여야 열린다'
                if gain:
                    tail += ' · ' + acc('그때만 ' + ' '.join(gain[:5]))
                if lose:
                    tail += ' · ' + warn('타면 잃음 ' + ' '.join(lose[:5]))
                sets[o['name']] = (None,
                                   f'{bold(str(len(on_ready)) + "개")}'
                                   + dim(f' (수치 무시하면 {len(on)})  ') + tail)
                continue
            g = dict(got)
            g[fid] = o['v']
            sets[o['name']] = (obtainable(run, D, g, rf, lover, fmap, have, PQ, reach), '')  # (전체, 수치까지)
        live = [x[0][1] for x in sets.values() if x[0] is not None]
        common = set.intersection(*live) if live else set()
        for nm, (pair, why) in sets.items():
            if pair is None:
                L.append(f'   {" " * 26} {dim("·")} {pad(nm, 22)} {why}')
                continue
            whole, ready = pair
            only = sorted(ready - common)
            tail = (acc('여기서만 ' + ' '.join(only[:6])) if only else dim('여기서만 딸 수 있는 것 없음'))
            L.append(f'   {" " * 26} {dim("·")} {pad(nm, 22)} {bold(str(len(ready)) + "개")}'
                     + dim(f' (수치 무시하면 {len(whole)})') + f'  {tail}')
    return L


def report(run, D, forks, rf, owned, show_all=False, PQ=None, DEP=None):
    L = []
    M = run.M
    got, raw = run_forks(run, forks)
    fmap = {f['id']: f for f in forks}
    lover = lover_of(run)
    lover_ko = M['lover'].get(str(lover), '아직 정해지지 않음')

    L.append(bold('활협전 세이브 읽기') + dim(f'   {save_kind(run.path)}  '
             + time.strftime('%m/%d %H:%M', time.localtime(os.path.getmtime(run.path)))))

    L.append(rule('지금'))
    L.append(f'   {bold(run.when())}   슬롯 {run.slot}'
             + ('   ' + warn('회차 2회+ (NG+)') if run.gs.get('NewGamePlus') else ''))
    SUM = load_json('summary.json') or {}
    sc_txt = (SUM.get(run.script) or '')[:70]
    # 미션 키가 M0000 이면 「진행 중인 미션 없음」이 아니라 대개 본편 장면 안이다.
    # 장면 이름만 적으면 그것을 알 수 없어서, 그 장면의 첫 대사를 같이 적는다.
    L.append(f'   현재 장면   {acc(run.script)}' + (dim('   ' + sc_txt) if sc_txt else ''))
    if run.mission and run.mission != 'M0000':
        # 미션 키만 적어 두면 「왜 이벤트가 안 뜨지」에 답이 안 된다. 그 미션이 언제
        # 열리는지를 같이 적는다.
        MIS = load_json('missions.json') or {}
        d = MIS.get(run.mission) or {}
        tail = ''
        if d.get('when'):
            tail = dim(f'   {d["when"]}') + (dim(f' · {mission_ko(d["desc"])}') if d.get('desc') else '')
            if d.get('wk') and d['wk'] > run.wk:
                tail += warn('   아직 안 왔다 — 그때까지 본편 이벤트는 없다')
        L.append(f'   메인 미션   {acc(run.mission)}{tail}')

    L.append(rule('이 회차의 갈래'))
    have0 = owned or {x['id'] for x in D['items'] if x.get('owned')}
    L += fork_lines(run, D, forks, rf, got, lover, fmap, have0, PQ or {},
                    make_reachable(run, D, PQ, DEP, got, make_decided(run, got)))
    tail = (dim('   (「변심의 꿈」에서 고르면 정해진다)') if lover is None
            else dim(f'   (바꾸려면 변심 10 -> 「변심의 꿈」. 지금 변심 '
                     f'{run.stats.get("change-heart", "?")})'))
    L.append(f'   {pad("마음에 둔 사람", 24)} '
             + (cname(lover_ko) if lover is not None else warn(lover_ko)) + tail)

    L.append(rule('스탯'))
    # m-internal(무공 내공)은 아래 무공 칸에서 계열별로 따로 찍는다.
    KEY = ['stamina', 'life', 'internal', 'disposition', 'mental',
           'talking', 'karma', 'training', 'behaviour', 'literacy', 'dexterity',
           'fame', 'action', 'change-heart']
    row = []
    for k in KEY:
        if k in run.stats:
            row.append(f'{run.stat_ko(k)} {bold(run.stats[k])}')
    for i in range(0, len(row), 5):
        L.append('   ' + '   '.join(pad(x, 16) for x in row[i:i + 5]))
    # 무공은 계열별로 나뉘고 계열마다 단계 상한이 따로 있다. 절대 상한은 100 이지만
    # (게임 데이터의 _max), 실제로는 그보다 훨씬 낮은 데서 막힌다 — 작성자의 회차는 권장
    # 25 에서 수련 버튼이 잠겼다. 그 상한을 푸는 규칙은 아직 못 읽었다(위키 미확인 9번).
    # 어디가 찼고 어디가 비었는지는 보여야 포인트를 어디 넣을지 정할 수 있다.
    MART = ['m-sword', 'm-projectile', 'm-fist', 'm-leg',
            'm-odd', 'm-soft', 'm-stick', 'm-internal']
    mv = [(run.stat_ko(k), run.stats.get(k)) for k in MART if k in run.stats]
    if any(v for _, v in mv):
        top = max(v or 0 for _, v in mv)
        cells = []
        for n, v in mv:
            if not v:
                cells.append(dim(f'{n} 0'))
            elif v == top:
                cells.append(f'{n} {bold(v)}' + warn('*'))   # 제일 높은 것 — 여기가 먼저 막힌다
            else:
                cells.append(f'{n} {bold(v)}')
        for i in range(0, len(cells), 4):
            L.append('   ' + '   '.join(pad(x, 14) for x in cells[i:i + 4]))
        mp = run.stats.get('martial-point')
        if mp:
            L.append(f'   {pad("무학 포인트", 14)} {bold(mp)}'
                     + dim('   계열마다 상한이 따로 있다 (' + warn('*') + dim(' 가 지금 제일 높은 계열)')))

    assets = run.stats.get('assets')
    if assets is not None:
        gap = -9000 - assets
        tail = ok('상관형 영입선 통과') if gap <= 0 else warn(f'상관형 영입선(-9000)까지 +{gap}')
        L.append(f'   {pad("문파 자산", 14)} {bold(assets)}   {tail}')
    if 'money' in run.stats:
        L.append(f'   {pad("은자", 14)} {bold(run.stats["money"])}')
    # 쌓이기만 하고 줄지 않는 값. 다음 문턱을 같이 적어야 「얼마나 더 모아야 하나」에 답이 된다.
    for t in track_stats(run, D, {x['id'] for x in D['items'] if x.get('owned')}):
        nx = (ok('문턱 전부 넘김') if t['next'] is None
              else dim(f'다음 {t["next"]}') + warn(f'  (+{t["next"] - t["cur"]})'))
        lib = dim(f'   도감 {"·".join(str(m) for m in t["lib"])}') if t['lib'] else ''
        L.append(f'   {pad(t["name"], 14)} {bold(t["cur"])}   {nx}{lib}')

    L.append(rule('호감도'))
    act = sorted((r for r in run.rel.values() if r.get('Value')),
                 key=lambda r: -r['Value'])
    def away(r):
        # 엽 남매는 떠나도 Active 가 1 로 남는다. 당문에 있음 플래그를 같이 본다
        fid = (PRES.get(run.char_ko(r['Key'])) or {}).get('flag')
        return not r.get('Active') or (fid and run.flags.get(fid) == 0)
    row = [f'{cname(run.char_ko(r["Key"]))} {bold(r["Value"])}'
           + (dim('·부재') if away(r) else '') for r in act[:24]]
    for i in range(0, len(row), 5):
        L.append('   ' + '   '.join(pad(x, 16) for x in row[i:i + 5]))

    # ---- 도감 대조 ----
    if D:
        # 「지금 챙길 것」이 도감 앞에 붙어 나오므로 도감을 먼저 낸다.
        # 자유행동 확률표는 참고용이라 뒤로 보낸다.
        L += library_section(run, D, got, rf, owned, lover, fmap, show_all, PQ, DEP)
        L += asura_section(run, owned)
        L += league_section(run)
        L += oneshot_section(run)
        L += branched_section(run)
        L += leave_section(run, load_json('presence.json') or {})
        L += odds_section(run, load_json('pos.json') or [], AFFECT, lover_ko)
        L += lover_tally(run, D, got, rf, owned, fmap, PQ, DEP)
    return '\n'.join(L)


# ---------------------------------------------------------------- 놓친 플래그 판정
RE_WHENNUM = re.compile(r'(\d+)년차? (\d+)월(?: (상순|중순|하순))?')
_ST = {'상순': 1, '중순': 2, '하순': 3}


def when_key(txt):
    """'1년차 4월 하순 ~ 2년차 1월 하순' 에서 마지막 시점을 뽑는다."""
    ms = RE_WHENNUM.findall(txt or '')
    if not ms:
        return None
    y, m, st = ms[-1]
    return int(y) * 1000 + int(m) * 10 + _ST.get(st, 3)


def presence_deadline(PQ):
    """인물이 당문에 있게 만들 수 있는 마지막 시점. 영입 창의 끝이다."""
    out = {}
    for name, d in (PQ.get('chars') or {}).items():
        w = d.get('when') or ''
        # 창이 열려 있는 표현이면 마감으로 쓰지 않는다.
        # '1년 9월 상순 첫 만남 → 외성 회복 이후' 를 1년 9월 마감으로 읽으면 안 된다.
        if '→' in w or '이후' in w:
            continue
        wk = when_key(w)
        if not wk:
            continue
        # '우소매' 처럼 플래그가 둘 적힌 경우가 있다
        for fid in re.split(r'\s*/\s*', d.get('flag') or ''):
            if fid:
                out[fid] = (name, d.get('when'), wk)
    return out


# 「공략 중」은 한 번 켜지면 회차 끝까지 남는다. 0 으로 되돌리는 자리는 ch5_4_8_6 하나인데
# 그것은 켜는 자리(ch5_5_1)와 같은 사건의 다른 가지라, 켜진 뒤에는 다시 오지 않는다.
# 그래서 누군가 켜져 있으면 다른 사람의 결말은 그 자리에서 닫힌다 — 하후란이 켜진 세이브에서
# 용상·소사매 결말을 「가능」으로 보여 주고 있었다(작성자가 잡았다).
ROUTE_FLAG = {'소사매': 'G11000', '상관형': 'G11001', '엽운상': 'G11002',
              '용상': 'G11003', '하후란': 'G11005'}
ASURA_LOSES = ('용상', '하후란')      # 수라장(ch7_5_6_3_2)이 2 로 바꾸는 사람. 소사매는 남는다
# 결말 장면은 갈래가 아니라 순서다. 위에서부터 먼저 맞는 하나만 잡는다.
ENDING_ORDER = {
    'ch8_8_': ('소사매', '용상', '하후란', '엽운상'),
    'ch8_6_3_2': ('소사매', '엽운상', '상관형', '하후란', '용상'),
    'ch7_5_2_9': ('소사매', '엽운상', '상관형', '하후란', '용상'),
}
# 5장(M4002_02) = 3년차 5월 상순, 한 번뿐. 소사매(ch5_5_1)와 엽운상(ch5_4_1 → S0208_*)이
# 둘 다 이 사슬 안에서만 켜지고, 엽운상 루트로 넘어가면 공동 영전을 건너뛰므로 서로 배타다.
SISTER_LAST_WK = 3051
# 하후란은 설산행 결승일(S2504_02, 3년차 7월 중순)의 S2504_02_07 에서만 켜진다. 그 미션은 特定 이고
# SetMissionTime 으로 옮기는 대본이 없다(설산행 사슬은 Mission("S2504", …) 로 단계만 넘긴다).
SNOW_FINAL_WK = 3072


def route_closed(run, who, script):
    """이 사람의 「공략 중 == 1」을 요구하는 경로가 이미 닫혔는가. 닫혔으면 사유."""
    fid = ROUTE_FLAG.get(who)
    if not fid:
        return None
    cur = run.flags.get(fid) or 0
    if cur == 2:
        return f'{cname(who)} 공략은 수라장으로 끝났다'
    if who in ('소사매', '엽운상') and cur != 1 and run.wk > SISTER_LAST_WK:
        return f'{cname(who)} 공략 중은 5장(3년차 5월 상순)에서만 켜진다 — 지났다'
    if who == '하후란' and cur != 1 and run.wk > SNOW_FINAL_WK:
        return f'{cname(who)} 공략 중은 설산행 결승일(3년차 7월 중순)에서만 켜진다 — 지났다'
    if who == '엽운상' and cur != 1 and (run.flags.get('E12000') or 0) == 0 and run.wk > 2041:
        return f'{cname(who)} 이 당문에 없다 — 5장에서 루트로 넘어가지 못한다'
    on = [w for w, f in ROUTE_FLAG.items() if w != who and run.flags.get(f) == 1]
    if not on:
        return None
    if script.startswith('ch8_') and who in ASURA_LOSES:
        return (f'{cname(on[0])} 공략 중이 이미 켜져 있다 — 둘이 되면 8장 갈림에서 '
                f'수라장이 나고 {cname(who)} 공략이 끝난다')
    for pre, order in ENDING_ORDER.items():
        if script.startswith(pre) and who in order:
            for other in order[:order.index(who)]:
                if other in on:
                    return f'{cname(other)} 공략이 먼저 잡힌다 — 결말은 하나뿐이다'
    return None


def missed_flags(run, o, D, PQ, reach=None):
    """이 경로가 요구하는 플래그 중, 이미 만들 수 없게 된 것.

    두 가지로 판단한다.
      1. 인물이 당문에 있어야 하는데 지금 없고, 영입 창이 지났다
      2. 그 값을 세우는 곳이 전부 지금보다 앞에 있다 (시점을 모르는 자리가 하나도 없을 때만)
    둘 다 아니면 아직 못 한 것이지 못 하는 것이 아니므로 조용히 넘어간다.
    """
    fw = (D or {}).get('flagWhen') or {}
    ko = (D or {}).get('flagKo') or {}
    lab2id = {}
    for fid, lab in run.M['flags'].items():
        lab2id.setdefault(lab, fid)
    dead = presence_deadline(PQ or {})
    out = []
    for chunk in (o.get('flags') or []):
        m = RE_FLAGCMP.match(chunk)
        # >= 는 대개 횟수 누적이다. 그 값을 세우는 자리를 값으로 못 찾으니 불가 판정에
        # 쓰면 안 된다. 요구사항으로 적어 두기만 하고(flag_bits) 여기서는 건너뛴다.
        if not m or m.group(2) != '==':
            continue
        lab, want = m.group(1).strip(), int(m.group(3))
        if any(k in lab for k in FLAG_RUNTIME):
            continue
        # 한국어 이름이 없는 플래그는 조건문에 아이디 그대로 적힌다(Talk_Girl_05_02_001 — 한#23 을 여는 값).
        # 이름표로만 찾으면 그런 값은 통째로 건너뛰어, 세울 기회가 지났어도 「아직」으로 남는다.
        fid = lab2id.get(lab) or (lab if lab in fw else None)
        if not fid or run.flags.get(fid) == want:
            continue
        short = re.sub(r'\s*\(.*', '', lab)
        if want == 1 and fid in dead and run.wk > dead[fid][2]:
            who, win, _ = dead[fid]
            out.append(f'{paint(short)} — {cname(who)} 영입 창({win})이 지났다')
            continue
        e = (fw.get(fid) or {}).get('set', {}).get(str(want))
        if e and not e.get('unknown') and not (fw.get(fid) or {}).get('add') \
                and e.get('max') is not None and e['max'] < run.wk:
            out.append(f'{short} {want} — 세울 수 있는 마지막 시점이 지났다')
            continue
        if reach is not None and not reach(fid, want):
            # 도달 불가만으로 「못 한다」고 말하는 것은 인물 유무처럼 확실한 것에만 쓴다.
            # 한#16 은 「공동 영전 - 서행 참전」을 요구하는 것으로 잡혀 불가로 떴는데,
            # 작성자가 그 회차에서 실제로 땄다. 경로에 딸려 온 조건이 그 항목의 조건이
            # 아니었던 것이다. 확실한 축이 아니면 열어 두고 표시만 한다.
            hf = getattr(reach, 'hard', None)
            firm = bool(hf and hf(fid, want))
            if fid in dead or re.match(r'^E1[23][0-9]{3}$', fid or '') or firm:
                why = (getattr(reach, 'why', None) if firm else None)
                out.append(f'{paint(short)} — {why or "이 회차에서는 만들 수 없다"}')
            else:
                out.append(('soft', f'{paint(short)} — 만들 수 있는지 확인 못 함'))
    return out


# ---------------------------------------------------------------- 플래그 도달 가능성
# 스크립트 접두사가 갈래를 못 박는다. build_site 의 BRANCH_PREFIX 와 같은 표다.
# 플래그를 세우는 자리가 다른 갈래에만 있으면, 그 플래그는 이 회차에서 못 만든다.
# 「하후란을 스승으로 모심」이 그랬다 — 세우는 자리가 공동파 라인(ch2_5_)뿐인데
# 잔류 회차에서도 만들 수 있는 것으로 보였다.
# 회의에서 노선은 하나만 고른다. 「너의 결정」이 굳으면 다른 노선의 플래그는 그 회차에서
# 영영 안 선다 — 득표 비교(Ch_7_4_3_1_002)로 갈리는 자리라 lua 의 if 만 보면 안 잡힌다.
# 용상 루트(미션 S0021_01)가 요구하는 항전 노선이 그것이다.
DECIDED_ROUTE = {'M70052': ('M70015', 2)}      # 항전 노선 <- 너의 결정 == 2

SETTER_FORK = (
    (('ch2_4_', 'ch3_3_', 'ch3_1_', 'ch2_6_', 'ch2_8_', 'section_02_'), 'study', '0'),
    (('ch2_5_', 'ch3_2_', 'section_01_'), 'study', '2'),
)


def make_decided(run, got):
    """그 갈래가 이미 굳었는가. 0 은 「안 함」이자 「아직 안 정함」이라 갈라 본다."""
    def decided(k):
        cur = got.get(k)
        if cur is None:
            return False
        if cur == '0' and k in UNDECIDED:
            return False
        # 당문 회의는 2년 2월 상순이다. 그 순이 지나야 유학 선택이 굳는다.
        if k == 'study' and cur == '0' and run.wk <= STUDY_WK:
            return False
        return True
    return decided


def setter_blocked(sc, got, decided):
    """그 스크립트가 이 회차가 안 고른 갈래에만 있는가."""
    for pres, fork, val in SETTER_FORK:
        if sc.startswith(pres) and decided(fork) and got.get(fork) != val:
            return True
    return False


def make_reachable(run, D, PQ, DEP, got=None, decided=None):
    """이 세이브에서 (플래그, 값) 을 아직 만들 수 있는가.

    세우는 자리마다 그 자리에 닿는 조건이 또 플래그일 수 있어 한 단계로는 부족하다.
    최소 고정점을 돌린다 — 순환(자기 값이 이미 있어야 자기 값을 만드는 꼴)은 못 만드는 것으로 본다.

    모르는 것은 막지 않는다. 「못 한다」고 잘못 말하는 쪽이 훨씬 나쁜 오류다.
    """
    fw = (D or {}).get('flagWhen') or {}
    dead = presence_deadline(PQ or {})
    memo = {}
    pruned = []                                # (플래그, 사유) — 길이 닫혀서 버린 자리

    def go(fid, val, stack=frozenset()):
        if run.flags.get(fid) == val:
            return True
        key = (fid, val)
        if key in stack:
            return False                       # 순환
        if key in memo:
            return memo[key]
        memo[key] = True                       # 재귀 도중에는 낙관적으로
        r = _go(fid, val, stack | {key})
        memo[key] = r
        return r

    def hard(fid, val):
        """못 만드는 이유가 「이 회차가 안 고른 갈래에만 있어서」인가.

        그것만 확실한 불가로 친다. 나머지는 우리가 조건을 잘못 붙였을 수 있다.
        """
        n = len(pruned)
        memo.clear()
        r = go(fid, val)
        if r or len(pruned) <= n:
            return False
        mine = [w for f, w in pruned[n:] if f == fid]
        go.why = mine[-1] if mine else pruned[-1][1]
        return True

    go.hard = hard
    go.why = None

    def _go(fid, val, stack):
        if val == 1 and fid in dead and run.wk > dead[fid][2]:
            return False                       # 영입 창이 지났다
        ex = DECIDED_ROUTE.get(fid)
        if ex and val == 1 and run.flags.get(ex[0]) and run.flags.get(ex[0]) != ex[1]:
            pruned.append((fid, '회의에서 다른 노선으로 굳었다'))
            return False
        # 기본값 그대로면 아무것도 안 해도 성립한다. 세우는 곳이 없어도 된다.
        d = ((D or {}).get('flagDefault') or {}).get(fid)
        if d is not None and val == d:
            return True
        e = (DEP or {}).get(fid)
        if e is None:
            # lua 어디서도 세우지 않는 플래그는 기본값에서 움직이지 않는다.
            if d is None:
                return True                    # 정의를 모르면 막지 않는다
            return val == d
        if e.get('add'):
            return True                        # 더하는 곳이 있으면 어디로든 갈 수 있다
        places = e.get(str(val))
        if not places:
            return False                       # 그 값을 세우는 곳이 없다
        when = (fw.get(fid) or {}).get('set', {}).get(str(val)) or {}
        for p in places:
            if p.get('misDead'):
                pruned.append((fid, '이 빌드에서 꺼진 사건 안에만 있다'))
                continue
            if p.get('optDead'):
                pruned.append((fid, '그 값을 세우는 선택지가 이 빌드에서 잠겨 있다'))
                continue
            if got is not None and decided is not None and setter_blocked(p.get('sc') or '', got, decided):
                pruned.append((fid, '이 회차가 안 고른 갈래에만 있다'))
                continue
            # 읽어 낸 조건이 이미 막혔으면 못 읽은 조건이 남아 있어도 그 자리는 못 쓴다.
            # 순서를 뒤집기 전에는 unknown 하나로 통째로 열려서, 용상 루트가 요구하는
            # 「용상에게 고백함」이 용상 없는 회차에서도 만들 수 있는 것으로 보였다.
            if not all(go(f, v, stack) for f, v in p.get('need') or []):
                continue
            # 그 사건을 여는 미션에 마감이 적혀 있고 그게 지났으면 그 자리는 못 쓴다.
            # 용상 루트(S0021_01)가 그렇다 — 서무림맹 갈래로도 열리지만 4년 1월 하순까지다.
            mm = p.get('misMax')
            if mm is not None and mm < run.wk:
                pruned.append((fid, f'그 사건의 마감({wk_stage_ko(mm)})이 지났다'))
                continue
            if p.get('unknown'):
                return True                    # 나머지 조건을 못 읽었으면 열어 둔다
            # 그 자리의 시점이 확실히 지났으면 그 자리는 못 쓴다
            if not when.get('unknown') and when.get('max') is not None \
                    and when['max'] < run.wk and len(places) == 1:
                continue
            return True
        return False

    return go


def affect_ceiling(run, who, D, DEP, AF, reach):
    """이 회차에서 그 인물 호감도가 최대 얼마까지 오를 수 있는가 (넉넉하게 잡은 상한).

    조건을 못 읽은 자리와 수치 조건은 전부 「닿는다」로 세고, 시점도 안 본다.
    그렇게 후하게 세고도 모자라면 그때만 못 한다고 말할 수 있다.
    """
    cur = run.affection(who)
    if cur is None:
        return None
    lover = run.stats.get('lover')
    top = cur
    for g in AF.get(who) or []:
        if g['d'] <= 0:
            continue
        ok = True
        for fid, val in g['need']:
            if fid == '@lover':
                if lover is not None and int(lover) != val:
                    ok = False
            elif reach and not reach(fid, val):
                ok = False
        if ok:
            top += g['d']
    return top


AFFECT = {}
DEPG = {}
CAST = {}          # 장면마다 누가 나오는가 (mk_cast.py)
PRES = {}          # 인물이 당문에 있는지 보는 플래그 (mk_presence.py)


def affect_short(run, o, D, PQ, reach):
    """요구 호감도가 이 회차의 상한을 넘으면 그 이유를 돌려준다."""
    if not AFFECT:
        return None
    for r in list(o.get('reqs') or []) + list(o.get('upReqs') or []):
        if r.get('any') or r.get('neg') or r.get('op') not in ('>=', '>'):
            continue
        m = re.match(r'^(.+?) 호감도$', r.get('stat') or '')
        if not m:
            continue
        who = m.group(1)
        need = r['val'] + (1 if r['op'] == '>' else 0)
        top = affect_ceiling(run, who, D, None, AFFECT, reach)
        if top is not None and top < need:
            cur = run.affection(who)
            return (f'{who} 호감도 {need} 이 필요한데 이 회차에 남은 자리를 다 더해도 '
                    f'{top} 까지다 (지금 {cur})')
    return None


RE_FLAGREQ_CHUNK = re.compile(r'\[플래그 ([^\]]+?)\]\s*==\s*(-?\d+)')


def scene_group(sc):
    """ch2_4_8_6_1 -> ch2_4_8. 같은 사건 묶음을 한 덩어리로 본다."""
    parts = (sc or '').split('_')
    while parts and parts[-1].isdigit():
        parts.pop()
        if len(parts) <= 3:
            break
    return '_'.join(parts) if len(parts) >= 3 else None


def scene_reset_block(run, o, D, DEP):
    """장면 묶음이 시작할 때 리셋하는 값을, 그 장면 안에서 반대로 요구하는 경로.

    당문 대난투는 ch2_4_8_1 이 「결투 범용 이벤트 플래그」를 0 으로 깔고 시작한다.
    대장간에서 지면 그 플래그가 1 일 때만 생#68 이 뜨는데, 그 묶음 안에는 1 로
    세우는 자리가 없다 — 즉 대장간으로는 영영 안 나온다. 작성자가 직접 가서 지고
    「집단구타」를 받고 나서야 알았다.
    """
    grp = scene_group(o.get('script'))
    if not grp:
        return None
    lab2id = {}
    for fid, lab in run.M['flags'].items():
        lab2id.setdefault(lab, fid)
    for chunk in (o.get('flags') or []):
        for lab, val in RE_FLAGREQ_CHUNK.findall(chunk):
            lab = re.sub(r'\s*\(.*\)$', '', lab).strip()
            # 임시 플래그는 장면마다 스크래치로 쓰여 오르내린다. 여기에 이 규칙을 대면
            # 멀쩡한 경로를 못 한다고 말한다.
            if lab.startswith('임시 플래그'):
                continue
            fid = lab2id.get(lab)
            e = (DEP or {}).get(fid or '')
            if not e:
                continue
            here = lambda v: [p for p in (e.get(str(v)) or [])
                              if p['sc'].startswith(grp + '_')]
            if here(val):
                continue
            for other, places in e.items():
                # 'add' 같은 메타 키가 섞여 있다. 값 목록만 본다.
                if other == str(val) or not isinstance(places, list):
                    continue
                for p in places:
                    # 묶음을 여는 스크립트가 깔고 시작할 때만. 중간에서 바뀌는 것은
                    # 순서를 모르니 못 한다고 말하지 않는다.
                    if p['sc'] == grp + '_1' and not p['need'] and not p.get('unknown'):
                        return (f'{lab} 은 이 사건이 시작할 때 {other} 으로 깔린다 '
                                f'({p["sc"]}). 그 안에 {val} 로 만드는 자리가 없다')
    return None


def opt_verdict(run, it, o, got, rf, lover, fmap, D=None, PQ=None, reach=None):
    """이 경로를 이 회차에서 아직 탈 수 있는가. (판정, 사유)"""
    # 이 경로가 요구하는 분기
    need = {}
    if o.get('branch') is not None:
        need['study'] = o['branch']
    if o.get('qc') is not None:
        need['qingcheng'] = o['qc']
    for r in (o.get('req') or []):
        for k, v in (rf.get('routes', {}).get(r) or {}).items():
            need[k] = v
    for r in (o.get('req') or []):
        why = route_closed(run, r, o.get('script') or '')
        if why:
            return '불가', why
    lv = opt_lover(o)
    # 「그 사람을 앎」은 회차를 넘어 남는다(NG+ 탈백문 회차에 G10006 = 1). 이미 알면 갈래를 안 묶는다
    knows = {3: 'G10004', 5: 'G10005', 6: 'G10006'}.get(lv)
    if lv is not None and not (knows and run.flags.get(knows)):
        for k, v in (rf.get('lovers', {}).get(str(lv)) or {}).items():
            need[k] = v
    # 조건문에 분기 플래그가 직접 적힌 경우 (예: 「가출 경로」 == 폐사찰)
    for chunk in (o.get('flags') or []):
        for fid, f in fmap.items():
            m = re.match(r'\[플래그 ' + re.escape(f['flag']) + r'[^\]]*\]\s*==\s*(-?\d+)', chunk)
            if m:
                need[fid] = m.group(1)
    # 유학 선택은 값 0 이 「잔류」이기도 하고 「아직 안 정함」이기도 하다.
    # 회의는 2년 2월 상순에 열리므로, 그 순까지는 아직 안 정한 것으로 본다.
    decided = make_decided(run, got)

    # 부모 분기를 다르게 골랐으면 자식 분기 자체가 열리지 않는다.
    # (공동파 회차에서는 「가출 경로」가 영영 정해지지 않으므로 그것을 요구하는 경로도 못 탄다)
    for k in list(need):
        p = (fmap.get(k) or {}).get('parent')
        while p:
            if decided(p['fork']) and got[p['fork']] != p['v']:
                return '불가', ('why', p['fork'], got[p['fork']], p['v'])
            p = (fmap.get(p['fork']) or {}).get('parent')
    for k, v in need.items():
        cur = got.get(k)
        if not decided(k):
            continue
        if cur != v:
            return '불가', ('why', k, cur, v)
    # 「그 갈래를 고르지 않았을 때만」 열리는 경로. 8장이 미션 단위로 갈려서
    # 서무림맹을 결성하면 ch8_6_* 후일담(한청서 37~46)이 통째로 안 열린다.
    for k, v in (o.get('notBranch') or {}).items():
        if decided(k) and got.get(k) == v:
            return '불가', ('not', k, v)
    # 요구하는 갈래 자체가 심계를 요구하기도 한다. 생#98 「패자의 죽음」이 그랬다 —
    # 그 항목에는 심계 조건이 없지만 청성 라인(ch3_1_*)이고, 청성행은 ch2_4_9_2 에서
    # 「마음에 둔 사람 == 엽운상」일 때만 갈린다. 그 연결이 없어서 소사매 회차에서도
    # 「가능」으로 보였고, 작성자가 저번 런에 안 떴다고 알려 주어 드러났다.
    if lv is None:
        for k, v in need.items():
            # 이미 그 갈래로 들어선 뒤에는 묻지 않는다. 갈림을 지난 뒤 심계를 바꾼 세이브에서
            # 생#42 를 「심계가 엽운상이어야 한다」로 띄웠다(작성자 제보, 2026-10-07).
            if decided(k):
                continue
            for opt in ((fmap.get(k) or {}).get('options') or []):
                nl = opt.get('needLover')
                if opt.get('v') == v and nl is not None:
                    lv = int(nl)
                    break
            if lv is not None:
                break
    if o.get('script') == 'ch8_2_6_2_5':
        st, why = jhg_state(run)
        if st == 'bad':
            return '불가', why
    # 못 만드는 플래그를 심계보다 먼저 본다. 심계를 먼저 보면 엽운상이 이미 떠난 회차에서도
    # 「심계만 바꾸면 된다」로 보인다 — 생#103 · 한#15 가 그랬다.
    gone = missed_flags(run, o, D, PQ, reach)
    hard = [g for g in gone if not isinstance(g, tuple)]
    if hard:
        return '불가', hard[0]
    gone = forced_leave(run, o, got, decided)
    if gone:
        return '불가', gone
    if wants_retire(o) and not run.flags.get('M70019') and run.flags.get('M70004') == 1:
        return '불가', '서무림맹 결성 가능(M70004)이 켜져 회의에 「강호 은퇴」가 안 뜬다'
    if lv is not None and lover is not None and lv != lover:
        want = run.M['lover'].get(str(lv), lv)
        have = run.M['lover'].get(str(lover), lover)
        # 한 런에 심계는 한 명으로 본다(작성자의 방침). 꿈으로 바꿀 수는 있지만
        # 갈아타면 다른 쪽이 닫히므로, 선택으로 보고 따로 모아 보여준다.
        return '심계', f'심계가 {want} 여야 한다 (지금 {have})'
    short = affect_short(run, o, D, PQ, reach)
    if short:
        return '불가', short
    dead = scene_reset_block(run, o, D, DEPG)
    if dead:
        return '불가', dead
    wk = o.get('wk')
    # 「3년차 12월 상순 ~ 4년차 1월 하순」 같은 구간이면 시작이 아니라 끝을 본다. 시작만 보면
    # 12월 중순에 서 있는 순간 한#24 가 「시점 지남」으로 빠졌다(작성자가 그 결투 중이었다).
    end = when_key(o.get('when')) if '~' in (o.get('when') or '') else wk
    if wk is not None and (end or wk) < run.wk:
        return '지남', f'{o.get("when", "")}'
    # 추정 창의 상한도 본다. 넘겼으면 「아직 딸 수 있는 것」에 둘 이유가 없다.
    # 다만 상한에 순(旬)이 안 적혀 있으면 그 달 전체가 창이다 — 「4년차 3월 무렵」을
    # 3월 상순과 견주어 지났다고 하면, 마지막 달의 항목이 통째로 사라진다(작성자가 잡았다).
    wmax = o.get('wkMax')
    if wk is None and wmax is not None and passed(wmax, run.wk):
        return '지남', f'{o.get("estText") or ""} (추정 창을 넘겼다)'
    return '가능', o.get('when') or o.get('estText') or ''


def wants_retire(o):
    return any('[플래그 강호 은퇴] == 1' in c for c in (o.get('flags') or []))


def add_meeting_gate(D):
    """은퇴 경로에 「이부귀 호감도 < 20」을 붙인다. 회의 전 개방 제안(ch7_3_3)이 피할 수 없는
    대화라, 20 이상이면 M70004 가 켜져 은퇴가 사라진다. Save_019 · 020 이 한#31 을 「대기」로 띄웠다."""
    for it in D['items']:
        for o in it.get('opts') or []:
            if wants_retire(o) and not any(r.get('stat') == '이부귀 호감도' for r in o.get('reqs') or []):
                o.setdefault('reqs', []).append(
                    {'stat': '이부귀 호감도', 'op': '<', 'val': 20, 'neg': False, 'solo': False})


def forced_leave(run, o, got, decided):
    """경로가 「그 사람이 당문에 있음」을 요구하는데, 그 전에 이 회차에서 못 막는 이탈이 있는가.

    공동파 회차의 한#15 가 「심계만 바꾸면 된다」로 보였다. 엽 남매는 3년 1월 상순에 떠나고
    청성 회차만 붙잡는다(presence.json 의 note).
    """
    when = o.get('wk') or o.get('wkEst')
    if when is None:
        return None
    for who, e in PRES.items():
        need = f'[플래그 {who}이 당문에 있음] == 1'
        if not any(need in c for c in (o.get('flags') or [])):
            continue
        for r in e.get('leave') or []:
            wk = r.get('wk')
            note = r.get('note') or ''
            if wk is None or not (run.wk <= wk < when):
                continue
            # run_forks 가 유학 선택 1 을 「잔류 + 청성행 1」로 바꿔 놓는다. study 를 1 과 견주면
            # 청성 회차에서도 늘 떠난 것으로 나온다 — 작성자의 청성 회차가 한#15 를 「불가」로 띄웠다.
            if not note.startswith('유학 선택 == 1'):
                continue
            lost = ((decided('study') and str(got.get('study')) == '2')
                    or (decided('qingcheng') and str(got.get('qingcheng')) != '1'))
            if lost:
                return f'{who} 이 {r.get("when")} 에 떠난다 — 청성 회차만 붙잡는다'
    return None


def opt_lover(o):
    for r in list(o.get('reqs') or []) + list(o.get('upReqs') or []):
        if r.get('any') or r.get('stat') != '마음에 둔 사람':
            continue
        if r.get('op') == '==' and not r.get('neg'):
            return r.get('val')
    return None


def sun_index(wk):
    """연/월/순을 하나의 순번으로. 남은 순 수를 세려면 필요하다."""
    if wk is None:
        return None
    y, m, st = wk // 1000, (wk // 10) % 100, wk % 10
    return y * 36 + (max(m, 1) - 1) * 3 + max(st, 1)


def tight_room(run, o):
    """지금은 맞지만 여유가 얼마 안 남은 조건 중 가장 빡빡한 것. (여유, 이름)"""
    singles = [p for k, p in _atoms(o)
               if k != 'any' and not passed(p[4], run.wk)]
    best = None
    for name, op, val, *_ in _tighten(singles):
        if name == '마음에 둔 사람':
            continue
        cur = cur_value(run, name)
        if not isinstance(cur, int) or not isinstance(val, int):
            continue
        if not _holds(op, cur, val):
            continue
        room = {'<': val - cur - 1, '<=': val - cur,
                '>': cur - val - 1, '>=': cur - val}.get(op)
        if room is not None and (best is None or room < best[0]):
            best = (room, name)
    return best


def now_section(run, todo):
    """지금 신경 쓸 것만 위로 올린다.

    도감 목록은 시점순이라 「이번 순에 벌어지는 것」과 「조건이 곧 닫히는 것」이
    같은 무게로 섞인다. 작성자가 그 둘을 매번 손으로 골라내고 있었다.
    """
    now = sun_index(run.wk)
    picks = []
    for it, o, why in todo:
        wk = o.get('wk')
        d = None if wk is None else sun_index(wk) - now
        room = tight_room(run, o)
        if d is not None and d < 0:
            continue
        if d is not None and d == 0:
            picks.append((0, it, o, ok('지금 이 순')))
        elif d is not None and d <= 3:
            picks.append((1, it, o, warn(f'{d}순 뒤 · {o.get("when", "")}')))
        elif room and room[0] <= 3:
            when = o.get('when') or o.get('estText') or ''
            # 다른 조건이 이미 모자란 것을 「곧 닫힘」으로만 적으면, 그것만 지키면
            # 되는 줄 안다. 생#77 은 변심 여유 2 였지만 용상 호감도가 이미 넘었다.
            unmet = req_line(run, o, pathof(it, o))[1]
            picks.append((2, it, o,
                          warn(f'{paint(room[1])} 여유 {room[0]}')
                          + (bad(f' · 다른 조건 {unmet}개 모자람') if unmet else '')
                          + dim(f' · {when}')))
        if len(picks) >= 12:
            break
    if not picks:
        return []
    picks.sort(key=lambda x: x[0])
    L = [rule('지금 챙길 것')]
    L.append(dim('   이번 순에 벌어지는 것, 곧 오는 것, 조건이 곧 닫히는 것.'))
    L.append('')
    for _, it, o, tag in picks[:6]:
        L.append(f'   {pad(ok(it["type"][0] + "#" + str(it["no"])), 16)}'
                 f'{pad(it["title"], 30)} {tag}')
        rl = route_line(it, o)
        if rl:
            L.append(f'   {" " * 16}{dim("↳")} {dim(paint(rl))}')
    return L


def grade(run, it, o):
    """이 항목을 얼마나 믿을 수 있나. (모자란 수치, 못 읽은 조건, 대기 플래그)

    시점조차 못 잡은 경로는 조건이 없는 게 아니라 우리가 못 읽은 것이다.
    생#71 은 설산행(하후란 루트) 전투인데 조건이 하나도 안 잡혀서 확실로 보였다.
    """
    _, unmet, unknown, _, pend = req_line(run, o, pathof(it, o))
    if o.get('wk') is None and o.get('wkEst') is None:
        unknown += 1
    return unmet, unknown, pend


def tier(run, it, o, got=None, fmap=None):
    """믿을 수 있는 순서. 0 이 제일 확실하다."""
    unmet, unknown, pend = grade(run, it, o)
    # 아직 그 갈래로 서 있지 않으면 「확실」이라고 부를 수 없다. 조건은 다 맞아도
    # 갈래를 먼저 타야 그 장면이 온다.
    if got is not None and fmap is not None and need_line(o, got, fmap):
        pend += 1
    if unmet:
        return 3                       # 수치가 모자란다 — 손을 대야 한다
    if unknown:
        return 2                       # 못 읽은 조건이 있다 — 우리가 틀릴 수 있다
    if pend:
        return 1                       # 조건은 맞고, 아직 그 사건이 안 왔다
    return 0


# 여러 단계를 순서대로 밟아야 하는 항목은 조건 한 줄로는 무엇을 해야 하는지 안 보인다.
# 그런 것은 순서를 손으로 적고, 단계마다 지금 세이브가 어디까지 왔는지를 붙인다.
# 한#24 는 선행 인물 줄에 1년차 닭 심부름이 뜨고 정작 3년 10월의 수용은 안 나왔다(작성자가 잡았다).
def recipe_han24(run):
    """(상태, 조건, 지금) 의 목록. 조건은 어느 회차에나 맞는 말로 쓰고, 회차 사정은 「지금」에 둔다."""
    f = lambda k: run.flags.get(k) or 0
    yes, no = ok('✓'), bad('✗')
    lover = lover_of(run)
    out = []

    others = [w for w, k in ROUTE_FLAG.items() if w != '용상' and f(k) == 1]
    cond = '용상이 아닌 히로인과 맺어진다 (그 사람 공략 중 1)'
    if others:
        out.append(('ok', cond, cname(others[0])))
    else:
        cand = []
        if run.wk <= SISTER_LAST_WK:
            cand.append('소사매 · 엽운상 3년 5월 상순')
        if f('M10017') == 1 and run.wk <= SNOW_FINAL_WK:
            cand.append('하후란 설산행 결승일')
        elif run.wk <= 3053:
            cand.append('하후란 3년 7월 설산행')
        out.append(('pend', cond, '아직 · 남은 후보 ' + ' / '.join(cand)) if cand
                   else ('bad', cond, '이 회차에 남은 후보가 없다'))

    cond = '3년 10월 무림대회에서 용상을 받아들인다 → 용상 당문 합류'
    aff = run.affection('용상')
    affs = '용상 호감도 ≥30 ' + ('?' if aff is None else (yes if aff >= 30 else no) + str(aff))
    if f('E13008') == 1:
        out.append(('ok', cond, '합류함'))
    elif f('M60036') == 1:
        out.append(('pend', cond, '받아들임 · 대회가 끝나면 합류'))
    elif run.wk > 3111:
        out.append(('bad', cond, '받아들이지 않고 지나갔다'))
    else:
        out.append(('pend', cond, '아직 · ' + affs))

    cond = '심계 = 용상 (①을 본 뒤라면 언제든 「변심의 꿈」으로 — 무림대회 전이어도 된다)'
    if lover == 8:
        out.append(('ok', cond, ''))
    else:
        ch = cur_value(run, '변심')
        out.append(('pend', cond, f'지금 {cname(run.M["lover"].get(str(lover), "없음"))} · '
                                  f'변심 {"?" if ch is None else ch}/10'))

    # 작성자가 플레이로 확인(2026-10-02): 고백 없이 은퇴하면 작별 장소 선택 없이 곧장 대문 결말로 간다.
    # 대본 · 데이터 · 코드 어디서도 이 둘을 잇는 자리를 못 찾았다. 원리는 모르고 결과만 안다.
    cond = '은퇴 회의 전에 용상에게 고백 (S0020 「내 마음 속 사람은 바로 당신입니다」)'
    if f('G00004') == 1:
        out.append(('ok', cond, '고백함'))
    else:
        out.append(('pend', cond, '아직 · 안 하면 은퇴 뒤 작별 장소 선택이 안 뜬다(플레이 확인)'))

    cond = '3년 12월 상순 회의가 「강호 은퇴」로 끝난다'
    dec = f('M70015')
    if f('M70019') == 1:
        out.append(('ok', cond, ''))
    elif dec not in (0, 1):
        out.append(('bad', cond, '다른 길을 골랐다'))
    elif f('M70004') == 1:
        out.append(('bad', cond, '서무림맹 결성 가능이 켜져 은퇴 선택지가 없다'))
    else:
        lee = run.affection('이부귀')
        bits = ['이부귀 호감도 <20 ' + ('?' if lee is None else (yes if lee < 20 else no) + str(lee)),
                '금오상인 ' + ('사망 — 전술 5 미만이어야 한다' if f('M50018') == 1 else '생존 ' + yes)]
        out.append(('pend', cond, '아직 · ' + ' · '.join(bits)))

    out.append(('pend', '은퇴 뒤 작별 장소에서 뒷산: 「마음을 밝힌다」 → 결투 승리 → 「난 당신을 보내줄 수 없어」',
                '뒷산을 먼저 · 결투에 지면 작별 화면으로 돌아간다'))
    return out


QC_FORK_WK = 2091          # 2년 8월 갈림(ch2_4_9_2)이 지난 뒤의 첫 순


def _num(run, name):
    v = cur_value(run, name)
    return v if isinstance(v, (int, float)) else None


def _cmp_bit(run, name, op, th):
    v = _num(run, name)
    if v is None:
        return None, f'{name} ?'
    good = CMP[op](v, th)
    return good, f'{name} {op}{th} ' + (ok('✓') if good else bad('✗')) + str(int(v))


def recipe_sheng99(run):
    """생#99 「전방주시 태만」. 조건은 임시 플래그 2 == 1 하나로 보이지만 그 값은 ch2_6_2_3 에서만 서고,

    거기 닿는 길의 수치(수양 · 성정 · 도덕 · 구력 주사위)가 진짜 조건이다. 자동 추출은 그 수치를
    「길에 따라 다름」으로 내려 「확실 · 수치 조건 없음」이라 했다(작성자 제보, 2026-10-07).
    """
    f = lambda k: run.flags.get(k) or 0
    out = []
    cond = '2년 8월 갈림에서 당문에 남는다 (청성으로 가지 않는다)'
    if f('M20008') == 1:
        out.append(('bad', cond, '청성으로 갔다'))
    elif f('M20008') == 2:
        out.append(('bad', cond, '공동파 유학 회차다'))
    elif run.wk >= QC_FORK_WK:
        out.append(('ok', cond, ''))
    else:
        out.append(('pend', cond, '방어 자리에서 대문 + 첫 주사위 50 미만이면 남는다'))

    a, ta = _cmp_bit(run, '수양', '>=', 41)
    b, tb = _cmp_bit(run, '성정', '<', 80)
    st = 'bad' if (a is False or b is False) else 'ok' if (a and b) else 'pend'
    out.append((st, '2년 9월 상순 「제가 한번 해보겠습니다」', ta + ' · ' + tb))

    a, ta = _cmp_bit(run, '도덕', '>=', 40)
    g = _num(run, '구력')
    if g is None:
        b, tb = None, '구력 ?'
    else:
        b = g + DICE_HI >= 70
        tb = (f'주사위 1~50 + 구력 >=70 · 구력 {int(g)} '
              + ('확정' if g >= 69 else '주사위를 위로 옮기면 된다' if b else bad('모자람')))
    st = 'bad' if (a is False or b is False) else 'ok' if (a and b) else 'pend'
    out.append((st, '「정신적 고통」', ta + ' · ' + tb))

    v = _num(run, '이사형 호감도')
    cond = '「그를 위해 용서를 빈다」 → 주사위 1~50 + 이사형 호감도 <20'
    if v is None:
        out.append(('pend', cond, '이사형 호감도 ?'))
    elif v <= 18:
        out.append(('ok', cond, f'이사형 {int(v)} · 주사위를 안 옮겨도 된다'))
    elif v + DICE_LO < 20:
        out.append(('ok', cond, f'이사형 {int(v)} · 주사위 범위를 아래로 옮겨야 한다'))
    else:
        out.append(('bad', cond, f'이사형 {int(v)} · 범위를 옮겨도 못 맞춘다'))
    return out


def recipe_sheng102(run):
    """생#102 「늑대도 야식은 먹어야지」. 청성 회차의 2년 12월 상순."""
    f = lambda k: run.flags.get(k) or 0
    yes, no = ok('✓'), bad('✗')
    out = []
    cond = '엽운상이 당문에 있다'
    out.append(('ok' if f('E12000') == 1 else 'pend' if run.wk < QC_FORK_WK else 'bad', cond, ''))

    cond = '2년 6월 상순 가출에서 첫 번째 선택지 (폐사찰)'
    r = f('M20028')
    out.append(('ok', cond, '') if r == 1 else ('bad', cond, '여관으로 갔다') if r == 2
               else ('pend', cond, '아직'))

    cond = '2년 8월 갈림에서 청성으로 간다'
    went = f('M20008') == 1
    if went:
        out.append(('ok', cond, ''))
    elif f('M20008') == 2 or run.wk >= QC_FORK_WK:
        out.append(('bad', cond, '당문에 남았다'))
    else:
        lv = lover_of(run)
        out.append(('pend', cond, '마음에 둔 사람 엽운상 ' + (yes if lv == 2 else no)
                    + ' · 방어 자리에서 대문을 고르지 않는다'))

    v = _num(run, '이사형 호감도')
    cond = '2년 12월 상순 대화 화면에서 결투를 고르고 진다 — 이사형 호감도 <30 이어야 싸움이 이어진다'
    if v is None:
        out.append(('pend', cond, '이사형 호감도 ?'))
    else:
        ahead = 0 if went else 6     # 폐사찰 +1 · 「당문으로 돌아간다」 +3 · 청성 갈림 +2
        tail = f'이사형 {int(v)}' + (f' · 갈림까지 +{ahead} 쯤 더 붙는다 → {int(v) + ahead}' if ahead else '')
        out.append(('ok' if v + ahead < 30 else 'bad' if v >= 30 and went else 'pend', cond, tail))

    out.append(('pend', '이어지는 싸움에서도 진다', ''))
    return out


RECIPES = {20023: recipe_han24, 10098: recipe_sheng99, 10101: recipe_sheng102}


def recipe_tier(run, it):
    """순서표가 있는 항목의 등급은 순서표가 정한다. 없으면 None."""
    fn = RECIPES.get(it['id'])
    if not fn:
        return None
    sts = [st for st, _, _ in fn(run)]
    return 3 if 'bad' in sts else 1 if 'pend' in sts else 0


def recipe_lines(run, it, indent):
    fn = RECIPES.get(it['id'])
    if not fn:
        return []
    mark = {'ok': ok('✓'), 'pend': warn('·'), 'bad': bad('✗')}
    out = []
    for i, (st, cond, now) in enumerate(fn(run)):
        cond = dim(cond) if st == 'ok' else bad(cond) if st == 'bad' else cond
        out.append(f'{indent}{"①②③④⑤⑥⑦⑧⑨"[i]} {mark[st]} {cond}'
                   + (dim('   ' + now) if now else ''))
    return out


TIERMARK = ['확실', '대기', '미확인', '모자람']


def verdicts(run, D, got, rf, owned, lover, fmap, PQ=None, DEP=None):
    """항목마다 이 회차에서 어떤 상태인가. 계산만 하고 그리지 않는다.

    세이브 리더와 웹 공략기가 **같은 판정**을 쓰게 하려고 떼어 놓았다. 둘이 갈라지면
    같은 항목을 두고 서로 다른 말을 하게 된다.
    """
    reach = make_reachable(run, D, PQ, DEP, got, make_decided(run, got))
    items = D['items']
    have = owned or {x['id'] for x in items if x.get('owned')}
    todo, heart, passed, cant, sheetno = [], [], [], [], []
    for it in items:
        if it['id'] in have or it.get('blocked') or not it.get('reachable'):
            continue
        best = None
        for o in (it.get('opts') or []):
            v, why = opt_verdict(run, it, o, got, rf, lover, fmap, D, PQ, reach)
            rank = {'가능': 0, '심계': 1, '지남': 2, '불가': 3}[v]
            # 같은 판정이면 조건이 덜 모자란 경로를 보여 준다. 생#68 은 부엌과 대장간
            # 둘 다 되는데, 부엌 쪽만 도덕 60 미만을 요구해서 못 하는 길이 먼저 보였다.
            miss = 0
            if v == '가능':
                _, unmet, unknown, _, _ = req_line(run, o, pathof(it, o))
                miss = unmet * 2 + unknown
            key = (rank, miss)
            if best is None or key < best[0]:
                best = (key, v, why, o)
        if best is None:
            continue
        key, v, why, o = best
        rank = key[0]
        if isinstance(why, tuple) and why and why[0] in ('why', 'not'):
            f = fmap.get(why[1], {})
            nm = lambda x: next((p['name'] for p in f.get('options', []) if p['v'] == x), f'값 {x}')
            if why[0] == 'not':
                why = f'{f.get("flag", why[1])} 이 {nm(why[2])} 이면 이 라인이 안 열린다'
            else:
                _, fid, cur, need = why
                why = f'{f.get("flag", fid)} 이 {nm(cur)} 인데 {nm(need)} 가 필요하다'
        # 커뮤니티 시트가 「현재 달성 불가능」이라고 적어 둔 것은 따로 모은다.
        # 2차 정보지만 생사부 77 은 시트가 맞고 우리가 틀렸다 — 게임 파일로도 확인됐다.
        sh = (it.get('sheet') or {}).get('cond') or ''
        if rank == 0 and ('달성 불가능' in sh or '暂无法达成' in sh) and it['id'] not in SHEET_WRONG:
            sheetno.append((it, o, sh))
            continue
        [todo, heart, passed, cant][rank].append((it, o, why))

    todo.sort(key=lambda x: (tier(run, x[0], x[1], got, fmap),
                             x[1].get('wk') or x[1].get('wkEst') or 999999))
    miss = [i for i in items if i['id'] not in have]
    skip = len(miss) - (len(todo) + len(heart) + len(passed) + len(cant))
    return {'reach': reach, 'have': have, 'miss': miss, 'skip': skip,
            'todo': todo, 'heart': heart, 'passed': passed,
            'cant': cant, 'sheetno': sheetno}


def library_section(run, D, got, rf, owned, lover, fmap, show_all, PQ=None, DEP=None):
    V = verdicts(run, D, got, rf, owned, lover, fmap, PQ, DEP)
    todo, heart, passed = V['todo'], V['heart'], V['passed']
    cant, sheetno, miss, skip = V['cant'], V['sheetno'], V['miss'], V['skip']
    L = [rule('도감 — 이 회차에서 아직 딸 수 있는 것')]
    L.append(dim('   지금 세이브 기준이다. 공략기 런 플래너의 「N개」는 세이브와 무관하게'))
    L.append(dim('   도감 전체를 회차로 가른 묶음 크기라 숫자가 다르다.'))
    ready = sum(1 for it, o, _ in todo if not grade(run, it, o)[0])
    solid = [(it, o) for it, o, _ in todo if grade(run, it, o) == (0, 0, 0)]
    L.append(dim(f'   미획득 {len(miss)}개 — 가능 {len(todo)}')
             + dim(f'(수치까지 맞는 것 ') + bold(str(ready))
             + dim(' · 조건을 다 읽었고 다 맞는 것 ') + ok(str(len(solid))) + dim(')')
             + dim(f' · 심계를 바꿔야 {len(heart)} · '
                   f'시점 지남 {len(passed)} · 이 회차 불가 {len(cant)}'
                   + (f' · 시트가 불가라 함 {len(sheetno)}' if sheetno else '')
                   + (f' · 현재 빌드에서 막힘 {skip}' if skip else '')))
    L.append(dim('   확실 = 조건을 다 읽었고 다 맞음 · 대기 = 조건은 맞고 그 사건이 아직 안 옴'))
    L.append(dim('   미확인 = 우리가 못 읽은 조건이 있음 · 모자람 = 수치를 더 맞춰야 함'))
    L.append('')
    head = now_section(run, todo)
    if head:
        L = head + [''] + L
    for it, o, why in todo[:30]:
        tag = f'{it["type"][0]}#{it["no"]}'
        # 조건을 전부 읽었고 전부 맞는 것만 확실이라고 부른다. 나머지는 「아직 모르는
        # 조건이 남아 있다」는 뜻이고, 그것이 이 도구가 틀리는 자리다.
        t = tier(run, it, o, got, fmap)
        rt = recipe_tier(run, it)
        if rt is not None and it['id'] != 20023:
            t = rt
        paint_t = [ok, acc, warn, bad][t]
        # 판정을 시기보다 앞에 둔다. 시기 뒤에 붙이면 「3년차 12월 … 모자람」처럼 시기가
        # 모자란 것으로 읽힌다 — 시기는 조건이 아니라 그 사건이 오는 때다.
        mark = pad(paint_t(TIERMARK[t]), 8)
        L.append(f'   {pad(ok(tag), 16)}{pad(it["title"], 30)} {mark}'
                 + (dim('시기 ' + why) if why else ''))
        steps = recipe_lines(run, it, '   ' + ' ' * 16)
        if steps:
            L.extend(steps)
            continue
        for who, d in prereq_hint(run, o, PQ or {}):
            first = (d.get('how') or [''])[0]
            L.append(f'   {" " * 16}{dim("↳")} {cname(who)}{acc(" 영입")} {dim(d.get("when", ""))}  '
                     + dim(re.sub(r'^[①-⑨]\s*', '', first)[:52]))
        rl = route_line(it, o)
        if rl:
            L.append(f'   {" " * 16}{dim("↳")} {dim(paint(rl))}')
        via = o.get('via')
        if via:
            bits = []
            if via.get('choices'):
                bits.append('고르기: ' + ' → '.join('「' + c + '」' for c in via['choices']))
            for d in via.get('dice') or []:
                bits.append('주사위' + (' + ' + d['props'] if d.get('props') else '') + ' ' + d.get('th', ''))
            L.append(f'   {" " * 16}{dim("↳")} {acc("앞 장면")} '
                     + warn(', '.join(via['at']) + ' 을 거쳐야 조건이 선다') + dim('  ' + ' · '.join(bits)))
        nl = need_line(o, got, fmap)
        if nl:
            L.append(f'   {" " * 16}{dim("↳")} {acc("갈래")} {warn(nl)}')
        line, unmet, unknown, judged, pend = req_line(run, o, pathof(it, o))
        if line:
            mark = (warn(f'{unmet}개 모자람') if unmet
                    else dim('확인 못 함') if unknown
                    else ok('수치 맞음') if judged
                    else dim('수치 조건 없음'))
            if pend:
                mark += dim(f' · 플래그 {pend}개 대기')
            L.append(f'   {" " * 16}{dim("└")} {line}   {mark}')
        # 어느 한 길에만 걸린 조건. 다른 길로도 올 수 있어 판정에는 안 쓴다.
        alt = [f"{r['stat']} {'아님 ' if r.get('neg') else ''}{r['op']}{r['val']}"
               for r in (o.get('pathReqs') or []) if 'stat' in r]
        if alt:
            L.append(f'   {" " * 16}{dim("· 길에 따라 다름(조건 아님): " + ", ".join(alt[:6]))}')
    if len(todo) > 30:
        L.append(dim(f'   … 그리고 {len(todo) - 30}개 더'))

    if heart:
        L.append(rule('다른 심계라야 되는 것'))
        L.append(dim('   한 회차 안에서는 심계를 바꾸지 않는다고 보고 짠 것이다.'))
        L.append(dim('   「변심의 꿈」으로 갈아탈 수는 있지만, 갈아타면 지금 심계로 열리는 쪽이 닫힌다.'))
        for it, o, why in heart[:15]:
            L.append(f'   {pad(warn(it["type"][0] + "#" + str(it["no"])), 16)}'
                     f'{pad(it["title"], 30)} {dim(why)}')
    if sheetno:
        L.append(rule('공략 시트가 「현재 달성 불가능」이라고 적어 둔 것'))
        L.append(dim('   2차 정보다. 다만 생사부 77 은 시트가 맞았다 — 그 도감을 주는 전투가'))
        L.append(dim('   전부 deadEnd 가 아니라, 져도 스크립트가 다른 것을 준다.'))
        for it, o, sh in sheetno[:12]:
            L.append(f'   {pad(dim(it["type"][0] + "#" + str(it["no"])), 16)}'
                     f'{pad(it["title"], 30)} {dim(sh[:40])}')
    if passed:
        L.append(rule('시점이 지난 것 (이 회차에서는 놓침)'))
        for it, o, why in passed[:15]:
            L.append(f'   {pad(bad(it["type"][0] + "#" + str(it["no"])), 16)}'
                     f'{pad(it["title"], 30)} {dim(why)}')
        if len(passed) > 15:
            L.append(dim(f'   … 그리고 {len(passed) - 15}개 더'))

    if show_all and cant:
        L.append(rule('이 회차의 갈래로는 불가'))
        for it, o, why in cant[:30]:
            L.append(f'   {pad(dim(it["type"][0] + "#" + str(it["no"])), 16)}'
                     f'{pad(it["title"], 30)} {dim(why)}')
    elif cant:
        L.append(dim(f'\n   갈래가 달라 이 회차에서 못 따는 것 {len(cant)}개 '
                     '— 보려면 --all'))
    return L


# 쌓이기만 하고 줄지 않는 값들. 지금 얼마고 다음 문턱이 얼마인지 보여 줄 만하다.
# 게임 UI 에 안 뜨는 내부 스탯이라 savemap 의 EXTRA_STATS 로 이름을 붙여야 읽힌다.
TRACK = ('누적 연단', '누적 무학', '누적 단조', '누적 공헌', '요리')


def track_stats(run, D, have):
    """모으는 값과, 아직 못 딴 도감이 요구하는 문턱들."""
    marks = {n: set() for n in TRACK}
    for it in D['items']:
        if it['id'] in have or it.get('blocked') or not it.get('reachable'):
            continue
        for o in (it.get('opts') or []):
            for r in (o.get('reqs') or []) + (o.get('upReqs') or []):
                for a in (r['any'] if 'any' in r else [r]):
                    if a.get('stat') in marks and a.get('op') in ('>=', '>'):
                        marks[a['stat']].add(a['val'] + (1 if a['op'] == '>' else 0))
    # 도감이 아니어도 그 값에서 열리는 자리가 있다. 조건문 전체에서도 문턱을 모은다.
    every = {n: set(marks[n]) for n in TRACK}
    RE_TH = re.compile(r'\[([가-힣 ]+)\]\s*(>=|>)\s*(\d+)')
    for conds in ((load_json('graph.json') or {}).get('switch') or {}).values():
        for t in (conds or []):
            for nm, op, v in RE_TH.findall(t):
                if nm in every:
                    every[nm].add(int(v) + (1 if op == '>' else 0))
    out = []
    for n in TRACK:
        cur = cur_value(run, n)
        ms, ev = sorted(marks[n]), sorted(every[n])
        if cur is None or not ev:
            continue
        out.append({'name': n, 'cur': cur, 'lib': ms, 'marks': ev,
                    'next': next((m for m in ev if m > cur), None),
                    'done': sum(1 for m in ev if m <= cur)})
    return out


def save_verdicts(path=None):
    """지금 세이브 기준 판정을 웹 공략기가 심을 모양으로. 세이브가 없으면 None.

    브라우저는 file:// 에서 세이브 파일을 읽지 못한다. 그래서 gen_html.py 가 구울 때
    이것을 불러 결과를 HTML 안에 박는다. 세이브가 바뀌면 워치 루프가 다시 굽는다.
    """
    M = load_json('savemap.json')
    D = load_json('data.json')
    if M is None or D is None:
        return None
    add_meeting_gate(D)
    path = path or (find_saves() or [None])[0]
    if not path:
        return None
    forks = load_json('forks.json') or []
    rf = load_json('route_forks.json') or {}
    PQ = load_json('prereq.json') or {}
    DEP = load_json('flagdep.json') or {}
    AFFECT.update(load_json('affect.json') or {})
    DEPG.update(DEP)
    CAST.update(load_json('cast.json') or {})
    PRES.update(load_json('presence.json') or {})
    run = Run(path, M)
    got, _ = run_forks(run, forks)
    fmap = {f['id']: f for f in forks}
    V = verdicts(run, D, got, rf, universe_owned(), lover_of(run), fmap, PQ, DEP)

    def plain(s):
        return RE_ANSI.sub('', s or '').strip()

    items = {}
    for bucket, rows in (('가능', V['todo']), ('심계', V['heart']),
                         ('지남', V['passed']), ('불가', V['cant'])):
        for it, o, why in rows:
            e = {'b': bucket, 'why': plain(str(why))}
            if bucket == '가능':
                e['t'] = tier(run, it, o, got, fmap)
                line, unmet, unknown, judged, pend = req_line(run, o, pathof(it, o))
                e['cond'] = plain(line)
                e['unmet'] = unmet
                e['pend'] = pend
                e['wk'] = o.get('wk') or o.get('wkEst')
            items[str(it['id'])] = e
    for it, o, sh in V['sheetno']:
        items[str(it['id'])] = {'b': '시트불가', 'why': plain(sh)[:60]}

    return {
        'track': track_stats(run, D, V['have']),
        'when': run.when(),
        'wk': run.wk,
        'slot': run.slot,
        'script': run.script,
        'ngplus': bool(run.gs.get('NewGamePlus')),
        'lover': M['lover'].get(str(lover_of(run)), '아직 정해지지 않음'),
        'saved': time.strftime('%m/%d %H:%M', time.localtime(os.path.getmtime(path))),
        'counts': {'miss': len(V['miss']), '가능': len(V['todo']),
                   '심계': len(V['heart']), '지남': len(V['passed']),
                   '불가': len(V['cant']), '시트불가': len(V['sheetno']),
                   '빌드막힘': V['skip']},
        'items': items,
    }


# ---------------------------------------------------------------- 진입점
def pick(argv):
    saves = find_saves()
    if not saves:
        return None
    for a in argv:
        if a.startswith('-'):
            continue
        hit = [s for s in saves if a.lower() in os.path.basename(s).lower()]
        if hit:
            return hit[0]
    return saves[0]


def main():
    argv = sys.argv[1:]
    M = load_json('savemap.json')
    if M is None:
        print('savemap.json 이 없다. 먼저 python mk_savemap.py 를 돌려라.')
        return 1
    if '--list' in argv:
        for s in find_saves():
            print(f'{time.strftime("%m/%d %H:%M", time.localtime(os.path.getmtime(s)))}  '
                  f'{save_kind(s):16} {os.path.basename(s)}')
        return 0

    path = pick(argv)
    if not path:
        print(f'세이브를 찾지 못했다: {SAVE_DIR}')
        return 1

    D = load_json('data.json')
    add_meeting_gate(D)
    forks = load_json('forks.json') or []
    rf = load_json('route_forks.json') or {}
    PQ = load_json('prereq.json') or {}
    DEP = load_json('flagdep.json') or {}
    AFFECT.update(load_json('affect.json') or {})
    DEPG.update(DEP)
    CAST.update(load_json('cast.json') or {})
    PRES.update(load_json('presence.json') or {})
    owned = universe_owned()

    if '--where' in argv:
        who = argv[argv.index('--where') + 1]
        run = Run(path, M)
        POS = {'position': load_json('pos.json') or []}
        out = where_section(run, POS, AFFECT, who)
        out += [''] + where_section(run, POS, AFFECT, who, down=True)
        out += [''] + event_moves(run, AFFECT, who)
        out += [''] + event_moves(run, AFFECT, who, down=True)
        print(chr(10).join(out))
        return 0

    if '--flags' in argv:
        needle = argv[argv.index('--flags') + 1]
        run = Run(path, M)
        for fid, val in sorted(run.flags.items()):
            ko = run.flag_ko(fid)
            if needle in fid or needle in ko:
                print(f'{fid:12} {val:>6}   {ko}')
        return 0

    if '--story' in argv:
        needle = argv[argv.index('--story') + 1]
        run = Run(path, M)
        print(story_report(run, needle))
        return 0

    show_all = '--all' in argv
    watch = '--watch' in argv
    last = None
    skip = set()          # 못 읽은 파일. 감시 중에 계속 되돌아오지 않게 기억한다
    uni = universe_mtime()
    baking = None
    while True:
        mt = os.path.getmtime(path)
        if mt != last:
            last = mt
            try:
                run = Run(path, M)
            except Exception as e:
                # 한 파일을 못 읽는다고 감시가 죽으면 안 된다. 건너뛰고 다음으로 간다.
                skip.add(path)
                print(bad(f'{os.path.basename(path)} 를 읽지 못했다: {e}'))
                nxt = next((p for p in find_saves() if p not in skip), None)
                if not watch or nxt is None:
                    return 1
                path, last = nxt, None
                continue
            if watch:
                os.system('cls' if os.name == 'nt' else 'clear')
            print(report(run, D, forks, rf, owned, show_all, PQ, DEP))
            if watch:
                print(dim('\n   세이브가 바뀌면 다시 그린다. Ctrl+C 로 종료.'))
                # 웹 공략기에도 이 회차 판정이 박혀 있다. 세이브가 바뀌면 같이 갱신한다.
                if not (baking and baking.is_alive()):
                    baking = threading.Thread(target=bake_web, args=(False,),
                                              daemon=True)
                    baking.start()
        if not watch:
            return 0
        time.sleep(3)
        # 도감 JSON 이 바뀌면 새로 딴 것이 있다는 뜻이다. 웹 공략기를 다시 굽는다.
        um = universe_mtime()
        if um != uni and not (baking and baking.is_alive()):
            uni = um
            print(dim('   도감이 바뀌었다. 웹 공략기를 다시 굽는 중... (1분 남짓)'))

            # 굽는 데 1분이 넘게 걸린다. 그동안 리더가 멈춰 있으면 안 된다.
            baking = threading.Thread(target=bake_web, args=(True,), daemon=True)
            baking.start()
        cands = [p for p in find_saves() if p not in skip]
        if cands and cands[0] != path:
            path, last = cands[0], None


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
