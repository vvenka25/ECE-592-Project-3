#!/usr/bin/env python3
"""Plan or execute one selected exercise; Q4 is preserved and Q6 is unselected."""
import argparse
import csv
import ctypes
from datetime import datetime,timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shlex
import shutil
import subprocess as sp
import sys
import tarfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'trackb'))
from evidence import mapping_audit

def private_core_cookie():
    # Linux PR_SCHED_CORE CREATE/GET, current thread. Fork/exec inherit it.
    libc=ctypes.CDLL(None,use_errno=True)
    libc.prctl.argtypes=[ctypes.c_int,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p]
    if libc.prctl(62,1,0,0,None):raise OSError(ctypes.get_errno(),'PR_SCHED_CORE_CREATE')
    cookie=ctypes.c_ulonglong()
    if libc.prctl(62,0,0,0,ctypes.byref(cookie)) or not cookie.value:raise OSError(ctypes.get_errno(),'PR_SCHED_CORE_GET')
    return cookie.value

def platform(cpu):
    helper_affinity=set(os.sched_getaffinity(0))|{cpu}
    p=json.loads(sp.check_output([sys.executable,str(ROOT/'scripts/preflight.py'),str(cpu)],cwd=ROOT,text=True,
        preexec_fn=lambda:os.sched_setaffinity(0,helper_affinity)))
    p['collector_affinity']=sorted(os.sched_getaffinity(0))
    if (ROOT/'trackb/build/platform-info').exists():
        p['cpuid']=sp.check_output([str(ROOT/'trackb/build/platform-info'),str(cpu)],text=True)
    p['online_cpus']=Path('/sys/devices/system/cpu/online').read_text().strip()
    p['active_siblings']=sorted(set(expand(p['siblings']))&set(expand(p['online_cpus']))-{cpu})
    p['base_page_size']=os.sysconf('SC_PAGE_SIZE')
    p['machine_id']=os.uname().nodename
    return p

def expand(text):
    result=[]
    for piece in text.split(','):
        if '-' in piece:
            lo,hi=map(int,piece.split('-'));result+=list(range(lo,hi+1))
        else:result.append(int(piece))
    return result

def sibling_ticks(p,cpu):
    siblings=set(expand(p['siblings']))-{cpu};result={}
    for line in p['cpu_stat'].splitlines():
        fields=line.split()
        if fields[0][3:].isdigit() and int(fields[0][3:]) in siblings:
            v=list(map(int,fields[1:9]));result[fields[0][3:]]={'total':sum(v),'busy':sum(v)-v[3]-v[4]}
    return result

def page_node_audit(out,name):
    result={}
    for phase in ('before','after'):
        rows=list(csv.DictReader((out/f'{name}.{phase}.page_nodes.csv').open()))
        count=0;nodes={};errors={}
        for row in rows:
            first,n,status=(int(row[k]) for k in ('first_page','page_count','node_or_error'))
            if first!=count or n<1:raise ValueError('Incomplete/noncontiguous page-node query')
            count+=n;target=nodes if status>=0 else errors;key=str(status);target[key]=target.get(key,0)+n
        result[phase]=dict(queried_pages=count,nodes=nodes,errors=errors)
    return result

def placement_ok(audit,span,node,queries):
    required=(span+4095)//4096*4096
    for phase in ('before','after'):
        fields=audit.get(phase,{})
        if fields.get('Size')!=f'{required//1024} kB' or fields.get('Rss')!=f'{required//1024} kB' or fields.get('AnonHugePages')!='0 kB':return False
        query=queries.get(phase,{})
        if query.get('queried_pages')!=required//4096 or query.get('errors'):return False
        pages={int(n):int(count) for n,count in query.get('nodes',{}).items()}
        if sum(pages.values())!=required//4096:return False
        if node is not None and (pages.get(node)!=required//4096 or any(n!=node and count for n,count in pages.items())):return False
    return True

def cases(question,a):
    result=[]
    def add(label,mode,param,kib=0,**kw):
        c=dict(question=question,label=label,mode=mode,param=param,kib=kib,seed=a.seed,
               iterations=a.iterations or (1048576 if question==3 else 100000),samples=a.samples)
        if question==5:c['register_class']='64-bit integer GPR'
        c.update(kw);result.append(c)
    if question==3:
        for p,label in ((0,'always-zero'),(1,'always-one'),(2,'alternating'),(3,'shuffled')):
            add('branch-'+label,0,p,64)
        add('branch-shuffled-seed2',0,3,64,seed=271828)
        add('branchless-alternating',1,2,64);add('branchless-shuffled',1,3,64)
        add('branchless-shuffled-seed2',1,3,64,seed=271828)
    elif question==1:
        for streams in (1,2,4):add(f'{streams}-chains',0,streams)
        add('zero-work',0,1,iterations=0)
    elif question==2:
        for mode,label in enumerate(('overlap','serial','fenced')):
            add(label+'-cold-k0',mode,0,a.footprint_mib*1024)
            add(label+'-cold-k64',mode,64,a.footprint_mib*1024)
            add(label+'-hot-k64',mode,64,16)
    elif question==5:
        lo=0 if a.lo is None else a.lo;hi=(256 if a.stage=='pilot' else 512) if a.hi is None else a.hi
        for mode,label in ((0,'gpr-lea1'),(1,'gpr-lea4'),(6,'gpr-lea8'),(2,'nop-window-control'),(4,'gpr-lea4-dependent')):
            add(label,mode,lo,a.footprint_mib*1024,lo=lo,hi=hi,step=4 if a.stage=='fine' else 32 if a.stage=='pilot' else 16)
    elif question==8:
        for nodes in (128,256,384):
            for mode,label in enumerate(('compact','scattered')):add(f'{label}-{nodes}',mode,nodes)
    if a.stage=='smoke':
        for c in result:
            c.update(iterations=128,samples=2)
            if question in (2,5):c['kib']=16
            if question==3:c['kib']=1
            if question==5:c.update(param=0,lo=0,hi=8,step=4)
        # Cover each kernel family, not every performance configuration.
        if question==3:result=[result[2],result[3],result[6]]
        if question==1:result=result[:3]
        if question==2:result=[c for c in result if 'hot' in c['label']]
        if question==8:result=[c for c in result if c['param']==256]
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--question',required=True,choices=('Q3','Q1','Q2','Q5','Q8','all'))
    p.add_argument('--stage',choices=('smoke','pilot','measure','fine'),default='measure')
    p.add_argument('--cpu',type=int,required=True);p.add_argument('--numa-node',type=int)
    p.add_argument('--environment',choices=('native','enclave','both'),default='native')
    p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true')
    p.add_argument('--iterations',type=int);p.add_argument('--samples',type=int,default=15)
    p.add_argument('--repeats',type=int,default=2);p.add_argument('--seed',type=int,default=42)
    p.add_argument('--order-seed',type=int,default=1);p.add_argument('--footprint-mib',type=int,default=256)
    p.add_argument('--lo',type=int);p.add_argument('--hi',type=int)
    p.add_argument('--pmu',choices=('auto','required','off'),default='auto')
    p.add_argument('--require-idle-sibling',action='store_true',help='Stop and retain evidence if coarse sibling busy ticks are observed')
    p.add_argument('--core-scheduling',choices=('off','private'),default='off',help='Require a private inherited Linux core-scheduling cookie; kernel/interrupt contexts remain possible')
    a=p.parse_args()
    if a.stage=='pilot':
        if a.iterations is None:a.iterations=10000
        a.samples=min(a.samples,5)
    if a.cpu not in os.sched_getaffinity(0):p.error('CPU is not currently online/permitted')
    if min(a.samples,a.repeats,a.seed,a.order_seed)<1 or not 1<=a.footprint_mib<=256:p.error('Invalid count/seed/footprint')
    if a.iterations is not None and not 1<=a.iterations<=1000000000:p.error('Iterations must be 1..1000000000')
    if a.question=='all' and a.stage not in ('smoke','pilot'):p.error('Use all only for smoke/pilot validation; measure one question at a time')
    if a.stage=='fine' and (a.question!='Q5' or a.lo is None or a.hi is None):p.error('Fine Q5 needs a measured --lo/--hi bracket')
    if a.lo is not None or a.hi is not None:
        if a.question!='Q5' or a.lo is None or a.hi is None or not 0<=a.lo<=a.hi<=512 or a.lo%4 or a.hi%4:p.error('Q5 bounds must be multiples of four in 0..512')
    before=platform(a.cpu)
    if before['base_page_size']!=4096:p.error('These x86 page-layout experiments require a 4096-byte base page')
    if a.numa_node is None:a.numa_node=before['node']
    if a.numa_node!=before['node']:p.error('Select CPU-local memory for this suite; record remote experiments separately')
    if a.numa_node is not None and not shutil.which('numactl'):p.error('numactl is required for explicit memory binding')
    envs=('native','enclave') if a.environment=='both' else (a.environment,)
    questions=(3,1,2,5,8) if a.question=='all' else (int(a.question[1:]),)
    jobs=[];out=a.out.resolve()
    for q in questions:
        qq=[]
        for repetition in range(1,(1 if a.stage in ('smoke','pilot') else a.repeats)+1):
            for c in cases(q,a):
                for env in envs:
                    name=f'Q{q}-r{repetition}-{c["label"]}-{env}'
                    command=['numactl',f'--membind={a.numa_node}'] if a.numa_node is not None else []
                    command+=[str(ROOT/'trackb/build'/f'trackb-{env}')]
                    values=dict(question=q,cpu=a.cpu,mode=c['mode'],param=c['param'],footprint_kib=c['kib'],iterations=c['iterations'],
                                samples=c['samples'],seed=c['seed'],order_seed=a.order_seed+repetition-1,metadata=str(out/name),run_id=name,pmu=a.pmu)
                    values.update({k:c[k] for k in ('lo','hi','step') if k in c})
                    for key,value in values.items():command+=['--'+key.replace('_','-'),str(value)]
                    qq.append(dict(name=name,environment=env,repetition=repetition,parameters=c,command=command))
        random.Random(a.order_seed+q).shuffle(qq);jobs+=qq
    if not a.execute:
        for job in jobs:print(shlex.join(job['command']))
        print(f'{len(jobs)} jobs planned, Q3/Q1/Q2/Q5/Q8 order; no files created. Add --execute.',file=sys.stderr);return
    if out.exists():p.error('Use a fresh result directory; existing evidence is never overwritten')
    controller_candidates=set(os.sched_getaffinity(0))-set(expand(before['siblings']))
    if not controller_candidates:p.error('A separate permitted core is required for the collector/helpers')
    controller_cpu=min(controller_candidates)
    os.sched_setaffinity(0,{controller_cpu})
    core_cookie=private_core_cookie() if a.core_scheduling=='private' else 0
    targets=['native']+(['enclave'] if 'enclave' in envs else [])
    sp.run(['make','-C',str(ROOT/'trackb'),*targets],check=True)
    sp.run(['make','-C',str(ROOT/'trackb'),'-q',*targets],check=True)
    lock_path=Path(f'/tmp/hw3-trackb-{os.getuid()}-core-{min(expand(before["siblings"]))}.lock')
    lock=lock_path.open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    files=[ROOT/'trackb/build/trackb-native',ROOT/'trackb/build/platform-info']
    if 'enclave' in envs:files += [ROOT/'trackb/build/trackb-enclave',ROOT/'trackb/build/suite.signed.so']
    hashes={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in files}
    sources={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted((ROOT/'trackb').glob('*')) if x.is_file()}
    purpose='functional validation only' if a.stage=='smoke' else 'pilot validation only' if a.stage=='pilot' else 'measurement'
    manifest=dict(method='trackb-v1',question=a.question,stage=a.stage,purpose=purpose,created_utc=datetime.now(timezone.utc).isoformat(),
                  cpu=a.cpu,numa_node_requested=a.numa_node,order_seed=a.order_seed,binary_sha256=hashes,source_sha256=sources,
                  controller_affinity=[controller_cpu],
                  core_scheduling=dict(policy=a.core_scheduling,cookie=core_cookie,inheritance='fork/exec' if core_cookie else 'off'),
                  cooperative_core_lock=str(lock_path),sibling_state_claim='no online SMT sibling at initial check' if not before['active_siblings'] else 'uncontrolled; cooperative lock does not reserve other users',
                  require_idle_sibling=a.require_idle_sibling,initial_platform=before,jobs=jobs)
    if core_cookie and before['active_siblings']:manifest['sibling_state_claim']='private inherited core-scheduling group excludes unrelated userspace co-scheduling; kernel/interrupt contexts remain possible'
    out.mkdir(parents=True)
    with tarfile.open(out/'source-snapshot.tar.gz','w:gz') as tar:
        for name in sources:tar.add(ROOT/name,arcname=name,recursive=False)
        for name in ('scripts/preflight.py','src/platform.c','analysis/review_sweep.py'):
            tar.add(ROOT/name,arcname=name,recursive=False)
    (out/'binaries').mkdir()
    for path in files:shutil.copy2(path,out/'binaries'/path.name)
    def save():(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    save()
    with (out/'metadata.txt').open('w') as f:
        for cmd in (['uname','-a'],['lscpu'],['gcc','--version'],['numactl','--show']):
            f.write(shlex.join(cmd)+'\n');f.flush();sp.run(cmd,stdout=f,stderr=sp.STDOUT)
        for exe in files:
            if exe.name=='trackb-enclave':sp.run(['ldd',str(exe)],stdout=f,stderr=sp.STDOUT)
        if shutil.which('rpm'):sp.run(['rpm','-qa','*sgx*'],stdout=f,stderr=sp.STDOUT)
    for index,job in enumerate(jobs):
        for name,digest in {**hashes,**sources}.items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Source/binary changed: '+name)
        name=job['name'];b=platform(a.cpu)
        (out/(name+'.platform-before.json')).write_text(json.dumps(b,indent=2)+'\n')
        if not before['active_siblings'] and b['active_siblings']:
            job['status']='topology-changed';save();raise SystemExit('An initially offline SMT sibling became online; choose/revalidate placement before collecting further data')
        print(f'[{index+1}/{len(jobs)}] {name}',flush=True)
        job['started_utc']=datetime.now(timezone.utc).isoformat()
        with (out/(name+'.csv')).open('x') as raw,(out/(name+'.log')).open('x') as log:
            child=sp.Popen(job['command'],cwd=ROOT,stdout=raw,stderr=log);started=report=time.monotonic()
            try:
                while child.poll() is None:
                    time.sleep(.2)
                    if time.monotonic()-report>=15:print(f'  running, {time.monotonic()-started:.0f}s elapsed',flush=True);report=time.monotonic()
            except KeyboardInterrupt:
                child.terminate();child.wait();job['status']='interrupted';save();raise
        after=platform(a.cpu);(out/(name+'.platform-after.json')).write_text(json.dumps(after,indent=2)+'\n')
        b0,b1=sibling_ticks(b,a.cpu),sibling_ticks(after,a.cpu)
        job.update(status='success' if child.returncode==0 else 'failed',returncode=child.returncode,elapsed_seconds=time.monotonic()-started,
                   finished_utc=datetime.now(timezone.utc).isoformat(),
                   sibling_cpu_ticks={c:{k:b1[c][k]-v for k,v in values.items()} for c,values in b0.items() if c in b1})
        if child.returncode==0:
            with (out/(name+'.csv')).open() as f:rows=list(csv.DictReader(f))
            expected=job['parameters']['samples']*(1 if 'lo' not in job['parameters'] else len(range(job['parameters']['lo'],job['parameters']['hi']+1,job['parameters']['step'])))
            if len(rows)!=expected:raise RuntimeError('Incomplete output: '+name)
            job['sample_count']=len(rows);job['migration_samples']=sum(r['status']!='ok' for r in rows)
            job['samples_with_faults']=sum(int(r['minor_faults'])+int(r['major_faults'])>0 for r in rows)
            job['samples_with_context_switches']=sum(int(r['voluntary_cs'])+int(r['involuntary_cs'])>0 for r in rows)
            job['mapping_audit']=mapping_audit(out,job) if int(rows[0]['span_bytes']) else {'placement':'register-only workload'}
            if job['environment']=='native' and int(rows[0]['span_bytes']):
                job['page_node_audit']=page_node_audit(out,name)
                job['placement_verified']=placement_ok(job['mapping_audit'],int(rows[0]['span_bytes']),a.numa_node,job['page_node_audit'])
                job['placement_method']='complete read-only per-page node query plus VMA/RSS/no-THP checks'
        save()
        if child.returncode:
            print((out/(name+'.log')).read_text(),file=sys.stderr);raise SystemExit('Stopped after failure; partial evidence retained')
        if job.get('placement_verified') is False:raise SystemExit('Native page/NUMA treatment not verified at both snapshots; campaign stopped, evidence retained')
        if not before['active_siblings'] and after['active_siblings']:
            job['sibling_gate_passed']=False;save();raise SystemExit('SMT sibling became online during collection; evidence retained, campaign stopped')
        if a.require_idle_sibling:
            job['sibling_gate_passed']=(b['active_siblings']==after['active_siblings'] and not any(x['busy'] for x in job['sibling_cpu_ticks'].values()));save()
            if not job['sibling_gate_passed']:raise SystemExit('Sibling activity observed; evidence retained, campaign stopped')
    print(f'Saved {len(jobs)} jobs to {out}; run trackb/review.py before inferring results.')

if __name__=='__main__':main()
