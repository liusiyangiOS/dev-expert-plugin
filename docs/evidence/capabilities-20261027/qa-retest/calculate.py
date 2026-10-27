import collections
import csv
import math
import pathlib
import statistics

p = pathlib.Path(__file__).parent.parent / 'fixtures'
for name in ('baseline.csv', 'candidate.csv', 'candidate-tail-case.csv'):
    with (p / name).open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    x = sorted(int(r['latency_ms']) for r in rows)
    rank = lambda q: x[math.ceil(q * len(x)) - 1]
    print(name, 'count', len(rows), 'unique_ids', len({r['sample_id'] for r in rows}),
          'distribution', dict(sorted(collections.Counter(x).items())),
          'mean', statistics.mean(x), 'p50', statistics.median(x),
          'p95', rank(.95), 'p99', rank(.99),
          'http', dict(collections.Counter(r['http_status'] for r in rows)),
          'business', dict(collections.Counter(r['business_ok'] for r in rows)),
          'joint', dict(collections.Counter((r['latency_ms'], r['business_ok']) for r in rows)))
