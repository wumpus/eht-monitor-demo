import sys
from collections import defaultdict
import datetime

import sqlite3


if len(sys.argv) > 1:
    db = sys.argv[1]
else:
    db = 'vlbimon.db'

con = sqlite3.connect(db)
cur = con.cursor()

res = cur.execute('SELECT name FROM sqlite_master')
names = res.fetchall()

timeseries = []
surprised = []
for name in names:
    name = name[0]  # tuple of length 1
    if name.startswith('ts_param_'):
        timeseries.append(name)
    elif name.startswith('idx_'):
        continue
    else:
        surprised.append(name)

if surprised:
    print('surprised by extra tables, this is not surprising if grafana has altered this db')
    print(surprised)

distinct_query = 'SELECT DISTINCT(station) FROM {}'
all_stations = set()
param_stations = defaultdict(set)
prefix_stations = defaultdict(set)
suffixes = defaultdict(set)
rows_param_station = defaultdict(dict)

for ts in timeseries:
    param = ts.split('_', 2)[2]
    prefix, suffix = param.split('_', 1)

    res = cur.execute(distinct_query.format(ts))
    values = res.fetchall()
    stations = set(v[0] for v in values)
    for station in stations:
        all_stations.add(station)
        param_stations[param].add(station)
        prefix_stations[prefix].add(station)
        suffixes[prefix].add(suffix)  # set only if there is actual data

        # param_stations is already set
        # add in a row count for param and station
        count_query = "SELECT COUNT(*) FROM {} WHERE station = '{}';"
        res = cur.execute(count_query.format(ts, station))
        rows = res.fetchone()[0]
        rows_param_station[param][station] = rows

firstlast_query = 'SELECT * FROM {} ORDER BY time {} LIMIT 1'
param_start = defaultdict(list)
prefix_start = defaultdict(list)
param_end = defaultdict(list)
prefix_end = defaultdict(list)

for ts in timeseries:
    param = ts.split('_')[2]
    prefix = param.split('_')[0]

    res = cur.execute(firstlast_query.format(ts, 'ASC'))

    cols = [c[0] for c in res.description]
    assert cols == ['time', 'station', 'value']

    values = res.fetchall()
    for v in values:
        param_start[param].append(v[0])
        prefix_start[prefix].append(v[0])

    res = cur.execute(firstlast_query.format(ts, 'DESC'))
    values = res.fetchall()
    for v in values:
        param_end[param].append(v[0])
        prefix_end[prefix].append(v[0])

print('stations', *all_stations)

utc = datetime.timezone.utc
print('prefixes')
for pre in sorted(prefix_start.keys()):
    print('', pre+'_', *[p for p in sorted(prefix_stations[pre])])
    for suffix in sorted(suffixes[pre]):
        print(' ', suffix, end=' ')
        param = pre + '_' + suffix
        for station in sorted(rows_param_station[param]):
            print(station, '({})'.format(rows_param_station[param][station]), end=' ')
        print()
    print(' ', min(prefix_start[pre]), max(prefix_end[pre]))
    print(' ', datetime.datetime.fromtimestamp(min(prefix_start[pre]), tz=utc).isoformat(),
          datetime.datetime.fromtimestamp(max(prefix_end[pre]), tz=utc).isoformat())
    
