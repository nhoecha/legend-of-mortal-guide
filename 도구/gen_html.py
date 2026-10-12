"""Render the self-contained 도감 planner page (생사부 + 한청서 + 풍운사)."""
import json, os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '활협전-도감.html')

PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>활협전 도감 공략기</title>
<style>
:root{
  --bg:#faf7f2; --panel:#fff; --line:#e5ded2; --ink:#2b2622; --dim:#7a6f63;
  --accent:#8b3a2f; --ok:#2f7d4f; --no:#a33; --chip:#f0eae0; --code:#f5f1ea;
  --t1:#8b3a2f; --t2:#2f5f8b; --t3:#7a5a1f;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#17140f; --panel:#201c16; --line:#332c22; --ink:#ece4d8; --dim:#a2968a;
  --accent:#e0785f; --ok:#6fc48f; --no:#e5766e; --chip:#2a241c; --code:#181410;
  --t1:#e0785f; --t2:#7fb2e0; --t3:#d8b869;
}}
:root[data-theme="dark"]{
  --bg:#17140f; --panel:#201c16; --line:#332c22; --ink:#ece4d8; --dim:#a2968a;
  --accent:#e0785f; --ok:#6fc48f; --no:#e5766e; --chip:#2a241c; --code:#181410;
  --t1:#e0785f; --t2:#7fb2e0; --t3:#d8b869;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Pretendard","Malgun Gothic","Apple SD Gothic Neo",system-ui,sans-serif;
  font-size:15px;line-height:1.6}
header{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);
  padding:12px 20px 9px}
h1{margin:0 0 2px;font-size:19px;letter-spacing:-.02em}
.sub{color:var(--dim);font-size:12.5px;margin-bottom:9px}
.bar{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:6px}
.bar .lbl{font-size:11.5px;color:var(--dim);margin-right:2px}
button.f{background:var(--chip);border:1px solid var(--line);color:var(--ink);
  border-radius:99px;padding:4px 11px;font-size:12.5px;cursor:pointer;font-family:inherit}
button.f[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
button.tag{font-size:12px;padding:3px 9px}
input#q{flex:1;min-width:150px;background:var(--panel);border:1px solid var(--line);
  border-radius:8px;padding:6px 10px;color:var(--ink);font-family:inherit;font-size:13px}
.stats{display:flex;gap:12px;flex-wrap:wrap;font-size:12.5px;color:var(--dim);margin-top:6px}
.stats b{color:var(--ink)}
main{padding:12px 20px 60px;max-width:1020px;margin:0 auto}
.card{background:var(--panel);border:1px solid var(--line);border-radius:11px;
  margin-bottom:8px;overflow:hidden}
.head{display:flex;gap:9px;align-items:baseline;padding:10px 14px;cursor:pointer;flex-wrap:wrap}
.tp{font-size:11px;border-radius:5px;padding:1px 6px;border:1px solid currentColor;white-space:nowrap}
.tp1{color:var(--t1)} .tp2{color:var(--t2)} .tp3{color:var(--t3)}
.no{color:var(--dim);font-variant-numeric:tabular-nums;font-size:12.5px;min-width:30px}
.title{font-weight:600;flex:1;min-width:150px}
.badge{font-size:11.5px;border-radius:99px;padding:2px 8px;white-space:nowrap;border:1px solid transparent}
.b-own{color:var(--ok);border-color:var(--ok)}
.b-miss{color:var(--dim);border-color:var(--line)}
.b-no{color:var(--no);border-color:var(--no)}
.b-blk{color:var(--t3);border-color:var(--t3)}
.r-ok{color:var(--ok);border-color:var(--ok);font-weight:600}
.r-heart{color:var(--t2);border-color:var(--t2)}
.r-past{color:var(--dim);border-color:var(--line)}
.r-no{color:var(--no);border-color:var(--no);opacity:.75}
.runline{display:block;margin-top:4px;color:var(--dim)}
.runline b.ok{color:var(--ok)}
.trackline{display:block;margin-top:2px}
.trackline .ok{color:var(--ok)}
.trackline .dim{color:var(--dim)}
.blk{background:var(--code);border:1px dashed var(--t3);border-radius:8px;
  padding:8px 10px;margin:8px 0;font-size:12.5px;color:var(--dim)}
.body{display:none;padding:0 14px 14px;border-top:1px solid var(--line)}
.card.open .body{display:block}
.desc{color:var(--dim);font-size:13.5px;white-space:pre-wrap;margin:10px 0 4px}
.tags{display:flex;gap:4px;flex-wrap:wrap;margin:6px 0 0}
.tg{font-size:11px;color:var(--dim);background:var(--chip);border-radius:5px;padding:1px 7px;cursor:pointer}
.tg:hover{color:var(--accent)}
h4{margin:14px 0 6px;font-size:12.5px;color:var(--dim);font-weight:600;letter-spacing:.04em}
.path{border-left:2px solid var(--line);padding:2px 0 2px 12px;margin:0 0 12px}
.step{display:flex;gap:8px;align-items:flex-start;padding:3px 0}
.k{font-size:11px;color:var(--dim);min-width:46px;padding-top:2px}
.k.sel{color:var(--accent)}
.txt{flex:1}
code{background:var(--code);border:1px solid var(--line);border-radius:5px;padding:1px 5px;
  font-size:12.5px;font-family:ui-monospace,Consolas,monospace;word-break:break-word}
.entry{font-size:13px;background:var(--chip);border-radius:7px;padding:6px 9px;margin:4px 0}
.rate{color:var(--accent);font-weight:600}
.end{font-weight:600;color:var(--accent);padding:4px 0 0}
.sheet{margin-top:10px;font-size:12.5px;color:var(--dim);background:var(--code);
  border:1px dashed var(--line);border-radius:8px;padding:8px 10px}
.small{font-size:11.5px;color:var(--dim)}
.none{color:var(--dim);font-size:13px;padding:8px 0}
.when{font-size:11.5px;color:var(--dim);background:var(--chip);border-radius:6px;
  padding:2px 8px;white-space:nowrap}
.org{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:6px 0 2px}
.org b{font-size:13px}
.orgk{font-size:11px;border:1px solid var(--accent);color:var(--accent);
  border-radius:99px;padding:1px 7px}
.orgc{font-size:12px;color:var(--dim);margin:2px 0 6px}
.guess{color:var(--dim);font-size:11px}
.sum{font-size:12.5px;color:var(--dim);border-left:2px solid var(--line);
  padding:1px 0 1px 8px;margin:3px 0 6px}
.tabs{display:flex;gap:6px;margin-bottom:10px;align-items:center;flex-wrap:wrap;border-bottom:1px solid var(--line)}
#theme{margin-left:auto;background:var(--chip);border:1px solid var(--line);color:var(--ink);
  border-radius:99px;padding:4px 12px;font-size:12.5px;cursor:pointer;font-family:inherit}
button.tb{background:none;border:none;border-bottom:2px solid transparent;color:var(--dim);
  font-size:14px;font-weight:600;padding:4px 8px;cursor:pointer;font-family:inherit}
button.tb[aria-pressed="true"]{color:var(--ink);border-bottom-color:var(--accent)}

.wnav{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 16px}
button.wtab.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.wbody{max-width:60em;line-height:1.75}
.wtitle{margin:0 0 14px;font-size:1.3em}
.wh1{margin:26px 0 8px;font-size:1.15em;border-bottom:1px solid var(--line);padding-bottom:4px}
.wh2{margin:22px 0 6px;font-size:1.02em}
.wh3{margin:16px 0 4px;font-size:.96em;color:var(--dim)}
.wp{margin:8px 0}
.wul{margin:8px 0 8px 20px;padding:0}
.wul li{margin:3px 0}
.wpre{background:var(--soft);border:1px solid var(--line);border-radius:6px;padding:10px 12px;
      overflow-x:auto;font-size:.86em;line-height:1.5;white-space:pre}
.wq{margin:10px 0;padding:8px 12px;border-left:3px solid var(--accent);background:var(--soft);
    color:var(--dim);font-size:.94em}
.wtb{border-collapse:collapse;margin:10px 0;font-size:.92em;display:block;overflow-x:auto}
.wtb th,.wtb td{border:1px solid var(--line);padding:4px 9px;text-align:left;vertical-align:top}
.wtb th{background:var(--soft)}
.whr{border:none;border-top:1px solid var(--line);margin:22px 0}
a.wlink{color:var(--accent);text-decoration:none;border-bottom:1px dotted var(--accent)}
.ev{background:var(--panel);border:1px solid var(--line);border-radius:11px;
  padding:13px 15px;margin-bottom:10px}
.ev h3{margin:0 0 7px;font-size:15px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.ev .evb{font-size:13px;line-height:1.62;white-space:pre-wrap;color:var(--ink)}
.ev .evb em{font-style:normal;color:var(--accent);font-weight:600}
.evsrc{font-size:10.5px;font-weight:600;border-radius:4px;padding:1px 6px;
  border:1px solid var(--line);color:var(--dim)}
.evsrc.game{color:var(--accent);border-color:var(--accent)}
#evnote{font-size:12.5px;color:var(--dim);margin:0 0 12px;line-height:1.6}
.lpts{width:64px;background:var(--panel);border:1px solid var(--line);border-radius:6px;
  padding:1px 6px;color:var(--ink);font-family:inherit;font-size:12px}
.lc{font-size:11.5px;color:var(--accent);font-weight:600}
.arow.onrun{outline:2px solid var(--ok,#3a7);outline-offset:2px;border-radius:6px;padding:4px}
.arow summary .arun{margin-left:8px;font-size:11px;padding:1px 8px}
.upm{font-size:10.5px;color:var(--t2);border:1px solid var(--t2);border-radius:4px;padding:0 5px}
.lok{font-size:11.5px;color:var(--ok);font-weight:600}
.preq.no2{color:var(--no);border-color:var(--no)}
.pq.some{opacity:.72;border-style:dashed}
.pq{font-size:11px;border-radius:99px;padding:1px 8px;white-space:nowrap;cursor:pointer;
  color:var(--t3);border:1px solid var(--t3);background:transparent;font-family:inherit}
.pq:hover{background:var(--t3);color:var(--bg)}
.pqbox{background:var(--code);border:1px dashed var(--t3);border-radius:8px;
  padding:9px 11px;margin:9px 0;font-size:12.5px;line-height:1.65}
.pqbox h5{margin:0 0 4px;font-size:12.5px;color:var(--t3)}
.pqbox ul{margin:3px 0 0;padding-left:17px}
.pqbox li{margin:2px 0}
.pqmeta{color:var(--dim);font-size:11.5px;margin-top:3px}
.pqbox + .pqbox{margin-top:-2px}
.bcard{background:var(--panel);border:1px solid var(--line);border-radius:11px;
  padding:12px 14px;margin-bottom:9px}
.bhead{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin-bottom:5px}
.bn{font-size:20px;font-weight:700;color:var(--accent);font-variant-numeric:tabular-nums}
.bn small{font-size:12px;color:var(--dim);font-weight:400}
.pill{font-size:11px;border-radius:99px;padding:2px 9px;border:1px solid currentColor;white-space:nowrap}
.p-save{color:var(--ok)} .p-lock{color:var(--t3)} .p-kind{color:var(--dim);border-color:var(--line)}
.bbar{display:flex;gap:3px;margin:7px 0 5px;flex-wrap:wrap}
.seg{height:9px;flex:1;min-width:12px;border-radius:3px;background:var(--chip);
  border:1px solid var(--line)}
.seg.miss{background:var(--accent);border-color:var(--accent)}
.brow{display:flex;gap:8px;align-items:baseline;padding:2px 0;font-size:13px;flex-wrap:wrap}
.brow .mk{width:16px;color:var(--dim)}
.brow .bt{min-width:150px}
.brow .bc{color:var(--dim);font-size:12px;flex:1}
.hint{background:var(--chip);border-radius:8px;padding:8px 11px;font-size:12.5px;
  color:var(--dim);margin:10px 0 14px;line-height:1.7}
.yr{font-size:16px;font-weight:700;margin:18px 0 6px;padding-bottom:4px;
  border-bottom:1px solid var(--line)}
.tnode{display:flex;gap:10px;margin:0 0 2px}
.trail{width:14px;flex:none;position:relative}
.trail::before{content:"";position:absolute;left:6px;top:0;bottom:0;border-left:2px solid var(--line)}
.tdot{position:absolute;left:1px;top:9px;width:11px;height:11px;border-radius:50%;
  background:var(--bg);border:2px solid var(--accent)}
.tbody{flex:1;background:var(--panel);border:1px solid var(--line);border-radius:10px;
  padding:8px 12px;margin-bottom:7px}
.thead{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;margin-bottom:3px}
.tt{font-weight:600;font-size:14px}
.trow{display:flex;gap:8px;align-items:baseline;padding:2px 0;font-size:13px;flex-wrap:wrap}
.p-save2{color:var(--ok);border:1px solid var(--ok);border-radius:99px;font-size:11px;padding:1px 8px}
.rbtn{margin-right:2px}
.sum2{font-size:12px;color:var(--dim);margin:1px 0 4px}
.more{cursor:pointer;color:var(--accent)}
.det{margin:2px 0 8px 22px;padding-left:10px;border-left:2px solid var(--line)}
.plan{background:var(--panel);border:1px solid var(--line);border-radius:11px;
  padding:12px 14px;margin:6px 0 14px}
.prow{display:flex;gap:10px;align-items:baseline;padding:3px 0;border-top:1px solid var(--line);
  flex-wrap:wrap;font-size:13px}
.prow:first-of-type{border-top:none}
.pst{min-width:104px;font-weight:600}
.preq{font-family:ui-monospace,Consolas,monospace;background:var(--code);
  border:1px solid var(--line);border-radius:5px;padding:1px 7px;font-size:12.5px}
.pwho{color:var(--dim);font-size:12px;flex:1}
.conf{color:var(--no);font-weight:600;font-size:12px}
.nreq{display:flex;gap:5px;flex-wrap:wrap;align-items:center;margin:5px 0 6px;
  padding:5px 8px;background:var(--chip);border-radius:7px}
.nrl{font-size:11px;color:var(--dim);font-weight:600;margin-right:2px}
.nreq.up{background:transparent;border:1px dashed var(--line)}
.nreq.none2{background:transparent;padding:2px 0}
input.ck{width:15px;height:15px;accent-color:var(--ok);cursor:pointer;margin:0 2px 0 0;flex:none}
.trow.done > *:not(input){opacity:.45;text-decoration:line-through;text-decoration-thickness:1px}
.trow.done .more{text-decoration:none;opacity:.7}
.card.done .title{opacity:.5;text-decoration:line-through}
.ckcount{color:var(--ok);font-weight:600}
details.plan summary{list-style:none}
details.plan summary::-webkit-details-marker{display:none}
details.plan summary::before{content:"▸ ";color:var(--dim)}
details.plan[open] summary::before{content:"▾ "}
.chip{font-family:ui-monospace,Consolas,monospace;font-size:11px;background:var(--code);
  border:1px solid var(--line);border-radius:5px;padding:0 5px;color:var(--dim)}
.sum::before{content:"QUOTEOPEN";opacity:.5}
.sum::after{content:"QUOTECLOSE";opacity:.5}
.gsec{background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:12px 14px;margin:10px 0}
.gsec h3{margin:0 0 8px;font-size:14px}
.gt{width:100%;border-collapse:collapse;font-size:13px}
.gt td{padding:5px 6px;border-top:1px solid var(--line);vertical-align:top}
.gt td:first-child{width:9em;color:var(--dim);white-space:nowrap}
.gbad{color:var(--no)}
tr.growbad td{background:color-mix(in srgb, var(--no) 10%, transparent)}
.grow{display:flex;gap:7px;align-items:center;padding:4px 0;border-top:1px solid var(--line)}
.gempty{background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:20px;color:var(--dim)}
.how{padding:0 12px 9px 34px;font-size:12.5px;color:var(--dim);line-height:1.6}
.how b{color:var(--ink);font-weight:600}
.hreq{color:var(--accent)}
</style></head><body>
<header>
  <h1>활협전 도감 공략기 <span class="small">— 생사부 · 한청서 · 풍운사 통합</span></h1>
  <div class="sub">게임 파일에서 직접 추출 (build 2025-10-10) · 획득 표시는 이 페이지를 구운 사람의 세이브 기준 (공개본은 비워 두었다)</div>
  <div class="sub">한 사람이 자기 플레이에 필요한 만큼 만든 비공식 팬 도구다. 판정과 조건에 오류가 있을 수 있다. 기준 판 release_1.0.5000.13</div>
  <div class="tabs">
    <button class="tb" data-v="list" aria-pressed="true">도감 목록</button>
    <button class="tb" data-v="bundle">묶음 지도</button>
    <button class="tb" data-v="run">런 플래너</button>
    <button class="tb" data-v="goal">이번 런 목표</button>
    <button class="tb" data-v="events">사건 조건</button>
    <button class="tb" data-v="wiki">시스템</button>
    <button id="theme" title="테마 전환">테마</button>
  </div>
  <div id="filters">
  <div class="bar"><span class="lbl">종류</span>
    <button class="f" data-t="all" aria-pressed="true">전체</button>
    <button class="f" data-t="생사부">생사부</button>
    <button class="f" data-t="한청서">한청서</button>
    <button class="f" data-t="풍운사">풍운사</button>
    <span class="lbl" style="margin-left:10px">상태</span>
    <button class="f" data-s="all">전체</button>
    <button class="f" data-s="miss" aria-pressed="true">미획득 (달성 가능)</button>
    <button class="f" data-s="own">획득</button>
    <button class="f" data-s="blocked">사실상 불가</button>
    <button class="f" data-s="unreach">경로 없음</button>
    <button class="f" id="runf" data-s="run" hidden>이번 회차에 가능</button>
  </div>
  <div class="bar"><span class="lbl">루트</span><span id="tagbar"></span></div>
  <div class="bar">
    <input id="q" placeholder="이름 · 조건 · 인물 · 장소 검색 (예: 소사매, 온천, 도덕)">
    <button class="f" id="expand">모두 펼치기</button>
    <button class="f" id="reset">필터 해제</button>
  </div>
  <div class="stats" id="stats"></div>
  </div>
</header>
<main>
  <div id="list"></div>
  <div id="bundles" hidden></div>
  <div id="run" hidden></div>
  <div id="goal" hidden></div>
  <div id="events" hidden></div>
  <div id="wiki" hidden></div>
</main>
<script id="data" type="application/json">__DATA__</script>
<script id="evdata" type="application/json">__EVENTS__</script>
<script id="pqdata" type="application/json">__PREREQ__</script>
<script id="rundata" type="application/json">__RUN__</script>
<script id="inhdata" type="application/json">__INHERIT__</script>
<script id="fkdata" type="application/json">__FORKS__</script>
<script id="rfdata" type="application/json">__ROUTEFORKS__</script>
<script id="wkdata" type="application/json">__WIKI__</script>
<script>
const THKEY='hwal-theme-v1';
const THEMES=[['auto','시스템 테마'],['light','라이트'],['dark','다크']];
let theme='auto';
try { theme = localStorage.getItem(THKEY) || 'auto'; } catch(e){}
function applyTheme(){
  const r=document.documentElement;
  if(theme==='auto') r.removeAttribute('data-theme'); else r.setAttribute('data-theme',theme);
  const b=document.getElementById('theme');
  const t=THEMES.find(x=>x[0]===theme);
  if(b) b.textContent = (theme==='dark'?'🌙 ':theme==='light'?'☀️ ':'🖥 ')+t[1];
}
applyTheme();
document.getElementById('theme').addEventListener('click',()=>{
  const i=THEMES.findIndex(x=>x[0]===theme);
  theme=THEMES[(i+1)%THEMES.length][0];
  try { localStorage.setItem(THKEY,theme); } catch(e){}
  applyTheme();
});

const D = JSON.parse(document.getElementById('data').textContent);
const list = document.getElementById('list');
let fType='all', fStat='miss', query='', fTag='';

const CKKEY='hwal-run-check-v1';
let CK = {};
try { CK = JSON.parse(localStorage.getItem(CKKEY) || '{}'); } catch(e) { CK = {}; }
function saveCK(){ try { localStorage.setItem(CKKEY, JSON.stringify(CK)); } catch(e){} }
function ckBox(id){ return '<input type="checkbox" class="ck" data-ck="'+id+'"'+(CK[id]?' checked':'')+'>'; }
function ckCount(){ return Object.values(CK).filter(Boolean).length; }

const esc = s => (s??'').toString().replace(/[&<>]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const BSN = String.fromCharCode(92)+'n';
const escn = s => esc(s).split(BSN).join('<br>');
const TCLS = {'생사부':'tp1','한청서':'tp2','풍운사':'tp3'};

const PQ = JSON.parse(document.getElementById('pqdata').textContent);
// 세이브 판정. 브라우저는 file:// 에서 세이브를 못 읽으므로 구울 때 심는다.
// save_read.save_verdicts() 가 만든 것이라, 리더와 웹이 같은 판정을 쓴다.
const RUN = JSON.parse(document.getElementById('rundata').textContent);
const RB = {'가능':'r-ok','심계':'r-heart','지남':'r-past','불가':'r-no','시트불가':'r-no'};
const RLBL = {'가능':'이번 회차 가능','심계':'심계를 바꿔야','지남':'시점 지남',
              '불가':'이 회차 갈래로는 불가','시트불가':'시트가 불가라 함'};
function runOf(it){ return (RUN && RUN.items) ? RUN.items[String(it.id)] : null; }
// 쌓이기만 하는 값들. 지금 얼마고 다음 문턱이 얼마인지. 문턱은 조건문 전체에서 모은 것이고,
// 괄호 안은 그중 아직 못 딴 도감이 요구하는 값이다.
function trackLine(){
  const T = (RUN && RUN.track) || [];
  if(!T.length) return '';
  return '<span class="trackline">' + T.map(t=>{
    const nx = t.next===null||t.next===undefined
        ? '<span class="ok">문턱 전부 넘김</span>'
        : '<span class="dim">→ 다음 '+t.next+'</span>';
    const lib = t.lib && t.lib.length ? ' <span class="dim">(도감 '+t.lib.join('·')+')</span>' : '';
    return esc(t.name)+' <b>'+t.cur+'</b> '+nx+lib;
  }).join('<span class="dim"> · </span>') + '</span>';
}
function pqOf(it){ return PQ.items[String(it.id)] || []; }
// 일부 경로만 그 인물을 요구하는 경우. 「맞아 죽다」는 21개 경로 중 하나만 하후란
// 호감도를 보는데, 예전에는 항목 전체가 하후란 전용으로 보였다.
function pqSomeOf(it){ return (PQ.partial||{})[String(it.id)] || {}; }
function pqBadge(it){
  const n = pqOf(it), some = pqSomeOf(it);
  let h = '';
  if(n.length)
    h += '<button class="pq" data-pq="'+it.id+'" title="이 인물이 먼저 당문에 있어야 한다">'
       + '선행 · '+n.join('+')+'</button>';
  Object.entries(some).forEach(([name, c])=>{
    h += '<button class="pq some" data-pq="'+it.id+'" title="경로 '+c[1]+'개 중 '+c[0]
       + '개만 이 인물을 요구한다. 나머지 경로로도 딸 수 있다.">'
       + '일부 경로 · '+esc(name)+' ('+c[1]+'개 중 '+c[0]+')</button>';
  });
  return h;
}
function pqBoxes(it){
  const some = pqSomeOf(it);
  return [...pqOf(it), ...Object.keys(some)].map(name=>{
    const c = PQ.chars[name]; if(!c) return '';
    const p = some[name];
    return '<div class="pqbox"><h5>'
      + (p ? '일부 경로만 — '+esc(name)+'을(를) 요구한다'
           : '선행 조건 — '+esc(name)+'을(를) 먼저 확보해야 한다')+'</h5>'
      + (p ? '<div>경로 <b>'+p[1]+'개 중 '+p[0]+'개</b>만 '+esc(name)
             + ' 호감도를 본다. <b>나머지 경로로도 딸 수 있다.</b></div>' : '')
      + '<div>이 경로는 <b>'+esc(name)+' 호감도</b>를 요구한다. 그런데 호감도를 올리려면 그 전에 '
      + '<code>'+esc(c.flagKo)+'</code> 상태가 되어 있어야 한다.</div>'
      + '<ul>'+c.how.map(h=>'<li>'+esc(h)+'</li>').join('')+'</ul>'
      + '<div class="pqmeta">플래그 '+esc(c.flag)+' · 세우는 사건 '+esc(c.by)
      + ' · 시기 '+esc(c.when)+(c.sure?'':' · 미션 조건이 따로 없는 메인 스토리 흐름이라 확정도가 낮다')
      + '</div></div>';
  }).join('');
}

function stepHTML(s){
  const cls = s.k==='선택지' ? 'k sel' : 'k';
  let t = esc(s.text);
  if(s.k==='조건'||s.k==='그 외') t = '<code>'+t+'</code>';
  if(s.k==='주사위'){
    t = esc(s.text) + (s.th? ' <code>주사위 '+esc(s.th)+'</code>':'');
    if(s.props) t += ' <span class="small">(판정: '+esc(s.props)+')</span>';
  }
  return '<div class="step"><div class="'+cls+'">'+esc(s.k)+'</div><div class="txt">'+t+'</div></div>';
}
function entryHTML(e, depth){
  if(e.type==='free'){
    let h = '<div class="entry">자유행동 <b>'+esc(e.label)+'</b> → 결과 <b>'+esc(e.result)+'</b>';
    if(e.rate!=null) h += ' <span class="rate">가중치 '+e.rate+'</span>';
    if(e.cond) h += '<br><span class="small">발생 조건: <code>'+esc(e.cond)+'</code></span>';
    return h + '</div>';
  }
  let h = '<div class="entry">앞 장면 <code>'+esc(e.label)+'</code>'
        + (e.kind==='combat'?' <span class="small">(전투로 진입)</span>':'')
        + (e.summary? '<div class="sum">'+escn(e.summary)+'</div>':'') + '</div>';
  if(e.steps && e.steps.length) h += '<div class="path">'+e.steps.map(stepHTML).join('')+'</div>';
  if(depth<2 && e.up && e.up.length) h += e.up.slice(0,2).map(u=>entryHTML(u,depth+1)).join('');
  return h;
}
const VIA = {'GameOver':'사망','combat':'전투 패배 시 사망','ending':'엔딩 진입','achievement':'업적 달성','cg':'결말 그림'};
function badgeOf(it){
  const base = it.owned ? '<span class="badge b-own">획득</span>'
       : (!it.reachable ? '<span class="badge b-no">경로 없음</span>'
       : (it.blocked ? '<span class="badge b-blk">사실상 불가</span>'
                     : '<span class="badge b-miss">미획득</span>'));
  const r = it.owned ? null : runOf(it);
  if(!r) return base;
  const tip = r.why ? ' title="'+esc(r.why)+'"' : '';
  return base + '<span class="badge '+(RB[r.b]||'r-no')+'"'+tip+'>'+RLBL[r.b]+'</span>';
}
function bodyInner(it){
  let b = '';
  b += '<div class="desc">'+escn(it.desc)+'</div>';
  if(it.tags && it.tags.length)
    b += '<div class="tags">'+it.tags.map(t=>'<span class="tg" data-tag="'+esc(t)+'">'+esc(t)+'</span>').join('')+'</div>';
  b += pqBoxes(it);
  if(it.blocked)
    b += '<div class="blk"><b>사실상 획득 불가</b><br>'
       + it.blockReason.map(esc).join('<br>')
       + '<br><span class="small">조건에 쓰이는 플래그를 세팅하는 스크립트·데이터가 게임 안에 없다. 미구현이거나 잘려나간 루트로 보인다.</span></div>';
  if(!it.paths.length){
    b += '<div class="none">이 항목으로 가는 경로가 게임 스크립트에 존재하지 않는다. (현재 빌드 기준 획득 불가)</div>';
  } else {
    b += '<h4>도달 경로 '+it.paths.length+'개</h4>';
    it.paths.forEach((p,i)=>{
      b += '<div class="path">';
      b += '<div class="small">경로 '+(i+1)+' · 장면 <code>'+esc(p.script)+'</code></div>';
      if(p.summary) b += '<div class="sum">'+escn(p.summary)+'</div>';
      if(p.origin){
        const o=p.origin;
        let line='<div class="org"><span class="orgk">'+esc(o.kind)+'</span>';
        if(o.when)  line += '<b>'+esc(o.when)+'</b>';
        if(o.where) line += '<b>'+esc(o.where)+'</b>';
        if(!o.when && !o.where) line += '<span class="small">시작 장면 <code>'+esc(o.via)+'</code></span>';
        if(o.guess) line += '<span class="guess">(이름 규칙 추정)</span>';
        if(o.rootOnly) line += '<span class="guess">(시점 데이터 없음 — 흐름 시작점만)</span>';
        b += line + '</div>';
        if(o.summary) b += '<div class="sum">'+escn(o.summary)+'</div>';
        if(o.conds && o.conds.length)
          b += '<div class="orgc">발생 조건: '+o.conds.map(c=>'<code>'+esc(c)+'</code>').join(' · ')+'</div>';
      }
      const ov=(it.opts||[])[i];
      if(ov && ov.via){
        const bits=[];
        if(ov.via.choices && ov.via.choices.length) bits.push('고르기: '+ov.via.choices.map(c=>'「'+esc(c)+'」').join(' → '));
        (ov.via.dice||[]).forEach(d=>{ bits.push('주사위'+(d.props? ' + '+esc(d.props):'')+' '+esc(d.th)+' → 「'+esc(d.text)+'」'); });
        b += '<div class="orgc"><b>반드시 거치는 앞 장면</b> <code>'+ov.via.at.map(esc).join(', ')+'</code> — 여기서만 이 항목의 조건('+esc(ov.via.flag)+' = '+ov.via.val+')이 선다. 아래 갈래 중 이 장면을 지나는 길만 통한다.'+(bits.length? '<br>'+bits.join(' · '):'')+'</div>';
      }
      (p.entries||[]).slice(0,3).forEach(e=>{ b += entryHTML(e,0); });
      if(p.steps.length) b += p.steps.map(stepHTML).join('');
      b += '<div class="end">→ '+esc(VIA[p.via]||p.via)+(p.combat? ' <code>'+esc(p.combat)+'</code>':'')+'</div>';
      if(p.combatDesc) b += '<div class="small">'+esc(p.combatDesc)+'</div>';
      b += '</div>';
    });
  }
  if(it.sheet && it.sheet.cond)
    b += '<div class="sheet"><b>커뮤니티 시트(참고, 미검증)</b><br>'+esc(it.sheet.cond)+'</div>';
  return b;
}
// 커뮤니티 시트처럼 「어떻게 따나」를 한 줄로. 카드를 안 펴고도 흐름이 보이게.
const VIA_KO = {combat:'전투 패배', GameOver:'그 장면에서 사망', ending:'엔딩', death:'사망'};
function howLine(it){
  const i = it.opts.findIndex(o=>o===pickOpt(it, curRoute));
  const o = i>=0 ? it.opts[i] : it.opts[0];
  const p = i>=0 ? it.paths[i] : it.paths[0];
  if(!o || !p) return '';
  const bits = [];
  // 언제·어디서
  const og = p.origin || {};
  const when = o.when || og.when || o.estText || '';
  let where = o.where || og.where || '';
  // Travel_S2501_01 같은 내부 이름은 장소가 아니다. 사람이 읽을 것만 남긴다.
  if(/^[A-Za-z][\w]*$/.test(where)) where = '';
  const head = [when, where].filter(Boolean).join(' · ');
  // 무슨 장면인가 — 「장소 · 인물 — 무슨 일」 에서 뒷부분만 쓴다
  let sc = og.summary || p.summary || '';
  const dash = sc.indexOf(' — ');
  if(dash > 0) sc = sc.slice(dash + 3);
  sc = sc.replace(/\s+/g,' ').trim();
  if(sc.length > 46) sc = sc.slice(0,45) + '…';
  if(sc) bits.push(sc);
  // 그 시점에만 필요한 심계. 회차 심계와 달라도 되므로 상충 판정에는 안 넣고 글로만 알린다.
  if(o.loverLater) bits.push('⚠ '+o.loverLater);
  // 무엇을 고르고 무엇에 지나
  // 원문이 중국어로 남은 선택지, 「N번째 결과」 같은 자리표시는 적어야 도움이 안 된다.
  const HAN = /[一-鿿]/;
  const useful = t => t && !HAN.test(t) && !/^\d+번째 결과$/.test(t) && t!=='?';
  const push = st => {
    const t = String(st.text||'').trim();
    if(st.k==='선택지'){ if(useful(t)) bits.push('「'+t.slice(0,24)+'」'); }
    else if(st.k==='주사위'){
      const th = st.th ? ' '+st.th : '';
      bits.push(useful(t) ? '주사위 '+t.slice(0,16)+th : ('주사위'+th));
    }
  };
  (p.entries||[]).slice(0,1).forEach(e=>{ (e.steps||[]).forEach(st=>{ if(bits.length<4) push(st); }); });
  (p.steps||[]).forEach(st=>{ if(bits.length<5) push(st); });
  if(p.combatDesc) bits.push(p.combatDesc+' 패배');
  else if(VIA_KO[p.via]) bits.push(VIA_KO[p.via]);
  // 조건 두 개까지
  // 같은 스탯에 서로 반대되는 조건이 함께 잡히면 그 장면 안의 다른 갈래가 섞인 것이다.
  // 어느 쪽이 이 항목의 조건인지 모르므로 그 스탯은 통째로 뺀다.
  const flat = (o.reqs||[]).filter(r=>!r.any);
  const side = r => (r.op==='>='||r.op==='>') !== !!r.neg ? '>' : ((r.op==='<='||r.op==='<') !== !!r.neg ? '<' : '=');
  const mixed = new Set();
  flat.forEach(a=>flat.forEach(b=>{ if(a.stat===b.stat && side(a)!==side(b)) mixed.add(a.stat); }));
  const req = [];
  flat.forEach(r=>{
    if(req.length>=2 || mixed.has(r.stat)) return;
    if(r.stat==='마음에 둔 사람'){ req.push('심계 '+(LOVER_NAME[r.val]||r.val)+(r.neg||r.op!=='=='?' 아님':'')); return; }
    req.push(r.stat+' '+(r.neg?FLIPTXT[r.op]||r.op:r.op)+r.val);
  });
  const tail = req.length ? ' <span class="hreq">· '+esc(req.join(' · '))+'</span>' : '';
  if(!bits.length && !head) return '';
  return '<div class="how">'+(head?'<b>'+esc(head)+'</b> — ':'')+esc(bits.join(' → '))+tail+'</div>';
}
const FLIPTXT = {'>=':'<','<=':'>','>':'<=','<':'>=','==':'≠','!=':'='};

function cardHTML(it){
  const badge = badgeOf(it);
  const b = '<div class="body">'+bodyInner(it)+'</div>';
  const org = (it.paths.find(p=>p.origin && (p.origin.when||p.origin.where))||{}).origin;
  const chip = org ? '<span class="when">'+esc([org.when,org.where].filter(Boolean).join(' · '))+'</span>' : '';
  return '<div class="card'+(CK[it.id]?' done':'')+'" data-id="'+it.id+'">'
    + '<div class="head">'+ckBox(it.id)+'<span class="tp '+(TCLS[it.type]||'')+'">'+esc(it.type)+'</span>'
    + '<span class="no">#'+it.no+'</span>'
    + '<span class="title">'+escn(it.title)+'</span>'+chip+pqBadge(it)+badge+'</div>'
    + howLine(it) + b + '</div>';
}
function match(it){
  if(fType!=='all' && it.type!==fType) return false;
  if(fStat==='miss' && (it.owned || it.blocked || !it.reachable)) return false;
  if(fStat==='blocked' && !it.blocked) return false;
  if(fStat==='own' && !it.owned) return false;
  if(fStat==='unreach' && it.reachable) return false;
  // 이번 회차 필터: 지났거나 갈래가 달라 못 따는 것은 아예 빼고 본다
  if(fStat==='run'){
    if(it.owned || it.blocked || !it.reachable) return false;
    const r = runOf(it);
    if(!r || r.b !== '가능') return false;
  }
  if(fTag && !(it.tags||[]).includes(fTag)) return false;
  if(!query) return true;
  return JSON.stringify(it).toLowerCase().includes(query);
}
function render(){
  const rows = D.items.filter(match);
  list.innerHTML = rows.map(cardHTML).join('') || '<div class="none">결과 없음</div>';
  const byT = {};
  rows.forEach(r=>{ byT[r.type]=(byT[r.type]||0)+1; });
  const miss = rows.filter(r=>!r.owned && r.reachable && !r.blocked).length;
  document.getElementById('stats').innerHTML =
      '표시 <b>'+rows.length+'</b>'
    + ' (생사부 <b>'+(byT['생사부']||0)+'</b> · 한청서 <b>'+(byT['한청서']||0)+'</b> · 풍운사 <b>'+(byT['풍운사']||0)+'</b>)'
    + ' · 그중 달성 가능한 미획득 <b>'+miss+'</b>'
    + ' · 전체 획득 <b>'+D.stats.owned+'</b>/'+D.stats.total
    + (RUN ? '<span class="runline">세이브 <b>'+esc(RUN.when)+'</b>'
             + (RUN.lover ? ' · 심계 '+esc(RUN.lover) : '')
             + ' — 이번 회차 가능 <b class="ok">'+RUN.counts['가능']+'</b>'
             + ' · 시점 지남 '+RUN.counts['지남']
             + ' · 갈래가 달라 불가 '+RUN.counts['불가']
             + trackLine() + '</span>' : '');
}
const tagCount = {};
D.items.forEach(i=>(i.tags||[]).forEach(t=>tagCount[t]=(tagCount[t]||0)+1));
const ROUTES = ['소사매','엽운상','용상','우소매','하후란','욱죽','위국','상관형',
                '대사형','이사형','삼사형','사사형','엽운주','복운','금오상인',
                '공동파','청성파','아미파','금향궁','서무림맹','당문'];
document.getElementById('tagbar').innerHTML = ROUTES.filter(t=>tagCount[t])
  .map(t=>'<button class="f tag" data-tag="'+t+'">'+t+' <span class="small">'+tagCount[t]+'</span></button>').join(' ');

function setTag(t){
  fTag = (fTag===t) ? '' : t;
  document.querySelectorAll('button.tag').forEach(b=>b.setAttribute('aria-pressed', b.dataset.tag===fTag));
  render();
}
document.getElementById('tagbar').addEventListener('click', e=>{
  const b=e.target.closest('button.tag'); if(b) setTag(b.dataset.tag);
});
function bindChecks(root){
  root.addEventListener('change', e=>{
    const b = e.target.closest('input.ck');
    if(!b) return;
    CK[b.dataset.ck] = b.checked;
    saveCK();
    const row = b.closest('.trow'); if(row) row.classList.toggle('done', b.checked);
    const card = b.closest('.card'); if(card) card.classList.toggle('done', b.checked);
    updateCkLabel();
  });
  root.addEventListener('click', e=>{ if(e.target.closest('input.ck')) e.stopPropagation(); }, true);
}
function updateCkLabel(){
  const el=document.getElementById('ckinfo');
  document.querySelectorAll('.ckinfo, #ckinfo').forEach(el=>{
    el.innerHTML = '이번 런 목표 <span class="ckcount">'+ckCount()+'</span>개';
  });
  if(!gwrap.hidden) renderGoal();
}
list.addEventListener('click', e=>{
  const tg = e.target.closest('.tg');
  if(tg){ setTag(tg.dataset.tag); window.scrollTo(0,0); return; }
  const h = e.target.closest('.head'); if(!h) return;
  h.parentElement.classList.toggle('open');
});
document.querySelectorAll('button.f[data-t]').forEach(b=>b.addEventListener('click',()=>{
  fType=b.dataset.t;
  document.querySelectorAll('button.f[data-t]').forEach(x=>x.setAttribute('aria-pressed', x===b));
  render();
}));
document.querySelectorAll('button.f[data-s]').forEach(b=>b.addEventListener('click',()=>{
  fStat=b.dataset.s;
  document.querySelectorAll('button.f[data-s]').forEach(x=>x.setAttribute('aria-pressed', x===b));
  render();
}));
if(RUN){ const rb=document.getElementById('runf'); if(rb) rb.hidden=false; }
document.getElementById('q').addEventListener('input', e=>{ query=e.target.value.trim().toLowerCase(); render(); });
document.getElementById('expand').addEventListener('click', ()=>{
  const any = list.querySelector('.card:not(.open)');
  list.querySelectorAll('.card').forEach(c=> c.classList.toggle('open', !!any));
});
document.getElementById('reset').addEventListener('click', ()=>{
  fType='all'; fStat='miss'; fTag=''; query='';
  document.getElementById('q').value='';
  document.querySelectorAll('button.f[data-t]').forEach(x=>x.setAttribute('aria-pressed', x.dataset.t==='all'));
  document.querySelectorAll('button.f[data-s]').forEach(x=>x.setAttribute('aria-pressed', x.dataset.s==='miss'));
  document.querySelectorAll('button.tag').forEach(x=>x.setAttribute('aria-pressed', false));
  render();
});
// ================= 묶음 지도 =================
const bwrap = document.getElementById('bundles');
let bOnlyMiss = true;
function condText(cs){
  const uniq=[...new Set(cs)];
  let shown=uniq.slice(0,2).map(c=> c.length>90 ? c.slice(0,90)+'…' : c);
  let t=shown.map(esc).join('  또는  ');
  if(uniq.length>2) t += ' <span class="small">외 '+(uniq.length-2)+'가지</span>';
  return t;
}
function bundleHTML(b){
  const kinds = Object.entries(b.kinds).map(([k,v])=>'<span class="pill p-kind">'+esc(k)+' '+v+'</span>').join(' ');
  const flag = b.saveable
    ? '<span class="pill p-save">세이브 후 분기 가능</span>'
    : '<span class="pill p-lock">이전 세이브 필요</span>';
  const when = [b.when,b.where].filter(Boolean).join(' · ');
  let h = '<div class="bcard">';
  h += '<div class="bhead"><span class="bn">'+b.miss+'<small> / '+b.total+'</small></span>';
  h += '<span class="small">미획득 / 이 지점에서 갈리는 전체</span>';
  h += flag + kinds + '</div>';
  h += '<div class="bhead">';
  if(when) h += '<span class="when">'+esc(when)+'</span>';
  h += '<code>'+esc(b.script)+'</code></div>';
  if(b.summary) h += '<div class="sum">'+escn(b.summary)+'</div>';
  h += '<div class="bbar">'+b.items.map(i=>'<div class="seg'+(i.owned||i.blocked?'':' miss')+'" title="'+esc(i.title)+'"></div>').join('')+'</div>';
  h += b.items.map(i=>'<div class="brow"><span class="mk">'+(i.owned?'✅':(i.blocked?'🚫':'⬜'))+'</span>'
      + '<span class="tp '+(TCLS[i.type]||'')+'">'+esc(i.type)+'</span>'
      + '<span class="bt"><b>#'+i.no+'</b> '+escn(i.title)+'</span>'
      + '<span class="bc">'+condText(i.conds)+'</span></div>').join('');
  return h + '</div>';
}
function renderBundles(){
  const rows = D.bundles.filter(b=> bOnlyMiss ? b.miss>=2 : true);
  const saveable = rows.filter(b=>b.saveable).length;
  bwrap.innerHTML =
      '<div class="hint">'
    + '<b>읽는 법</b> — 큰 숫자는 <b>이 한 장면에서 갈리는 미획득 개수</b>다. 막대는 항목 하나가 칸 하나이고, 색칠된 칸이 아직 못 본 것.<br>'
    + '<span class="pill p-save">세이브 후 분기 가능</span> 선택지·주사위로 갈리므로 <b>직전에 세이브하고 로드하며 여러 개를 회수</b>할 수 있다.<br>'
    + '<span class="pill p-lock">이전 세이브 필요</span> 루트 플래그·스탯으로 갈리므로, 그 값이 정해지기 <b>전</b>으로 돌아가야 한다.'
    + '</div>'
    + '<div class="bar"><span class="lbl">보기</span>'
    + '<button class="f" id="bfilter" aria-pressed="'+bOnlyMiss+'">미획득 2개 이상만</button>'
    + '<span class="small">표시 '+rows.length+'개 · 그중 세이브 분기 가능 '+saveable+'개</span></div>'
    + (rows.map(bundleHTML).join('') || '<div class="none">결과 없음</div>');
  document.getElementById('bfilter').addEventListener('click', ()=>{ bOnlyMiss=!bOnlyMiss; renderBundles(); });
}
// ================= 런 플래너 =================
const rwrap = document.getElementById('run');
const OPEN_ROUTES = ['소사매','엽운상','용상','하후란'];
const DEAD_ROUTES = ['우소매','욱죽','위국','상관형','서행'];
let curRoute='소사매', runMissOnly=true, hideDone=false, autoRunPick=null;
function pickOpt(it, route){
  const cand = it.opts.filter(o=> o.req.length===0 || o.req.includes(route));
  if(!cand.length) return null;
  const exact = cand.filter(o=>o.wk!=null).sort((a,b)=>a.wk-b.wk);
  if(exact.length) return exact[0];
  const est = cand.filter(o=>o.wkEst!=null).sort((a,b)=>a.wkEst-b.wkEst);
  if(est.length) return est[0];
  const always = cand.filter(o=>o.timeKind==='상시');
  return always[0] || cand[0];
}
function sortKey(o){
  if(o.wk!=null) return o.wk;
  if(o.wkEst!=null) return o.wkEst + 0.5;   // 같은 시점이면 추정을 뒤로
  return o.timeKind==='상시' ? 900000 : 999999;
}
function renderRun(){
  const allPicked=[];
  D.items.forEach(it=>{
    if(!it.reachable || it.blocked) return;
    if(runMissOnly && it.owned) return;
    if(hideDone && CK[it.id]) return;
    const o=pickOpt(it, curRoute);
    if(o) allPicked.push({it,o});
  });
  // 묶음은 항상 전체로 계산한다. 한 회차만 볼 때 묶음이 다시 갈라지면 안 되기 때문.
  const runInfo = autoRuns(allPicked);
  if(autoRunPick!=null && !runInfo.runs[autoRunPick]) autoRunPick = null;
  const picked = autoRunPick!=null ? runInfo.runs[autoRunPick].map(nd=>nd.x) : allPicked;
  // 시점 -> 장면 -> 항목
  const byWhen = new Map();
  picked.forEach(({it,o})=>{
    const key = sortKey(o);
    if(!byWhen.has(key)) byWhen.set(key, new Map());
    const sc = byWhen.get(key);
    const label = o.script;
    if(!sc.has(label)) sc.set(label, {o, items:[]});
    sc.get(label).items.push({it, req:o.req, reqs:o.reqs, upReqs:o.upReqs});
  });
  const keys=[...byWhen.keys()].sort((a,b)=>a-b);
  let html='';
  html += '<div class="hint"><b>이 런에서 볼 수 있는 것</b>을 시간순으로 세운 트리다. '
        + '루트를 고르면 그 루트에서 <b>불가능한 항목은 빠진다</b>. '
        + '한 장면에 2개 이상이 걸려 있고 선택지·주사위로 갈리면 '
        + '<span class="p-save2">세이브 포인트</span>로 표시된다 — 거기서 저장하고 되돌리며 여러 개를 회수할 수 있다.'
        + '<br><b>이 시점까지 필요</b>는 그 장면의 분기에 직접 걸린 수치, <b>그 전에 미리</b>는 거기까지 오는 길목(최대 6단계 위)에 걸린 수치다. '
        + '<b>수치 조건 없음</b>이면 우리가 훑은 범위 안에 능력치 조건이 없었다는 뜻이다.</div>';
  html += '<div class="bar"><span class="lbl">루트</span>'
        + OPEN_ROUTES.map(r=>'<button class="f rbtn rt" data-r="'+r+'" aria-pressed="'+(r===curRoute)+'">'+r+'</button>').join('')
        + '<button class="f rbtn rt" data-r="솔로" aria-pressed="'+(curRoute==='솔로')+'">솔로(무루트)</button>'
        + '<span class="small">· 우소매·욱죽·위국·상관형·서행 루트는 플래그 미구현이라 제외</span></div>';
  html += '<div class="bar"><button class="f" id="rmiss" aria-pressed="'+runMissOnly+'">미획득만</button>'
        + '<button class="f" id="rhide" aria-pressed="'+hideDone+'">체크한 건 숨기기</button>'
        + '<button class="f" id="rreset">체크 초기화</button>'
        + '<span class="small" id="ckinfo"></span>'
        + '<span class="small">· 표시 '+picked.length+'개 · 시점 확보 '
        + picked.filter(x=>x.o.wk!=null).length+'개</span>'
        + (autoRunPick!=null
            ? '<span class="p-save2">'+(autoRunPick+1)+'회차만 보는 중</span>'
              + '<button class="f arun" data-i="">전체 보기</button>'
            : '')
        + '</div>';
  html += autoRunsHTML(runInfo, autoRunPick);
  html += prereqRunHTML(picked);
  html += forksHTML(picked);
  // ---- 수치 계획 ----
  // 노드에 직접 걸린 조건(reqs)과 거기 오는 길목에 걸린 조건(upReqs)을 함께 모은다.
  // upReqs 를 빼먹으면 카드에는 보이는데 상단 요약·계승 계획에는 안 잡힌다.
  const agg = new Map();
  const anyAgg = new Map();   // 'A 또는 B' 택일 그룹. 상충 검사와 계승 계획에서는 제외한다.
  picked.forEach(({it,o})=>{
    [['node', o.reqs], ['up', o.upReqs]].forEach(([kind, list])=>{
      (list||[]).forEach(r=>{
        if(r.any){
          const key = r.any.map(a=>a.stat+' '+a.op+' '+a.val).join(' 또는 ');
          if(!anyAgg.has(key)) anyAgg.set(key, {alts:r.any, items:[], when:null, up:kind==='up'});
          const e = anyAgg.get(key);
          if(kind==='node') e.up = false;
          if(!e.items.some(x=>x.id===it.id)) e.items.push(it);
          const w0 = o.wk!=null?o.wk:(o.wkEst!=null?o.wkEst:null);
          if(w0!=null && (e.when==null || w0<e.when)) e.when=w0;
          return;
        }
        if(r.neg) return;
        if(!agg.has(r.stat)) agg.set(r.stat, new Map());
        const k = r.op+' '+r.val;
        if(!agg.get(r.stat).has(k))
          agg.get(r.stat).set(k, {op:r.op, val:r.val, items:[], when:null, up:true});
        const e = agg.get(r.stat).get(k);
        if(kind==='node') e.up = false;
        if(!e.items.some(x=>x.id===it.id)) e.items.push(it);
        const w = o.wk!=null?o.wk:(o.wkEst!=null?o.wkEst:null);
        if(w!=null && (e.when==null || w<e.when)) e.when=w;
      });
    });
  });
  const fmtW = k => k==null? '' : Math.floor(k/1000)+'년차 '+Math.floor((k%1000)/10)+'월';
  const order = [...agg.entries()].sort((a,b)=>{
    const lover = x => x[0]==='마음에 둔 사람' ? 1 : 0;
    if(lover(a)!==lover(b)) return lover(a)-lover(b);
    const n=x=>[...x[1].values()].reduce((s,e)=>s+e.items.length,0);
    return n(b)-n(a);
  });
  // 상충 판정: 같은 스탯에 위/아래 요구가 같이 걸린 경우.
  // 다만 두 요구의 시점이 다르면 순차적으로 맞출 수 있으므로 경고를 낮춘다.
  const cdir = e => (e.op==='>='||e.op==='>') ? 'hi' : (e.op==='<='||e.op==='<') ? 'lo' : null;
  const clash = order.map(([stat,m])=>{
    const es=[...m.values()];
    const hi=es.filter(e=>cdir(e)==='hi'), lo=es.filter(e=>cdir(e)==='lo');
    if(!hi.length || !lo.length) return null;
    const mw = xs => xs.reduce((a,e)=>(e.when!=null && (a==null||e.when<a))?e.when:a, null);
    const hw=mw(hi), lw=mw(lo);
    const seq = hw!=null && lw!=null && hw!==lw;   // 시점을 모르면 상충으로 본다(안전한 쪽)
    return {stat, es:es.sort((a,b)=>b.val-a.val), seq};
  }).filter(Boolean);
  const hardC = clash.filter(c=>!c.seq), softC = clash.filter(c=>c.seq);
  const clashRow = c => {
    const wtxt = e => e.when!=null ? ' <span class="when">'+esc(fmtW(e.when))+'</span>' : '';
    return '<div class="prow"><span class="pst">'+esc(c.stat)+'</span><span class="pwho">'
         + c.es.map(e=>'<span class="preq">'+esc(e.op+' '+e.val)+'</span>'+wtxt(e)+' <span class="small">'
           + e.items.slice(0,3).map(i=>esc(i.type[0]+'#'+i.no)).join(', ')
           + (e.items.length>3?' 외 '+(e.items.length-3):'')+'</span>').join('<br>')
         + '</span></div>';
  };
  if(hardC.length){
    html += '<div class="plan"><div class="thead"><span class="tt conf">⚠ 수치 상충 '+hardC.length+'건</span>'
          + '<span class="small">같은 스탯에 위/아래 요구가 같은 시점에 걸려 있다. 한 회차에 둘 다는 불가하니 나눠 잡아야 한다.</span></div>';
    hardC.forEach(c=>{ html += clashRow(c); });
    html += '</div>';
  }
  if(softC.length){
    html += '<div class="plan"><div class="thead"><span class="tt">ℹ 시점이 다른 위/아래 요구 '+softC.length+'건</span>'
          + '<span class="small">같은 스탯이지만 요구 시점이 다르다. 앞 시점을 먼저 맞추고 나중에 값을 옮기면 한 회차에도 된다.</span></div>';
    softC.forEach(c=>{ html += clashRow(c); });
    html += '</div>';
  }
  if(anyAgg.size){
    html += '<div class="plan"><div class="thead"><span class="tt">▸ 택일 조건 '+anyAgg.size+'건</span>'
          + '<span class="small">아래 중 <b>하나만</b> 맞추면 된다. 상충 검사와 계승 계획에서는 제외했다.</span></div>';
    [...anyAgg.entries()].forEach(([key,e])=>{
      html += '<div class="prow"><span class="pst">다음 중 하나</span><span class="pwho">'
            + e.alts.map(a=>'<span class="preq">'+esc(a.stat+' '+a.op+' '+a.val)+'</span>').join(' <span class="small">또는</span> ')
            + (e.up?' <span class="upm">길목</span>':'')
            + (e.when!=null?' <span class="when">'+esc(fmtW(e.when))+'</span>':'')
            + ' <span class="small">'+e.items.slice(0,3).map(i=>esc(i.type[0]+'#'+i.no)).join(', ')
            + (e.items.length>3?' 외 '+(e.items.length-3):'')+'</span></span></div>';
    });
    html += '</div>';
  }
  html += exclusiveHTML(picked);
  html += inheritHTML(order, picked);
  html += '<details class="plan"><summary class="tt" style="cursor:pointer">수치 계획 전체 보기 · 길목 조건 포함 ('+order.length+'종)</summary>';
  if(!order.length) html += '<div class="none">표시된 항목에 수치 조건이 없다.</div>';
  order.forEach(([stat, m])=>{
    const es=[...m.values()];
    const hi=es.some(e=>e.op==='>='||e.op==='>'), lo=es.some(e=>e.op==='<='||e.op==='<');
    const label = stat==='마음에 둔 사람' ? '심계 (루트)' : stat;
    html += '<div class="prow"><span class="pst">'+esc(label)+(hi&&lo?' <span class="conf">⚠ 상충</span>':'')+'</span><span class="pwho">';
    html += es.sort((a,b)=>b.val-a.val).map(e=>
        '<span class="preq">'+esc(e.op+' '+e.val)+'</span> '
      + (e.up? '<span class="upm">길목</span> ':'')
      + (e.when!=null? '<span class="small">('+fmtW(e.when)+'까지) </span>':'')
      + '<span class="small">'+e.items.slice(0,3).map(i=>esc(i.type[0]+'#'+i.no)).join(', ')
      + (e.items.length>3? ' 외 '+(e.items.length-3):'')+'</span>').join('<br>');
    html += '</span></div>';
  });
  html += '</details>';

  let curYear=null;
  keys.forEach(k=>{
    const yr2 = k>=900000 ? null : Math.floor(k/1000);
    const ylabel = k===900000 ? '상시 · 아무 때나 (자유행동)' : (k>=999999 ? '시점 미상' : yr2+'년차');
    if(ylabel!==curYear){ curYear=ylabel; html += '<div class="yr">'+ylabel+'</div>'; }
    const scenes = byWhen.get(k);
    [...scenes.entries()].forEach(([sc, g])=>{
      const saveable = g.items.length>1 && g.o.save;
      g.items.sort((a,b)=> (a.it.type+a.it.no).localeCompare(b.it.type+b.it.no));
      html += '<div class="tnode"><div class="trail"><div class="tdot"></div></div><div class="tbody">';
      const label = g.o.when || g.o.estText || (g.o.timeKind==='상시' ? '아무 때나' : '시점 미상');
      html += '<div class="thead"><span class="tt">'+esc(label)+'</span>';
      if(g.o.timeKind==='추정') html += '<span class="pill p-lock">추정</span>';
      if(g.o.where) html += '<span class="when">'+esc(g.o.where)+'</span>';
      if(saveable) html += '<span class="p-save2">세이브 포인트 · '+g.items.length+'개</span>';
      html += '<code>'+esc(sc)+'</code></div>';
      const sm = (D.items.find(x=>x.paths.some(p=>p.script===sc))||{}).paths?.find(p=>p.script===sc)?.summary;
      if(sm) html += '<div class="sum2">'+escn(sm.slice(0,90))+'</div>';
      const nodeReq = new Map(), upReq = new Map(), anyReq = new Map(), loverReq = new Map();
      g.items.forEach(x=>{
        (x.reqs||[]).forEach(r=>{
          if(r.any){ anyReq.set(r.any.map(a=>a.stat+' '+a.op+' '+a.val).join('|'), r.any); return; }
          if(r.stat==='마음에 둔 사람'){ loverReq.set(r.op+r.val+(r.neg?'!':''), r); return; }
          if(r.neg) return;
          nodeReq.set(r.stat+' '+r.op+' '+r.val, r);
        });
        (x.upReqs||[]).forEach(r=>{
          if(r.any){ anyReq.set(r.any.map(a=>a.stat+' '+a.op+' '+a.val).join('|'), r.any); return; }
          if(r.stat==='마음에 둔 사람'){ loverReq.set(r.op+r.val+(r.neg?'!':''), r); return; }
          if(r.neg) return;
          const k=r.stat+' '+r.op+' '+r.val;
          if(!nodeReq.has(k)) upReq.set(k, r);
        });
      });
      // 같은 스탯·같은 방향은 가장 빡센 값만 남긴다
      const tighten = m => {
        const best = new Map();
        [...m.values()].forEach(r=>{
          const dir = (r.op==='>='||r.op==='>') ? 'hi' : (r.op==='<='||r.op==='<') ? 'lo' : r.op;
          const k = r.stat+'|'+dir;
          const cur = best.get(k);
          if(!cur) { best.set(k, r); return; }
          if(dir==='hi' && r.val>cur.val) best.set(k, r);
          if(dir==='lo' && r.val<cur.val) best.set(k, r);
        });
        return [...best.values()];
      };
      const chips = m => tighten(m).map(r=>'<span class="preq">'+esc(r.stat+' '+r.op+' '+r.val)+'</span>').join(' ');
      if(nodeReq.size)
        html += '<div class="nreq"><span class="nrl">이 시점까지 필요</span>'+chips(nodeReq)+'</div>';
      if(upReq.size)
        html += '<div class="nreq up"><span class="nrl">그 전에 미리</span>'+chips(upReq)+'</div>';
      if(loverReq.size){
        const set = itemLover({o:{reqs:[...loverReq.values()], upReqs:[]}});
        html += '<div class="nreq"><span class="nrl">심계</span><span class="preq">'
              + esc(loverText(set) || '조건 있음') + '</span>'
              + '<span class="small">— 한 회차에 하나뿐이다. 다른 심계를 요구하는 항목과 같이 못 담는다.</span></div>';
      }
      if(anyReq.size)
        html += [...anyReq.values()].map(alts=>
          '<div class="nreq"><span class="nrl">다음 중 하나</span>'
          + alts.map(a=>'<span class="preq">'+esc(a.stat+' '+a.op+' '+a.val)+'</span>').join(' <span class="small">또는</span> ')
          + '</div>').join('');
      if(!nodeReq.size && !upReq.size && !anyReq.size && !loverReq.size)
        html += '<div class="nreq none2"><span class="nrl">수치 조건 없음</span>'
              + '<span class="small">— 선택지·주사위·플래그만으로 갈린다</span></div>';
      g.items.forEach(x=>{
        const it=x.it, req=x.req||[];
        html += '<div class="trow'+(CK[it.id]?' done':'')+'" data-row="'+it.id+'">'+ckBox(it.id)
             + '<span>'+(it.owned?'✅':'⬜')+'</span>'
             + '<span class="tp '+(TCLS[it.type]||'')+'">'+esc(it.type)+'</span>'
             + '<b>#'+it.no+'</b> <span>'+escn(it.title)+'</span>'
             + (req.length? '<span class="small">('+esc(req.join('/'))+' 루트 전용)</span>':'')
             + pqBadge(it)
             + '<span class="small more" data-id="'+it.id+'">자세히 ▾</span>'
             + '</div><div class="det" data-det="'+it.id+'" hidden></div>';
      });
      html += '</div></div>';
    });
  });
  rwrap.innerHTML = html;
  rwrap.querySelectorAll('.more').forEach(el=>el.addEventListener('click', ()=>{
    const d = rwrap.querySelector('[data-det="'+el.dataset.id+'"]');
    if(!d) return;
    if(!d.dataset.filled){
      const it = D.items.find(x=>x.id==el.dataset.id);
      d.innerHTML = bodyInner(it);
      d.dataset.filled = '1';
    }
    d.hidden = !d.hidden;
    el.textContent = d.hidden ? '자세히 ▾' : '접기 ▴';
  }));
  rwrap.querySelectorAll('button.rt').forEach(b=>b.addEventListener('click',()=>{ curRoute=b.dataset.r; autoRunPick=null; renderRun(); }));
  rwrap.querySelectorAll('button.arun').forEach(b=>b.addEventListener('click',e=>{
    e.preventDefault(); e.stopPropagation();
    autoRunPick = b.dataset.i==='' ? null : parseInt(b.dataset.i,10);
    renderRun();
    rwrap.scrollIntoView({block:'start'});
  }));
  const lp = document.getElementById('lpts');
  if(lp) lp.addEventListener('change', ()=>{
    legacyPts = parseInt(lp.value,10)||0;
    try { localStorage.setItem(IHKEY, String(legacyPts)); } catch(e){}
  });
  document.getElementById('rmiss').addEventListener('click', ()=>{ runMissOnly=!runMissOnly; renderRun(); });
  document.getElementById('rhide').addEventListener('click', ()=>{ hideDone=!hideDone; renderRun(); });
  document.getElementById('rreset').addEventListener('click', ()=>{
    if(!confirm('이번 런 체크를 전부 지울까요?')) return;
    CK={}; saveCK(); renderRun();
  });
  updateCkLabel();
}
// 이번 런의 큰 갈림길. forks.json 이 부모/자식 관계를 들고 있어서, 자식 분기를 요구하면서
// 부모를 다른 값으로 못박는 조합을 모순으로 잡아낼 수 있다.
const FORKS = JSON.parse(document.getElementById('fkdata').textContent);
const FKMAP = Object.fromEntries(FORKS.map(f=>[f.id,f]));
// 루트나 심계를 그 사람으로 두는 것 자체가 못박는 분기 (하후란 = 공동파·탈백문·설산행).
// 항목 조건문에는 루트/심계만 적히고 거기까지 간 경위는 안 적히므로 여기서 이어 붙인다.
const RF = JSON.parse(document.getElementById('rfdata').textContent);
const ROUTE_FORKS = RF.routes, LOVER_FORKS = RF.lovers;
// 루트가 심계를 요구하는 경우 (소사매 루트 = 심계 소사매). 길목이 심계를 보기 때문이다.
const ROUTE_LOVER = RF.routeLover || {};
const FLAGWORD = String.fromCharCode(54540,47000,44536);   // 플래그
const BS = String.fromCharCode(92);
const RXO = BS+'[', RXC = BS+']', RXS = BS+'s', RXD = BS+'d';

function forkNeeds(picked){
  // 자동 분배와 같은 추출기를 쓴다. 예전에는 항목 전체를 문자열로 훑어서
  // 이번 런에서 고르지 않은 경로의 분기까지 트리에 올라왔다.
  const need = {};
  picked.forEach(x=>{
    Object.entries(itemForkSets(x)).forEach(([id, vals])=>{
      vals.forEach(v=>{
        if(!need[id]) need[id] = new Map();
        if(!need[id].has(v)) need[id].set(v, []);
        if(!need[id].get(v).some(y=>y.id===x.it.id)) need[id].get(v).push(x.it);
      });
    });
  });
  return need;
}

// ---- 자동 회차 분배 ----------------------------------------------------
// 항목마다 "이 회차가 어떤 모습이어야 하는가"를 뽑고, 서로 못 겹치는 것끼리 색칠하듯 갈라
// 최소 회차 수를 찾는다. 그래프 색칠은 NP-난해라 DSATUR 휴리스틱을 쓴다.

// 이번 런에서 고른 경로(x.o)가 요구하는 분기 값. 항목 전체를 훑으면 다른 경로의 제약까지 끌어온다.
function itemForkSets(x){
  const it = x.it, o = x.o;
  const s = JSON.stringify(o), out = {};
  FORKS.forEach(f=>{
    const re = new RegExp(RXO+FLAGWORD+' '+f.flag+'[^'+RXC+']*'+RXC+RXS+'*=='+RXS+'*(-?'+RXD+'+)','g');
    let m;
    while((m = re.exec(s))) (out[f.id] = out[f.id] || new Set()).add(m[1]);
  });
  // 선행 인물이 분기를 못박는 경우도 있다 (욱죽 = 공동파/철권문, 하후란 = 공동파/탈백문).
  pqOf(it).forEach(c=>{
    const fk = ((PQ.chars||{})[c]||{}).forks;
    if(!fk) return;
    Object.entries(fk).forEach(([id,v])=>{ if(!out[id]) out[id] = new Set([v]); });
  });
  // 마지막이 스크립트 이름으로 추론한 갈래다. 앞의 둘은 게임에서 확인된 사실이라 그쪽이 먼저다.
  if(o && o.branch != null && !out['study']) out['study'] = new Set([o.branch]);
  // 유학 선택 플래그는 값이 시점에 따라 바뀐다. 회의에서 0(잔류)이 되고, 2년 8월 청성행에
  // 들어가는 ch3_3_1_1 이 1로 덮는다. 그래서 조건문의 ==1 은 "회의에서 청성을 골랐다"가
  // 아니라 "청성행을 탔다"는 뜻이고, 잔류(0)와 배타가 아니라 그 하위 상태다.
  if(out['study'] && out['study'].has('1')){
    out['qingcheng'] = new Set(['1']);
    const rest = [...out['study']].filter(v=>v!=='1');
    out['study'] = new Set(rest.length ? rest : ['0']);
  }
  if(o && o.qc != null && !out['qingcheng']) out['qingcheng'] = new Set([o.qc]);
  // 「그 갈래가 아닐 때만」 열리는 경로. 엽운상 루트는 공동파 유학 회차에서 못 탄다 —
  // 이것을 안 보면 새로 풀린 한청서 38 · 풍운사 19 가 공동파 묶음에 같이 담긴다.
  Object.entries((o && o.notBranch) || {}).forEach(([id, badv])=>{
    const rest = (((FKMAP[id]||{}).options)||[]).map(p=>p.v).filter(v=>v!==badv);
    if(!rest.length) return;
    out[id] = out[id] ? new Set([...out[id]].filter(v=>v!==badv)) : new Set(rest);
  });
  // 심계를 한 사람으로 못박는 항목은 그 사람을 만나는 갈래도 함께 못박는다
  const lv = itemLover(x);
  if(lv && lv.size===1)
    Object.entries(LOVER_FORKS[String([...lv][0])] || {}).forEach(([id,v])=>{ out[id] = new Set([v]); });
  // 이 경로가 요구하는 공략 루트가 분기를 못박는 경우 (경로당 루트는 0개 아니면 1개다)
  ((o && o.req) || []).forEach(r=>{
    Object.entries(ROUTE_FORKS[r] || {}).forEach(([id,v])=>{ out[id] = new Set([v]); });
  });
  // 자식 분기를 요구하면 부모도 그 값으로 못박힌다
  let grew = true;
  while(grew){
    grew = false;
    Object.keys(out).forEach(id=>{
      const p = (FKMAP[id]||{}).parent;
      if(!p) return;
      if(!out[p.fork]){ out[p.fork] = new Set([p.v]); grew = true; }
    });
  }
  return out;
}

// 항목이 요구하는 수치 구간. {stat: {lo, hi, when}}
function itemBounds(x){
  const out = {}, w = x.o.wk!=null?x.o.wk:(x.o.wkEst!=null?x.o.wkEst:null);
  [...(x.o.reqs||[]), ...(x.o.upReqs||[])].forEach(r=>{
    if(r.any || r.neg || r.stat==='마음에 둔 사람') return;
    const e = out[r.stat] = out[r.stat] || {lo:null, hi:null, when:w};
    if(r.op==='>=' || r.op==='>'){ const v = r.op==='>'? r.val+1 : r.val; if(e.lo==null||v>e.lo) e.lo=v; }
    if(r.op==='<=' || r.op==='<'){ const v = r.op==='<'? r.val-1 : r.val; if(e.hi==null||v<e.hi) e.hi=v; }
  });
  return out;
}

// 배타 그룹에서 이 항목이 서 있는 쪽
function itemSides(it){
  const out = {}, cs = pqOf(it);
  (PQ.exclusive||[]).forEach(gr=>{
    const hit = gr.options.filter(o=>o.chars.some(c=>cs.includes(c)));
    if(hit.length===1) out[gr.group] = hit[0].name;
  });
  return out;
}

function clashReason(a, b){
  for(const id of Object.keys(a.forks)){
    if(!b.forks[id]) continue;
    const inter = [...a.forks[id]].filter(v=>b.forks[id].has(v));
    if(!inter.length){
      const f = FKMAP[id] || {q:id};
      const nm = v => ((f.options||[]).find(o=>o.v===v)||{}).name || v;
      return (f.flag||id)+' — '+[...a.forks[id]].map(nm).join('/')+' ↔ '+[...b.forks[id]].map(nm).join('/');
    }
  }
  if(a.lover && b.lover){
    const inter = [...a.lover].filter(v=>b.lover.has(v));
    if(!inter.length) return '심계 — '+loverText(a.lover)+' ↔ '+loverText(b.lover);
  }
  for(const g of Object.keys(a.sides))
    if(b.sides[g] && b.sides[g]!==a.sides[g]) return g+' — '+a.sides[g]+' ↔ '+b.sides[g];
  if(a.routes.length && b.routes.length){
    const inter = a.routes.filter(r=>b.routes.includes(r));
    if(!inter.length) return '루트 — '+a.routes.join('/')+' ↔ '+b.routes.join('/');
  }
  for(const st of Object.keys(a.bounds)){
    const x=a.bounds[st], y=b.bounds[st];
    if(!y) continue;
    if(x.when!=null && y.when!=null && x.when!==y.when) continue;
    if(x.lo!=null && y.hi!=null && x.lo>y.hi) return st+' — >= '+x.lo+' ↔ <= '+y.hi;
    if(y.lo!=null && x.hi!=null && y.lo>x.hi) return st+' — >= '+y.lo+' ↔ <= '+x.hi;
  }
  return null;
}

// 심계(마음에 둔 사람)는 크고 작음을 재는 수치가 아니라 택일 값이다. 한 회차에 하나뿐이므로
// 분기(fork)와 같은 방식으로 "허용되는 값의 집합"을 만들어 교집합으로 상충을 본다.
const LOVER_ALL = [0,1,2,3,4,5,6,7,8];
// 값은 「변심의 꿈」의 안내 문구에서 확인했다 (zh-cn 사본이 원문을 그대로 들고 있다):
// 0 唐默铃 소사매 / 1 瑞杏 서행 / 2 叶云裳 엽운상 / 3 虞小梅 우소매 / 4 上官萤 상관형
// 5 夏侯兰 하후란 / 7 魏菊 위국 / 8 龙湘 용상. 6 은 어디서도 세워지지 않는 욱죽 자리다.
const LOVER_NAME = {0:'소사매',1:'서행',2:'엽운상',3:'우소매',4:'상관형',5:'하후란',6:'욱죽',7:'위국',8:'용상'};
function loverText(set){
  if(!set) return '';
  const v = [...set];
  if(v.length===1) return LOVER_NAME[v[0]] || String(v[0]);
  if(v.length===LOVER_ALL.length-1){
    const miss = LOVER_ALL.find(x=>!set.has(x));
    return (LOVER_NAME[miss]||miss)+' 아님';
  }
  return v.map(x=>LOVER_NAME[x]||x).join('/');
}
const QC_LOVER = 2;                         // 청성행 갈림길이 읽는 심계 값 = 엽운상
function itemLover(x){
  // 청성행은 조건 텍스트에 심계가 안 적힌다. ch2_4_9_2 가 Lover_Girl_002 로 갈라서 그렇다.
  let set = x.o.qc === '1' ? new Set([QC_LOVER]) : null;
  // 루트가 심계를 못박는 경우도 조건문에는 안 적힌다
  ((x.o && x.o.req) || []).forEach(r=>{
    if(ROUTE_LOVER[r] === undefined) return;
    const s2 = new Set([ROUTE_LOVER[r]]);
    set = set ? new Set([...set].filter(v=>s2.has(v))) : s2;
  });
  [...(x.o.reqs||[]), ...(x.o.upReqs||[])].forEach(r=>{
    if(r.any) return;                       // 택일 그룹은 건드리지 않는다(가짜 상충 방지)
    if(r.stat!=='마음에 둔 사람') return;
    // 부정 덩어리에 비교가 둘 이상이었으면 드모르간 때문에 이 조건 하나만 뒤집을 수 없다.
    // 심계는 값이 하나뿐이라 잘못 좁히면 가짜 상충이 되므로 그런 것은 버린다.
    if(r.neg && r.solo === false) return;
    // '== N' 이면서 부정이 아니면 그 값이어야 하고, 그 밖에는 그 값이 아니어야 한다
    const eq = (r.op==='==') !== !!r.neg;
    const s = eq ? new Set([r.val]) : new Set(LOVER_ALL.filter(v=>v!==r.val));
    set = set ? new Set([...set].filter(v=>s.has(v))) : s;
  });
  return set;
}

function autoRuns(picked){
  const nodes = picked.map(x=>({
    x, it:x.it, forks: itemForkSets(x), bounds: itemBounds(x),
    // 루트도 분기·심계와 같이 고른 경로 기준이다. 항목 전체(reqRoutes)를 쓰면
    // 루트가 필요 없는 경로를 골랐는데도 다른 경로의 루트 요구가 회차를 제약한다.
    sides: itemSides(x.it), routes: x.o.req || [], lover: itemLover(x)
  }));
  const n = nodes.length;
  if(!n) return {runs:[], n:0, clique:[], why:new Map()};
  const adj = nodes.map(()=>new Set());
  const why = new Map();
  for(let i=0;i<n;i++) for(let j=i+1;j<n;j++){
    const r = clashReason(nodes[i], nodes[j]);
    if(r){ adj[i].add(j); adj[j].add(i); why.set(i+'-'+j, r); }
  }
  const color = new Array(n).fill(-1);
  for(let step=0; step<n; step++){
    let best=-1, bs=-1, bd=-1;
    for(let i=0;i<n;i++){
      if(color[i]>=0) continue;
      const used = new Set([...adj[i]].map(j=>color[j]).filter(c=>c>=0));
      if(used.size>bs || (used.size===bs && adj[i].size>bd)){ bs=used.size; bd=adj[i].size; best=i; }
    }
    const used = new Set([...adj[best]].map(j=>color[j]).filter(c=>c>=0));
    let c=0; while(used.has(c)) c++;
    color[best]=c;
  }
  const runs = [];
  color.forEach((c,i)=>{ (runs[c] = runs[c] || []).push(nodes[i]); });
  runs.sort((a,b)=>b.length-a.length);
  const byDeg = [...Array(n).keys()].sort((a,b)=>adj[b].size-adj[a].size);
  const clique = [];
  byDeg.forEach(i=>{ if(clique.every(j=>adj[i].has(j))) clique.push(i); });
  return {runs, n, clique, why, nodes};
}

function runName(g){
  const bits = [];
  FORKS.forEach(f=>{
    const vals = new Set();
    g.forEach(nd=>{ if(nd.forks[f.id]) [...nd.forks[f.id]].forEach(v=>vals.add(v)); });
    if(vals.size===1){
      const nm = ((f.options||[]).find(o=>o.v===[...vals][0])||{}).name;
      if(nm) bits.push(nm);
    }
  });
  const rs = new Set();
  g.forEach(nd=>{ if(nd.routes.length===1) rs.add(nd.routes[0]); });
  if(rs.size===1) bits.push([...rs][0]+' 루트');
  // 이 묶음이 심계를 하나로 못박는가
  let lv = null;
  g.forEach(nd=>{ if(nd.lover) lv = lv ? new Set([...lv].filter(v=>nd.lover.has(v))) : new Set(nd.lover); });
  if(lv && lv.size && lv.size < LOVER_ALL.length) bits.push('심계 · '+loverText(lv));
  return bits.length? bits.join(' · ') : '제약 없음';
}

function autoRunsHTML(info, sel){
  const {runs, n, clique, why} = info;
  if(!n) return '';
  const proven = clique.length >= runs.length;
  let h = '<div class="plan"><div class="thead"><span class="tt">▸ 자동 회차 분배 — '
        + (proven? '최소 ' : '') + runs.length + '회차'
        + (proven? '' : ' (하한 '+clique.length+')') + '</span>'
        + '<span class="small"><b>이 숫자는 세이브와 무관하다.</b> 도감 전체를 '
        + '「한 회차에 같이 담을 수 있는가」만으로 가른 것이라, 지금 회차에서 실제로 딸 수 있는 '
        + '개수와는 다르다. 그쪽은 <code>도구/run.bat</code> 이 세이브를 읽어 알려준다. '
        + '담긴 '+n+'개를 서로 상충하지 않는 묶음으로 갈랐다. '
        + '분기 트리 모순 · 문파/인물 배타 · 공략 루트 · 수치 위아래(같은 시점)를 모두 따진다. '
        + (proven
            ? '서로 전부 상충하는 '+clique.length+'개조가 있으므로 이보다 줄일 수 없다.'
            : '색칠 휴리스틱 결과라 실제로는 '+clique.length+'회차까지 줄 수 있을지도 모른다.')
        + ' <b>이 회차만 보기</b>를 누르면 아래 계획 전체가 그 묶음만으로 다시 세워진다.</span></div>';
  runs.forEach((g,idx)=>{
    const on = sel===idx;
    h += '<details class="prow arow'+(on?' onrun':'')+'" style="display:block"'+(on?' open':'')+'>'
       + '<summary style="cursor:pointer">'
       + '<span class="pst">'+(idx+1)+'회차</span> '
       + '<span class="preq">'+esc(runName(g))+'</span> '
       + '<span class="small">'+g.length+'개 · 내부 상충 0건</span> '
       + '<button class="f arun" data-i="'+(on?'':idx)+'">'+(on?'전체로 돌아가기':'이 회차만 보기')+'</button>'
       + '</summary>'
       + '<div class="pwho" style="margin-top:6px">'
       + g.map(nd=>'<span class="preq">'+esc(nd.it.type[0]+'#'+nd.it.no)+' '+escn(nd.it.title)+'</span>').join(' ')
       + '</div></details>';
  });
  h += '<div class="prow"><span class="pst small">상충 쌍</span><span class="pwho small">'
     + why.size+'쌍이 같은 회차에 못 들어간다. 예: '
     + [...why.values()].slice(0,3).map(esc).join(' / ')
     + '</span></div></div>';
  return h;
}

// 이 회차를 돌려면 먼저 데려와야 하는 인물들. 항목 카드를 펼쳐야 보이던 것을 회차 상단으로 끌어올린다.
function prereqRunHTML(picked){
  const need = new Map();
  picked.forEach(({it})=>{
    pqOf(it).forEach(c=>{
      if(!PQ.chars[c]) return;
      if(!need.has(c)) need.set(c, []);
      if(!need.get(c).some(x=>x.id===it.id)) need.get(c).push(it);
    });
  });
  if(!need.size) return '';
  const keyOf = c => {
    const m = /(\d+)\s*년\s*(\d+)\s*월/.exec((PQ.chars[c]||{}).when || '');
    return m ? (+m[1])*100 + (+m[2]) : 9999;
  };
  const order = [...need.keys()].sort((a,b)=>keyOf(a)-keyOf(b));
  let h = '<div class="plan"><div class="thead"><span class="tt">▸ 이 회차에 먼저 데려와야 할 인물 '+order.length+'명</span>'
        + '<span class="small">아래 항목들은 인물 호감도를 요구하는데, 호감도를 올리려면 그 인물이 당문에 있어야 한다. '
        + '<b>영입 사건을 놓치면 조건을 다 맞춰도 항목을 못 딴다.</b> 시기가 이른 순이다.</span></div>';
  order.forEach(c=>{
    const d = PQ.chars[c], its = need.get(c);
    h += '<div class="prow" style="align-items:flex-start"><span class="pst">'+esc(c)+'</span><span class="pwho">'
       + '<div><span class="preq">'+esc(d.when || '시기 미상')+'</span> '
       + '<span class="small">사건 <code>'+esc(d.by)+'</code> · 플래그 <code>'+esc(d.flag)+'</code></span>'
       + (d.sure ? '' : ' <span class="upm">확정도 낮음</span>')
       + '</div>'
       + '<ul style="margin:4px 0 4px 16px;padding:0">'
       + (d.how||[]).map(x=>'<li class="small">'+esc(x)+'</li>').join('')
       + '</ul>'
       + '<div class="small">요구 항목 · '
       + its.map(i=>'<span class="preq">'+esc(i.type[0]+'#'+i.no)+' '+escn(i.title)+'</span>').join(' ')
       + '</div></span></div>';
  });
  return h + '</div>';
}

function forksHTML(picked){
  const need = forkNeeds(picked);
  const itemsOf = its => its.slice(0,3).map(i=>esc(i.type[0]+'#'+i.no)).join(', ')
                       + (its.length>3? ' 외 '+(its.length-3):'');

  let h = '<div class="plan"><div class="thead"><span class="tt">이번 런의 주요 분기</span>'
    + '<span class="small">담긴 항목들이 요구하는 큰 선택을 트리로 세운 것. 들여쓴 갈래는 '
    + '부모를 그 값으로 골랐을 때만 열린다. 한 분기에 값이 둘 이상이거나 부모와 어긋나면 '
    + '<span class="conf">한 회차에 다 담을 수 없다</span>.</span></div>';

  let any = false;
  const render = (f, depth) => {
    const mm = need[f.id];
    const kids = FORKS.filter(c=>c.parent && c.parent.fork===f.id && need[c.id]);
    if(!mm && !kids.length) return '';
    any = true;
    let r = '';
    if(mm){
      const vals = [...mm.keys()];
      const clash = vals.length > 1;
      let broken = null;
      if(f.parent){
        const pm = need[f.parent.fork], pf = FKMAP[f.parent.fork];
        const pname = (pf.options.find(o=>o.v===f.parent.v)||{}).name || f.parent.v;
        if(pm && !pm.has(f.parent.v)){
          const other = [...pm.keys()].map(v=>(pf.options.find(o=>o.v===v)||{}).name||v);
          broken = '부모 분기가 ' + other.join(', ') + ' 로 잡혀 있어 이 갈래는 열리지 않는다. 필요: ' + pname;
        }
      }
      r += '<div class="prow" style="padding-left:'+(depth*18)+'px"><span class="pst">'
        + (depth? '└ ':'') + esc(f.q)
        + (clash? ' <span class="conf">⚠ 상충</span>':'')
        + (broken? ' <span class="conf">⚠ 모순</span>':'')
        + '</span><span class="pwho">';
      r += vals.sort((a,b)=>mm.get(b).length-mm.get(a).length).map(v=>{
        const name = (f.options.find(o=>o.v===v)||{}).name || v;
        return '<span class="preq'+((clash||broken)?' no2':'')+'">'+esc(name)+'</span> '
          + '<span class="small">'+itemsOf(mm.get(v))+'</span>';
      }).join('<br>');
      if(broken) r += '<br><span class="small conf">'+esc(broken)+'</span>';
      if(f.note) r += '<br><span class="small">'+esc(f.note)+'</span>';
      r += '</span></div>';
    }
    kids.forEach(c=>{ r += render(c, depth+1); });
    return r;
  };

  FORKS.filter(f=>!f.parent).forEach(f=>{ h += render(f, 0); });
  if(!any) h += '<div class="prow"><span class="pst small">없음</span>'
    + '<span class="pwho small">이 런의 항목들이 요구하는 큰 분기가 없다.</span></div>';
  h += '</div>';
  h += otherForksHTML(picked);
  return h;
}

// 트리에 등록하지 않은 나머지 결정 플래그. 서로의 배타 관계는 아직 조사하지 않았다.
const KNOWN = FORKS.map(f=>f.flag);
const BINARY = {
  '대사형 완쾌': ['살리지 않음', '대사형 살리기'],
  '금오상인 사망': ['살려둠', '금오상인 처치'],
  '공동파 장문인이 됨': ['안 됨', '공동파 장문인이 됨'],
  '주인공 강릉대전 참전': ['불참', '강릉대전 참전'],
  '비협천리행': ['안 함', '비협천리행'],
  '지옥도행': ['안 감', '지옥도행'],
};
const FORKRE = new RegExp(RXO+FLAGWORD+' ([^'+RXC+']{2,70})'+RXC+RXS+'*=='+RXS+'*(-?'+RXD+'+)','g');
function forkOptions(label){
  const m = [...label.matchAll(new RegExp('('+RXD+'+)'+RXS+'*:'+RXS+'*([^/)]+)','g'))];
  if(m.length>=2){ const o={}; m.forEach(x=>o[x[1]]=x[2].trim()); return o; }
  return null;
}
function otherForksHTML(picked){
  const forks = new Map();
  picked.forEach(({it,o})=>{
    // 항목 전체가 아니라 고른 경로의 플래그 조각만 본다 (itemForkSets 와 같은 기준)
    const s = JSON.stringify((o&&o.flags)||[]);
    let m; FORKRE.lastIndex = 0;
    while((m = FORKRE.exec(s))){
      const label = m[1], val = m[2];
      if(KNOWN.some(k=>label.startsWith(k))) continue;
      if(!forkOptions(label) && !BINARY[label]) continue;
      if(!forks.has(label)) forks.set(label, new Map());
      const mm = forks.get(label);
      if(!mm.has(val)) mm.set(val, []);
      if(!mm.get(val).some(x=>x.id===it.id)) mm.get(val).push(it);
    }
  });
  if(!forks.size) return '';
  let h = '<div class="plan"><div class="thead"><span class="tt">그 외 분기</span>'
    + '<span class="small">항목 조건에서 그대로 긁어온 결정 플래그들. '
    + '서로 배타인지는 아직 조사하지 않았으니 참고용으로만 본다.</span></div>';
  [...forks.entries()].forEach(([label, mm])=>{
    const opts = forkOptions(label);
    const base = label.split('(')[0].trim();
    const clash = mm.size > 1;
    h += '<div class="prow"><span class="pst">'+esc(base)+(clash?' <span class="conf">⚠ 상충</span>':'')
       + '</span><span class="pwho">';
    h += [...mm.entries()].sort((a,b)=>b[1].length-a[1].length).map(([v, its])=>{
      const name = opts ? (opts[v] || v) : (BINARY[label] ? (BINARY[label][+v] ?? v) : v);
      return '<span class="preq'+(clash?' no2':'')+'">'+esc(name)+'</span> <span class="small">'
        + its.slice(0,3).map(i=>esc(i.type[0]+'#'+i.no)).join(', ')
        + (its.length>3? ' 외 '+(its.length-3):'')+'</span>';
    }).join('<br>');
    h += '</span></div>';
  });
  return h + '</div>';
}

const INH = JSON.parse(document.getElementById('inhdata').textContent);
const IHKEY='hwal-legacy-points-v1';
let legacyPts = 222;
try { const v=localStorage.getItem(IHKEY); if(v) legacyPts = parseInt(v,10)||222; } catch(e){}

// 같은 런에 담을 수 없는 조합(예: 공동파 유학 문파 선택)을 상충 칸에 같이 띄운다
function exclusiveHTML(picked){
  const groups = PQ.exclusive || [];
  let h = '';
  groups.forEach(gr=>{
    const sides = gr.options.map(opt=>({
      opt,
      items: picked.filter(({it}) => pqOf(it).some(c=>opt.chars.includes(c))).map(x=>x.it)
    })).filter(s=>s.items.length);
    if(sides.length < 2) return;
    h += '<div class="plan"><div class="thead"><span class="tt conf">⚠ 같은 런 불가 — '+esc(gr.group)+'</span>'
       + '<span class="small">'+esc(gr.why)+'</span></div>';
    sides.forEach(s=>{
      h += '<div class="prow"><span class="pst">'+esc(s.opt.name)+'</span><span class="pwho">'
         + s.items.map(i=>'<span class="preq">'+esc(i.type[0]+'#'+i.no)+' '+escn(i.title)+'</span>').join(' ')
         + '</span></div>';
    });
    h += '<div class="prow"><span class="pst small">→ 나눌 것</span><span class="pwho small">'
       + '이 둘은 서로 다른 회차로 갈라야 한다. 한쪽을 고르면 다른 쪽 항목은 이번 런에서 포기.</span></div></div>';
  });
  return h;
}

// 계승 포인트로 시작부터 채울 수 있는 수치와, 게임 안에서 벌어야 하는 수치를 갈라 보여준다
function inheritHTML(order, picked){
  const need = new Map();   // stat -> 가장 빡센 하한
  order.forEach(([stat, m])=>{
    if(stat==='마음에 둔 사람') return;
    [...m.values()].forEach(e=>{
      if(e.op!=='>=' && e.op!=='>') return;
      const v = e.op==='>' ? e.val+1 : e.val;
      if(!need.has(stat) || v>need.get(stat).v) need.set(stat, {v, items:e.items});
    });
  });
  // 선행 인물의 호감도·조건도 계승 대상에 넣는다
  const extra = [];
  const chars = new Set();
  picked.forEach(({it})=>pqOf(it).forEach(c=>chars.add(c)));

  const rows = [], nope = [];
  [...need.entries()].forEach(([stat, {v, items}])=>{
    const inh = INH[stat];
    const who = items.slice(0,3).map(i=>i.type[0]+'#'+i.no).join(', ')
              + (items.length>3? ' 외 '+(items.length-3):'');
    if(inh){
      const gap = v - (inh.start||0);
      const clicks = gap>0 ? Math.ceil(gap/inh.step) : 0;
      rows.push({stat, v, inh, clicks, who});
    } else {
      nope.push({stat, v, who});
    }
  });
  rows.sort((a,b)=>b.clicks-a.clicks);

  let h = '<div class="plan"><div class="thead"><span class="tt">계승 포인트 계획</span>'
    + '<span class="small">회차 시작 화면에서 미리 올려둘 수 있는 값. 본 엔딩이 늘수록 포인트도 늘어난다. '
    + '보유 포인트 <input id="lpts" class="lpts" type="number" value="'+legacyPts+'" min="0"> 점</span></div>';

  if(rows.length){
    h += '<div class="prow"><span class="pst small">올릴 수 있음</span><span class="pwho small">'
       + '시작값 → 목표값 · 필요한 클릭 수. 클릭당 소모 포인트는 게임 파일에 없어서 표시하지 않는다.</span></div>';
    rows.forEach(r=>{
      h += '<div class="prow"><span class="pst">'+esc(r.stat)+'</span><span class="pwho">'
         + '<span class="preq">'+esc(String(r.inh.start))+' → '+esc(String(r.v))+'</span> '
         + (r.clicks? '<span class="lc">+'+r.inh.step+' × '+r.clicks+'번</span>'
                    : '<span class="lok">시작값으로 이미 충족</span>')
         + ' <span class="small">['+esc(r.inh.tab)+'] '+esc(r.who)+'</span></span></div>';
    });
  }
  if(nope.length){
    h += '<div class="prow"><span class="pst small">계승 불가</span><span class="pwho small">'
       + '계승 목록에 없다. 게임 안에서 직접 올려야 한다.</span></div>';
    nope.forEach(r=>{
      h += '<div class="prow"><span class="pst">'+esc(r.stat)+'</span><span class="pwho">'
         + '<span class="preq no2">'+esc('>= '+r.v)+'</span> <span class="small">'+esc(r.who)+'</span></span></div>';
    });
  }

  // 선행 인물 호감도 — 조건표에 안 잡혀도 계승으로 밀어줄 수 있다
  const cr = [...chars].map(c=>({c, inh: INH[c+' 호감도']})).filter(x=>x.inh);
  if(cr.length){
    h += '<div class="prow"><span class="pst small">선행 인물</span><span class="pwho small">'
       + '이번 런의 선행 조건에 걸린 인물들. 호감도를 계승으로 미리 밀어두면 사건 진입이 쉬워진다.</span></div>';
    cr.forEach(({c, inh})=>{
      h += '<div class="prow"><span class="pst">'+esc(c)+' 호감도</span><span class="pwho">'
         + '<span class="preq">시작 '+esc(String(inh.start))+'</span> <span class="lc">+'+inh.step+'씩</span></span></div>';
    });
  }

  h += wulinHTML(picked);
  h += '</div>';
  return h;
}

// 서무림맹을 결성할 런이면 문파·인물 호감도 조건을 따로 세워준다
function wulinHTML(picked){
  const hits = picked.filter(({it}) =>
    JSON.stringify(it.opts||[]).includes('서무림맹') || (it.desc||'').includes('서무림맹'));
  if(!hits.length) return '';
  const rows = [
    ['개방 호감도', '이부귀가 결성을 제안하게 하려면 이부귀 호감도 2성 이상. 개방 설득에도 쓰인다.'],
    ['아미파 호감도', '아미파 설득 조건이 호감도 2성 이상이다.'],
    ['공동파 호감도', '공동파 설득 노선을 탈 때.'],
    ['청성파 호감도', '청성파 설득 노선을 탈 때.'],
    ['이부귀 호감도', '개방 제안 노선의 핵심. 2성 이상.'],
    ['학문', '직접 제안하기 노선은 전술 5레벨 + 학문 60 이상이 필요하다.'],
  ];
  let h = '<div class="prow"><span class="pst small">서무림맹</span><span class="pwho small">'
        + '이번 런에 서무림맹 관련 항목이 '+hits.length+'개 있다. 결성은 문파·인물 호감도에 크게 걸리므로 '
        + '계승에서 미리 밀어두는 게 특히 효과가 크다.</span></div>';
  rows.forEach(([k, why])=>{
    const inh = INH[k];
    if(!inh) return;
    h += '<div class="prow"><span class="pst">'+esc(k)+'</span><span class="pwho">'
       + '<span class="preq">시작 '+esc(String(inh.start))+'</span> <span class="lc">+'+inh.step+'씩</span> '
       + '<span class="small">'+esc(why)+'</span></span></div>';
  });
  return h;
}

// 선행 배지를 누르면 그 항목의 상세를 펼쳐 선행 조건 상자를 보여준다
document.addEventListener('click', e=>{
  const b = e.target.closest('button.pq');
  if(!b) return;
  e.stopPropagation();
  const card = b.closest('.card');
  if(card){ card.classList.add('open'); card.scrollIntoView({block:'nearest'}); return; }
  const row = b.closest('.trow');
  if(row){
    const more = row.querySelector('.more');
    const d = rwrap.querySelector('[data-det="'+row.dataset.row+'"]');
    if(d && d.hidden && more) more.click();
    if(d) d.scrollIntoView({block:'nearest'});
  }
}, true);

const EV = JSON.parse(document.getElementById('evdata').textContent);
const ewrap = document.getElementById('events');
// ================= 이번 런 목표 =================
// 체크박스는 「딴 것을 지우는」 용도가 아니라 「이번 회차에 보고 싶은 것」을 고르는 용도다.
// 고른 것들의 조건을 한데 모아, 회차를 시작하기 전이나 중간에 무엇을 맞춰야 하는지 본다.
const gwrap = document.getElementById('goal');

function goalPicked(){
  const out = [];
  D.items.forEach(it=>{
    if(!CK[it.id]) return;
    const o = pickOpt(it, curRoute) || (it.opts||[])[0];
    if(o) out.push({it, o});
  });
  return out;
}

// 여러 항목의 수치 구간을 합친다. 상충하면 그 사실을 남긴다.
function mergeBounds(picked){
  const out = {};
  picked.forEach(x=>{
    const b = itemBounds(x);
    Object.entries(b).forEach(([stat, e])=>{
      const g = out[stat] = out[stat] || {lo:null, hi:null, loBy:[], hiBy:[]};
      const tag = x.it.type[0]+'#'+x.it.no;
      if(e.lo!=null && (g.lo==null || e.lo>g.lo)){ g.lo=e.lo; g.loBy=[tag]; }
      else if(e.lo!=null && e.lo===g.lo) g.loBy.push(tag);
      if(e.hi!=null && (g.hi==null || e.hi<g.hi)){ g.hi=e.hi; g.hiBy=[tag]; }
      else if(e.hi!=null && e.hi===g.hi) g.hiBy.push(tag);
    });
  });
  return out;
}

function mergeForks(picked){
  const out = {};
  picked.forEach(x=>{
    const f = itemForkSets(x);
    Object.entries(f).forEach(([id, set])=>{
      const tag = x.it.type[0]+'#'+x.it.no;
      const g = out[id] = out[id] || {set:new Set(set), by:{}};
      [...set].forEach(v=>{ (g.by[v] = g.by[v] || []).push(tag); });
      g.set = new Set([...g.set].filter(v=>set.has(v)));
    });
  });
  return out;
}

function mergeLover(picked){
  const by = {};
  let set = null, conflict = false;
  picked.forEach(x=>{
    const s = itemLover(x);
    if(!s || !s.size) return;
    const tag = x.it.type[0]+'#'+x.it.no;
    [...s].forEach(v=>{ (by[v] = by[v] || []).push(tag); });
    if(set === null) set = new Set(s);
    else {
      const next = new Set([...set].filter(v=>s.has(v)));
      if(!next.size) conflict = true; else set = next;
    }
  });
  return {set, by, conflict};
}

function renderGoal(){
  const picked = goalPicked();
  let h = '<div class="hint"><b>도감 목록이나 런 플래너에서 체크한 것</b>이 여기 모인다. '
        + '체크는 「이미 딴 것」 표시가 아니라 <b>이번 회차에 보고 싶은 것</b>을 고르는 용도다.<br>'
        + '고른 항목들의 조건을 합쳐, 회차를 시작하기 전이나 도중에 무엇을 맞춰야 하는지 한 장으로 본다. '
        + '수치는 <b>가장 빡센 값</b>으로 합쳐지고, 서로 부딪히면 그 자리에 표시된다.</div>';
  h += '<div class="bar"><span class="small ckinfo"></span>'
     + '<button class="f" id="greset">전부 지우기</button></div>';
  if(!picked.length){
    h += '<div class="gempty">아직 고른 것이 없다. 도감 목록에서 이번 회차에 보고 싶은 항목의 '
       + '체크박스를 눌러 두면 여기에 조건이 모인다.</div>';
    gwrap.innerHTML = h;
    bindGoal();
    return;
  }

  // ---- 갈래
  const fk = mergeForks(picked);
  let rows = '';
  FORKS.forEach(f=>{
    const g = fk[f.id];
    if(!g) return;
    const names = v => (f.options.find(o=>o.v===v)||{}).name || ('값 '+v);
    if(!g.set.size){
      const parts = Object.entries(g.by).map(([v,tags])=>
        '<span class="gbad">'+esc(names(v))+'</span> <span class="small">'+tags.join(' ')+'</span>');
      rows += '<tr><td>'+esc(f.flag)+'</td><td><b class="gbad">한 회차에 같이 못 담는다</b> '
            + parts.join(' <span class="small">vs</span> ')+'</td></tr>';
    } else {
      const v = [...g.set];
      rows += '<tr><td>'+esc(f.flag)+'</td><td><b>'+v.map(names).map(esc).join(' 또는 ')+'</b>'
            + '<span class="small"> ' + (g.by[v[0]]||[]).join(' ') + '</span></td></tr>';
    }
  });
  const lv = mergeLover(picked);
  if(lv.conflict){
    rows += '<tr><td>마음에 둔 사람</td><td><b class="gbad">한 회차에 같이 못 담는다</b> '
          + Object.entries(lv.by).map(([v,t])=>esc(LOVER_NAME[v]||v)+' <span class="small">'+t.join(' ')+'</span>').join(' vs ')
          + '</td></tr>';
  } else if(lv.set && lv.set.size){
    rows += '<tr><td>마음에 둔 사람</td><td><b>'+esc(loverText(lv.set))+'</b></td></tr>';
  }
  if(rows) h += '<div class="gsec"><h3>갈래 — 회차를 시작할 때 정할 것</h3><table class="gt">'+rows+'</table></div>';

  // ---- 수치
  const bd = mergeBounds(picked);
  const keys = Object.keys(bd).sort();
  if(keys.length){
    let tr = '';
    keys.forEach(k=>{
      const g = bd[k];
      const bad = (g.lo!=null && g.hi!=null && g.lo>g.hi);
      let need = '';
      if(g.lo!=null) need += '<b>'+g.lo+' 이상</b> <span class="small">'+g.loBy.join(' ')+'</span>';
      if(g.lo!=null && g.hi!=null) need += ' <span class="small">그리고</span> ';
      if(g.hi!=null) need += '<b>'+g.hi+' 이하</b> <span class="small">'+g.hiBy.join(' ')+'</span>';
      tr += '<tr class="'+(bad?'growbad':'')+'"><td>'+esc(k)+'</td><td>'+need
          + (bad?' <b class="gbad">← 서로 부딪힌다</b>':'')+'</td></tr>';
    });
    h += '<div class="gsec"><h3>수치 — 합쳐서 맞춰야 하는 값</h3><table class="gt">'+tr+'</table></div>';
  }

  // ---- 플래그 (루트·사건 진행 상태)
  const FKFLAGS = new Set(FORKS.map(f=>f.flag));
  const fl = {};
  picked.forEach(x=>{
    (x.o.flags||[]).forEach(t=>{
      const m = /^\[플래그 ([^\]]+?)\]\s*(==|>=)\s*(-?\d+)$/.exec(t);
      if(!m) return;
      const lab = m[1].replace(/\s*\(.*$/, '').trim();
      // 분기는 위에서 따로 보여 주고, 임시·대화 플래그는 그때그때 값이라 뺀다.
      if(FKFLAGS.has(lab)) return;
      if(/^(임시 플래그|Talk_Option|전투 결과|결투 승패|결투 범용)/.test(lab)) return;
      // 한글 이름이 없는 것은 우리가 뜻을 모르는 내부 플래그다. 적어 봐야 못 쓴다.
      if(/^[A-Za-z]\w*\d$/.test(lab) || /^\(설명/.test(lab)) return;
      const key = lab + (m[2]==='>=' ? ' ≥ ' : ' = ') + m[3];
      (fl[key] = fl[key] || []).push(x.it.type[0]+'#'+x.it.no);
    });
  });
  // 공략 루트는 한 회차에 하나뿐이다. 둘 이상 필요하면 같이 담을 수 없다.
  const routeNeed = Object.keys(fl).filter(k=>/ 공략 중 = 1$/.test(k));
  if(routeNeed.length > 1){
    h += '<div class="gsec"><h3 class="gbad">한 회차에 같이 담을 수 없다</h3>'
       + '<div>공략 루트는 한 회차에 하나뿐인데 '
       + routeNeed.map(k=>'<b>'+esc(k.replace(' = 1',''))+'</b> <span class="small">'+fl[k].join(' ')+'</span>').join(' · ')
       + ' 가 모두 필요하다. 회차를 나눠야 한다.</div></div>';
  }
  if(Object.keys(fl).length){
    let tr = '';
    Object.entries(fl).sort().forEach(([k, tags])=>{
      tr += '<tr><td>'+esc(k.replace(/ = 1$/,''))+'</td><td><span class="small">'+tags.join(' ')+'</span>'
          + (/ = 0$/.test(k) ? ' <span class="small">(0 이어야 함)</span>' : '')+'</td></tr>';
    });
    h += '<div class="gsec"><h3>진행 상태 — 그때까지 세워져 있어야 하는 것</h3><table class="gt">'+tr+'</table></div>';
  }

  // ---- 인물
  const who = {};
  picked.forEach(x=>{
    pqOf(x.it).forEach(n=>{ (who[n] = who[n] || []).push(x.it.type[0]+'#'+x.it.no); });
  });
  if(Object.keys(who).length){
    let tr = '';
    Object.entries(who).forEach(([n, tags])=>{
      const c = PQ.chars[n] || {};
      tr += '<tr><td>'+esc(n)+'</td><td><span class="small">'+tags.join(' ')+'</span> · '
          + esc(c.when||'')+' <span class="small">'+esc((c.how||[])[0]||'')+'</span></td></tr>';
    });
    h += '<div class="gsec"><h3>인물 — 미리 거두어야 하는 사람</h3><table class="gt">'+tr+'</table></div>';
  }

  // ---- 고른 항목 목록 (시점순)
  const sorted = picked.slice().sort((a,b)=>sortKey(a.o)-sortKey(b.o));
  let li = '';
  sorted.forEach(x=>{
    const w = x.o.when || x.o.estText || '시점 미상';
    li += '<div class="grow">'+ckBox(x.it.id)
        + '<span class="tp '+(TCLS[x.it.type]||'')+'">'+esc(x.it.type)+'</span> '
        + '<b>#'+x.it.no+'</b> '+escn(x.it.title)
        + '<span class="small"> · '+esc(w)+'</span></div>';
  });
  h += '<div class="gsec"><h3>고른 항목 '+picked.length+'개</h3>'+li+'</div>';
  gwrap.innerHTML = h;
  bindGoal();
}

function bindGoal(){
  const r = document.getElementById('greset');
  if(r) r.addEventListener('click', ()=>{ CK={}; saveCK(); updateCkLabel(); render(); renderGoal(); });
  updateCkLabel();
}

function renderEvents(){
  const nl = String.fromCharCode(10);
  let h = '<p id="evnote">루트 진입·주요 분기처럼 도감 항목 하나로 떨어지지 않는 조건들. '
        + '<span class="evsrc">시트</span> 는 공략 시트에서 옮겨온 것, '
        + '<span class="evsrc game">게임 파일</span> 은 미션 조건 데이터에서 직접 추출한 것.</p>';
  EV.forEach(e=>{
    const tag = e.src==='game'
      ? '<span class="evsrc game">게임 파일</span>' : '<span class="evsrc">시트</span>';
    h += '<div class="ev"><h3>'+esc(e.name)+tag+'</h3><div class="evb">'
       + esc(e.body).split(nl).join(nl) + '</div></div>';
  });
  ewrap.innerHTML = h;
}
const WK = JSON.parse(document.getElementById('wkdata').textContent);
const wwrap = document.getElementById('wiki');
let wikiPage = 0;
function renderWiki(){
  let h = '<div class="wnav">' + WK.map((p,i)=>
      '<button class="f wtab'+(i===wikiPage?' on':'')+'" data-w="'+i+'">'+esc(p.title)+'</button>'
    ).join(' ') + '</div>';
  h += '<div class="wbody"><h2 class="wtitle" id="w-'+esc(WK[wikiPage].name)+'">'
     + esc(WK[wikiPage].title) + '</h2>' + WK[wikiPage].html + '</div>';
  wwrap.innerHTML = h;
  wwrap.querySelectorAll('button.wtab').forEach(b=>b.addEventListener('click',()=>{
    wikiPage = +b.dataset.w; renderWiki(); wwrap.scrollIntoView({block:'start'});
  }));
  wwrap.querySelectorAll('a.wlink').forEach(a=>a.addEventListener('click',ev=>{
    const n = a.getAttribute('href').slice(3);
    const i = WK.findIndex(p=>p.name===n);
    if(i>=0){ ev.preventDefault(); wikiPage=i; renderWiki(); }
  }));
}
document.querySelectorAll('button.tb').forEach(b=>b.addEventListener('click',()=>{
  const v=b.dataset.v;
  document.querySelectorAll('button.tb').forEach(x=>x.setAttribute('aria-pressed', x===b));
  document.getElementById('list').hidden = (v!=='list');
  bwrap.hidden = (v!=='bundle');
  rwrap.hidden = (v!=='run');
  gwrap.hidden = (v!=='goal');
  ewrap.hidden = (v!=='events');
  wwrap.hidden = (v!=='wiki');
  document.getElementById('filters').hidden = (v==='events' || v==='wiki' || v==='goal');
  if(v==='bundle') renderBundles();
  if(v==='run') renderRun();
  if(v==='goal') renderGoal();
  if(v==='events') renderEvents();
  if(v==='wiki') renderWiki();
}));
bindChecks(list); bindChecks(rwrap); bindChecks(gwrap);
render();
</script></body></html>
"""


def main():
    data = open('data.json', encoding='utf-8').read()
    events = open('events.json', encoding='utf-8').read()
    page = PAGE.replace('__DATA__', data.replace('</script>', '<\\/script>'))
    page = page.replace('__EVENTS__', events.replace('</script>', '<\\/script>'))
    prereq = open('prereq.json', encoding='utf-8').read()
    page = page.replace('__PREREQ__', prereq.replace('</script>', '<\\/script>'))
    inherit = open('inherit.json', encoding='utf-8').read()
    page = page.replace('__INHERIT__', inherit.replace('</script>', '<\\/script>'))
    forks = open('forks.json', encoding='utf-8').read()
    page = page.replace('__FORKS__', forks.replace('</script>', '<\\/script>'))
    rforks = open('route_forks.json', encoding='utf-8').read()
    page = page.replace('__ROUTEFORKS__', rforks.replace('</script>', '<\\/script>'))
    wiki = open('wiki.json', encoding='utf-8').read()
    page = page.replace('__WIKI__', wiki.replace('</script>', '<\\/script>'))
    # 지금 세이브의 판정. 세이브가 없거나 못 읽어도 공략기 자체는 나와야 한다.
    run = 'null'
    try:
        import save_read
        v = save_read.save_verdicts()
        if v:
            run = json.dumps(v, ensure_ascii=False)
            print('  세이브 판정 실었다:', v['when'],
                  '| 가능', v['counts']['가능'],
                  '| 지남', v['counts']['지남'],
                  '| 불가', v['counts']['불가'])
    except Exception as e:
        print('  세이브 판정 못 실었다:', type(e).__name__, e)
    page = page.replace('__RUN__', run)
    page = page.replace('QUOTEOPEN', '\u201C').replace('QUOTECLOSE', '\u201D')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(page)
    print('wrote', OUT, round(len(page.encode()) / 1024), 'KB')


if __name__ == '__main__':
    main()
