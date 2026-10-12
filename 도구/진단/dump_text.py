import sys, re, json, io, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import game
g = game.Game()
M = json.load(open('savemap.json', encoding='utf-8'))['chars']
G = json.load(open('graph.json', encoding='utf-8'))
FK = json.load(open('data.json', encoding='utf-8'))['flagKo']
RE_OPT = re.compile(r'"(?:[a-z]+\+)?(O_[A-Za-z0-9_]+)')


def txt(k):
    return re.sub(r'\\n|[\r\n]+', ' ', g.t('Story/' + k) or '')


def dump(sc, a, b, out):
    L = open(f'lua/{sc}.lua', encoding='utf-8').read().split('\n')
    who = ''
    out.write(f'\n===== {sc} {a}-{b}\n')
    for i in range(a - 1, min(b, len(L))):
        ln = L[i]
        m = re.search(r'setcharacter\(characters\.Get\("([^"]+)"\)', ln)
        if m: who = M.get(m.group(1), m.group(1))
        if 'setcharacter(narrative)' in ln: who = '(지문)'
        for nm in re.findall(r'(?:Switch|Condition)\("([^"]+)"\)', ln):
            out.write(f'{i+1}: [COND {nm} {G["switch"].get(nm) or G["condition"].get(nm)}]\n')
        m = re.match(r'^(\t*)(if|elseif|else|end)\b(.*)', ln)
        if m: out.write(f'{i+1}: {m.group(1)}{m.group(2)}{m.group(3)[:40]}\n')
        m = re.search(r'(Set|Add)Flag\("([^"]+)", *(-?\d+)', ln)
        if m: out.write(f'{i+1}: [{m.group(1).upper()} {m.group(2)} ({FK.get(m.group(2), "")}) {m.group(3)}]\n')
        m = re.search(r'--index:(\S+)', ln)
        if m: out.write(f'{i+1}: >>> 고름 {m.group(1)} = {txt(m.group(1))}\n')
        elif RE_OPT.search(ln):
            for k in RE_OPT.findall(ln): out.write(f'{i+1}: [OPTION {k}] {txt(k)}\n')
        m = re.search(r'SetNextScript\("([^"]+)"', ln)
        if m: out.write(f'{i+1}: [NEXT {m.group(1)}]\n')
        m = re.search(r'Character\("([^"]+)", *(-?\d+)', ln)
        if m: out.write(f'{i+1}: [호감도 {M.get(m.group(1), m.group(1))} {m.group(2)}]\n')
        m = re.search(r'Dice\("([^"]+)"', ln)
        if m: out.write(f'{i+1}: [DICE {m.group(1)} {json.dumps(G["dice"].get(m.group(1)), ensure_ascii=False)}]\n')
        for k in re.findall(r'GetStoryText\("([^"]+)"\)', ln):
            out.write(f'{i+1}: {who}: {txt(k)}\n')


out = io.open(sys.argv[1], 'w', encoding='utf-8')
for spec in sys.argv[2:]:
    sc, a, b = spec.split(':')
    dump(sc, int(a), int(b), out)
out.close()
