#!/usr/bin/env python3
"""Prepare/execute one experimental stage. Default prints commands only."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import shlex
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--stage',required=True,choices=('smoke','calibration','prefetch','translation','frontend','coarse','fine','overhead'))
p.add_argument('--cpu',required=True,type=int)
p.add_argument('--out',required=True,type=Path)
p.add_argument('--environment',choices=('native','enclave','both'),default='native')
p.add_argument('--numa-node',type=int,help='Use numactl --membind; EPC placement still requires verification')
p.add_argument('--sibling-state',choices=('uncontrolled','reserved-idle'),default='uncontrolled',help='User-supplied description, not automatic reservation')
p.add_argument('--footprint-mib',type=int,default=256)
p.add_argument('--iterations',type=int,default=100000)
p.add_argument('--samples',type=int,default=15)
p.add_argument('--seed',type=int,default=42)
p.add_argument('--order-seed',type=int,default=1)
p.add_argument('--lo',type=int)
p.add_argument('--hi',type=int)
p.add_argument('--perf-events',help='Optional perf stat events; counts include initialization and warm-up')
p.add_argument('--huge-policy',choices=('collapse','advice'),default='collapse',help='Translation stage: verify full THP after collapse, or reproduce best-effort advice')
p.add_argument('--execute',action='store_true')
a=p.parse_args()
if a.cpu not in os.sched_getaffinity(0): p.error('CPU is not permitted by this process affinity mask')
if not 1<=a.footprint_mib<=256: p.error('Stage footprint must be 1..256 MiB (leaves room for the stride-128 control)')
if a.stage=='translation' and a.huge_policy=='collapse' and a.footprint_mib%2:
    p.error('Strict translation control needs an even MiB footprint for 2 MiB page collapse')
if a.iterations<1 or a.samples<1 or a.seed<1 or a.order_seed<1: p.error('Iterations, samples and seeds must be positive')
if a.stage=='fine' and (a.lo is None or a.hi is None): p.error('Choose --lo and --hi from the accepted coarse run')
lo=0 if a.lo is None else a.lo; hi=1024 if a.hi is None else a.hi
if not 0<=lo<=hi<=1024 or lo%4 or hi%4: p.error('Spacing bounds must be multiples of four within 0..1024')
if a.numa_node is not None and (a.numa_node<0 or not shutil.which('numactl')): p.error('NUMA binding needs a valid node and numactl')
if a.perf_events and not shutil.which('perf'): p.error('--perf-events needs perf')
envs=('native','enclave') if a.environment=='both' else (a.environment,)
cases=[]
def add(tag,kib=None,**kw):
    c=dict(tag=tag,kib=kib or a.footprint_mib*1024,stride=64,width=1,align=0,pages='4k',
           seed=a.seed,iters=a.iterations,samples=a.samples,lo=lo,hi=hi,step=32)
    c.update(kw); cases.append(c)
if a.stage=='smoke': add('functional',kib=16,iters=100,samples=2,lo=0,hi=8,step=4)
elif a.stage=='calibration':
    for kib in sorted({16,1024,a.footprint_mib*1024}|{m*1024 for m in (64,128) if m<=a.footprint_mib}):
        add(f'footprint-{kib}KiB',kib=kib,lo=0,hi=0,step=4)
elif a.stage=='prefetch':
    for seed in sorted({a.seed,314159,271828}): add(f'seed-{seed}',seed=seed)
    add('stride-128',stride=128)
elif a.stage=='translation':
    add('pages-4k')
    if a.huge_policy=='collapse': add('pages-collapse',pages='collapse',native_only=True)
    else: add('pages-huge',pages='huge',native_only=True)
elif a.stage=='frontend':
    for kib in (16,a.footprint_mib*1024):
        add(f'frontend-{kib}KiB',kib=kib)
        add(f'wide-nop-{kib}KiB',kib=kib,width=2)
        for align in (16,32): add(f'align-{align}-{kib}KiB',kib=kib,align=align)
elif a.stage=='coarse': add('baseline',step=16)
elif a.stage=='fine': add('candidate',step=4)
elif a.stage=='overhead':
    for iters in (0,1000,10000,a.iterations): add(f'batch-{iters}',kib=16,iters=iters,lo=0,hi=0,step=4)

out=a.out.resolve(); jobs=[]
for i,c in enumerate(cases):
    for env in envs:
        if env=='enclave' and c.get('native_only'): continue
        name=f'{i:02d}-{c["tag"]}-{env}'
        command=[]
        if a.numa_node is not None: command=['numactl',f'--membind={a.numa_node}']
        command += [str(ROOT/'build'/f'rob-{env}'),str(a.cpu),'1',str(c['iters']),str(c['samples']),
                    str(c['lo']),str(c['hi']),str(c['step']),str(c['seed']),
                    '--kib',str(c['kib']),'--stride',str(c['stride']),'--nop-bytes',str(c['width']),
                    '--alignment',str(c['align']),'--order-seed',str(a.order_seed),
                    '--metadata',str(out/name),'--run-id',f'{a.stage}-{name}']
        if env=='native': command+=['--pages',c['pages']]
        if a.perf_events: command=['perf','stat','-x',',','-e',a.perf_events,'-o',str(out/(name+'.perf.csv')),'--',*command]
        jobs.append(dict(name=name,environment=env,parameters=c,command=command))
random.Random(a.order_seed).shuffle(jobs)
if not a.execute:
    for j in jobs: print(shlex.join(j['command'])+' > '+shlex.quote(str(out/(j['name']+'.csv'))))
    print(f'\n{len(jobs)} jobs planned; add --execute to create a fresh result directory and run.',file=sys.stderr)
    sys.exit(0)
if out.exists(): p.error('Output directory already exists; use a fresh directory to preserve earlier evidence')
targets=['native']+(['enclave'] if 'enclave' in envs else [])
print('Preparing benchmark build: make '+' '.join(targets),flush=True)
build=subprocess.run(['make',*targets],cwd=ROOT)
if build.returncode:
    p.error('Build failed; see make diagnostics above. No measurements were started')
required=[ROOT/'build/rob-native',ROOT/'build/platform-info']
if 'enclave' in envs: required += [ROOT/'build/rob-enclave',ROOT/'build/rob.signed.so']
for path in required:
    if not path.exists(): p.error(f'Build first: missing {path}')
check=subprocess.run(['make','-q',*targets],cwd=ROOT)
if check.returncode:
    p.error('Build did not reach an up-to-date state; check make errors or file timestamps. No measurements were started')
hashes={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in required}
out.mkdir(parents=True)
manifest={'stage':a.stage,'cpu':a.cpu,'numa_node_requested':a.numa_node,
          'sibling_state_claim':a.sibling_state,'order_seed':a.order_seed,'binary_sha256':hashes,
          'perf_events':a.perf_events,'perf_scope':'whole process, includes initialization and warm-up; enclave counter coverage must be verified',
          'note':'No automatic core reservation or PMU access. NUMA binding does not prove EPC placement.',
          'jobs':jobs}
def save(): (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
def platform():
    return json.loads(subprocess.check_output([sys.executable,str(ROOT/'scripts/preflight.py'),str(a.cpu)],cwd=ROOT,text=True))
def busy(data):
    text=data['siblings']; cpus=[]
    for piece in text.split(','):
        if '-' in piece:
            x,y=map(int,piece.split('-')); cpus.extend(range(x,y+1))
        else: cpus.append(int(piece))
    result={}
    for line in data['cpu_stat'].splitlines():
        parts=line.split()
        if parts and parts[0].startswith('cpu') and parts[0][3:].isdigit():
            cpu=int(parts[0][3:])
            if cpu in cpus and cpu!=a.cpu:
                ticks=list(map(int,parts[1:9])); result[str(cpu)]={'total':sum(ticks),'busy':sum(ticks)-ticks[3]-ticks[4]}
    return result
save()
with (out/'metadata.txt').open('w') as f:
    subprocess.run(['bash',str(ROOT/'scripts/metadata.sh')],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
for index,j in enumerate(jobs):
    if any(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest for name,digest in hashes.items()):
        raise SystemExit('Binary changed during campaign; stopping')
    before=platform(); (out/(j['name']+'.platform-before.json')).write_text(json.dumps(before,indent=2)+'\n')
    print(f'[{index+1}/{len(jobs)}] {j["name"]}',flush=True)
    with (out/(j['name']+'.csv')).open('x') as f,(out/(j['name']+'.log')).open('x') as log:
        child=subprocess.Popen(j['command'],cwd=ROOT,stdout=f,stderr=log)
        started=time.monotonic(); report=started
        try:
            while child.poll() is None:
                time.sleep(.2)
                if time.monotonic()-report>15:
                    print(f'  {j["name"]}: running, {time.monotonic()-started:.0f}s elapsed',flush=True); report=time.monotonic()
        except KeyboardInterrupt:
            child.terminate(); child.wait(); j['status']='interrupted'; save(); raise
    after=platform(); (out/(j['name']+'.platform-after.json')).write_text(json.dumps(after,indent=2)+'\n')
    b0,b1=busy(before),busy(after)
    j['sibling_cpu_ticks']={cpu:{name:b1[cpu][name]-vals[name] for name in ('total','busy')} for cpu,vals in b0.items() if cpu in b1}
    j['elapsed_seconds']=time.monotonic()-started; j['returncode']=child.returncode
    j['status']='success' if child.returncode==0 else 'failed'
    if child.returncode==0:
        with (out/(j['name']+'.csv')).open() as f: rows=list(csv.DictReader(f))
        j['sample_count']=len(rows)
        j['migration_samples']=sum(r['status']=='migration' for r in rows)
        j['samples_with_context_switches']=sum(int(r['voluntary_cs'])+int(r['involuntary_cs'])>0 for r in rows)
        j['samples_with_faults']=sum(int(r['minor_faults'])+int(r['major_faults'])>0 for r in rows)
    save()
    if child.returncode:
        print((out/(j['name']+'.log')).read_text(),file=sys.stderr)
        raise SystemExit('Stage stopped after failure; partial data retained')
print(f'Saved {len(jobs)} jobs to {out}. Review raw samples and controls before proceeding.')
