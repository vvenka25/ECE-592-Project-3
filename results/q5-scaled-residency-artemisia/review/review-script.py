#!/usr/bin/env python3
"""Review one or several suite campaigns, keeping machines/runs/repeats separate."""
import argparse
import csv
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics as st
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

NAMES={3:{0:'conditional',1:'branchless'},1:{0:'IMUL streams'},
       2:{0:'younger independent',1:'dependency serialized',2:'LFENCE serialized'},
       5:{0:'GPR LEA one chain',1:'GPR LEA four chains',2:'NOP window control',4:'GPR LEA dependent loads',6:'GPR LEA eight chains'},
       8:{0:'compact',1:'scattered'}}
def write_csv(path,rows):
    if not rows:return
    with path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def load(root):
    m=json.loads((root/'manifest.json').read_text());result=[];hashes={}
    paths=[root/'manifest.json',root/'metadata.txt',root/'source-snapshot.tar.gz']
    for job in m['jobs']:
        if job.get('status')!='success':raise ValueError('Incomplete campaign: '+str(root)+' '+job['name'])
        p=job['parameters'];path=root/(job['name']+'.csv');paths.append(path)
        paths += list(root.glob(job['name']+'.*.smaps'))+list(root.glob(job['name']+'.*.numa_maps'))
        paths += list(root.glob(job['name']+'.*.page_nodes.csv'))
        paths += list(root.glob(job['name']+'.platform-*.json'))+[root/(job['name']+'.log')]
        with path.open() as f:rows=list(csv.DictReader(f))
        params=list(range(p['lo'],p['hi']+1,p['step'])) if 'lo' in p else [p['param']]
        if len(rows)!=job['sample_count'] or len(rows)!=len(params)*p['samples']:raise ValueError('Incomplete CSV: '+str(path))
        for r in rows:
            if r['method']!='trackb-v1' or r['question']!=f'Q{p["question"]}' or r['timer_unit']!='tsc_ticks':raise ValueError('Mixed question/method/units')
            expected=dict(mode=p['mode'],iterations=p['iterations'],seed=p['seed'],cpu_id=m['cpu'],order_seed=m['order_seed']+job['repetition']-1)
            if any(int(r[k])!=v for k,v in expected.items()):raise ValueError('Raw parameters differ from manifest')
            footprint=0 if p['question']==1 else int(r['param'])*64 if p['question']==8 else p['kib']*1024
            span=0 if p['question']==1 else (int(r['param'])*4096 if p['mode'] else (footprint+4095)//4096*4096) if p['question']==8 else footprint
            if int(r['footprint_bytes'])!=footprint or int(r['span_bytes'])!=span:raise ValueError('Unexpected footprint/span')
            if int(r['work_per_iteration'])!=(32 if p['question']==1 else 2 if p['question']==5 else 1):raise ValueError('Unexpected normalization')
            if r['environment']!=('native' if job['environment']=='native' else 'sgx-hw-debug'):raise ValueError('Environment mismatch')
            if r['status']!='ok':raise ValueError('Resolve migration/invalid samples before this all-sample analysis')
        if len({r['build_id'] for r in rows})!=1:raise ValueError('Mixed binary identities')
        if job.get('placement_verified') is False:raise ValueError('Native placement treatment failed; review the retained mapping evidence explicitly')
        if job.get('sibling_gate_passed') is False:raise ValueError('Required idle-sibling gate failed; review retained interference evidence explicitly')
        for param in params:
            rr=sorted((r for r in rows if int(r['param'])==param),key=lambda r:int(r['sample_id']))
            if [int(r['sample_id']) for r in rr]!=list(range(p['samples'])):raise ValueError('Duplicate/missing condition')
            work=int(rr[0]['iterations'])*int(rr[0]['work_per_iteration'])
            vals=[int(r['elapsed_ticks'])/(work or 1) for r in rr]
            qs=st.quantiles(vals,n=10,method='inclusive') if len(vals)>1 else [vals[0]]*9
            flags=[sum(int(r[k]) for k in ('minor_faults','major_faults','voluntary_cs','involuntary_cs'))>0 for r in rr]
            clean=[v for v,flag in zip(vals,flags) if not flag]
            point=dict(campaign=str(root),purpose=m['purpose'],job=job['name'],question=p['question'],machine=rr[0]['machine_id'],
                       environment=job['environment'],repetition=job['repetition'],build_id=rr[0]['build_id'],
                       mode=p['mode'],param=param,seed=p['seed'],order_seed=int(rr[0]['order_seed']),cpu=m['cpu'],
                       numa_node=m['numa_node_requested'],footprint_bytes=int(rr[0]['footprint_bytes']),span_bytes=int(rr[0]['span_bytes']),
                       iterations=p['iterations'],work_per_iteration=int(rr[0]['work_per_iteration']),work_unit=rr[0]['work_unit'] if work else 'invocation',
                       samples=len(vals),median=st.median(vals),minimum=min(vals),p10=qs[0],p90=qs[8],maximum=max(vals),
                       early_median=st.median(vals[:max(1,len(vals)//3)]),late_median=st.median(vals[-max(1,len(vals)//3):]),
                       samples_with_faults=sum(int(r['minor_faults'])+int(r['major_faults'])>0 for r in rr),
                       samples_with_context_switches=sum(int(r['voluntary_cs'])+int(r['involuntary_cs'])>0 for r in rr),
                       unflagged_median=st.median(clean) if clean else '',pmu_status=rr[0]['pmu_status'],pmu_scope=rr[0]['pmu_scope'])
            usable=work and all(r['pmu_status']=='ok' and int(r['pmu_time_enabled'])>0 and
                               int(r['pmu_time_running'])/int(r['pmu_time_enabled'])>=.98 for r in rr)
            for i in range(3):
                point[f'pmu_name{i}']=rr[0][f'pmu_name{i}']
                point[f'pmu{i}_per_work']=st.median(int(r[f'pmu{i}'])/work for r in rr) if usable else ''
            point['native_pmu_qualified']=bool(usable and job['environment']=='native')
            result.append(point)
    for path in paths:hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    return m,result,hashes

def contrasts(points):
    groups=defaultdict(list);out=[]
    for p in points:groups[p['campaign'],p['question'],p['environment'],p['repetition']].append(p)
    def emit(group,kind,a,b,qualification,extra=''):
        if not a or not b:return
        if a['build_id']!=b['build_id'] or a['iterations']!=b['iterations']:raise ValueError('Unmatched contrast')
        out.append(dict(campaign=group[0],question=group[1],environment=group[2],repetition=group[3],contrast=kind,
                        baseline_job=a['job'],treatment_job=b['job'],baseline_median=a['median'],treatment_median=b['median'],
                        delta=b['median']-a['median'],treatment_over_baseline=b['median']/a['median'],qualification=qualification,
                        additional_cost_per_stlb_miss=extra))
    for group,pp in groups.items():
        q=group[1]
        def find(**kw):return next((p for p in pp if all(p[k]==v for k,v in kw.items())),None)
        if q==3:
            for mode in (0,1):
                base=find(mode=mode,param=2)
                for p in pp:
                    if p['mode']==mode and p['param']==3:emit(group,'shuffled-minus-alternating-'+NAMES[3][mode],base,p,'Pattern contrast; timing delta is not automatically a misprediction penalty')
        elif q==1:
            emit(group,'four-chains-versus-one',find(param=1,iterations=next((p['iterations'] for p in pp if p['iterations']),-1)),
                 find(param=4),'Fixed 32 IMUL operations; combine latency/throughput difference with single-resource model; replication alternative remains explicit')
        elif q==2:
            for p in pp:
                if p['mode'] in (1,2):emit(group,NAMES[2][p['mode']]+'-versus-independent',find(mode=0,param=p['param'],footprint_bytes=p['footprint_bytes']),p,
                                          'Assembly places blocked older IMUL before younger work; compare K=0 fence cost and hot/cold controls')
        elif q==5:
            for point in pp:
                if point['mode']!=2:emit(group,'GPR-allocation-versus-NOP-at-N='+str(point['param']),find(mode=2,param=point['param']),point,
                                        'Integer GPR64 speculative allocation diagnostic; account for execution/scheduler limits and committed mappings before total PRF conversion')
        elif q==8:
            for p in pp:
                if p['mode']!=1:continue
                base=find(mode=0,param=p['param']);qual='Inconclusive miss attribution: qualified native PMU coverage/cache control unavailable';extra=''
                if base and p['native_pmu_qualified'] and base['native_pmu_qualified']:
                    hit=p['pmu0_per_work']-base['pmu0_per_work']
                    if hit>.5 and max(p['pmu1_per_work'],base['pmu1_per_work'])<.01 and max(p['pmu2_per_work'],base['pmu2_per_work'])<.01 and base['pmu0_per_work']<.05:
                        qual='Supports L1 DTLB miss resolved by STLB: delta STLB hits/load >0.5, baseline <0.05; walks and L1D misses/load <0.01'
                        extra=(p['median']-base['median'])/hit
                    else:qual='Inconclusive requested miss class: native PMU rates do not meet declared cache/walk/baseline criteria'
                if p['purpose']!='measurement':qual='Functional/pilot validation only; no final miss-cost inference';extra=''
                emit(group,'scattered-minus-compact',base,p,qual,extra)
    return out

def review(roots,out):
    points=[];audits={}
    for root in roots:
        m,pp,hashes=load(root);points+=pp
        audits[str(root)]=dict(manifest=m,input_sha256=hashes)
    out.mkdir(parents=True,exist_ok=True)
    script=Path(__file__).read_bytes()
    (out/'review-script.py').write_bytes(script)
    (out/'analysis-provenance.json').write_text(json.dumps(dict(script_sha256=hashlib.sha256(script).hexdigest(),
        python=sys.version,matplotlib=matplotlib.__version__,argv=sys.argv),indent=2)+'\n')
    write_csv(out/'summary.csv',points);write_csv(out/'contrasts.csv',contrasts(points))
    adjacent=[];curves=defaultdict(list)
    for point in points:
        if point['question']==5:curves[point['campaign'],point['job']].append(point)
    for (campaign,job),curve in curves.items():
        curve.sort(key=lambda p:p['param'])
        for a,b in zip(curve,curve[1:]):
            adjacent.append(dict(campaign=campaign,job=job,n_before=a['param'],n_after=b['param'],
                                 median_change=b['median']-a['median'],minimum_change=b['minimum']-a['minimum']))
    write_csv(out/'q5-adjacent-changes.csv',adjacent)
    (out/'audit.json').write_text(json.dumps(audits,indent=2)+'\n')
    for q in (3,1,2,5,8):
        pp=[p for p in points if p['question']==q and p['iterations']>0]
        if not pp:continue
        panels=sorted({(p['machine'],p['environment'],p['footprint_bytes'] if q==2 else 0) for p in pp});cols=min(2,len(panels));rows=math.ceil(len(panels)/cols)
        fig,axes=plt.subplots(rows,cols,figsize=(6*cols,4.5*rows+(1 if q==2 else 0)),squeeze=False)
        legend={}
        for ax,panel in zip(axes.flat,panels):
            curves=defaultdict(list)
            for p in pp:
                if (p['machine'],p['environment'],p['footprint_bytes'] if q==2 else 0)!=panel:continue
                curves[p['campaign'],p['repetition'],p['mode'],p['seed'],p['footprint_bytes'] if q in (2,5) else 0,p['iterations'],p['build_id']].append(p)
            for key,curve in sorted(curves.items()):
                curve.sort(key=lambda p:p['param']);p=curve[0]
                label=f"{NAMES[q].get(p['mode'],str(p['mode']))}, r{p['repetition']}, seed={p['seed']}"
                if len(roots)>1:label+=', '+Path(p['campaign']).name
                xs=[p['param'] for p in curve];ys=[p['median'] for p in curve]
                line,=ax.plot(xs,ys,'o-',markersize=3,label=label)
                legend.setdefault(label,line)
                ax.fill_between(xs,[p['p10'] for p in curve],[p['p90'] for p in curve],alpha=.10,color=line.get_color())
            labels={1:'Independent dependency chains',2:'Younger-chain IMUL instructions per iteration',3:'Pattern (0 zero; 1 one; 2 alternating; 3 shuffled)',5:'Filler instructions per load-to-load gap',8:'Nodes (equal cache-line count in each pair)'}
            selected=[p for p in pp if (p['machine'],p['environment'],p['footprint_bytes'] if q==2 else 0)==panel]
            config=f"; CPU {','.join(str(x) for x in sorted({p['cpu'] for p in selected}))}; memory node {','.join(str(x) for x in sorted({p['numa_node'] for p in selected},key=str))}"
            unit='block (one load plus arithmetic)' if q==2 else pp[0]['work_unit'].replace('_',' ')
            title=panel[0]+' '+panel[1]+config
            if q==2:title=panel[0]+' '+panel[1]+'\n'+config.lstrip('; ')+f'; {panel[2]//1024} KiB'
            ax.set(title=title,xlabel=labels[q],ylabel='Host TSC ticks per '+unit);ax.grid(alpha=.25)
            if q!=2:ax.legend(fontsize=6)
            if q==3:ax.set_xticks([0,1,2,3]);ax.set_xticklabels(['zero','one','alternating','shuffled'])
        for ax in list(axes.flat)[len(panels):]:ax.set_visible(False)
        purpose='VALIDATION ONLY (functional/pilot)' if any(p['purpose']!='measurement' for p in pp) else 'Separate runs/repeats; all samples retained'
        fig.suptitle(f'Q{q}: {purpose}\nMedians and observed p10–p90; panel scales differ; no confidence interval',fontsize=10)
        if q==2:
            fig.legend(list(legend.values()),list(legend),loc='lower center',ncol=2,fontsize=7)
            fig.tight_layout(rect=(0,.10,1,1))
        else:fig.tight_layout()
        for ext in ('png','pdf'):fig.savefig(out/f'Q{q}.{ext}',dpi=180)
        plt.close(fig)
    note=['# Suite review','',f'{sum(p["samples"] for p in points)} raw observations retained across {len(roots)} campaign(s).',
          '',f'Faulted observations: {sum(p["samples_with_faults"] for p in points)}; context-switch deltas: {sum(p["samples_with_context_switches"] for p in points)}.',
          '', 'No campaigns, machines or repetitions are pooled. Zero-work controls remain ticks/invocation and are omitted from per-work plots.',
          '', 'Inspect summary.csv, contrasts.csv and audit.json alongside the original logs, mapping/SMT metadata and assembly validation.',
          'Q5 curves are speculative integer-GPR allocation diagnostics; no automatic total PRF capacity is reported.',
          'Q8 extra cost per additional STLB service is emitted only for the explicitly qualified native event/cache conditions; enclave counter coverage remains unverified.',
          'SMT reservation, interrupt/AEX coverage and frequency stability are not established by this analyzer.','']
    if any(p['purpose']!='measurement' for p in points):note+=['This collection contains functional/pilot validation data; do not use those observations as completed experimental conclusions.','']
    (out/'REVIEW.md').write_text('\n'.join(note));print(f'Saved {len(points)} separate condition summaries to {out}')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directories',type=Path,nargs='+');p.add_argument('--out',type=Path)
    a=p.parse_args();review(a.directories,a.out or a.directories[0]/'review')
