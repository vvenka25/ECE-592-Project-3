#ifndef TRUSTED
#define _GNU_SOURCE
#include <sys/mman.h>
#include <errno.h>
/* Linux UAPI value; older libc headers may predate the running kernel. */
#ifndef MADV_COLLAPSE
#define MADV_COLLAPSE 25
#endif
#endif
#include "common.h"
#include <stdlib.h>
static unsigned char *allocation, *base;
static size_t span;
static struct rob_cursor cursors[2];
static uint64_t rng(uint64_t *s) { *s ^= *s << 13; *s ^= *s >> 7; *s ^= *s << 17; return *s; }
static void shuffle(size_t *order, size_t count, uint64_t *seed) {
    for (size_t i=0; i<count; ++i) order[i]=i;
    for (size_t i=count-1; i; --i) {
        size_t j=rng(seed)%(i+1), t=order[i]; order[i]=order[j]; order[j]=t;
    }
}
void *memory_base(void) { return base; }
size_t memory_span(void) { return span; }
void release_memory(void) {
#ifdef TRUSTED
    free(allocation);
#else
    if (allocation) munmap(allocation,span);
#endif
    allocation=base=NULL; span=0;
    cursors[0].a=cursors[0].b=cursors[1].a=cursors[1].b=NULL;
}
int setup_memory(size_t footprint, uint64_t seed, unsigned stride, unsigned pages) {
    if (footprint<8192 || footprint%128 || !seed ||
        (stride!=64 && stride!=128) || pages>ROB_PAGES_COLLAPSE ||
        footprint>512UL*1024*1024/(stride/64)) return -1;
    if (pages==ROB_PAGES_COLLAPSE && (footprint*(stride/64))%ROB_HUGE_SIZE) return -1;
#ifdef TRUSTED
    if (pages!=ROB_PAGES_DEFAULT) return -1;
#endif
    release_memory();
    span=footprint*(stride/64);
#ifdef TRUSTED
    allocation=malloc(span+63);
    if (allocation) base=(unsigned char *)(((uintptr_t)allocation+63)&~(uintptr_t)63);
#else
    if (pages==ROB_PAGES_COLLAPSE) {
        /* Leave holes at both ends so smaps can identify the exact mapping.
           No MAP_FIXED: trim only memory owned by this allocation. */
        size_t reserve=span+2*ROB_HUGE_SIZE;
        unsigned char *raw=mmap(NULL,reserve,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
        if (raw!=MAP_FAILED) {
            allocation=(unsigned char *)(((uintptr_t)raw+ROB_HUGE_SIZE)&~(uintptr_t)(ROB_HUGE_SIZE-1));
            size_t prefix=(size_t)(allocation-raw),suffix=reserve-prefix-span;
            if (munmap(raw,prefix) || munmap(allocation+span,suffix)) {
                int saved=errno; munmap(raw,reserve); allocation=NULL; errno=saved;
            }
        }
    } else {
        allocation=mmap(NULL,span,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
        if (allocation==MAP_FAILED) allocation=NULL;
    }
    base=allocation;
    if (base && pages!=ROB_PAGES_DEFAULT &&
        madvise(base,span,pages==ROB_PAGES_4K?MADV_NOHUGEPAGE:MADV_HUGEPAGE)) {
        int saved=errno; release_memory(); errno=saved; return -2;
    }
#endif
    size_t count=footprint/128;
    size_t *a=malloc(count*sizeof(*a)), *b=malloc(count*sizeof(*b));
    if (!base || !a || !b) { free(a); free(b); release_memory(); return -1; }
    /* Separate shuffles from a deterministic stream; no paired address offset. */
    shuffle(a,count,&seed); shuffle(b,count,&seed);
    for (size_t i=0; i<count; ++i) {
        size_t next=(i+1)%count;
        unsigned char *pa=base+stride*a[i], *pb=base+stride*(count+b[i]);
        void *an=base+stride*a[next], *bn=base+stride*(count+b[next]);
        *(void **)pa=an; *(void **)pb=bn;
        /* One dependent cycle visits A[i],B[i],A[i+1],B[i+1],... */
        *(void **)(pa+8)=pb; *(void **)(pb+8)=an;
    }
    cursors[0].a=cursors[1].a=base+stride*a[0];
    cursors[0].b=cursors[1].b=base+stride*(count+b[0]);
    free(a); free(b);
#ifndef TRUSTED
    /* Graph writes populated every page. Collapse is setup, never timed. */
    if (pages==ROB_PAGES_COLLAPSE && madvise(base,span,MADV_COLLAPSE)) {
        int saved=errno; release_memory(); errno=saved; return -3;
    }
#endif
    return 0;
}
uintptr_t run_kernel(unsigned n, unsigned dependent, uint64_t iterations, unsigned nop_bytes, unsigned alignment) {
    kernel_fn f=get_kernel(n,dependent,nop_bytes,alignment);
    if (!f || !base || dependent>1) return 0;
    struct rob_cursor *c=&cursors[dependent];
    f(c->a,c->b,iterations,c);
    return (uintptr_t)c->a^(uintptr_t)c->b;
}
