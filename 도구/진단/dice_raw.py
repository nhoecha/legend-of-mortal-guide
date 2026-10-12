import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import game
g = game.Game()
want = set(sys.argv[1:])
for ref in g.byclass.get('DiceResultData', []):
    o = g.obj(ref, 'Mortal.Story.DiceResultData')
    if o.get('__name') in want:
        print('=====', o.get('__name'))
        for k, v in o.items():
            if k.startswith('__'): continue
            print('  ', k, '=', json.dumps(v, ensure_ascii=False, default=str)[:900])
