#include "bench.h"
#include <stdlib.h>
#include <string.h>
#ifndef TRUSTED
#include <sys/mman.h>
#endif
_Static_assert(offsetof(struct tb_state,pattern)==16,"Assembly ABI");
_Static_assert(offsetof(struct tb_state,out0)==40,"Assembly ABI");
_Static_assert(sizeof(struct tb_state)==64,"Assembly ABI");
static struct tb_config cfg;
static struct tb_state state;
static void *allocation;
static unsigned char *arena;
static size_t span,nodes;
static uint64_t random_next(uint64_t *s) { *s^=*s<<13;*s^=*s>>7;*s^=*s<<17;return *s; }
static void shuffle(size_t *v,size_t n,uint64_t *seed) {
    for(size_t i=n-1;i>0;--i) { size_t j=random_next(seed)%(i+1),t=v[i];v[i]=v[j];v[j]=t; }
}
void tb_free(void) {
#ifdef TRUSTED
    free(allocation);
#else
    if(allocation) munmap(allocation,span);
#endif
    allocation=NULL;arena=NULL;span=nodes=0;memset(&state,0,sizeof(state));
}
void *tb_base(void) { return arena; }
size_t tb_span(void) { return span; }
uint64_t tb_result(unsigned which) { return which==0?state.out0:which==1?state.out1:which==3?(uintptr_t)arena:state.index; }
static unsigned char *node(size_t i) {
    if(cfg.question==8 && cfg.mode==1) return arena+i*4096+(i%64)*64;
    return arena+i*64;
}
int tb_init(const struct tb_config *c) {
    tb_free();cfg=*c;
    if(!cfg.seed || !tb_lookup(cfg.question,cfg.mode,cfg.param)) return -1;
    if(cfg.question==1) return 0;
    if(cfg.question==3) {
        if(cfg.param>3 || cfg.footprint<1024 || cfg.footprint>1048576 || (cfg.footprint&(cfg.footprint-1))) return -1;
        span=cfg.footprint;nodes=span;
    } else if(cfg.question==8) {
        if(cfg.param<64 || cfg.param>384 || cfg.param%64) return -1;
        nodes=cfg.param;span=cfg.mode?nodes*4096:((nodes*64+4095)&~(size_t)4095);
    } else {
        if(cfg.footprint<8192 || cfg.footprint>256UL*1024*1024 || cfg.footprint%128) return -1;
        span=cfg.footprint;nodes=span/64;
    }
#ifdef TRUSTED
    size_t alignment=cfg.question==8?4096:64;
    allocation=malloc(span+alignment-1);
    if(allocation) arena=(unsigned char *)(((uintptr_t)allocation+alignment-1)&~(uintptr_t)(alignment-1));
#else
    allocation=mmap(NULL,span,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(allocation==MAP_FAILED) allocation=NULL;
    arena=allocation;
    if(arena && madvise(arena,span,MADV_NOHUGEPAGE)) { tb_free();return -2; }
#endif
    if(!arena) { tb_free();return -2; }
    uint64_t seed=cfg.seed;
    if(cfg.question==3) {
        for(size_t i=0;i<span;++i) arena[i]=cfg.param==0?0:cfg.param==1?1:(i&1);
        if(cfg.param==3) for(size_t i=span-1;i>0;--i) { size_t j=random_next(&seed)%(i+1);unsigned char t=arena[i];arena[i]=arena[j];arena[j]=t; }
        state.pattern=arena;state.mask=span-1;return 0;
    }
    size_t *order=malloc(nodes*sizeof(*order));
    if(!order) { tb_free();return -2; }
    for(size_t i=0;i<nodes;++i) order[i]=i;
    shuffle(order,nodes,&seed);
    if(cfg.question==5) {
        size_t half=nodes/2;
        for(size_t i=0;i<half;++i) {
            unsigned char *a=node(order[i]),*b=node(order[half+i]);
            void *an=node(order[(i+1)%half]),*bn=node(order[half+(i+1)%half]);
            *(void **)a=an;*(void **)b=bn;*(void **)(a+8)=b;*(void **)(b+8)=an;
        }
        state.a=node(order[0]);state.b=node(order[half]);
    } else {
        for(size_t i=0;i<nodes;++i) *(void **)node(order[i])=node(order[(i+1)%nodes]);
        state.a=node(order[0]);
    }
    free(order);return 0;
}
uint64_t tb_run(unsigned mode,unsigned param,uint64_t iterations) {
    tb_fn f=tb_lookup(cfg.question,mode,param);
    if(!f)return 0;
    uint64_t value=f(&state,iterations);
    if(nodes && cfg.question!=3)state.index=(state.index+iterations)%(cfg.question==5?nodes/2:nodes);
    return value;
}
int tb_warm(unsigned mode,unsigned param) {
    if(!tb_lookup(cfg.question,mode,param)) return -1;
    if(cfg.question==5) tb_run(mode,0,nodes/2);
    else if(cfg.question==2) tb_run(mode,0,nodes);
    else if(cfg.question==8 || cfg.question==3) tb_run(mode,param,nodes*2);
    tb_run(mode,param,64);return 0;
}
