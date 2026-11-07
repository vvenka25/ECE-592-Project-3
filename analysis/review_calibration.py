#!/usr/bin/env python3
"""Reproduce calibration summaries and figures from preserved raw samples."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import statistics as stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def review(root, out):
    manifest=json.loads((root/'manifest.json').read_text())
    groups={}; summary=[]; mappings=[]
    for job in manifest['jobs']:
        if job.get('status')!='success': raise ValueError('Incomplete job: '+job['name'])
        path=root/(job['name']+'.csv')
        rows=list(csv.DictReader(path.open()))
        if len(rows)!=job['sample_count']: raise ValueError('Sample-count mismatch: '+str(path))
        if any(r['method']!='rob-v2' or int(r['nops_per_gap'])!=0 for r in rows):
            raise ValueError('Expected v2 N=0 calibration data')
        for dep in (0,1):
            rr=sorted((r for r in rows if int(r['dependent'])==dep),key=lambda r:int(r['sample_id']))
            if not rr: raise ValueError('Missing dependency control')
            if any(r['status']!='ok' for r in rr): raise ValueError('Review migration rows explicitly before summarizing')
            vals=[int(r['elapsed_ticks'])/(2*int(r['iterations'])) for r in rr]
            q=stats.quantiles(vals,n=10,method='inclusive') if len(vals)>1 else [vals[0]]*9
            third=max(1,len(vals)//3)
            early,late=stats.median(vals[:third]),stats.median(vals[-third:])
            foot=int(rr[0]['footprint_bytes']); env=job['environment']
            key=(env,foot,dep)
            if key in groups: raise ValueError('Separate repeated cases rather than silently pooling')
            groups[key]=(rr,vals)
            summary.append(dict(environment=env,footprint_bytes=foot,dependent=dep,samples=len(rr),
                median=stats.median(vals),minimum=min(vals),p10=q[0],p90=q[8],maximum=max(vals),
                early_median=early,late_median=late,late_vs_early_percent=100*(late/early-1),
                samples_with_context_switches=sum(int(r['voluntary_cs'])+int(r['involuntary_cs'])>0 for r in rr),
                samples_with_faults=sum(int(r['minor_faults'])+int(r['major_faults'])>0 for r in rr),
                run_id=rr[0]['run_id'],build_id=rr[0]['build_id']))
        # Audit actual native mapping, and retain the EPC observation limitation.
        log=(root/(job['name']+'.log')).read_text()
        base=re.search(r'native data mapping: (0x[0-9a-f]+)',log)
        record=dict(job=job['name'],environment=job['environment'],phases={})
        for phase in ('before','after'):
            smaps=(root/(job['name']+'.'+phase+'.smaps')).read_text()
            numa=(root/(job['name']+'.'+phase+'.numa_maps')).read_text().splitlines()
            blocks=re.split(r'(?=^[0-9a-f]+-[0-9a-f]+ )',smaps,flags=re.M)
            selected=[]
            for block in blocks:
                lines=block.splitlines()
                if not lines: continue
                m=re.match(r'([0-9a-f]+)-([0-9a-f]+)',lines[0])
                if not m: continue
                native=base and int(m[1],16)<=int(base[1],16)<int(m[2],16)
                if native or '/dev/sgx' in lines[0]:
                    fields={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in lines[1:] if ':' in line}
                    selected.append(dict(mapping=lines[0],details={x:fields.get(x) for x in ('Size','Rss','KernelPageSize','MMUPageSize','AnonHugePages','VmFlags')},
                        numa_line=next((line for line in numa if line.split()[0]==m[1]),None)))
            if not selected: raise ValueError('Data mapping not found: '+job['name'])
            record['phases'][phase]=selected
        mappings.append(record)
    out.mkdir(parents=True,exist_ok=True)
    summary.sort(key=lambda r:(r['environment'],r['footprint_bytes'],r['dependent']))
    with (out/'summary.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
    audit={'samples':sum(r['samples'] for r in summary),'migrations':sum(j['migration_samples'] for j in manifest['jobs']),
           'samples_with_faults':sum(r['samples_with_faults'] for r in summary),
           'samples_with_context_switches':sum(r['samples_with_context_switches'] for r in summary),
           'sibling_state_claim':manifest['sibling_state_claim'],
           'sibling_cpu_ticks':{j['name']:j['sibling_cpu_ticks'] for j in manifest['jobs']},
           'mapping_audit':mappings,
           'epc_note':'Device mappings report no N0/N1 page counts here; Rss=0 must not be interpreted as zero EPC residency or evidence of no reclamation.',
           'input_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(root.iterdir()) if x.is_file()}}
    (out/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    feet=sorted({foot for env,foot,dep in groups}); colors={0:'tab:blue',1:'tab:orange'}
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),sharey=True)
    for ax,env in zip(axes,('native','enclave')):
        for dep in (0,1):
            rr=[next(r for r in summary if r['environment']==env and r['footprint_bytes']==foot and r['dependent']==dep) for foot in feet]
            xs=[foot/1048576 for foot in feet]; ys=[r['median'] for r in rr]
            ax.errorbar(xs,ys,yerr=[[r['median']-r['p10'] for r in rr],[r['p90']-r['median'] for r in rr]],fmt='o-',capsize=3,color=colors[dep],label='dependent' if dep else 'independent')
        ax.set(xscale='log',yscale='log',title=env,xlabel='Full-traversal footprint')
        ax.set_xticks([foot/1048576 for foot in feet]); ax.set_xticklabels(['16 KiB' if foot==16384 else f'{foot/1048576:g} MiB' for foot in feet],rotation=25)
        ax.grid(alpha=.25); ax.legend()
    axes[0].set_ylabel('Median host TSC ticks per load (log scale)')
    fig.suptitle('Artemisia v2 calibration at N=0; bars show observed p10–p90')
    fig.tight_layout()
    for ext in ('png','pdf'): fig.savefig(out/('footprint-summary.'+ext),dpi=180)
    plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(11,7),sharex=True)
    for row,env in enumerate(('native','enclave')):
        for dep in (0,1):
            ax=axes[row,dep]
            for foot,color in ((128*1048576,'tab:purple'),(256*1048576,'tab:green')):
                if (env,foot,dep) not in groups: continue
                rr,vals=groups[env,foot,dep]; xx=[int(r['sample_id']) for r in rr]
                ax.plot(xx,vals,'o-',color=color,label=f'{foot//1048576} MiB',markersize=3)
                disturbed=[i for i,r in enumerate(rr) if int(r['voluntary_cs'])+int(r['involuntary_cs'])]
                ax.scatter([xx[i] for i in disturbed],[vals[i] for i in disturbed],marker='x',s=45,color='crimson',zorder=4)
            ax.set_title(env+(' dependent' if dep else ' independent')); ax.grid(alpha=.25); ax.legend(fontsize=8)
            if row==1: ax.set_xlabel('Sample ID within condition (collection order)')
            if dep==0: ax.set_ylabel('Host TSC ticks per load')
    fig.suptitle('Large-footprint samples; red × marks a recorded context-switch delta\nAll samples retained; panel y-scales differ')
    fig.tight_layout()
    for ext in ('png','pdf'): fig.savefig(out/('large-footprint-samples.'+ext),dpi=180)
    plt.close(fig)
    print(f'Summarized {audit["samples"]} samples; {audit["migrations"]} migration, {audit["samples_with_faults"]} faulted, {audit["samples_with_context_switches"]} with context-switch deltas')
    print('Saved summary.csv, audit.json, and PNG/PDF figures to '+str(out))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path); p.add_argument('--output',type=Path)
    a=p.parse_args(); review(a.directory,a.output or a.directory/'review')
