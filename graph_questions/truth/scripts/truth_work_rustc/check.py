import json
T = './truth/'
O = '.'
for r in ('jq', 'fmt'):
    n = json.load(open(T + r + '.json')); o = json.load(open(O + f'truth_multi-{r}.json'))
    print(r, list(o.keys())[:4])
    of = set(o['files']); nf = set(n['files'])
    print(' files only old', sorted(of - nf)[:8], 'only new', sorted(nf - of)[:8])
    oe = {tuple(e[:2]) for e in o['edges']} if isinstance(o.get('edges'), list) else set()
    ne = {tuple(e) for e in n['edges']}
    print(' edges old', len(oe), 'new', len(ne), 'old-only', sorted(oe - ne)[:6], 'new-only', sorted(ne - oe)[:6])
for r in ('serde', 'jq', 'fmt'):
    n = json.load(open(T + r + '.json')); fs = set(n['files'])
    print(r, len(fs), len(n['edges']), all(a in fs and b in fs and a != b for a, b in n['edges']), n['edges'] == sorted(n['edges']))
