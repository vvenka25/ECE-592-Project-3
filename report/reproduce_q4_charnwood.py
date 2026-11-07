#!/usr/bin/env python3
"""Run unchanged Q4 natively on Charnwood in a separate source/build tree."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess as sp
import sys
import tarfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'trackb'))
from run import private_core_cookie

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',choices=('coarse','fine'),required=True)
    p.add_argument('--cpu',type=int,required=True)
    p.add_argument('--workdir',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--lo',type=int);p.add_argument('--hi',type=int)
    p.add_argument('--order-seed',type=int,default=1)
    p.add_argument('--execute',action='store_true')
    a=p.parse_args();work=a.workdir.resolve();out=a.out.resolve()
    if work==ROOT or ROOT in work.parents:p.error('Use a separate host-local workdir outside the preserved project, e.g. /tmp/...')
    if a.stage=='fine' and (a.lo is None or a.hi is None):p.error('Fine bounds must come from this machine\'s coarse observations')
    if (a.lo is None)!=(a.hi is None) or (a.lo is not None and (not 0<=a.lo<=a.hi<=1024 or a.lo%4 or a.hi%4)):p.error('Supply both valid bounds, multiples of four')
    command=[sys.executable,'scripts/run_rob.py','--stage',a.stage,'--cpu',str(a.cpu),'--numa-node','0',
             '--environment','native','--order-seed',str(a.order_seed),'--out',str(out),'--execute']
    if a.lo is not None:command+=['--lo',str(a.lo),'--hi',str(a.hi)]
    if not a.execute:
        print('Plan: verify original archive; extract unchanged Q4 sources to '+str(work))
        print('Private inherited core-scheduling group; controller on a different core; legacy helper mask includes selected CPU.')
        print('In '+str(work)+': '+shlex.join(command));return
    if not os.uname().nodename.split('.')[0].startswith('charnwood'):p.error('This helper is for Charnwood; completed Artemisia Q4 must remain untouched')
    if out.exists():p.error('Use a fresh output directory; existing measurements are preserved')
    allowed=set(os.sched_getaffinity(0))
    if a.cpu not in allowed:p.error('CPU is not currently permitted/online')
    text=Path(f'/sys/devices/system/cpu/cpu{a.cpu}/topology/thread_siblings_list').read_text().strip()
    siblings=set()
    for part in text.split(','):
        if '-' in part:
            lo,hi=map(int,part.split('-'));siblings.update(range(lo,hi+1))
        else:siblings.add(int(part))
    controls=allowed-siblings
    if not controls:p.error('A different permitted physical core is required for the controller')
    controller=min(controls)
    archive=ROOT/'preserved/q4-20261106.tar.gz'
    record=json.loads((ROOT/'preserved/q4-20261106.sha256.json').read_text())
    if not archive.exists():
        record=json.loads((ROOT/'preserved/q4-source-only-20261107.sha256.json').read_text())
        archive=ROOT/record['archive']
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==record['archive_sha256'],'Original archive changed'
    sources={}
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            name=member.name
            selected=name=='Makefile' or name in ('ROB_BENCHMARK.md','ROB_RESULTS_ARTEMISIA.md') or name.split('/')[0] in ('src','enclave','scripts','tests','analysis')
            if not selected or not member.isfile() or '__pycache__' in Path(name).parts:continue
            data=tar.extractfile(member).read()
            assert hashlib.sha256(data).hexdigest()==record['files'][name],name
            sources[name]=data
    marker=work/'.q4-preserved-workdir.json'
    if work.exists() and any(work.iterdir()) and not marker.exists():p.error('Use a fresh workdir or one previously created by this helper')
    if marker.exists():assert json.loads(marker.read_text())['archive_sha256']==record['archive_sha256']
    work.mkdir(parents=True,exist_ok=True)
    for name,data in sources.items():
        target=work/name
        if target.exists():assert target.read_bytes()==data,'Worktree source changed: '+name
        else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    for folder in ('src','enclave','scripts','tests','analysis'):
        for target in (work/folder).rglob('*'):
            if target.is_file() and '__pycache__' not in target.parts:assert str(target.relative_to(work)) in sources,'Unexpected extra Q4 source: '+str(target)
    assert not (work/'build').is_symlink(),'Build directory must be local to the isolated worktree'
    marker.write_text(json.dumps(dict(archive_sha256=record['archive_sha256']),indent=2)+'\n')
    cookie=private_core_cookie();os.sched_setaffinity(0,{controller})
    env=dict(os.environ,CCACHE_DISABLE='1',MPLCONFIGDIR=str(work/'mpl-cache'))
    env.pop('TEST_SGX',None);env.pop('TEST_THP',None)
    if not (work/'build/rob-native').exists():
        with (work/'build-check.log').open('w') as log:sp.run(['make','native','check'],cwd=work,env=env,stdout=log,stderr=sp.STDOUT,check=True)
    asm=sp.check_output(['objdump','-d','--no-show-raw-insn','--disassemble=main',str(work/'build/rob-native')],text=True)
    instructions=[line.split('\t')[-1].strip() for line in asm.splitlines() if '\t' in line]
    clocks=[i for i,x in enumerate(instructions) if x=='rdtscp'];assert len(clocks)==2
    for i in clocks:
        left=max(j for j in range(i) if instructions[j]=='lfence');right=next(j for j in range(i+1,len(instructions)) if instructions[j]=='lfence')
        assert not any(x.startswith(('call','j')) for x in instructions[left+1:right])
    with (work/(out.name+'.collection.log')).open('w') as log:
        sp.run(command,cwd=work,env=env,stdout=log,stderr=sp.STDOUT,check=True,
               preexec_fn=lambda:os.sched_setaffinity(0,{controller,a.cpu}))
    (out/'binaries').mkdir()
    (out/'native-timer-assembly.txt').write_text(asm)
    for name in ('rob-native','platform-info'):shutil.copy2(work/'build'/name,out/'binaries'/name)
    with tarfile.open(out/'source-snapshot.tar.gz','w:gz') as tar:
        for name in sorted(sources):tar.add(work/name,arcname=name,recursive=False)
    (out/'external-controls.json').write_text(json.dumps(dict(created_utc=datetime.now(timezone.utc).isoformat(),
        original_archive_sha256=record.get('original_archive_sha256',record['archive_sha256']),source_archive_sha256=record['archive_sha256'],source_sha256={k:hashlib.sha256(v).hexdigest() for k,v in sources.items()},
        core_scheduling=dict(policy='private inherited group',cookie=cookie,kernel_interrupts='not isolated'),
        cpu=a.cpu,controller=controller,legacy_runner_allowed_cpus=sorted({controller,a.cpu}),numa_node=0,argv=command),indent=2)+'\n')
    sp.run([sys.executable,'analysis/review_sweep.py',str(out)],cwd=work,env=env,check=True)
    print('Saved unchanged-source Charnwood Q4 evidence to '+str(out))

if __name__=='__main__':main()
