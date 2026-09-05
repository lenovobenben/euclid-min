import json
from pathlib import Path
from euclid_min.formats import load_profile, construction_sha256

root = Path(__file__).resolve().parent
repository_root = Path(__file__).resolve().parents[3]
source = json.loads((root / 'provenance.json').read_text(encoding='utf-8'))
profile = load_profile(repository_root / 'profiles' / 'regular-17-e-fixed-v1.yaml')
indices = {2:0,3:1,6:0,9:1,12:1,13:0,17:0,15:0,26:0,27:1,37:1,54:1,69:0,68:1,45:1,90:0,24:1,134:1}
program = []
names = {0:'O', 1:'A'}
def bind(pid):
    if pid in names:
        return names[pid]
    name = 'p' + str(pid)
    pair = ['unit_circle' if s == 'd1' else s for s in source['points'][str(pid)]['intersection_objects']]
    program.append({'id':name, 'op':'intersect', 'objects':pair, 'index':indices[pid]})
    names[pid] = name
    return name
for record in source['objects']:
    if record['id'] in ('d1', 'd17'):
        continue
    a, b = bind(record['a']['id']), bind(record['b']['id'])
    if record['type'] == 'circle':
        program.append({'id':record['id'], 'op':'circle', 'center':a, 'through':b})
    else:
        program.append({'id':record['id'], 'op':'line', 'through':[a,b]})
program += [
    {'id':'opposite_target', 'op':'intersect', 'objects':['unit_circle','d18'], 'index':0},
    {'id':'target_diameter', 'op':'line', 'through':['O','opposite_target']},
]
construction = {
    'id':'eddy119-public-prefix-adapted-17e',
    'title':'17 E adjacent-vertex construction adapted from Eddy119 public 37-move construction',
    'description':'Source: Eddy119, 2026-02-28, https://gist.github.com/mrflip/a973b1c60f4a38fc3277ddd57ce65b28?permalink_comment_id=6006486 . Adapted on 2026-09-05 by keeping the first 18 distinct drawable objects, making d1 the free unit circle, removing unused d17, and drawing the diameter through the negative target. All point inputs are initial points or exact intersection bindings.',
    'program':program,
}
certificate = {
    'schema':'euclid-min-certificate/v1',
    'problem':'regular-17-adjacent-vertex',
    'profile':{'id':profile.data['id'], 'sha256':profile.sha256},
    'construction':construction,
    'assertions':{'score':{'metric':'e_move','e_move':17}, 'targets':['B_plus'], 'claim':'verified_construction'},
    'software':{'producer':{'name':'public-source-exact-converter','version':'1.0.0'}},
    'integrity':{'construction_sha256':construction_sha256(construction)},
}
(root/'construction.json').write_text(
    json.dumps(certificate,ensure_ascii=False,indent=2)+'\n',
    encoding='utf-8',
)
print('saved construction.json', construction_sha256(construction), flush=True)
