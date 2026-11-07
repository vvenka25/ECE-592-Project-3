#!/usr/bin/env python3
"""Read preserved Q4 and new Charnwood evidence; never run a benchmark."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'analysis'))
from compare_sweeps import load

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'results/q4-comparison')
    a=parser.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    audit={};fig,ax=plt.subplots(figsize=(9,5))
    # Artemisia's accepted full-range baseline is in its preserved frontend
    # control campaign; there is no separate v2-coarse directory to invent.
    for name in ('v2-frontend','q4-coarse-charnwood'):
        root=ROOT/'results'/name;data=load(root)
        audit[name]={k:v for k,v in data.items() if k not in ('points','raw')}
        for job in data['manifest']['jobs']:
            p=job['parameters']
            if p['kib']!=262144 or p['stride']!=64 or p['width']!=1 or p['align']!=0:continue
            key=job['name'];points=data['points']
            ns=sorted(n for j,n,d in points if j==key and d==0)
            label=data['machines'][0]+' '+job['environment']
            ax.plot(ns,[points[key,n,0]['median']/points[key,n,1]['median'] for n in ns],'o-',markersize=3,label=label)
    ax.axhline(1,color='black',ls=':',lw=1)
    ax.set(xlabel='Single-byte NOPs per load-to-load gap',ylabel='Independent median / dependent median',
           title='Q4: two-machine overlap contrast\nSeparate all-sample medians; effective window, not an exact total ROB count')
    ax.grid(alpha=.25);ax.legend(fontsize=8);fig.tight_layout()
    for ext in ('pdf','png'):fig.savefig(a.out/f'curves.{ext}',dpi=180)
    plt.close(fig)
    rows=[]
    for name in ('v2-fine','v2-fine-repeat','q4-fine-charnwood','q4-fine-repeat-charnwood'):
        root=ROOT/'results'/name;data=load(root)
        audit[name]={k:v for k,v in data.items() if k not in ('points','raw')}
        control=root/'external-controls.json'
        if control.exists():audit[name]['external_controls']=json.loads(control.read_text())
        for job in data['manifest']['jobs']:
            key=job['name'];points=data['points']
            for n in sorted(n for j,n,d in points if j==key and d==0):
                p,q=points[key,n,0],points[key,n,1]
                rows.append(dict(campaign=name,machine=data['machines'][0],environment=job['environment'],nops_per_gap=n,
                                 independent_median=p['median'],dependent_median=q['median'],ratio=p['median']/q['median']))
    with (a.out/'fine-points.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    script=Path(__file__).read_bytes();(a.out/'plot-script.py').write_bytes(script)
    (a.out/'audit.json').write_text(json.dumps(dict(campaigns=audit,analysis_sha256=hashlib.sha256(script).hexdigest(),
        python=sys.version,matplotlib=matplotlib.__version__,interpretation='No automatic total ROB estimate or cross-machine TSC-duration assumption'),indent=2)+'\n')
    print('Saved Q4 comparison without modifying preserved inputs: '+str(a.out))

if __name__=='__main__':main()
