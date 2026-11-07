#!/usr/bin/env python3
"""Build-time kernels: same object for native and enclave, no runtime codegen."""
from pathlib import Path
import sys
out=Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=True)
ns=range(0,1025,4)
a=['.text']; h=['#include "common.h"']; tables=[]
for width in (1,2):
    for alignment in (0,16,32):
        entries=[]
        for n in ns:
            names=[]
            for mode in ('independent','dependent'):
                name=f'rob_{mode}_{n}_b{width}_a{alignment}'; names.append(name)
                a += ['.p2align 6',f'.globl {name}',f'.type {name}, @function',f'{name}:',
                      'test %rdx,%rdx',f'jz .Lend_{name}', '.p2align 6']
                if alignment: a += [f'.fill {alignment},1,0x90']
                a += [f'.Lloop_{name}:', 'mov (%rdi),%rdi' if mode=='independent' else 'mov 8(%rdi),%rdi']
                a += (['nop'] if width==1 else ['.byte 0x66,0x90'])*n
                a += ['mov (%rsi),%rsi' if mode=='independent' else 'mov 8(%rdi),%rdi']
                a += (['nop'] if width==1 else ['.byte 0x66,0x90'])*n
                a += ['dec %rdx',f'jnz .Lloop_{name}',f'.Lend_{name}:',
                      'mov %rdi,(%rcx)','mov %rsi,8(%rcx)','ret',f'.size {name},.-{name}']
                h += [f'extern void {name}(void *,void *,uint64_t,struct rob_cursor *);']
            entries.append('{'+','.join(names)+'}')
        table=f'table_b{width}_a{alignment}'
        h += [f'static kernel_fn const {table}[257][2]={{'+','.join(entries)+'};']
        tables.append((width,alignment,table))
a += ['.section .note.GNU-stack,"",@progbits']
h += ['kernel_fn get_kernel(unsigned n,unsigned dependent,unsigned width,unsigned alignment) {',
      'if(n>1024 || n%4 || dependent>1) return 0;']
for width,alignment,table in tables:
    h += [f'if(width=={width} && alignment=={alignment}) return {table}[n/4][dependent];']
h += ['return 0; }']
(out/'kernels.S').write_text('\n'.join(a)+'\n')
(out/'dispatch.c').write_text('\n'.join(h)+'\n')
