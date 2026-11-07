#!/usr/bin/env python3
"""Plot timings, keeping different methods, runs and controls separate."""
import argparse
import csv
from collections import defaultdict
import statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p=argparse.ArgumentParser()
p.add_argument('csv',nargs='+')
p.add_argument('--output',default='rob.png')
p.add_argument('--band',choices=('range','p10-p90'),default='p10-p90')
p.add_argument('--samples-at',type=int,help='Plot individual samples at this N in collection order')
a=p.parse_args(); groups=defaultdict(list)
fields=('machine_id','environment','dependent','method','build_id','run_id','footprint_bytes',
        'span_bytes','iterations','node_stride','nop_bytes','loop_alignment','page_policy','seed','order_seed')
for path in a.csv:
    if path.endswith('.summary.csv'): continue  # Ignore this script's derived output in globs.
    with open(path) as f:
        reader=csv.DictReader(f)
        required={'status','iterations','nops_per_gap','sample_id','elapsed_ticks','footprint_bytes','dependent','machine_id','environment'}
        if not required.issubset(reader.fieldnames or []): p.error(f'{path}: not a raw ROB sample CSV')
        for r in reader:
            if r['status']!='ok' or int(r['iterations'])==0: continue
            n=int(r['nops_per_gap'])
            if a.samples_at is not None and n!=a.samples_at: continue
            key=tuple(r.get(x,'legacy') for x in fields)
            groups[key,n].append((int(r.get('collection_order',r['sample_id'])),int(r['elapsed_ticks'])/(2*int(r['iterations']))))
if not groups: p.error('No accepted nonzero-work samples match the selection')
fig,ax=plt.subplots(figsize=(11,6))
summary=[]
for key in sorted({k for k,n in groups}):
    d=dict(zip(fields,key)); ns=sorted(n for k,n in groups if k==key)
    label=f"{d['machine_id']} {d['environment']} {'dep' if d['dependent']=='1' else 'ind'} {int(d['footprint_bytes'])/1048576:g} MiB"
    label+=f"\n{d['method']} seed={d['seed']} stride={d['node_stride']} NOP={d['nop_bytes']} align={d['loop_alignment']} pages={d['page_policy']} run={d['run_id']}"
    if a.samples_at is not None:
        vals=sorted(groups[key,a.samples_at]); ax.plot([x for x,y in vals],[y for x,y in vals],'.-',label=label)
        continue
    med=[]; low=[]; high=[]
    for n in ns:
        ordered=sorted(groups[key,n]); vals=[y for x,y in ordered]; s=sorted(vals)
        quant=statistics.quantiles(vals,n=10,method='inclusive') if len(vals)>1 else [vals[0]]*9
        med.append(statistics.median(vals))
        low.append(min(vals) if a.band=='range' else quant[0]); high.append(max(vals) if a.band=='range' else quant[8])
        third=max(1,len(vals)//3)
        early=statistics.median(vals[:third]); late=statistics.median(vals[-third:])
        summary.append({**d,'nops_per_gap':n,'samples':len(vals),'min':s[0],'median':med[-1],
                        'p10':quant[0],'p90':quant[8],'max':s[-1],'early_median':early,'late_median':late,
                        'late_vs_early_percent':100*(late/early-1)})
    line,=ax.plot(ns,med,label=label); ax.fill_between(ns,low,high,color=line.get_color(),alpha=.12)
ax.set(xlabel='Collection order' if a.samples_at is not None else 'NOP instructions per load-to-load gap',
       ylabel='Host TSC ticks per load (batch / 2 iterations)')
ax.set_title(f'Individual samples at N={a.samples_at}' if a.samples_at is not None else f'Median; shaded {a.band} of observed samples')
ax.legend(fontsize=6); ax.grid(alpha=.25); fig.tight_layout(); fig.savefig(a.output,dpi=180)
if summary:
    with open(a.output+'.summary.csv','w') as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
