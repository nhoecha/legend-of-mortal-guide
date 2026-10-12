import sys, os, struct, collections, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import game
g = game.Game()
want = sys.argv[1:]
refs = {}
for ref, o in g.all_of('FlagData', 'Mortal.Core.FlagData'):
    if '__error' not in o and o.get('__name') in want:
        refs[o['__name']] = ref
print('flag objects:', refs)
for name in want:
    if name not in refs:
        print('!!', name, 'has no FlagData object'); continue
    tf, tp = refs[name]
    hits = collections.defaultdict(list)
    for f, sf in g.sf.items():
        if f == tf:
            fid = 0
        else:
            ext = sf.externals
            if tf not in ext:
                continue
            fid = ext.index(tf) + 1
        pat = struct.pack('<iq', fid, tp)
        d = sf.data
        for pid, (sfid, spid, nm, bo, end) in g.mb[f].items():
            if (f, pid) == (tf, tp):
                continue
            if d.find(pat, bo, end) != -1:
                hits[g.cls.get((f, pid), '?')].append(nm or str(pid))
    print('=====', name, {k: len(v) for k, v in hits.items()})
    for k, v in hits.items():
        print('   ', k, sorted(v)[:40])
