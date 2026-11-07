#!/usr/bin/env python3
"""Build-time assembly, developed in Q3/Q1/Q2/Q5/Q8 order; identical in SGX."""
from pathlib import Path
import sys

out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
asm=['.text'];decl=['#include "bench.h"'];names=[]
def begin(name):
    names.append(name)
    decl.append(f'extern uint64_t {name}(struct tb_state *,uint64_t);')
    asm.extend(['.p2align 6',f'.globl {name}',f'.type {name},@function',f'{name}:'])
def end(name):asm.extend(['ret',f'.size {name},.-{name}'])

# Q3: equal-length arms, an observable counter in each arm, explicit JE.
for mode in ('branch','branchless'):
    name='tb_q3_'+mode;begin(name)
    asm+=['mov 16(%rdi),%r10','mov 24(%rdi),%r11','mov 32(%rdi),%rax',
          'xor %r8d,%r8d','xor %r9d,%r9d','test %rsi,%rsi',f'jz .Lend_{name}',
          '.p2align 6',f'.Lloop_{name}:','movzbl (%r10,%rax),%edx']
    if mode=='branch':
        asm+=['test %edx,%edx',f'jz .Lzero_{name}','add $1,%r8',f'jmp .Ljoin_{name}',
              f'.Lzero_{name}:','add $1,%r9',f'jmp .Ljoin_{name}',f'.Ljoin_{name}:']
    else:asm+=['add %rdx,%r8','xor $1,%edx','add %rdx,%r9']
    asm+=['inc %rax','and %r11,%rax','dec %rsi',f'jnz .Lloop_{name}',f'.Lend_{name}:',
          'mov %rax,32(%rdi)','mov %r8,40(%rdi)','mov %r9,48(%rdi)','mov %r8,%rax','xor %r9,%rax']
    end(name)

# Q1: same 32 integer multiplies per iteration; only chain assignment changes.
for chains in (1,2,4):
    name=f'tb_q1_{chains}';begin(name)
    asm += [f'mov ${2*i+3},%r{8+i}' for i in range(4)]
    asm+=['test %rsi,%rsi',f'jz .Lend_{name}', '.p2align 6',f'.Lloop_{name}:']
    asm += [f'imul $3,%r{8+i%chains},%r{8+i%chains}' for i in range(32)]
    asm+=['dec %rsi',f'jnz .Lloop_{name}',f'.Lend_{name}:','mov %r8,%rax','xor %r9,%rax',
          'xor %r10,%rax','xor %r11,%rax','mov %rax,40(%rdi)']
    end(name)

# Q2: older load-dependent multiply precedes every younger multiply.
for mode in ('overlap','serial','fenced'):
    for k in (0,16,32,64,128):
        name=f'tb_q2_{mode}_{k}';begin(name)
        asm+=['mov 0(%rdi),%r8','mov $7,%r9','xor %r10d,%r10d','mov $3,%r11',
              'test %rsi,%rsi',f'jz .Lend_{name}', '.p2align 6',f'.Lloop_{name}:',
              'mov (%r8),%r8','imul $3,%r8,%rax']
        if mode=='fenced':asm+=['lfence']
        asm+=['xor %rax,%r9' if mode=='serial' else 'xor %r11,%r9']
        asm += ['imul $3,%r9,%r9']*k
        # Common end fence prevents a serialized chain from overlapping the
        # next iteration's load; only within-block overlap is being tested.
        asm+=['xor %rax,%r10','lfence','dec %rsi',f'jnz .Lloop_{name}',f'.Lend_{name}:',
              'mov %r8,0(%rdi)','mov %r9,40(%rdi)','mov %r10,48(%rdi)','mov %r9,%rax','xor %r10,%rax']
        end(name)

# Q5: scaled-index LEA computes 3*x without modifying FLAGS. A mere constant
# offset was not a reliable ordinary-allocation treatment on the target CPU.
# Four-byte NOP controls match LEA instruction count and encoded byte length.
tables={}
gprs=['r8','r9','r10','r11','rbx','r12','r14','r15']
for dep in (0,1):
    for fill in ('lea1','lea4','nop','lea8'):
        table=[]
        for n in range(0,513,4):
            name=f'tb_q5_{fill}_d{dep}_{n}';begin(name);table.append(name)
            asm+=['push %rbx','push %r12','push %r14','push %r15',
                  'mov %rdi,%rcx','mov %rsi,%rdx','mov 0(%rcx),%rdi','mov 8(%rcx),%rsi']
            asm += [f'mov ${2*i+3},%{reg}' for i,reg in enumerate(gprs)]
            asm+=['test %rdx,%rdx',f'jz .Lend_{name}', '.p2align 6',f'.Lloop_{name}:']
            for gap in (0,1):
                asm += ['mov 8(%rdi),%rdi' if dep else ('mov (%rdi),%rdi' if gap==0 else 'mov (%rsi),%rsi')]
                chains=8 if fill=='lea8' else 4 if fill=='lea4' else 1
                for i in range(n):
                    reg=gprs[i%chains]
                    asm += ['.byte 0x0f,0x1f,0x40,0x00' if fill=='nop' else f'lea (%{reg},%{reg},2),%{reg}']
            asm+=['dec %rdx',f'jnz .Lloop_{name}',f'.Lend_{name}:','mov %rdi,0(%rcx)','mov %rsi,8(%rcx)',
                  'mov %r8,%rax']
            asm += [f'xor %{reg},%rax' for reg in gprs[1:]]
            asm += ['mov %rax,40(%rcx)','pop %r15','pop %r14','pop %r12','pop %rbx']
            end(name)
        tables[dep,fill]=table

# Q8: one dependent load per iteration; ring geometry is built outside timing.
name='tb_q8_chase';begin(name)
asm+=['mov 0(%rdi),%r8','test %rsi,%rsi',f'jz .Lend_{name}', '.p2align 6',f'.Lloop_{name}:',
      'mov (%r8),%r8','dec %rsi',f'jnz .Lloop_{name}',f'.Lend_{name}:','mov %r8,0(%rdi)',
      'mov %r8,40(%rdi)','mov %r8,%rax'];end(name)
asm+=['.section .note.GNU-stack,"",@progbits']
decl+=['tb_fn tb_lookup(unsigned q,unsigned mode,unsigned p) {',
       'if(q==3 && mode<2) return mode?tb_q3_branchless:tb_q3_branch;',
       'if(q==1 && mode==0) {']
for chains in (1,2,4):decl+=[f'if(p=={chains}) return tb_q1_{chains};']
decl+=['}', 'if(q==2) {']
for m,mode in enumerate(('overlap','serial','fenced')):
    for k in (0,16,32,64,128):decl+=[f'if(mode=={m} && p=={k}) return tb_q2_{mode}_{k};']
decl+=['}', 'if(q==5 && p<=512 && !(p%4)) {']
for dep in (0,1):
    for m,fill in enumerate(('lea1','lea4','nop','lea8')):
        mode=6+dep if fill=='lea8' else dep*3+m
        decl+=[f'if(mode=={mode}) {{ static tb_fn const t[]={{'+','.join(tables[dep,fill])+'};return t[p/4];}']
decl+=['}', 'if(q==8 && mode<2) return tb_q8_chase;', 'return 0;', '}']
(out/'kernels.S').write_text('\n'.join(asm)+'\n')
(out/'dispatch.c').write_text('\n'.join(decl)+'\n')
(out/'symbols.txt').write_text('\n'.join(names)+'\n')
