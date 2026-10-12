"""Build the story graph: scripts, branches, deaths, and reverse edges."""
import os, re, json, collections
import luaparse, game, cond

OUT = 'graph.json'


def main():
    g = game.Game()
    R = cond.Renderer(g)
    scripts = luaparse.load_all()

    # ---- collapse duplicate script variants (zh-cn / zh-tw) ----
    canon = {}
    for k in sorted(scripts):
        base = k.split('__')[0]
        canon.setdefault(base, k)
    trees = {}
    for base, k in canon.items():
        trees[base] = luaparse.parse(scripts[k])

    # ---- combat levels ----
    combat = {}
    lib_by_ref = {}
    for ref, o in g.all_of('LibraryItemData', 'Mortal.Core.LibraryItemData'):
        lib_by_ref[ref] = o['__name']
    for ref, o in g.all_of('CombatLevel', 'Mortal.Combat.CombatLevel'):
        dead = g.resolve(ref[0], o['_deadLibrary']) if o.get('_deadLibrary') else None
        combat[o['__name']] = {
            'dead': lib_by_ref.get(dead),
            'deadEnd': o.get('_deadEnd'),
            'desc': o.get('_desc') or '',
        }
    # ChangeScene("Battle", ...) 은 BattleLevel(BL_) 을 연다. 같은 번호의 CombatLevel(CL_)
    # 이 따로 있어서 둘을 한 이름으로 읽으면 결투의 사망 도감이 부대전에 딸려 붙는다.
    # BattleLevel 에는 _deadLibrary 자체가 없다. 작성자가 ch8_3_1_2 의 부대전 BL_1804_01 을
    # 지고도 죽지 않고 한#49 로 이어지는 것을 확인했는데, 그때 도구는 CL_1804_01 의
    # 사망(생#68)을 그 자리에 붙여 두고 있었다. 이름만 CL_ 것을 빌리고 사망은 잇지 않는다.
    for ref, o in g.all_of('BattleLevel'):
        if not o or '__error' in o:
            continue
        nm = o.get('__name') or ''
        if not nm.startswith('BL_'):
            continue
        combat[nm] = {
            'dead': None,
            'deadEnd': False,
            'desc': (combat.get('CL_' + nm[3:]) or {}).get('desc', ''),
        }

    # ---- free-action (position) entries: prefix+suffix -> script ----
    position = []
    for ref, o in g.all_of('PositionResultData', 'Mortal.Story.PositionResultData'):
        f = ref[0]
        prefix = o.get('_scriptPrefix') or ''
        outs = []
        for p in o.get('_list') or []:
            er = g.resolve(f, p)
            e = g.obj(er, 'Mortal.Story.PositionEventData')
            if not e or '__error' in e:
                continue
            cfg = g.obj(g.resolve(er[0], e['_config']), 'OBB.Framework.Data.StoryMappingItem') if e.get('_config') else None
            suffix = (cfg or {}).get('Value')
            outs.append({
                'name': e['__name'],
                'kind': (cfg or {}).get('Key', ''),
                'suffix': suffix,
                'script': f'{prefix}_{suffix}' if suffix else None,
                'rate': e.get('_defaultRate'),
                'cond': R.condition_item(er[0], e.get('_activeCondition')),
                'rateItems': [
                    {'rate': ri.get('_rate'), 'cond': R.condition_item(er[0], ri.get('_condition'))}
                    for ri in (e.get('_eventRateItem') or [])
                ],
            })
        position.append({'name': o['__name'], 'prefix': prefix, 'outcomes': outs})

    # 업무·자유를 누르면 var2 표(특수 사건)를 먼저 굴리고, 꽝(var1 로 넘기기만 하는 결과)이면 var1 표를 굴린다.
    # 뒷산 업무의 용상 도전(Back_02)이 이 첫 단계에 있어서, 이름만 보고 「둘러보기」로 잘못 불렀다.
    RE_HUB = re.compile(r'var1 = checkpointmanager\.Position\("(\w+)"\)\s*(?:--[^\n]*\s*)*'
                        r'var2 = checkpointmanager\.Position\("(\w+)"\)\s*(?:--[^\n]*\s*)*'
                        r'luamanager\.SetNextScript\(var2\)')
    then, sets = {}, {}
    for t in scripts.values():
        for m in RE_HUB.finditer(t):
            inner, first = m.groups()
            then[first] = inner
            # 뒷산 메뉴는 굴리기 직전에 B00001 을 0 으로 되돌린다. 세이브에 남은 값으로 판정하면 평소 수련이 빠진다.
            sets[first] = {f: int(v) for f, v in
                           re.findall(r'SetFlag\("(\w+)", (-?\d+)\)', t[:m.start()])}
    for pr in position:
        if pr['name'] in then:
            pr['then'] = then[pr['name']]
            if sets.get(pr['name']):
                pr['sets'] = sets[pr['name']]
            for o in pr['outcomes']:
                body = re.sub(r'--[^\n]*|\s', '', scripts.get(o['script'] or '', ''))
                if body == 'luamanager.SetNextScript(var1)luamanager.Init()':
                    o['forward'] = True

    # ---- switch / dice / condition definitions ----
    def switch_text(name):
        for ref in g.byclass.get('SwitchResultData', []):
            o = g.obj(ref, 'Mortal.Story.SwitchResultData')
            if o and o.get('__name') == name:
                f = ref[0]
                return [R.condition_item(f, it) for it in (o.get('_items') or [])]
        return None

    sw_index = {}
    for ref in g.byclass.get('SwitchResultData', []):
        o = g.obj(ref, 'Mortal.Story.SwitchResultData')
        if not o or '__error' in o:
            continue
        f = ref[0]
        sw_index[o['__name']] = [R.condition_item(f, it) for it in (o.get('_items') or [])]
    cond_index = {}
    for ref in g.byclass.get('ConditionResultData', []):
        o = g.obj(ref, 'Mortal.Core.ConditionResultData')
        if not o or '__error' in o:
            continue
        f = ref[0]
        cond_index[o['__name']] = [R.condition_item(f, it) for it in (o.get('_items') or [])]
    dice_index = {}
    for ref in g.byclass.get('DiceResultData', []):
        o = g.obj(ref, 'Mortal.Story.DiceResultData')
        if not o or '__error' in o:
            continue
        f = ref[0]
        props = []
        for p in o.get('_propertyItems') or []:
            t = R.E['DicePropertyType'].get(p.get('_type'), '?')
            if t in ('角色數值', '數值'):      # 열거형 이름이 빌드마다 다르다 — 「數值」도 스탯이다
                tgt = R.stat_name(g.resolve(f, p['_stat']))
            elif t == '好感度':
                tgt = R.rel_name(g.resolve(f, p['_relationship']))
            elif t == '旗標':
                tgt = R.flag_name(g.resolve(f, p['_flag']))
            else:
                tgt = ''
            props.append({'type': t, 'target': tgt, 'rate': p.get('_rate'), 'neg': p.get('_negative')})
        results = []
        for it in o.get('_resultItems') or []:
            results.append({
                'note': it.get('_devNote') or '',
                'cond': ' 그리고 '.join(f"{cond.CMP[c['_compareOp']]} {c['_value']}" for c in (it.get('_items') or [])),
            })
        dice_index[o['__name']] = {'props': props, 'results': results}


    # ---- missions: script -> when/where/conditions ----
    POS_KO = {'無': '', '正心堂': '정심당', '校場': '연무장', '煉丹房': '연단방', '鍛冶場': '대장간',
              '後山': '뒷산', '弟子房': '남제자방', '大門': '대문', '講經堂': '강경당',
              '伙房': '부엌', '女弟子房': '여제자방', '神秘房子': '신비한 집'}
    STAGE_KO = {1: '상순', 2: '중순', 3: '하순'}
    ptypes = cond.enum_values(g.w, 'Mortal.Core.PositionType')
    tct = cond.enum_values(g.w, 'Mortal.Core.TimeCheckType')

    def gt(t):
        if not t or not (t.get('Year') or t.get('Month')):
            return None
        return {'y': t.get('Year'), 'm': t.get('Month'), 's': STAGE_KO.get(t.get('Stage'), '')}

    mission = {}
    for ref, o in g.all_of('MissionCheckData', 'Mortal.Core.MissionCheckData'):
        if '__error' in o or not o.get('_startScript'):
            continue
        f = ref[0]
        info = {
            'key': o.get('_key'),
            'desc': o.get('_desc') or '',
            # 꺼 둔 미션이 23 개 있다. 정의는 멀쩡해서 시점·조건만 읽으면 살아 있는 것처럼
            # 보인다 — 하후란 동행 초대(S0604_01)를 「3년 1월 상순에 열린다」고 잘못 읽었다.
            'active': o.get('_active') is not False,
            # 자리가 붙은 미션은 그 자리에 **가야** 뜬다. 시간만 흘리면 그냥 지나간다.
            # 대사형 완쾌(S0401_01)가 연단방이고, 작성자가 그것 때문에 한 회차를 놓쳤다.
            'place': POS_KO.get(ptypes.get(o.get('_position')), ''),
            'timeType': tct.get(o.get('_timeCheckType'), ''),
            # False 면 시점 필드를 안 보고 조건만 본다. 30개가 그런데 그중 29개는
            # 조건문 안에 자기 시점 제한을 따로 들고 있고, 변심의 꿈만 그것마저 없다.
            'dayCheck': o.get('_dayCheck'),
            'time': gt(o.get('_specificTime')),
            'minTime': gt(o.get('_minTime')),
            'maxTime': gt(o.get('_maxTime')),
            'stage': STAGE_KO.get(o.get('_periodStage'), ''),
            'conds': [x for x in (R.condition_item(f, c) for c in (o.get('_conditions') or [])) if x],
        }
        # 한 시작 스크립트에 정의가 여럿 달린다(노선별·시기별 변형). 예전에는 setdefault 로
        # 첫 개만 남겨 42개를 버렸고, 그래서 용지단취가 항전 노선 전용처럼 보였다.
        # 첫 개는 그대로 두고 나머지를 alts 에 실어, 읽는 쪽이 택일로 합칠 수 있게 한다.
        prev = mission.get(o['_startScript'])
        if prev is None:
            mission[o['_startScript']] = info
        else:
            prev.setdefault('alts', []).append(info)

    hub = {}
    for ref, o in g.all_of('PositionController', 'Mortal.Free.PositionController'):
        if '__error' in o or not o.get('_scriptName'):
            continue
        hub[o['_scriptName']] = POS_KO.get(ptypes.get(o.get('_position')), '')

    # ---- scene summaries: first narrative lines of each script ----
    summary = {}
    for base, k in canon.items():
        txt = scripts[k]
        keys = re.findall(r'GetStoryText\("([^"]+)"\)', txt)
        out = []
        for kk in keys:
            v = g.t('Story/' + kk)
            if v:
                out.append(re.sub(r'\\n|[\r\n]+', ' ', v).strip())
            if len(out) >= 2:
                break
        if out:
            s = ' '.join(out)
            summary[base] = s[:160] + ('…' if len(s) > 160 else '')

    # ---- terminals & edges ----
    edges = collections.defaultdict(list)     # script -> [ {to, kind, path} ]
    deaths = collections.defaultdict(list)    # libid -> [ {script, path, via} ]
    for name, (tr, cp) in trees.items():
        for path, n in luaparse.terminals(tr, cp):
            p = [list(x) for x in path]
            if n['t'] == 'scene':
                if n['scene'] == 'GameOver' and n['arg']:
                    deaths[n['arg']].append({'script': name, 'path': p, 'via': 'GameOver'})
                elif n['scene'] in ('Combat', 'Battle'):
                    pre = 'BL_' if n['scene'] == 'Battle' else 'CL_'
                    lv = pre + n['arg'] if (pre + n['arg']) in combat else n['arg']
                    edges[name].append({'to': lv, 'kind': 'combat', 'path': p})
                    info = combat.get(lv)
                    # deadEnd 가 아니면 전투가 끝나고 스크립트로 돌아가므로, 그 스크립트가
                    # 무엇을 줄지 정한다. 전투에 적힌 dead 는 그때 쓰이지 않는다.
                    # 생사부 77 은 무림대회 전투 다섯 곳이 dead 로 가리키지만 전부
                    # deadEnd 가 아니고, 실제로 지면 스크립트가 생사부 79 를 준다.
                    if info and info['dead'] and info.get('deadEnd'):
                        deaths[info['dead']].append(
                            {'script': name, 'path': p, 'via': 'combat', 'combat': lv})
            elif n['t'] == 'award':
                deaths[n['id']].append({'script': name, 'path': p, 'via': n['kind']})
            elif n['t'] == 'next' and n.get('script'):
                edges[name].append({'to': n['script'], 'kind': 'next', 'path': p})

    # reverse edges
    rev = collections.defaultdict(list)
    for src, lst in edges.items():
        for e in lst:
            rev[e['to']].append({'from': src, 'kind': e['kind'], 'path': e['path']})
    for pr in position:
        for o in pr['outcomes']:
            if o['script']:
                rev[o['script']].append({'from': f"[자유행동] {pr['name']}", 'kind': 'position',
                                         'rate': o['rate'], 'cond': o['cond'], 'outcomeKind': o['kind']})

    data = {
        'combat': combat,
        'position': position,
        'switch': sw_index,
        'condition': cond_index,
        'dice': dice_index,
        'deaths': deaths,
        'edges': edges,
        'rev': rev,
        'scripts': sorted(trees),
        'mission': mission,
        'hub': hub,
        'summary': summary,
        'library': sorted(lib_by_ref.values()),
    }
    json.dump(data, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    print('scripts', len(trees), 'combat', len(combat), 'position', len(position))
    print('deaths ids', len(deaths), 'edges', sum(len(v) for v in edges.values()))
    print('switch', len(sw_index), 'dice', len(dice_index), 'condition', len(cond_index))
    print('mission scripts', len(mission), 'free hubs', len(hub), 'summaries', len(summary))


if __name__ == '__main__':
    main()
