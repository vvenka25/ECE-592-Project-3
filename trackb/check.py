"""Functional and assembly validation in Q3, Q1, Q2, Q5, Q8 order."""
import csv
import ctypes as C
import io
import os
from pathlib import Path
import re
import subprocess as sp
import tempfile

ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
MASK=(1<<64)-1
class State(C.Structure):
    _fields_=[('a',C.c_void_p),('b',C.c_void_p),('pattern',C.c_void_p),('mask',C.c_uint64),
              ('index',C.c_uint64),('out0',C.c_uint64),('out1',C.c_uint64),('out2',C.c_uint64)]
class Config(C.Structure):
    _fields_=[(name,C.c_uint64) for name in ('question','mode','param','footprint','seed')]
class Node(C.Structure):
    _fields_=[('ind',C.c_void_p),('serial',C.c_void_p),('padding',C.c_byte*48)]
FN=C.CFUNCTYPE(C.c_uint64,C.POINTER(State),C.c_uint64)

def bodies(path):
    nm=sp.check_output(['nm','-S','--defined-only',str(path)],text=True)
    sections=sp.check_output(['objdump','-h',str(path)],text=True)
    section=next(x.split() for x in sections.splitlines() if len(x.split())>3 and x.split()[1]=='.text')
    with tempfile.TemporaryDirectory() as tmp:
        target=Path(tmp)/'text';sp.run(['objcopy','--dump-section',f'.text={target}',str(path)],check=True)
        code=target.read_bytes()
    return {p[3]:code[int(p[0],16)-int(section[3],16):int(p[0],16)-int(section[3],16)+int(p[1],16)]
            for line in nm.splitlines() if len(p:=line.split())==4 and re.fullmatch(r'tb_q[12358]_.*',p[3])}

native=bodies('trackb/build/trackb-native')
assert len(native)==1053,len(native)
enclave_bytes_checked=Path('trackb/build/suite.so').exists()
if enclave_bytes_checked:
    assert native==bodies('trackb/build/suite.so'),'Native/enclave kernel bytes differ'
disasm=sp.check_output(['objdump','-d','--no-show-raw-insn','trackb/build/trackb-native'],text=True)
def insns(name):
    block=disasm.split('<'+name+'>:',1)[1].split('\n\n',1)[0]
    return [line.split('\t')[-1].strip() for line in block.splitlines() if '\t' in line]
main_ins=insns('main');mn=[x.split()[0] for x in main_ins]
clocks=[i for i,x in enumerate(mn) if x=='rdtscp'];assert len(clocks)==2
bounds=[]
for clock in clocks:
    before=max(i for i,x in enumerate(mn[:clock]) if x=='lfence')
    after=next(i for i in range(clock+1,len(mn)) if mn[i]=='lfence')
    assert clock-before<10 and after-clock<12
    assert not any(x.startswith(('call','j')) for x in mn[before+1:after])
    bounds.append((before,after))
assert any('tb_run' in x for x in main_ins[bounds[0][1]+1:bounds[1][0]])

with tempfile.TemporaryDirectory() as tmp:
    libpath=Path(tmp)/'engine.so'
    sp.run(['/usr/bin/gcc','-shared','-fPIC','-O2','-Itrackb','trackb/engine.c','trackb/build/dispatch.c',
            'trackb/build/kernels.o','-o',str(libpath)],check=True)
    lib=C.CDLL(str(libpath));lib.tb_lookup.argtypes=[C.c_uint]*3;lib.tb_lookup.restype=C.c_void_p
    lib.tb_init.argtypes=[C.POINTER(Config)];lib.tb_run.argtypes=[C.c_uint,C.c_uint,C.c_uint64];lib.tb_run.restype=C.c_uint64
    lib.tb_base.restype=C.c_void_p;lib.tb_span.restype=C.c_size_t
    def function(q,m,p):
        pointer=lib.tb_lookup(q,m,p);assert pointer,(q,m,p);return FN(pointer)
    # Q3: actual JE and equal two-arm ADD/JMP work; counters depend on input.
    branch=insns('tb_q3_branch');branchless=insns('tb_q3_branchless')
    assert sum(x.startswith('je ') for x in branch)==2  # guard and data branch
    assert sum(x.startswith('jmp ') for x in branch)==2
    assert bytes.fromhex('4983c001eb064983c101eb00') in native['tb_q3_branch'],'Branch arm lengths/work changed'
    assert not any(x.startswith(('cmov','set')) for x in branch)
    assert sum(x.startswith('je ') for x in branchless)==1
    pattern=(C.c_ubyte*16)(*([0,1,1,0]*4))
    for mode in (0,1):
        s=State(pattern=C.addressof(pattern),mask=15,index=13)
        function(3,mode,3)(C.byref(s),37)
        ones=sum(pattern[(13+i)%16] for i in range(37))
        assert (s.out0,s.out1,s.index)==(ones,37-ones,(13+37)%16)
        function(3,mode,3)(C.byref(s),0);assert (s.out0,s.out1)==(0,0)
    print('Q3: retained conditional branch, matched arms, branchless control and exact outcome counts passed')
    # Q1: 32 actual multiplies per iteration, only destination dependencies vary.
    for streams in (1,2,4):
        ii=insns(f'tb_q1_{streams}');assert sum(x.startswith('imul ') for x in ii)==32
        s=State();actual=function(1,0,streams)(C.byref(s),7)
        expected=0
        for i in range(4):expected^=((2*i+3)*pow(3,32*7//streams if i<streams else 0,1<<64))&MASK
        assert actual==s.out0==expected
    print('Q1: fixed multiply count, dependency streams and exact modular arithmetic passed')
    # Q2: exact pointer/compute results plus older blocked multiply ordering.
    ring=(Node*11)();addresses=[C.addressof(ring[i]) for i in range(11)]
    for i in range(11):ring[i].ind=addresses[(i+1)%11]
    for mode,label in enumerate(('overlap','serial','fenced')):
        for k in (0,16,32,64,128):
            ii=insns(f'tb_q2_{label}_{k}')
            mul=[i for i,x in enumerate(ii) if x.startswith('imul ')]
            assert len(mul)==k+1 and '%r8,%rax' in ii[mul[0]]
            assert any('(%r8),%r8' in x for x in ii[:mul[0]])
            assert sum(x=='lfence' for x in ii)==1+(mode==2)
            assert max(i for i,x in enumerate(ii) if x=='lfence')>mul[-1]
            s=State(a=addresses[0]);value=7;old_sum=0
            for iteration in range(3):
                old=addresses[(iteration+1)%11]*3&MASK
                value=(value^(old if mode==1 else 3))*pow(3,k,1<<64)&MASK;old_sum^=old
            actual=function(2,mode,k)(C.byref(s),3)
            assert s.a==addresses[3] and (s.out0,s.out1)==(value,old_sum) and actual==value^old_sum
    print('Q2: older blocked operation precedes younger work; dependency/fence controls and live results passed')
    # Q5: both layouts chase the intended lines and allocate nonidentity LEA destinations.
    a=(Node*5)();b=(Node*5)();aa=[C.addressof(a[i]) for i in range(5)];bb=[C.addressof(b[i]) for i in range(5)]
    serial=[v for pair in zip(aa,bb) for v in pair]
    for i in range(5):a[i].ind=aa[(i+1)%5];b[i].ind=bb[(i+1)%5]
    for i,address in enumerate(serial):C.c_void_p.from_address(address+8).value=serial[(i+1)%10]
    for mode in range(8):
        for n in (0,4,128,512):
            fill=3 if mode>=6 else mode%3;dep=mode-6 if mode>=6 else mode//3
            ii=insns(f'tb_q5_{("lea1","lea4","nop","lea8")[fill]}_d{dep}_{n}')
            assert sum(x.startswith('lea ') for x in ii)==(0 if fill==2 else 2*n)
            assert all(',2)' in x for x in ii if x.startswith('lea ')), 'Q5 must use scaled-index arithmetic, not constant offsets'
            if fill==2:
                first=bytes.fromhex('488b7f08' if dep else '488b3f')
                second=first if dep else bytes.fromhex('488b36')
                padding=bytes.fromhex('0f1f4000')*n
                assert first+padding+second+padding+bytes.fromhex('48ffca') in native[f'tb_q5_nop_d{dep}_{n}']
            assert len({len(native[f'tb_q5_{f}_d{dep}_{n}']) for f in ('lea1','lea4','lea8','nop')})==1
            s=State(a=aa[0],b=bb[0]);actual=function(5,mode,n)(C.byref(s),7)
            assert s.a==(serial[14%10] if dep else aa[7%5])
            assert s.b==(bb[0] if dep else bb[7%5])
            expected=0
            chains=(1,4,0,8)[fill]
            for i in range(8):
                exponent=2*7*max(0,(n+chains-1-i)//chains) if chains and i<chains else 0
                expected^=((2*i+3)*pow(3,exponent,1<<64))&MASK
            assert actual==expected==s.out0
    print('Q5: 64-bit GPR LEA/NOP controls, two rings, serial traversal and filler results passed')
    # Q8: equal cache-line counts and balanced L1-set offsets; exact full cycles.
    for count in (128,256,384):
        for mode in (0,1):
            cfg=Config(8,mode,count,0,42);assert lib.tb_init(C.byref(cfg))==0
            pointer=lib.tb_run(mode,count,0);start=pointer;seen=set()
            for _ in range(count):
                assert pointer not in seen;seen.add(pointer);pointer=C.c_void_p.from_address(pointer).value
            assert pointer==start and len(seen)==count
            assert len({p//4096 for p in seen})==(count if mode else count//64)
            assert len({(p//64)%64 for p in seen})==64
            assert lib.tb_run(mode,count,count)==start
            lib.tb_free()
    print('Q8: compact/scattered page geometry, equal cache-line footprint and full-cycle traversal passed')

cpu=int(os.environ.get('TEST_CPU',min(os.sched_getaffinity(0))))
assert cpu in os.sched_getaffinity(0),'TEST_CPU is not permitted'
exes=['trackb/build/trackb-native']
if os.environ.get('TEST_SGX')=='1':exes+=['trackb/build/trackb-enclave']
reference={}
for exe in exes:
    for q,mode,param,kib in ((3,0,3,16),(1,0,4,0),(2,0,32,16),(5,1,32,16),(5,6,32,16),(8,0,128,0),(8,1,128,0)):
        command=[exe,'--question',str(q),'--cpu',str(cpu),'--mode',str(mode),'--param',str(param),
                 '--footprint-kib',str(kib),'--iterations','64','--samples','2','--pmu','off']
        p=sp.run(command,text=True,capture_output=True)
        if p.returncode:raise RuntimeError(p.stderr)
        rows=list(csv.DictReader(io.StringIO(p.stdout)));assert len(rows)==2
        assert all(r['status']=='ok' and r['timer_unit']=='tsc_ticks' and r['pmu0']=='' and r['pmu_time_running']=='' and None not in r for r in rows)
        for sample,r in enumerate(rows):
            first,second,checksum=map(int,(r['result0'],r['result1'],r['checksum']))
            if q==3:assert first+second==64 and checksum==first^second
            elif q==2:assert checksum==first^second
            else:assert checksum==first
            period=int(r['node_count'])//2 if q==5 else int(r['node_count'])
            assert int(r['cursor_index'])==((64+(sample+1)*64)%period if period else 0)
        if q==8:
            match=re.search(r'(?:native|enclave) data mapping: (0x[0-9a-f]+)',p.stderr)
            assert match,'Q8 must record its actual arena base outside timing'
            base=int(match[1],16);assert base%4096==0,'Native/enclave Q8 arenas must be page aligned'
            order=list(range(param));rng=42
            for i in range(param-1,0,-1):
                rng^=(rng<<13)&MASK;rng^=rng>>7;rng^=(rng<<17)&MASK
                j=rng%(i+1);order[i],order[j]=order[j],order[i]
            for r in rows:
                node=order[int(r['cursor_index'])]
                offset=node*4096+(node%64)*64 if mode else node*64
                assert int(r['result0'])==base+offset,'Q8 geometry/cursor differs inside this actual build'
        if q in (1,3,5):
            values=[(r['result0'],r['result1']) for r in rows]
            if exe.endswith('native'):reference[q,mode,param]=values
            else:assert values==reference[q,mode,param],'Enclave result differs from native reference'
    p=sp.run([exe,'--question','4','--cpu',str(cpu)],capture_output=True)
    assert p.returncode==2 and not p.stdout
    for extra in (['--question','3','--param','0','--lo','3','--hi','3'],['--question','5','--hi','512']):
        p=sp.run([exe,'--cpu',str(cpu),*extra],capture_output=True)
        assert p.returncode==2 and not p.stdout,'Unsupported sweep arguments must not relabel initialized data'
    print(exe+': five-question CSV smoke checks passed')
with tempfile.TemporaryDirectory() as tmp:
    prefix=str(Path(tmp)/'placement')
    sp.run(['trackb/build/trackb-native','--question','8','--cpu',str(cpu),'--mode','0','--param','128',
            '--iterations','64','--samples','2','--pmu','off','--metadata',prefix],check=True,capture_output=True)
    for phase in ('before','after'):
        rr=list(csv.DictReader(Path(prefix+f'.{phase}.page_nodes.csv').open()))
        count=0
        for r in rr:
            assert int(r['first_page'])==count and int(r['page_count'])>0 and int(r['node_or_error'])>=0
            count+=int(r['page_count'])
        assert count==2,'Must query every compact-ring page in both snapshots'
print('Native read-only per-page residency metadata passed; no page migration requested.')
with tempfile.TemporaryDirectory() as tmp:
    source=Path(tmp)/'deny.c';shim=Path(tmp)/'deny.so'
    source.write_text('#include <errno.h>\nlong syscall(long number,...) { (void)number;errno=EPERM;return -1; }\n')
    sp.run(['/usr/bin/gcc','-shared','-fPIC',str(source),'-o',str(shim)],check=True)
    env=dict(os.environ,LD_PRELOAD=str(shim))
    command=['trackb/build/trackb-native','--question','8','--cpu',str(cpu),'--mode','1','--param','128','--iterations','64','--samples','2']
    p=sp.run(command+['--pmu','auto'],env=env,text=True,capture_output=True);assert p.returncode==0,p.stderr
    rows=list(csv.DictReader(io.StringIO(p.stdout)))
    assert len(rows)==2 and all(r['pmu_status'].startswith('unavailable-') and r['pmu0']==r['pmu_time_running']=='' for r in rows)
    p=sp.run(command+['--pmu','required'],env=env,text=True,capture_output=True)
    assert p.returncode!=0 and not p.stdout
print('PMU denial: auto records unavailable/blank counts; required fails before samples.')
print('Native timer boundary assembly and 1053 kernel bodies verified; no timing magnitude asserted.')
print('1053 native/enclave kernel byte comparisons passed.' if enclave_bytes_checked else 'Enclave byte comparison unavailable: no linked enclave in this build.')
if Path('trackb/build/trackb-enclave').exists():
    text=sp.check_output(['objdump','-d','--no-show-raw-insn','--disassemble=main','trackb/build/trackb-enclave'],text=True)
    ii=[x.split('\t')[-1].strip() for x in text.splitlines() if '\t' in x]
    clocks=[i for i,x in enumerate(ii) if x=='rdtscp'];assert len(clocks)==2
    bounds=[]
    for clock in clocks:
        left=max(i for i in range(clock) if ii[i]=='lfence')
        right=next(i for i in range(clock+1,len(ii)) if ii[i]=='lfence')
        assert not any(x.startswith(('call','j')) for x in ii[left+1:right])
        bounds.append((left,right))
    assert any('suite_run' in x for x in ii[bounds[0][1]+1:bounds[1][0]])
    print('Separate enclave-host timer brackets verified around suite_run; this is assembly inspection, not SGX execution.')
