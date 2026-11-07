"""Semantic and linked-code checks; timing magnitudes are never asserted."""
import csv
import ctypes as ct
import io
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

PAT=re.compile(r'rob_(independent|dependent)_(\d+)_b([12])_a(0|16|32)$')
def functions(binary):
    nm=subprocess.check_output(['nm','-S','--defined-only',binary],text=True)
    sections=subprocess.check_output(['objdump','-h',binary],text=True)
    line=next(x.split() for x in sections.splitlines() if len(x.split())>3 and x.split()[1]=='.text')
    vma=int(line[3],16)
    with tempfile.TemporaryDirectory() as tmp:
        raw=Path(tmp)/'text'
        subprocess.run(['objcopy','--dump-section',f'.text={raw}',binary],check=True)
        code=raw.read_bytes()
    found={}
    for line in nm.splitlines():
        fields=line.split()
        if len(fields)==4 and PAT.fullmatch(fields[3]):
            start,size=int(fields[0],16),int(fields[1],16)
            found[fields[3]]=(start,code[start-vma:start-vma+size])
    return found
native=functions('build/rob-native')
assert len(native)==3084,len(native)
for name,(start,code) in native.items():
    mode,n,width,align=PAT.fullmatch(name).groups(); n,width,align=map(int,(n,width,align))
    nop=b'\x90' if width==1 else b'\x66\x90'
    first=b'\x48\x8b\x3f' if mode=='independent' else b'\x48\x8b\x7f\x08'
    second=b'\x48\x8b\x36' if mode=='independent' else first
    body=first+nop*n+second+nop*n+b'\x48\xff\xca'
    at=code.index(body)
    assert (start+at)%64==align,name
if Path('build/rob.so').exists():
    enclave=functions('build/rob.so')
    assert {k:v[1] for k,v in native.items()}=={k:v[1] for k,v in enclave.items()},'Linked kernel bytes differ'
class Cursor(ct.Structure):
    _fields_=[('a',ct.c_void_p),('b',ct.c_void_p)]
class Node(ct.Structure):
    _fields_=[('ind',ct.c_void_p),('serial',ct.c_void_p)]
with tempfile.TemporaryDirectory() as tmp:
    so=tmp+'/common.so'
    subprocess.run(['/usr/bin/gcc','-shared','-fPIC','-O2','-Isrc','src/common.c','build/dispatch.c','build/kernels.o','-o',so],check=True)
    lib=ct.CDLL(so)
    a=(Node*7)(); b=(Node*11)()
    addr=lambda arr,i:ct.addressof(arr)+i*ct.sizeof(Node)
    all_nodes=[addr(a,i) for i in range(7)]+[addr(b,i) for i in range(11)]
    for arr in (a,b):
        for i in range(len(arr)): arr[i].ind=addr(arr,(i+1)%len(arr))
    for i,p in enumerate(all_nodes): ct.c_void_p.from_address(p+8).value=all_nodes[(i+1)%18]
    for n in (0,4,224,512,1024):
        for width in (1,2):
            for align in (0,16,32):
                for mode in ('independent','dependent'):
                    f=getattr(lib,f'rob_{mode}_{n}_b{width}_a{align}')
                    f.argtypes=[ct.c_void_p,ct.c_void_p,ct.c_uint64,ct.POINTER(Cursor)]; f.restype=None
                    for it in (0,1,2,19):
                        c=Cursor(); f(a,b,it,ct.byref(c))
                        expected=(addr(a,it%7),addr(b,it%11)) if mode=='independent' else (all_nodes[2*it%18],addr(b,0))
                        assert (c.a,c.b)==expected,(n,width,align,mode,it)
    lib.setup_memory.argtypes=[ct.c_size_t,ct.c_uint64,ct.c_uint,ct.c_uint]
    lib.memory_base.restype=ct.c_void_p
    lib.run_kernel.argtypes=[ct.c_uint,ct.c_uint,ct.c_uint64,ct.c_uint,ct.c_uint]; lib.run_kernel.restype=ct.c_size_t
    for stride in (64,128):
        assert lib.setup_memory(8192,42,stride,1)==0
        base=lib.memory_base(); count=64
        def cycle(start,offset):
            seen=[]; p=start
            while p not in seen:
                seen.append(p); p=ct.c_void_p.from_address(p+offset).value
            assert p==start
            return seen
        ca=cycle(base,0); cb=cycle(base+stride*count,0); serial=cycle(base,8)
        assert len(ca)==len(cb)==count and not set(ca)&set(cb)
        assert len(serial)==2*count and set(serial)==set(ca)|set(cb)
        assert len(set(y-x for x,y in zip(ca,cb)))>1,'Correlated shuffles'
        lib.release_memory()
        for dep in (0,1):
            assert lib.setup_memory(8192,42,stride,1)==0
            start=lib.run_kernel(0,dep,0,1,0)
            full=lib.run_kernel(0,dep,count,1,0)
            assert start==full,'Full traversal must return to the same cursor'
            part=lib.run_kernel(4,dep,5,1,0)
            assert part!=start,'Sample cursor failed to advance'
            assert lib.run_kernel(4,dep,count,1,0)==part,'Cursor reset between calls'
            assert lib.run_kernel(4,dep,count-5,1,0)==start,'Cursor continuation differs'
            lib.release_memory()
    assert lib.setup_memory(512*1024*1024,42,128,1)!=0,'Span limit'

cpu=min(os.sched_getaffinity(0))
args=[str(cpu),'1','100','2','0','8','4','42']
with tempfile.TemporaryDirectory() as tmp:
    for exe in ['build/rob-native']+(['build/rob-enclave'] if os.environ.get('TEST_SGX')=='1' else []):
        prefix=tmp+'/'+Path(exe).name
        cmd=[exe,*args,'--metadata',prefix,'--run-id','check']
        p=subprocess.run(cmd,text=True,capture_output=True)
        if p.returncode:
            print('Command: '+' '.join(cmd),file=sys.stderr)
            print(p.stdout+p.stderr,file=sys.stderr); sys.exit(1)
        rows=list(csv.DictReader(io.StringIO(p.stdout)))
        assert len(rows)==12 and all(r['status']=='ok' and int(r['elapsed_ticks'])>0 for r in rows)
        assert all(r['method']=='rob-v2' for r in rows)
        expected=[0,0]
        for i,r in enumerate(rows):
            dep=int(r['dependent'])
            if r['sample_id']=='0': expected[dep]=(expected[dep]+64)%8192
            assert int(r['cycle_position'])==expected[dep]
            assert int(r['collection_order'])==i
            expected[dep]=(expected[dep]+100)%8192
        assert len({r['build_id'] for r in rows})==1
        assert all(Path(prefix+'.'+phase+'.smaps').exists() for phase in ('before','after'))
        if exe.endswith('native'):
            base=int(re.search(r'native data mapping: (0x[0-9a-f]+)',p.stderr)[1],16)
            blocks=re.split(r'(?=^[0-9a-f]+-[0-9a-f]+ )',Path(prefix+'.before.smaps').read_text(),flags=re.M)
            mapping=next(x for x in blocks if x.startswith(f'{base:x}-'))
            assert re.search(r'^AnonHugePages:\s+0 kB',mapping,re.M),'4K allocation unexpectedly used THP'
        print(f'{exe}: CSV, continuous cursors and metadata smoke checks passed')
variant=subprocess.run(['build/rob-native',*args,'--kib','16','--stride','128',
                        '--nop-bytes','2','--alignment','32','--pages','huge'],
                       check=True,text=True,capture_output=True)
variant_rows=list(csv.DictReader(io.StringIO(variant.stdout)))
assert all((r['footprint_bytes'],r['span_bytes'],r['node_stride'],r['nop_bytes'],
            r['loop_alignment'],r['page_policy'])==('16384','32768','128','2','32','huge')
           for r in variant_rows)
for extra in (['--stride','96'],['--pages','unknown'],['--order-seed','0']):
    assert subprocess.run(['build/rob-native',*args,*extra],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==2
assert subprocess.run(['build/rob-native',*args,'--pages','collapse'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==2
# Regression: unavailable collapse and falsely successful collapse must never
# produce samples labeled as a strict huge-page control.
with tempfile.TemporaryDirectory() as tmp:
    source=Path(tmp)/'madvise.c'; interposer=Path(tmp)/'madvise.so'
    source.write_text('''#define _GNU_SOURCE
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <stdlib.h>
#include <errno.h>
int madvise(void *addr,size_t length,int advice) {
    int fake=getenv("ROB_FAKE_COLLAPSE_SUCCESS")!=NULL;
    if(advice==25) { if(fake) return 0; errno=ENOMEM; return -1; }
    if(fake && advice==MADV_HUGEPAGE) advice=MADV_NOHUGEPAGE;
    return (int)syscall(SYS_madvise,addr,length,advice);
}
''')
    subprocess.run(['/usr/bin/gcc','-shared','-fPIC',str(source),'-o',str(interposer)],check=True)
    command=['build/rob-native',str(cpu),'2','10','1','0','0','4','42','--pages','collapse']
    env=dict(os.environ,LD_PRELOAD=str(interposer))
    denied=subprocess.run(command,env=env,capture_output=True,text=True)
    assert denied.returncode==1 and not denied.stdout and 'MADV_COLLAPSE failed' in denied.stderr
    env['ROB_FAKE_COLLAPSE_SUCCESS']='1'
    partial=subprocess.run(command,env=env,capture_output=True,text=True)
    assert partial.returncode==1 and not partial.stdout and 'Full THP backing could not be verified' in partial.stderr
if os.environ.get('TEST_THP')=='1':
    real=subprocess.run(['build/rob-native',str(cpu),'8','100','2','0','0','4','42','--pages','collapse'],text=True,capture_output=True)
    if real.returncode:
        print(real.stderr,file=sys.stderr); sys.exit(1)
    assert 'THP verification before: AnonHugePages=8192 KiB' in real.stderr
    assert 'THP verification after: AnonHugePages=8192 KiB' in real.stderr
    assert len(list(csv.DictReader(io.StringIO(real.stdout))))==4
    print('Native 8 MiB strict THP verification passed')
print('3084 kernel bodies, alignment, native/enclave bytes, pointer cycles and traversal semantics passed')
print('Strict THP allocation-failure and partial-backing rejection checks passed')
