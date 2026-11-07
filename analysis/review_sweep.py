#!/usr/bin/env python3
"""Summarize completed spacing controls, preserving each job and every sample."""
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


def write_csv(path, rows):
    if not rows: return
    with path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def mapping_audit(root,job):
    if job['environment']!='native': return {'environment':'enclave','placement':'EPC node/residency not established by these device mappings'}
    name=job['name']; log=(root/(name+'.log')).read_text()
    base=re.search(r'native data mapping: (0x[0-9a-f]+)',log)
    if not base: raise ValueError('Native mapping address missing: '+name)
    result={}
    for phase in ('before','after'):
        text=(root/(name+'.'+phase+'.smaps')).read_text()
        numa=(root/(name+'.'+phase+'.numa_maps')).read_text().splitlines()
        for block in re.split(r'(?=^[0-9a-f]+-[0-9a-f]+ )',text,flags=re.M):
            lines=block.splitlines()
            if not lines: continue
            m=re.match(r'([0-9a-f]+)-([0-9a-f]+)',lines[0])
            if m and int(m[1],16)<=int(base[1],16)<int(m[2],16):
                fields={x.split(':',1)[0]:x.split(':',1)[1].strip() for x in lines[1:] if ':' in x}
                result[phase]={'mapping':lines[0],**{x:fields.get(x) for x in ('Size','Rss','AnonHugePages','KernelPageSize','MMUPageSize','THPeligible','VmFlags')},
                               'numa_line':next((x for x in numa if x.split()[0]==m[1]),None)}
                break
        if phase not in result: raise ValueError('Native data mapping not found: '+name)
    return result


def plot_curves(jobs,curves,audits,context,out,suffix=''):
    envs=[env for env in ('native','enclave') if any(j['environment']==env for j in jobs)]
    tags=sorted({j['parameters']['tag'] for j in jobs}); colors={tag:f'C{i%10}' for i,tag in enumerate(tags)}
    def label(job):
        tag=job['parameters']['tag']; cover=audits[job['name']].get('thp_coverage_percent')
        if cover:
            a,b=cover['before'],cover['after']
            tag+=f' ({a:.2f}% THP)' if a==b else f' ({a:.2f}->{b:.2f}% THP)'
        return tag
    fig,axes=plt.subplots(len(envs),2,figsize=(12,4*len(envs)),sharex=True,squeeze=False)
    for row,env in enumerate(envs):
        for dep in (0,1):
            ax=axes[row,dep]
            for job in jobs:
                if job['environment']!=env: continue
                points=curves[job['name']][1]; ns=sorted({n for n,d in points}); tag=job['parameters']['tag']
                ax.plot(ns,[points[n,dep]['median'] for n in ns],'o-',markersize=2.5,color=colors[tag],label=label(job))
                ax.fill_between(ns,[points[n,dep]['p10'] for n in ns],[points[n,dep]['p90'] for n in ns],color=colors[tag],alpha=.10)
            ax.set_title(env+(' dependent' if dep else ' independent')); ax.grid(alpha=.25); ax.legend(fontsize=7)
            if row==len(envs)-1: ax.set_xlabel('NOP instructions per load-to-load gap')
            if dep==0: ax.set_ylabel('Host TSC ticks per load')
    fig.suptitle(context+'\nMedians with observed p10–p90; all samples in reviewed jobs retained; panel y-scales differ',fontsize=11)
    fig.tight_layout()
    for ext in ('png','pdf'): fig.savefig(out/('curves'+suffix+'.'+ext),dpi=180)
    plt.close(fig)
    fig,axes=plt.subplots(1,len(envs),figsize=(5.5*len(envs),4.5),sharey=True,squeeze=False)
    axes=axes[0]
    for ax,env in zip(axes,envs):
        for job in jobs:
            if job['environment']!=env: continue
            points=curves[job['name']][1]; ns=sorted({n for n,d in points}); tag=job['parameters']['tag']
            ax.plot(ns,[points[n,0]['median']/points[n,1]['median'] for n in ns],'o-',markersize=2.5,color=colors[tag],label=label(job))
        ax.axhline(1,color='black',ls=':',lw=1); ax.set(title=env,xlabel='NOP instructions per gap'); ax.grid(alpha=.25); ax.legend(fontsize=7)
    axes[0].set_ylabel('Independent median / dependent median')
    fig.suptitle(context+'\nRelative timing: ratio of separate medians, not paired samples',fontsize=10)
    fig.tight_layout()
    for ext in ('png','pdf'): fig.savefig(out/('relative-timing'+suffix+'.'+ext),dpi=180)
    plt.close(fig)


def review(root,out,completed_only=False):
    manifest=json.loads((root/'manifest.json').read_text())
    summaries=[]; curves={}; adjacent=[]; audits={}; raw_paths=[root/'manifest.json']
    total=migration=faulted=switched=0; build_ids=set(); machines=set(); unreviewed=[]
    for job in manifest['jobs']:
        name=job['name']; params=job['parameters']
        if job.get('status')!='success':
            if not completed_only: raise ValueError('Incomplete job: '+name)
            unreviewed.append({'job':name,'status':job.get('status','not started'),'returncode':job.get('returncode')})
            continue
        path=root/(name+'.csv'); raw_paths.append(path)
        with path.open() as f: rows=list(csv.DictReader(f))
        if len(rows)!=job['sample_count']: raise ValueError('Manifest count mismatch: '+name)
        if len(rows)!=len(range(params['lo'],params['hi']+1,params['step']))*2*params['samples']:
            raise ValueError('Unexpected sweep sample count: '+name)
        total+=len(rows)
        for r in rows:
            if r['method']!='rob-v2': raise ValueError('Separate benchmark methods')
            expected={'footprint_bytes':params['kib']*1024,'node_stride':params['stride'],
                      'iterations':params['iters'],'seed':params['seed'],'order_seed':manifest['order_seed'],
                      'nop_bytes':params['width'],'loop_alignment':params['align'],'cpu_id':manifest['cpu']}
            if any(int(r[key])!=value for key,value in expected.items()):
                raise ValueError('Raw parameters differ from manifest: '+name)
            environment='sgx-hw-debug' if job['environment']=='enclave' else 'native'
            if r['environment']!=environment or r['page_policy']!=('epc' if job['environment']=='enclave' else params['pages']):
                raise ValueError('Environment/page policy differs from manifest: '+name)
            if r['timer_unit']!='tsc_ticks': raise ValueError('Unexpected timing unit: '+name)
            build_ids.add(r['build_id']); migration+=r['status']=='migration'
            machines.add(r['machine_id'])
            faulted+=int(r['minor_faults'])+int(r['major_faults'])>0
            switched+=int(r['voluntary_cs'])+int(r['involuntary_cs'])>0
        if any(r['status']!='ok' for r in rows): raise ValueError('Resolve non-ok rows explicitly before this all-sample review')
        if params['iters']==0: continue  # Cannot normalize a zero-work overhead control.
        points={}
        for n in range(params['lo'],params['hi']+1,params['step']):
            for dep in (0,1):
                rr=sorted((r for r in rows if int(r['nops_per_gap'])==n and int(r['dependent'])==dep),key=lambda r:int(r['sample_id']))
                if len(rr)!=params['samples'] or [int(r['sample_id']) for r in rr]!=list(range(params['samples'])):
                    raise ValueError('Incomplete or duplicate condition: '+name)
                v=[int(r['elapsed_ticks'])/(2*int(r['iterations'])) for r in rr]
                clean=[x for r,x in zip(rr,v) if not (int(r['minor_faults'])+int(r['major_faults'])+int(r['voluntary_cs'])+int(r['involuntary_cs']))]
                q=stats.quantiles(v,n=10,method='inclusive') if len(v)>1 else [v[0]]*9
                third=max(1,len(v)//3); early,late=stats.median(v[:third]),stats.median(v[-third:])
                point=dict(job=name,environment=job['environment'],tag=params['tag'],seed=params['seed'],
                           stride=params['stride'],pages=rr[0]['page_policy'],footprint_bytes=params['kib']*1024,
                           span_bytes=int(rr[0]['span_bytes']),nop_bytes=params['width'],alignment=params['align'],
                           nops_per_gap=n,dependent=dep,samples=len(v),median=stats.median(v),minimum=min(v),
                           p10=q[0],p90=q[8],maximum=max(v),early_median=early,late_median=late,
                           late_vs_early_percent=100*(late/early-1),
                           samples_with_faults=sum(int(r['minor_faults'])+int(r['major_faults'])>0 for r in rr),
                           samples_with_context_switches=sum(int(r['voluntary_cs'])+int(r['involuntary_cs'])>0 for r in rr),
                           unflagged_samples=len(clean),unflagged_median=stats.median(clean) if clean else '')
                summaries.append(point); points[n,dep]=point
        curves[name]=(job,points); audits[name]=mapping_audit(root,job)
        if job['environment']=='native' and params['pages'] in ('huge','collapse'):
            coverage={phase:100*int(audits[name][phase]['AnonHugePages'].split()[0])*1024/int(next(iter(points.values()))['span_bytes']) for phase in ('before','after')}
            audits[name]['thp_coverage_percent']=coverage
            audits[name]['page_control_status']='full at snapshots' if all(x==100 for x in coverage.values()) else 'incomplete huge-page backing; page-size control inconclusive'
            if params['pages']=='collapse' and any(x!=100 for x in coverage.values()):
                raise ValueError('Strict huge-page control lacks full backing: '+name)
        ns=sorted({n for n,d in points})
        for lo,hi in zip(ns,ns[1:]):
            a,b=points[lo,0],points[hi,0]
            adjacent.append(dict(job=name,environment=job['environment'],seed=params['seed'],stride=params['stride'],
                n_before=lo,n_after=hi,independent_median_before=a['median'],independent_median_after=b['median'],
                independent_median_change=b['median']-a['median'],
                independent_minimum_change=b['minimum']-a['minimum'],
                independent_unflagged_median_change=b['unflagged_median']-a['unflagged_median'] if a['unflagged_median']!='' and b['unflagged_median']!='' else '',
                dependent_median_change=points[hi,1]['median']-points[lo,1]['median'],
                ratio_before=a['median']/points[lo,1]['median'],ratio_after=b['median']/points[hi,1]['median']))
    if not curves: raise ValueError('No nonzero-work sweep data')
    if len(build_ids)!=1: raise ValueError('Separate different source/build identities')
    if len(machines)!=1: raise ValueError('Separate different machines')
    out.mkdir(parents=True,exist_ok=True)
    write_csv(out/'summary.csv',summaries); write_csv(out/'adjacent-changes.csv',adjacent)
    largest=[max((r for r in adjacent if r['job']==name),key=lambda r:r['independent_median_change']) for name in curves if any(r['job']==name for r in adjacent)]
    write_csv(out/'largest-adjacent-changes.csv',largest)
    sensitivity=[]
    for name in curves:
        for metric in ('independent_median_change','independent_minimum_change','independent_unflagged_median_change'):
            eligible=[r for r in adjacent if r['job']==name and r[metric]!='']
            if eligible:
                r=max(eligible,key=lambda r:r[metric])
                sensitivity.append(dict(job=name,metric=metric,n_before=r['n_before'],n_after=r['n_after'],change=r[metric]))
    write_csv(out/'largest-sensitivity-changes.csv',sensitivity)
    audit=dict(stage=manifest['stage'],samples=total,migration_samples=migration,samples_with_faults=faulted,
               samples_with_context_switches=switched,build_ids=sorted(build_ids),
               sibling_state_claim=manifest['sibling_state_claim'],sibling_cpu_ticks={j['name']:j.get('sibling_cpu_ticks') for j in manifest['jobs']},
               partial_campaign=bool(unreviewed),unreviewed_jobs=unreviewed,
               mapping_audit=audits,input_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in raw_paths},
               summary_rule='All samples retained; unflagged median is a sensitivity diagnostic, not the primary estimator',
               interpretation='Largest adjacent changes are descriptive observations, not automatic ROB capacity estimates')
    (out/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    jobs=sorted((x[0] for x in curves.values()),key=lambda j:j['name'])
    context=f"{next(iter(machines))} {manifest['stage']}; CPU {manifest['cpu']}, requested memory node {manifest.get('numa_node_requested')}"
    if unreviewed: context+='; completed jobs only, campaign incomplete'
    plot_curves(jobs,curves,audits,context,out)
    footprints=sorted({j['parameters']['kib'] for j in jobs})
    if len(footprints)>1:
        for kib in footprints:
            group=[j for j in jobs if j['parameters']['kib']==kib]
            plot_curves(group,curves,audits,context+f'; {kib} KiB footprint',out,f'-{kib}KiB')
    print(f'{total} samples; {migration} migration; {faulted} with faults; {switched} with context-switch deltas')
    for r in largest: print(f"{r['job']}: largest independent adjacent increase {r['n_before']}->{r['n_after']}: {r['independent_median_change']:.2f} ticks/load; ratio {r['ratio_before']:.3f}->{r['ratio_after']:.3f}")
    print('Saved review artifacts to '+str(out))
    if unreviewed: print('Campaign incomplete; unreviewed jobs: '+', '.join(x['job'] for x in unreviewed))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--output',type=Path)
    p.add_argument('--completed-only',action='store_true',help='Review successful jobs and explicitly label the campaign incomplete')
    a=p.parse_args();review(a.directory,a.output or a.directory/'review',a.completed_only)
