#!/usr/bin/env python3
"""Compare matched calibration campaigns without pooling their samples."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load(root):
    manifest=json.loads((root/'manifest.json').read_text())
    if manifest['stage']!='calibration': raise ValueError('Expected a calibration campaign')
    data={}
    for job in manifest['jobs']:
        if job.get('status')!='success': raise ValueError('Incomplete job: '+job['name'])
        with (root/(job['name']+'.csv')).open() as f: rows=list(csv.DictReader(f))
        if len(rows)!=job['sample_count']: raise ValueError('Sample-count mismatch')
        for r in rows:
            if r['status']!='ok' or r['method']!='rob-v2' or int(r['nops_per_gap'])!=0 or int(r['iterations'])==0:
                raise ValueError('Resolve invalid/migration/zero-work samples before comparing')
            key=(job['environment'],int(r['footprint_bytes']),int(r['dependent']))
            data.setdefault(key,[]).append(r)
    for rows in data.values(): rows.sort(key=lambda r:int(r['sample_id']))
    return manifest,data

def compare(first,repeat,out):
    m0,d0=load(first); m1,d1=load(repeat)
    for key in ('cpu','numa_node_requested','binary_sha256'):
        if m0[key]!=m1[key]: raise ValueError('Campaigns differ in '+key)
    jobs=lambda m:{j['name']:j['parameters'] for j in m['jobs']}
    if jobs(m0)!=jobs(m1) or d0.keys()!=d1.keys(): raise ValueError('Workload parameters do not match')
    output=[]
    for key in sorted(d0):
        r=dict(environment=key[0],footprint_bytes=key[1],dependent=key[2])
        for label,data in (('first',d0),('repeat',d1)):
            rows=data[key]; v=[int(x['elapsed_ticks'])/(2*int(x['iterations'])) for x in rows]
            n=max(1,len(v)//3); early=statistics.median(v[:n]); late=statistics.median(v[-n:])
            r.update({label+'_median':statistics.median(v),label+'_drift_percent':100*(late/early-1),label+'_samples':len(v)})
        r['median_change_percent']=100*(r['repeat_median']/r['first_median']-1); output.append(r)
    out.mkdir(parents=True,exist_ok=True)
    with (out/'comparison.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(output[0])); writer.writeheader(); writer.writerows(output)
    inputs=[first/'manifest.json',repeat/'manifest.json']+list(first.glob('*-native.csv'))+list(first.glob('*-enclave.csv'))+list(repeat.glob('*-native.csv'))+list(repeat.glob('*-enclave.csv'))
    (out/'comparison-inputs.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs)},indent=2)+'\n')
    fig,axes=plt.subplots(2,2,figsize=(11,7),sharex=True)
    for row,env in enumerate(('native','enclave')):
        for dep in (0,1):
            ax=axes[row,dep]; key=(env,256*1048576,dep)
            for data,label,color in ((d0,'first, order seed '+str(m0['order_seed']),'tab:blue'),(d1,'repeat, order seed '+str(m1['order_seed']),'tab:orange')):
                rows=data[key]; xs=[int(r['sample_id']) for r in rows]
                ys=[int(r['elapsed_ticks'])/(2*int(r['iterations'])) for r in rows]
                ax.plot(xs,ys,'o-',label=label,color=color,markersize=3)
                flags=[i for i,r in enumerate(rows) if int(r['voluntary_cs'])+int(r['involuntary_cs'])]
                ax.scatter([xs[i] for i in flags],[ys[i] for i in flags],color=color,marker='x',s=55,zorder=4)
            ax.set_title(env+(' dependent' if dep else ' independent')); ax.grid(alpha=.25); ax.legend(fontsize=8)
            if row==1: ax.set_xlabel('Sample ID within condition')
            if dep==0: ax.set_ylabel('Host TSC ticks per load')
    fig.suptitle('Artemisia 256 MiB calibration repeat; N=0, identical binaries\nAll samples retained; × indicates a context-switch delta; panel y-scales differ')
    fig.tight_layout()
    for ext in ('png','pdf'): fig.savefig(out/('256MiB-comparison.'+ext),dpi=180)
    plt.close(fig)
    for r in output:
        if r['footprint_bytes']==256*1048576:
            print(f"{r['environment']} dep={r['dependent']}: median {r['first_median']:.2f} -> {r['repeat_median']:.2f} ({r['median_change_percent']:+.2f}%); repeat drift {r['repeat_drift_percent']:+.2f}%")
    print('Saved comparison to '+str(out))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('first',type=Path); p.add_argument('repeat',type=Path); p.add_argument('--output',type=Path)
    a=p.parse_args(); compare(a.first,a.repeat,a.output or a.repeat/'review')
