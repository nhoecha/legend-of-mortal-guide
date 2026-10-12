# -*- coding: utf-8 -*-
"""위키/*.md 를 공략기의 「시스템」 탭에 넣을 HTML 로 굳힌다.

원본은 마크다운이라 깃으로 차이를 보기 쉽고, 읽기는 공략기 안에서 한다.
쓰는 문법은 제목·문단·목록·표·펜스 코드블록·인용, 그리고 인라인 굵게/코드/[[링크]] 뿐이다.
"""
import html
import json
import os
import re

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '위키')

# 페이지 순서. 여기 없는 파일은 이름순으로 뒤에 붙는다.
ORDER = ['분기와-회차설계', '심계와-공략루트', '성정-내리기', '업무-결과표', '게임파일과-세이브', '바깥-자료', '미확인-목록']


def inline(s):
    s = html.escape(s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'\[\[([^\]]+)\]\]', r'<a class="wlink" href="#w-\1">\1</a>', s)
    return s


def convert(md):
    out, i = [], 0
    lines = md.split('\n')
    while i < len(lines):
        ln = lines[i]
        if ln.startswith('```'):
            j = i + 1
            body = []
            while j < len(lines) and not lines[j].startswith('```'):
                body.append(lines[j])
                j += 1
            out.append('<pre class="wpre">' + html.escape('\n'.join(body)) + '</pre>')
            i = j + 1
            continue
        m = re.match(r'^(#{1,4}) (.+)$', ln)
        if m:
            n = len(m.group(1))
            out.append(f'<h{n + 1} class="wh{n}">{inline(m.group(2))}</h{n + 1}>')
            i += 1
            continue
        if ln.startswith('|') and i + 1 < len(lines) and re.match(r'^\|[\s:|-]+\|$', lines[i + 1]):
            head = [c.strip() for c in ln.strip('|').split('|')]
            j = i + 2
            rows = []
            while j < len(lines) and lines[j].startswith('|'):
                rows.append([c.strip() for c in lines[j].strip('|').split('|')])
                j += 1
            t = '<table class="wtb"><thead><tr>' \
                + ''.join(f'<th>{inline(c)}</th>' for c in head) + '</tr></thead><tbody>'
            for r in rows:
                t += '<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>'
            out.append(t + '</tbody></table>')
            i = j
            continue
        if re.match(r'^[-*] ', ln):
            items = []
            while i < len(lines) and re.match(r'^[-*] ', lines[i]):
                items.append(inline(lines[i][2:]))
                i += 1
            out.append('<ul class="wul"><li>' + '</li><li>'.join(items) + '</li></ul>')
            continue
        if ln.startswith('> '):
            body = []
            while i < len(lines) and lines[i].startswith('> '):
                body.append(inline(lines[i][2:]))
                i += 1
            out.append('<blockquote class="wq">' + ' '.join(body) + '</blockquote>')
            continue
        if ln.startswith('---') and set(ln) <= {'-'}:
            out.append('<hr class="whr">')
            i += 1
            continue
        if ln.strip():
            body = []
            while i < len(lines) and lines[i].strip() and not re.match(
                    r'^(#{1,4} |[-*] |> |\||```|---)', lines[i]):
                body.append(inline(lines[i]))
                i += 1
            out.append('<p class="wp">' + ' '.join(body) + '</p>')
            continue
        i += 1
    return '\n'.join(out)


def main():
    files = [f for f in os.listdir(SRC) if f.endswith('.md')]
    names = [f[:-3] for f in files]
    names.sort(key=lambda n: (ORDER.index(n) if n in ORDER else len(ORDER), n))
    pages = []
    for n in names:
        md = open(os.path.join(SRC, n + '.md'), encoding='utf-8').read()
        m = re.match(r'^# (.+)$', md.split('\n')[0])
        title = m.group(1) if m else n
        body = md.split('\n', 1)[1] if m else md
        pages.append({'name': n, 'title': title, 'html': convert(body)})
        print(f'{n:24} {len(md):>6}자 -> {len(pages[-1]["html"]):>6}자')
    json.dump(pages, open('wiki.json', 'w', encoding='utf-8'), ensure_ascii=False)


if __name__ == '__main__':
    main()
