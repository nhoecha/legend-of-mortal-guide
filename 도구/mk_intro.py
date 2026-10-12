# -*- coding: utf-8 -*-
"""도감 인물 소개(CharacterIntro0~4)를 한 사람씩 읽는 HTML 로 낸다. -> ../활협전-인물소개.html"""
import os, re, json, html, collections

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
import game

OUT = os.path.join(HERE, '..', '활협전-인물소개.html')
GROUPS = [('당문', ('sister', 'brother', 'master')), ('인연', ('girl',)), ('강호', ('special',))]


def natkey(c):
    return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', c)]


def collect(loc, chars):
    by = collections.defaultdict(dict)
    for k, v in loc.items():
        m = re.match(r'CharacterIntro(\d)/(.+)', k)
        if m and len(v.strip()) > 2:
            by[m.group(2)][int(m.group(1))] = v
    people = []
    for label, prefixes in GROUPS:
        for c in sorted((c for c in by if c.startswith(prefixes)), key=natkey):
            people.append({
                'id': c, 'group': label,
                'name': loc.get('Character/' + c) or chars.get(c) or c,
                'title': loc.get('CharacterTitle/' + c, ''),
                'stages': [[n + 1, by[c][n].split('\\n')] for n in sorted(by[c])],
            })
    return people


PAGE = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>활협전 인물 소개</title>
<style>
:root{--bg:#f6f1e7;--panel:#ede5d6;--ink:#2a2420;--dim:#7d7265;--line:#d8cdb9;--acc:#9c3b2e}
@media (prefers-color-scheme:dark){:root{--bg:#1b1917;--panel:#24211e;--ink:#e8e0d2;--dim:#978c7c;--line:#3a352f;--acc:#d9806f}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Noto Serif KR","Nanum Myeongjo","Malgun Gothic",serif;line-height:1.9}
.wrap{display:grid;grid-template-columns:230px 1fr;min-height:100vh}
nav{background:var(--panel);border-right:1px solid var(--line);padding:52px 0 18px;position:sticky;top:0;height:100vh;overflow-y:auto}
nav h2{font-size:12px;letter-spacing:.2em;color:var(--dim);margin:16px 20px 6px;font-weight:400}
nav button{display:block;width:100%;text-align:left;background:none;border:0;border-left:3px solid transparent;color:var(--ink);font:inherit;font-size:15px;padding:5px 17px;cursor:pointer}
nav button small{color:var(--dim);font-size:12px;margin-left:6px}
nav button:hover{background:var(--line)}
nav button.on{border-left-color:var(--acc);color:var(--acc);font-weight:700}
.wrap.fold{grid-template-columns:1fr}.wrap.fold nav{display:none}
#fold{position:fixed;top:12px;left:12px;z-index:2;background:var(--bg);border:1px solid var(--line);color:var(--dim);font:inherit;font-size:13px;padding:4px 12px;border-radius:6px;cursor:pointer}
#fold:hover{border-color:var(--acc);color:var(--acc)}
main{padding:48px 24px 96px;max-width:760px;width:100%;margin:0 auto}
.count{color:var(--dim);font-size:13px;letter-spacing:.1em}
h1{font-size:38px;margin:4px 0 0;letter-spacing:.04em}
.title{color:var(--acc);font-size:16px;margin-bottom:28px;min-height:1em}
section{border-top:1px solid var(--line);padding:22px 0 6px}
section h3{font-size:13px;letter-spacing:.2em;color:var(--dim);font-weight:400;margin:0 0 10px}
section p{margin:0 0 12px;font-size:18px;word-break:keep-all}
.pager{display:flex;justify-content:space-between;gap:12px;margin-top:36px}
.pager button{flex:1;background:var(--panel);border:1px solid var(--line);color:var(--ink);font:inherit;font-size:15px;padding:12px;border-radius:6px;cursor:pointer}
.pager button:hover{border-color:var(--acc);color:var(--acc)}
.pager button:disabled{opacity:.35;cursor:default}
.hint{color:var(--dim);font-size:12px;text-align:center;margin-top:12px}
@media (max-width:720px){.wrap{grid-template-columns:1fr}nav{position:static;height:auto;display:flex;flex-wrap:wrap;gap:2px;padding:48px 16px 10px}nav h2{width:100%;margin:8px 0 2px}nav button{width:auto;border-left:0;padding:3px 9px;border-radius:4px}nav button small{display:none}main{padding:28px 16px 72px}h1{font-size:30px}}
</style></head><body>
<button id="fold"></button>
<div class="wrap" id="wrap"><nav id="nav"></nav><main id="main"></main></div>
<script id="data" type="application/json">__DATA__</script>
<script>
const P = JSON.parse(document.getElementById('data').textContent);
const nav = document.getElementById('nav'), main = document.getElementById('main');
const el = (t, c, s) => { const e = document.createElement(t); if (c) e.className = c; if (s != null) e.textContent = s; return e; };
const wrap = document.getElementById('wrap'), fold = document.getElementById('fold');
function setFold(on) { wrap.classList.toggle('fold', on); fold.textContent = on ? '목록 펴기' : '목록 접기'; try { localStorage.setItem('introFold', on ? '1' : ''); } catch (e) {} }
fold.onclick = () => setFold(!wrap.classList.contains('fold'));
let folded = false; try { folded = localStorage.getItem('introFold') === '1'; } catch (e) {}
setFold(folded);
let cur = 0;
try { cur = Math.max(0, P.findIndex(p => p.id === localStorage.getItem('intro'))); } catch (e) {}
let g = '';
P.forEach((p, i) => {
  if (p.group !== g) { g = p.group; nav.append(el('h2', '', g)); }
  const b = el('button', '', p.name);
  if (p.title && p.title !== p.name) b.append(el('small', '', p.title));
  b.onclick = () => show(i);
  nav.append(b);
});
const btns = nav.querySelectorAll('button');
function show(i) {
  cur = i; const p = P[i];
  try { localStorage.setItem('intro', p.id); } catch (e) {}
  btns.forEach((b, j) => b.classList.toggle('on', j === i));
  main.replaceChildren(el('div', 'count', (i + 1) + ' / ' + P.length + ' · ' + p.group), el('h1', '', p.name), el('div', 'title', p.title));
  p.stages.forEach(([n, lines]) => {
    const s = el('section'); s.append(el('h3', '', n + '단계'));
    lines.forEach(t => s.append(el('p', '', t)));
    main.append(s);
  });
  const pg = el('div', 'pager');
  const a = el('button', '', i ? '← ' + P[i - 1].name : '←'), z = el('button', '', i < P.length - 1 ? P[i + 1].name + ' →' : '→');
  a.disabled = !i; z.disabled = i === P.length - 1;
  a.onclick = () => show(i - 1); z.onclick = () => show(i + 1);
  pg.append(a, z); main.append(pg, el('div', 'hint', '← → 키로 넘길 수 있다'));
  btns[i].scrollIntoView({block: 'nearest'}); window.scrollTo(0, 0);
}
addEventListener('keydown', e => {
  if (e.key === 'ArrowRight' && cur < P.length - 1) show(cur + 1);
  if (e.key === 'ArrowLeft' && cur > 0) show(cur - 1);
});
show(cur);
</script></body></html>
'''


def main():
    g = game.Game()
    chars = json.load(open('savemap.json', encoding='utf-8'))['chars']
    people = collect(g.loc, chars)
    data = json.dumps(people, ensure_ascii=False).replace('</', '<\\/')
    open(OUT, 'w', encoding='utf-8').write(PAGE.replace('__DATA__', data))
    print(len(people), sum(len(p['stages']) for p in people))
    for p in people:
        print(p['id'], p['name'], p['title'], [n for n, _ in p['stages']])


if __name__ == '__main__':
    main()
