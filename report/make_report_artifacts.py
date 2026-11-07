#!/usr/bin/env python3
"""Build report tables, original figures and source excerpts from HW3 artifacts.

This reads completed campaigns; it does not execute a benchmark. No Project 1
content, numerical evidence or artwork is consumed by this generator.
"""
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics as stats
import subprocess as sp
import sys
import tempfile
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path[:0]=[str(ROOT/'trackb'),str(ROOT/'analysis')]
import review as suite
from compare_sweeps import load as load_rob

OUT=ROOT/'report/generated'
FIG=ROOT/'report/figures'
SNIP=ROOT/'report/snippets'
BLUE='#215b83';ORANGE='#bc5b27';TEAL='#167c72';GRAY='#69717a';RED='#a63f3f'
plt.rcParams.update({'font.size':10,'axes.titlesize':10.5,'axes.labelsize':10,
    'legend.fontsize':8,'font.family':'DejaVu Sans','pdf.fonttype':42,
    'svg.hashsalt':'hw3-original-report-diagrams','axes.spines.top':False,
    'axes.spines.right':False,'savefig.facecolor':'white'})

CAMPAIGNS={
 1:('q1-charnwood-private','q1-artemisia'),
 2:('q2-charnwood-private','q2-artemisia-retry'),
 3:('q3-charnwood-private','q3-artemisia'),
 5:('q5-fine-charnwood-private','q5-fine-artemisia'),
 8:('q8-clock-charnwood-private','q8-clock-artemisia')}
COARSE5=('q5-charnwood-private','q5-scaled-residency-artemisia')
ROB_NAMES=('q4-coarse-charnwood','q4-fine-charnwood','q4-fine-repeat-charnwood',
           'v2-frontend','v2-fine','v2-fine-repeat')
DATA={};ROB={};INPUTS={};RAW={};EXCERPTS={}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load_data():
    for name in [n for names in CAMPAIGNS.values() for n in names]+list(COARSE5):
        root=Path('results')/name
        manifest,points,hashes=suite.load(root)
        assert manifest['purpose']=='measurement'
        DATA[name]=(manifest,points);INPUTS.update(hashes)
        for job in manifest['jobs']:
            path=root/(job['name']+'.csv')
            with path.open() as f:RAW[str(path)]=list(csv.DictReader(f))
    for name in ROB_NAMES:
        ROB[name]=load_rob(Path('results')/name)
        INPUTS.update(ROB[name]['input_sha256'])
    for name in ('trackb/gen_kernels.py','trackb/main.c','trackb/engine.c','trackb/Makefile',
                 'trackb/Enclave.config.xml','trackb/pmu.c','scripts/gen_kernels.py',
                 'enclave/Rob.config.xml','report/make_report_artifacts.py',
                 'trackb/review.py','analysis/compare_sweeps.py'):
        INPUTS[name]=sha(name)

def point(q,host='artemisia',env='native',rep=1,param=None,mode=0,seed=42,kib=None,coarse=False):
    index=0 if host=='charnwood' else 1
    name=(COARSE5 if coarse else CAMPAIGNS[q])[index]
    pp=DATA[name][1]
    if q==2 and kib is None:kib=262144
    found=[p for p in pp if p['environment']==env and p['repetition']==rep and
        (param is None or p['param']==param) and p['mode']==mode and p['seed']==seed and
        (kib is None or p['footprint_bytes']==kib*1024) and p['iterations']>0]
    assert len(found)==1,(q,host,env,rep,param,mode,kib,len(found))
    return found[0]

def vals(p,metric='ticks'):
    if metric=='ticks':return p['median'],p['p10'],p['p90']
    rows=RAW[p['campaign']+'/'+p['job']+'.csv']
    rows=[r for r in rows if int(r['param'])==p['param']]
    assert p['environment']=='native' and p['native_pmu_qualified']
    column='pmu3' if p['question']==8 else 'pmu0'
    numbers=[int(r[column])/(int(r['iterations'])*int(r['work_per_iteration'])) for r in rows]
    qq=stats.quantiles(numbers,n=10,method='inclusive')
    return stats.median(numbers),qq[0],qq[8]

def pair(q,host='artemisia',env='native',param=None,mode=0,metric='ticks',digits=2,**kw):
    v=[vals(point(q,host,env,rep,param,mode,**kw),metric)[0] for rep in (1,2)]
    return ' / '.join(f'{x:.{digits}f}' for x in v)

def table(name,headers,rows):
    content=['% Generated from actual raw HW3 measurements. R1 / R2 are separate processes.',
             r'\begin{tabular}{'+'l'+'r'*(len(headers)-1)+'}',r'\toprule',
             ' & '.join(headers)+r' \\',r'\midrule']
    content+=[' & '.join(str(x) for x in row)+r' \\' for row in rows]
    content += [r'\bottomrule',r'\end{tabular}','']
    (OUT/(name+'.tex')).write_text('\n'.join(content))

def q4p(host,env,rep,n,dep=0):
    name=('q4-fine-charnwood' if rep==1 else 'q4-fine-repeat-charnwood') if host=='charnwood' else ('v2-fine' if rep==1 else 'v2-fine-repeat')
    data=ROB[name]
    job=next(j for j in data['manifest']['jobs'] if j['environment']==env)
    return data['points'][job['name'],n,dep]

def q4pair(host,env,n,dep=0):return ' / '.join(f'{q4p(host,env,r,n,dep)["median"]:.2f}' for r in (1,2))

def build_tables():
    table('q1_native',['Chains','Charnwood cycles/IMUL','Artemisia cycles/IMUL'],
        [(n,pair(1,'charnwood',param=n,metric='cycles',digits=4),pair(1,param=n,metric='cycles',digits=4)) for n in (1,2,4)])
    table('q1_pair',['Chains','Artemisia native ticks/IMUL','Artemisia SGX ticks/IMUL'],
        [(n,pair(1,param=n,digits=4),pair(1,env='enclave',param=n,digits=4)) for n in (1,2,4)])
    conditions=[('Cold, independent, K=0',0,0,262144),('Cold, independent, K=64',0,64,262144),
        ('Cold, dependent, K=64',1,64,262144),('Cold, fenced, K=64',2,64,262144),
        ('Hot, independent, K=64',0,64,16),('Hot, dependent, K=64',1,64,16)]
    table('q2',['Condition','Charnwood native','Artemisia native','Artemisia SGX'],
        [(label,pair(2,'charnwood',param=k,mode=m,kib=f),pair(2,param=k,mode=m,kib=f),pair(2,env='enclave',param=k,mode=m,kib=f)) for label,m,k,f in conditions])
    patterns=[('Conditional, alternating',0,2,42),('Conditional, shuffled 42',0,3,42),
        ('Conditional, shuffled 271828',0,3,271828),('Branchless, alternating',1,2,42),('Branchless, shuffled 42',1,3,42)]
    table('q3_native',['Pattern','Charnwood cycles/decision','Artemisia cycles/decision'],
        [(label,pair(3,'charnwood',param=p,mode=m,seed=s,metric='cycles',digits=4),pair(3,param=p,mode=m,seed=s,metric='cycles',digits=4)) for label,m,p,s in patterns])
    table('q3_pair',['Pattern','Artemisia native ticks/decision','Artemisia SGX ticks/decision'],
        [(label,pair(3,param=p,mode=m,seed=s,digits=4),pair(3,env='enclave',param=p,mode=m,seed=s,digits=4)) for label,m,p,s in patterns])
    table('q4',['Charnwood N','Native ticks/load','Artemisia N','Native ticks/load','SGX ticks/load'],
        [(c,q4pair('charnwood','native',c),a,q4pair('artemisia','native',a),q4pair('artemisia','enclave',a)) for c,a in ((216,492),(220,496),(224,500))])
    table('q5_native',['Host','N','Four LEA chains','Eight LEA chains','NOP control','Serial loads'],
        [(host.capitalize(),n,*[pair(5,host,param=n,mode=m,digits=1) for m in (1,6,2,4)])
         for host,ns in (('charnwood',(128,136,144)),('artemisia',(200,208,216))) for n in ns])
    table('q5_pair',['N','Native four chains','SGX four chains','Native eight chains','SGX eight chains'],
        [(n,*[pair(5,env=e,param=n,mode=m,digits=1) for m,e in ((1,'native'),(1,'enclave'),(6,'native'),(6,'enclave'))]) for n in (200,208,212,216)])
    costs=suite.contrasts([p for name in CAMPAIGNS[8] for p in DATA[name][1]])
    def cost_pair(host,n):
        campaign='results/'+CAMPAIGNS[8][host=='artemisia']
        cc=[next(c for c in costs if c['campaign']==campaign and c['environment']=='native' and c['repetition']==r and f'scattered-{n}-' in c['treatment_job']) for r in (1,2)]
        assert all(c['additional_core_cycles_per_stlb_miss']!='' for c in cc)
        return ' / '.join(f'{c["additional_core_cycles_per_stlb_miss"]:.4f}' for c in cc)
    table('q8_cost',['Cache lines / nodes','Charnwood extra core cycles','Artemisia extra core cycles'],
        [(n,cost_pair('charnwood',n),cost_pair('artemisia',n)) for n in (128,256,384)])
    table('q8_pair',['Nodes','Native compact','Native scattered','SGX compact','SGX scattered'],
        [(n,*[pair(8,env=e,param=n,mode=m,digits=4) for e,m in (('native',0),('native',1),('enclave',0),('enclave',1))]) for n in (128,256,384)])
    table('samples',['Question','Charnwood rows','Artemisia native + SGX rows','Iterations / sample'],
        [(f'Q{q}',sum(p['samples'] for p in DATA[names[0]][1]),sum(p['samples'] for p in DATA[names[1]][1]),
          '1,048,576' if q==3 else '10,000' if q==5 else '100,000') for q,names in sorted(CAMPAIGNS.items())])
    with (OUT/'condition-summary.csv').open('w') as f:
        points=[p for names in CAMPAIGNS.values() for name in names for p in DATA[name][1]]
        writer=csv.DictWriter(f,fieldnames=list(points[0]));writer.writeheader();writer.writerows(points)
    with (OUT/'q8-contrasts.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(costs[0]));w.writeheader();w.writerows(costs)

def save(fig,name):
    fig.savefig(FIG/(name+'.pdf'),bbox_inches='tight',metadata={'CreationDate':None,'ModDate':None})
    fig.savefig(FIG/(name+'.svg'),bbox_inches='tight',metadata={'Date':None})
    fig.savefig(FIG/(name+'.png'),dpi=170,bbox_inches='tight')
    plt.close(fig)

def curve(ax,pp,color,label,rep=1,metric='ticks'):
    xx=[p['param'] for p in pp];vv=[vals(p,metric) for p in pp]
    ax.plot(xx,[v[0] for v in vv],color=color,marker='o' if rep==1 else 's',
        linestyle='-' if rep==1 else '--',markersize=3.5,lw=1.4,label=label if rep==1 else None)
    ax.fill_between(xx,[v[1] for v in vv],[v[2] for v in vv],color=color,alpha=.10)

def base_axes(titles,ylabel,xlabel=''):
    fig,axs=plt.subplots(1,len(titles),figsize=(8,2.65),layout='constrained',squeeze=False)
    axs=axs[0]
    for ax,title in zip(axs,titles):
        ax.set_title(title);ax.set_ylabel(ylabel);ax.set_xlabel(xlabel);ax.grid(alpha=.18);ax.set_axisbelow(True)
    return fig,axs

def result_plots():
    fig,axs=base_axes(['Two native machines','Artemisia: same kernel, two environments'],'Active core cycles / IMUL','Independent chains')
    for host,color in (('charnwood',BLUE),('artemisia',ORANGE)):
        for r in (1,2):curve(axs[0],[point(1,host,rep=r,param=n) for n in (1,2,4)],color,host.capitalize(),r,'cycles')
    for env,color in (('native',BLUE),('enclave',TEAL)):
        for r in (1,2):curve(axs[1],[point(1,env=env,rep=r,param=n) for n in (1,2,4)],color,env.upper() if env=='native' else 'Hardware SGX',r)
    axs[1].set_ylabel('Host TSC ticks / IMUL')
    for ax in axs:ax.set_xticks([1,2,4]);ax.set_ylim(bottom=0);ax.legend()
    save(fig,'q1-results')

    fig,axs=base_axes(['Two native machines: 256 MiB','Artemisia: 256 MiB'],'Host TSC ticks / block','Younger IMUL count K')
    # Native panel compares the matched independent/dependent controls on both hosts.
    for host,color in (('charnwood',BLUE),('artemisia',ORANGE)):
        for mode in (0,1):
            for r in (1,2):
                pp=[point(2,host,rep=r,param=k,mode=mode) for k in (0,64)]
                curve(axs[0],pp,color,host.capitalize()+(' ready' if mode==0 else ' dependent'),r)
                if mode==1:axs[0].lines[-1].set_linestyle(':' if r==1 else '-.')
    for env,color in (('native',BLUE),('enclave',TEAL)):
        for mode in (0,1,2):
            for r in (1,2):
                pp=[point(2,env=env,rep=r,param=k,mode=mode) for k in (0,64)]
                curve(axs[1],pp,color,('Native' if env=='native' else 'SGX')+' '+('ready','dependent','fenced')[mode],r)
                axs[1].lines[-1].set_linestyle(('-' if r==1 else '--') if mode==0 else ':' if mode==1 else '-.')
    for ax in axs:ax.set_xticks([0,64]);ax.legend(fontsize=7)
    save(fig,'q2-results')

    fig,axs=base_axes(['Two native machines','Artemisia: conditional branch'],'Active core cycles / decision')
    labels=['Branch\nregular','Branch\nshuffled','No branch\nregular','No branch\nshuffled']
    for host,color,offset in (('charnwood',BLUE,-.16),('artemisia',ORANGE,.16)):
        for r in (1,2):
            pp=[point(3,host,rep=r,param=p,mode=m) for m,p in ((0,2),(0,3),(1,2),(1,3))]
            vv=[vals(p,'cycles') for p in pp];xx=[i+offset+(r-1.5)*.05 for i in range(4)]
            axs[0].errorbar(xx,[v[0] for v in vv],yerr=[[v[0]-v[1] for v in vv],[v[2]-v[0] for v in vv]],
                fmt='o' if r==1 else 's',capsize=2,color=color,label=host.capitalize() if r==1 else None)
    axs[0].set_xticks(range(4),labels,fontsize=8);axs[0].set_ylim(bottom=0);axs[0].legend()
    for env,color in (('native',BLUE),('enclave',TEAL)):
        for r in (1,2):curve(axs[1],[point(3,env=env,rep=r,param=p) for p in (0,1,2,3)],color,'Native' if env=='native' else 'Hardware SGX',r)
    axs[1].set_xticks(range(4),['Zero','One','Alternating','Shuffled'],fontsize=8);axs[1].set_ylabel('Host TSC ticks / decision');axs[1].set_ylim(bottom=0);axs[1].legend()
    save(fig,'q3-results')

    fig,axs=base_axes(['Charnwood native: fine sweep','Artemisia: native and SGX'],'Host TSC ticks / load','Single-byte NOPs per gap N')
    for ax,host,ns,envs in ((axs[0],'charnwood',range(192,241,4),('native',)),(axs[1],'artemisia',range(480,561,4),('native','enclave'))):
        for env,color in zip(envs,(BLUE,TEAL)):
            for dep in ((0,1) if host=='charnwood' else (0,)):
                for r in (1,2):
                    pp=[q4p(host,env,r,n,dep) for n in ns]
                    ax.plot(list(ns),[p['median'] for p in pp],marker='o' if r==1 else 's',markersize=2.5,color=color if dep==0 else GRAY,
                        ls='-' if r==1 else '--',label=(('Independent' if dep==0 else 'Dependent') if host=='charnwood' else ('Native' if env=='native' else 'Hardware SGX')) if r==1 else None)
                    ax.fill_between(list(ns),[p['p10'] for p in pp],[p['p90'] for p in pp],alpha=.08,color=color if dep==0 else GRAY)
        ax.axvspan(220 if host=='charnwood' else 492,224 if host=='charnwood' else 500,color=ORANGE,alpha=.13)
        ax.legend(fontsize=8)
    axs[1].annotate('Retained SGX repeat peak\nat N=548',xy=(548,q4p('artemisia','enclave',2,548)['median']),xytext=(507,465),
        fontsize=8,arrowprops={'arrowstyle':'->','color':GRAY},color=GRAY)
    save(fig,'q4-results')

    fig,axs=plt.subplots(1,3,figsize=(8.1,3.05),layout='constrained')
    for ax,host,env,ns,title in ((axs[0],'charnwood','native',range(120,161,4),'Charnwood native'),
        (axs[1],'artemisia','native',range(192,233,4),'Artemisia native'),
        (axs[2],'artemisia','enclave',range(192,233,4),'Artemisia SGX')):
        for mode,color,label in ((1,BLUE,'Four chains'),(6,TEAL,'Eight chains'),(2,GRAY,'NOP'),(4,ORANGE,'Serial loads')):
            for r in (1,2):curve(ax,[point(5,host,env,r,n,mode) for n in ns],color,label,r)
        ax.set(title=title,xlabel='LEA/NOP writes per gap N',ylabel='Host TSC ticks / load');ax.grid(alpha=.18)
        ax.axvspan(128 if host=='charnwood' else 200,144 if host=='charnwood' else 216,color=ORANGE,alpha=.08)
    handles,labels=axs[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=4,frameon=False)
    save(fig,'q5-results')

    fig,axs=base_axes(['Charnwood native: coarse controls','Artemisia native: coarse controls'],'Host TSC ticks / load','Writes / NOPs per gap N')
    for ax,host in zip(axs,('charnwood','artemisia')):
        for mode,color,label in ((0,RED,'One chain'),(1,BLUE,'Four chains'),(6,TEAL,'Eight chains'),(2,GRAY,'NOP window'),(4,ORANGE,'Serial loads')):
            for r in (1,2):curve(ax,[point(5,host,rep=r,param=n,mode=mode,coarse=True) for n in range(0,513,16)],color,label,r)
        ax.axvspan(128 if host=='charnwood' else 200,144 if host=='charnwood' else 216,color=TEAL,alpha=.10)
        ax.axvspan(208 if host=='charnwood' else 496,224 if host=='charnwood' else 512,color=GRAY,alpha=.15)
        ax.legend(fontsize=7)
    save(fig,'q5-coarse-controls')

    fig,axs=base_axes(['Native extra cost: class-qualified','Artemisia: raw layout contrast'],'Active core cycles\nper added STLB service','Matched nodes / cache lines')
    costs=suite.contrasts([p for name in CAMPAIGNS[8] for p in DATA[name][1]])
    for host,color in (('charnwood',BLUE),('artemisia',ORANGE)):
        for r in (1,2):
            campaign='results/'+CAMPAIGNS[8][host=='artemisia']
            pp=[next(c for c in costs if c['campaign']==campaign and c['environment']=='native' and c['repetition']==r and f'scattered-{n}-' in c['treatment_job']) for n in (128,256,384)]
            axs[0].plot([128,256,384],[p['additional_core_cycles_per_stlb_miss'] for p in pp],color=color,
                marker='o' if r==1 else 's',ls='-' if r==1 else '--',label=host.capitalize() if r==1 else None)
    for env,color in (('native',BLUE),('enclave',TEAL)):
        for mode in (0,1):
            for r in (1,2):
                curve(axs[1],[point(8,env=env,rep=r,param=n,mode=mode) for n in (128,256,384)],color,
                    ('Native' if env=='native' else 'SGX')+(' compact' if mode==0 else ' scattered'),r)
                if mode==0:axs[1].lines[-1].set_linestyle(':' if r==1 else '-.')
    axs[1].set_ylabel('Host TSC ticks / load')
    for ax in axs:ax.set_ylim(bottom=0);ax.set_xticks([128,256,384]);ax.legend(fontsize=7.5)
    save(fig,'q8-results')

def snippets():
    with tempfile.TemporaryDirectory(prefix='hw3-report-asm-') as tmp:
        q=Path(tmp)/'suite';rob=Path(tmp)/'rob'
        sp.run([sys.executable,'trackb/gen_kernels.py',str(q)],check=True)
        sp.run([sys.executable,'scripts/gen_kernels.py',str(rob)],check=True)
        generated=(q/'kernels.S').read_text();original=(rob/'kernels.S').read_text()
    def body(text,name):return text.split(name+':',1)[1].split('.size '+name,1)[0].strip().splitlines()
    def hot(text,name):
        lines=body(text,name);start=next(i for i,s in enumerate(lines) if s.startswith('.Lloop_'))
        end=next(i for i in range(start,len(lines)) if lines[i].startswith('jnz '))
        return lines[start:end+1]
    def write(name,lines,function,origin):
        (SNIP/(name+'.S')).write_text('\n'.join(lines)+'\n')
        EXCERPTS[name]=dict(generator=origin,generator_sha256=sha(origin),function=function,
            note='Actual generated instructions; comments explicitly mark omitted repeated bodies.',excerpt_sha256=sha(SNIP/(name+'.S')))
    f='tb_q1_4';lines=hot(generated,f);write('q1',lines[:5]+['# The four-instruction group repeats eight times (32 IMULs).']+lines[-2:],f,'trackb/gen_kernels.py')
    f='tb_q2_overlap_64';lines=hot(generated,f);write('q2',lines[:5]+['# 63 further younger IMULs are omitted here.']+lines[-4:],f,'trackb/gen_kernels.py')
    f='tb_q3_branch';lines=hot(generated,f);write('q3',lines[:10],f,'trackb/gen_kernels.py')
    f='rob_independent_224_b1_a0';lines=hot(original,f);write('q4',lines[:2]+['# 224 actual one-byte NOPs (0x90); repeated text omitted.']+[lines[226]]+['# 224 further one-byte NOPs; repeated text omitted.']+lines[-2:],f,'scripts/gen_kernels.py')
    f='tb_q5_lea8_d0_208';lines=hot(generated,f);second=next(i for i,s in enumerate(lines) if s=='mov (%rsi),%rsi');write('q5',lines[:4]+['# Rotate over all eight accumulators: 208 LEAs/gap.']+[lines[second]]+['# 208 further scaled-index LEAs; repeated text omitted.']+lines[-2:],f,'trackb/gen_kernels.py')
    f='tb_q8_chase';write('q8',hot(generated,f),f,'trackb/gen_kernels.py')
    code=Path('trackb/main.c').read_text().splitlines()
    first=next(i for i,s in enumerate(code) if 'uint64_t start=__rdtscp' in s)
    (SNIP/'timer.c').write_text('\n'.join(s.strip() for s in code[first:first+3])+'\n')
    (SNIP/'q8-address.c').write_text('/* From trackb/engine.c, node(i): */\n'+next(s.strip() for s in Path('trackb/engine.c').read_text().splitlines() if 'return arena+i*4096' in s)+'\nreturn arena+i*64;\n')
    (OUT/'source-excerpts.json').write_text(json.dumps(EXCERPTS,indent=2)+'\n')

def write_audit():
    datasets={}
    for name,(m,pp) in DATA.items():
        datasets[name]=dict(manifest='results/'+name+'/manifest.json',question=m['question'],cpu=m['cpu'],
            numa_node=m['numa_node_requested'],purpose=m['purpose'],raw_rows=sum(p['samples'] for p in pp),
            build_ids=sorted({p['build_id'] for p in pp}),conditions=len(pp),
            faults=sum(p['samples_with_faults'] for p in pp),context_switches=sum(p['samples_with_context_switches'] for p in pp))
    for name,data in ROB.items():datasets[name]=dict(manifest='results/'+name+'/manifest.json',question='Q4',
        cpu=data['manifest']['cpu'],raw_rows=data['counts']['samples'],build_ids=data['builds'],disturbances=data['counts'])
    record=dict(generator='report/make_report_artifacts.py',python=sys.version,matplotlib=matplotlib.__version__,
        normalization='Q1: 32*I; Q2/Q3/Q8: I; Q4/Q5: 2*I. Separate process medians and inclusive p10/p90.',
        input_sha256=INPUTS,datasets=datasets,source_excerpts=EXCERPTS,
        reference_policy='Project 1 is format/structure only; none of its content is an input to this generator.',
        sample_enclave_evidence='User confirmed HW/debug SampleEnclave success; original output not saved. Custom SGX validation logs are retained.')
    (OUT/'artifact-audit.json').write_text(json.dumps(record,indent=2)+'\n')

def heading(ax,x,y,number,title):
    ax.text(x,y,f'{number}  {title}',transform=ax.transAxes,ha='left',va='top',
        fontsize=10,color=BLUE,fontweight='bold')

def box(ax,x,y,w,h,text,color=BLUE,fill='#f2f6f8',size=9):
    ax.add_patch(Rectangle((x,y),w,h,ec=color,fc=fill,lw=.9,transform=ax.transAxes))
    ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=size,
        color=color,transform=ax.transAxes)

def arrow(ax,a,b,color=GRAY,style='-',bend=0):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=9,color=color,
        lw=1,linestyle=style,connectionstyle=f'arc3,rad={bend}',transform=ax.transAxes))

def diagram(q,conditions,timing,inference):
    fig=plt.figure(figsize=(8,4.35));ax=fig.add_axes([0,0,1,1]);ax.set_axis_off()
    heading(ax,.035,.975,1,'Workload and dependencies')
    heading(ax,.035,.672,2,'Controlled comparison')
    box(ax,.035,.563,.93,.065,conditions,color=GRAY,fill='#fafbfc',size=9.4)
    heading(ax,.035,.522,3,'Timed batch and normalization')
    box(ax,.035,.415,.93,.067,timing,color=TEAL,fill='#f0f8f6',size=9.4)
    heading(ax,.035,.363,4,'Measured response')
    heading(ax,.57,.363,5,'Inference and control')
    ax.text(.57,.292,textwrap.fill(inference,44),transform=ax.transAxes,va='top',
        fontsize=9.4,linespacing=1.25,color='#202c35')
    chart=fig.add_axes([.10,.105,.40,.19]);chart.tick_params(labelsize=8,pad=2)
    chart.grid(alpha=.17);chart.xaxis.label.set_size(8.5);chart.yaxis.label.set_size(8.5)
    return fig,ax,chart

def methodology_diagrams():
    fig,ax,c=diagram(1,'Same 32 IMULs/loop; change only 1, 2 or 4 destination chains.',
        'Host timer around I=100,000 loops; ticks/IMUL = elapsed TSC / (32 I).',
        'A dependent result takes about three cycles, while independent work initiates about once per cycle. Fixed work and the separately cited single eligible IMUL resource model support pipelining; timing alone does not count replicated units.')
    ax.text(.04,.895,'One chain',fontsize=9,transform=ax.transAxes,color=GRAY)
    for x,label in ((.22,'r8 × 3'),(.43,'r8 × 3'),(.64,'r8 × 3')):box(ax,x,.833,.16,.075,label)
    arrow(ax,(.38,.87),(.43,.87));arrow(ax,(.59,.87),(.64,.87))
    ax.text(.04,.765,'Four chains',fontsize=9,transform=ax.transAxes,color=GRAY)
    for x,label in ((.22,'r8 × 3'),(.41,'r9 × 3'),(.60,'r10 × 3'),(.79,'r11 × 3')):box(ax,x,.719,.16,.075,label,color=TEAL)
    ax.text(.22,.697,'Each register feeds its next use; this four-instruction group repeats eight times.',fontsize=8,transform=ax.transAxes,color=GRAY)
    pp=[point(1,rep=1,param=n) for n in (1,2,4)];c.plot([1,2,4],[vals(p,'cycles')[0] for p in pp],'o-',color=BLUE)
    c.set(xlabel='Chains',ylabel='Core cycles/IMUL',ylim=(0,3.4),xticks=[1,2,4]);save(fig,'q1-method')

    fig,ax,c=diagram(2,'K=0 or 64 younger IMULs; independent / dependent / fenced; 16 KiB / 256 MiB.',
        'I=100,000 fenced blocks; ticks/block = elapsed TSC / I.',
        'The younger chain is ready while an older IMUL waits for the pointer load. Making it depend on that result, or fencing before it, raises cold K=64 time. A common end fence blocks overlap with the next iteration.')
    for x,w,label,col in ((.04,.19,'Older pointer\nload [r8]',BLUE),(.29,.19,'Older IMUL\nwaits for r8',RED),(.54,.22,'K younger IMULs\nindependent r9',TEAL),(.82,.14,'End\nLFENCE',GRAY)):
        box(ax,x,.80,w,.11,label,color=col)
    arrow(ax,(.23,.855),(.29,.855),RED);arrow(ax,(.48,.855),(.54,.855),GRAY,':');arrow(ax,(.76,.855),(.82,.855))
    ax.text(.04,.752,'Left to right is program order; solid red arrow is a true data dependency.',fontsize=8.6,transform=ax.transAxes)
    ax.text(.04,.712,'Control: XOR reads the older result (rAX) instead of ready r11; every block ends with LFENCE.',fontsize=8.6,transform=ax.transAxes)
    pp=[point(2,rep=1,param=64,mode=m) for m in (0,1,2)]
    c.bar(range(3),[p['median'] for p in pp],color=[TEAL,ORANGE,GRAY],width=.6)
    c.set(xticks=range(3),xticklabels=['Ready','Dependent','Fenced'],ylabel='TSC ticks/block');c.tick_params(axis='x',labelsize=7.5)
    save(fig,'q2-method')

    fig,ax,c=diagram(3,'Identical 64 KiB addresses; constants / alternating / balanced shuffled; two seeds.',
        'I=1,048,576 decisions; ticks/decision = elapsed TSC / I; branch retained in assembly.',
        'Shuffled outcomes increase native misses and core-cycle cost. The same outcome change barely affects branchless arithmetic, which helps distinguish prediction from the cost of reading the array. No single-miss penalty is inferred.')
    bits=[i&1 for i in range(65536)];seed=42;mask=(1<<64)-1
    for i in range(len(bits)-1,0,-1):
        seed^=(seed<<13)&mask;seed^=seed>>7;seed^=(seed<<17)&mask;j=seed%(i+1);bits[i],bits[j]=bits[j],bits[i]
    for y,label,values in ((.84,'Alternating',[i&1 for i in range(12)]),(.73,'Seed 42 prefix',bits[:12])):
        ax.text(.04,y+.035,label,transform=ax.transAxes,va='center',fontsize=8.5)
        for i,value in enumerate(values):box(ax,.23+i*.059,y,.05,.07,str(value),color=TEAL if value else BLUE)
    pp=[point(3,rep=1,param=p,mode=m) for m,p in ((0,2),(0,3),(1,2),(1,3))]
    c.bar(range(4),[vals(p,'cycles')[0] for p in pp],color=[BLUE,ORANGE,GRAY,GRAY],width=.6)
    c.set(xticks=range(4),xticklabels=['Alt.','Shuffle','BL alt.','BL sh.'],ylabel='Core cycles/decision');c.tick_params(axis='x',labelsize=7)
    save(fig,'q3-method')

    fig,ax,c=diagram(4,'256 MiB random rings; 1-byte NOPs; fine N: Charnwood 192–240, Artemisia 448–576.',
        'I=100,000 loops; 2 loads/loop; ticks/load = elapsed TSC / (2 I).',
        'Independent loads lose overlap as spacing grows and approach the dependent-load control. Repeated fine steps bracket an effective instruction window. N is per gap; neither N nor 2N is automatically a total ROB entry count.')
    labels=['Load A','N × NOP','Load B','N × NOP','Next A']
    for i,label in enumerate(labels):box(ax,.04+i*.19,.80,.16,.10,label,color=BLUE if i%2==0 else GRAY)
    for i in range(4):arrow(ax,(.20+i*.19,.85),(.23+i*.19,.85))
    ax.text(.04,.752,'Independent: A and B chase disjoint shuffled rings; each chain depends on its own prior load.',fontsize=8.5,transform=ax.transAxes)
    ax.text(.04,.711,'Dependent control: all loads follow one serialized cycle through the same complete line set.',fontsize=8.5,transform=ax.transAxes)
    ns=list(range(448,577,4));yy=[q4p('artemisia','native',1,n)['median']/q4p('artemisia','native',1,n,1)['median'] for n in ns]
    c.plot(ns,yy,'o-',markersize=2.3,color=BLUE);c.axvspan(492,500,color=ORANGE,alpha=.15);c.axhline(1,color=GRAY,ls=':',lw=.8)
    c.set(xlabel='NOPs per gap N',ylabel='Independent / serial');save(fig,'q4-method')

    fig,ax,c=diagram(5,'Scaled LEA, 1/4/8 accumulators; equal-length NOP control; I=10,000; fine step=4.',
        '2 loads and 2N filler writes/loop; ticks/load = elapsed TSC / (2 I).',
        'Four/eight-chain LEA curves rise before the NOP window. This identifies integer-destination pressure under a conditional allocation model. Chain-count and serial-load controls expose scheduler/dependency limits; total physical PRF occupancy is unresolved.')
    for i,label in enumerate(('Load A','N × LEA','Load B','N × LEA','Repeat')):box(ax,.04+i*.19,.81,.16,.10,label,color=TEAL if i in (1,3) else BLUE)
    for i in range(4):arrow(ax,(.20+i*.19,.86),(.23+i*.19,.86))
    ax.text(.04,.76,'LEA (r,r,2) → r computes 3r, updates a 64-bit GPR and does not write FLAGS.',fontsize=8.6,transform=ax.transAxes)
    ax.text(.04,.714,'Rotate eight accumulators; compare 4-byte NOPs with equal count/length and serialized loads.',fontsize=8.5,transform=ax.transAxes)
    ns=list(range(192,233,4))
    for mode,color,label in ((1,BLUE,'4 chains'),(2,GRAY,'NOP')):c.plot(ns,[point(5,param=n,mode=mode)['median'] for n in ns],'o-',markersize=2,color=color,label=label)
    c.axvspan(200,216,color=ORANGE,alpha=.10);c.set(xlabel='Writes / NOPs per gap N',ylabel='TSC ticks/load');c.legend(fontsize=7)
    save(fig,'q5-method')

    fig,ax,c=diagram(8,'128 / 256 / 384 identical cache-line counts; random cycle; page-aligned 4 KiB backing.',
        'I=100,000 dependent loads; native cost = Δ(core cycles/load) / Δ(STLB services/load).',
        'A compact baseline removes hit cost. Qualified native counters show STLB service with few cache misses/walks. The event-normalized difference estimates added L1-DTLB miss cost. Unverified protected counter coverage limits SGX to a layout timing contrast.')
    ax.text(.04,.902,'Compact: consecutive 64-byte lines',fontsize=8.5,transform=ax.transAxes)
    ax.text(.53,.902,'Scattered: one line per 4 KiB page',fontsize=8.5,transform=ax.transAxes)
    for i in range(4):
        box(ax,.04+i*.10,.79,.09,.075,'line '+str(i),color=BLUE,size=8)
        box(ax,.53+i*.11,.79,.095,.075,'page '+str(i),color=GRAY,size=8)
        ax.add_patch(Rectangle((.535+i*.11,.794),.018,.025,fc=TEAL,ec=TEAL,transform=ax.transAxes))
    ax.text(.04,.748,'Illustrative addresses; the recorded data footprint is 8 / 16 / 24 KiB in either layout.',fontsize=8.5,transform=ax.transAxes)
    ax.text(.04,.708,'Scattered node i: base + i·4096 + (i mod 64)·64; full-ring warming precedes timing.',fontsize=8.5,transform=ax.transAxes)
    costs=suite.contrasts([p for name in CAMPAIGNS[8] for p in DATA[name][1]])
    for host,color in (('charnwood',BLUE),('artemisia',ORANGE)):
        campaign='results/'+CAMPAIGNS[8][host=='artemisia']
        cc=[next(c for c in costs if c['campaign']==campaign and c['environment']=='native' and c['repetition']==1 and f'scattered-{n}-' in c['treatment_job']) for n in (128,256,384)]
        c.plot([128,256,384],[v['additional_core_cycles_per_stlb_miss'] for v in cc],'o-',color=color,markersize=3,label=host.capitalize())
    c.set(xlabel='Nodes / cache lines',ylabel='Extra core cycles',ylim=(0,10.5));c.legend(fontsize=7)
    save(fig,'q8-method')

def timing_diagram():
    fig=plt.figure(figsize=(8,2.65));ax=fig.add_axes([0,0,1,1]);ax.set_axis_off()
    ax.text(.02,.94,'Both timers execute in the host; setup, allocation and warm-up are outside.',fontsize=10,transform=ax.transAxes,color=BLUE)
    for y,label in ((.56,'Native'),(.18,'Hardware SGX')):
        ax.text(.02,y+.075,label,fontsize=9.5,transform=ax.transAxes,va='center')
        box(ax,.20,y,.145,.16,'LFENCE\nRDTSCP\nLFENCE',size=8.5)
        box(ax,.81,y,.145,.16,'LFENCE\nRDTSCP\nLFENCE',size=8.5)
        arrow(ax,(.345,y+.08),(.38,y+.08));arrow(ax,(.775,y+.08),(.81,y+.08))
    box(ax,.38,.56,.395,.16,'Dispatch → shared kernel → result / return',color=BLUE,size=9)
    box(ax,.38,.18,.085,.16,'ECALL\nentry',color=GRAY,size=8)
    box(ax,.47,.18,.215,.16,'Same kernel + private arena\ninside the enclave',color=TEAL,size=8.3)
    box(ax,.69,.18,.085,.16,'ECALL\nreturn',color=GRAY,size=8)
    ax.plot([.20,.955],[.48,.48],color=GRAY,ls=':',lw=1,transform=ax.transAxes)
    ax.text(.20,.416,'PMU enable/disable/read bracket is slightly wider; enclave event coverage is unverified.',fontsize=8.4,transform=ax.transAxes,color=GRAY)
    ax.text(.20,.062,'Entry/exit are included in SGX elapsed ticks; creating, initializing and warming the enclave are excluded.',fontsize=8.4,transform=ax.transAxes)
    save(fig,'shared-timing')

def main():
    for folder in (OUT,FIG,SNIP):folder.mkdir(parents=True,exist_ok=True)
    load_data();build_tables();result_plots();snippets()
    # Methodology and timing drawings are generated below from these same data.
    methodology_diagrams();timing_diagram();write_audit()
    print('Generated HW3 report tables, seven result/control plots, six original methodology panels, timing diagram, source excerpts and input audit.')

if __name__=='__main__':main()
