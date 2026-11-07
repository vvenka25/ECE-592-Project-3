#define _GNU_SOURCE
#include <cpuid.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
int main(int argc,char **argv) {
    if(argc!=2) return 2;
    char *end; long cpu=strtol(argv[1],&end,10);
    if(!*argv[1] || *end || cpu<0 || cpu>=CPU_SETSIZE) return 2;
    cpu_set_t set; CPU_ZERO(&set); CPU_SET(cpu,&set);
    if(sched_setaffinity(0,sizeof(set),&set)) { perror("affinity"); return 1; }
    unsigned a,b,c,d,max=__get_cpuid_max(0,NULL);
    if(max<0x12) { puts("CPUID leaf 0x12 unavailable"); return 0; }
    uint64_t total=0;
    for(unsigned i=0;i<64;++i) {
        __cpuid_count(0x12,i,a,b,c,d);
        printf("CPUID.12.%u eax=%08x ebx=%08x ecx=%08x edx=%08x\n",i,a,b,c,d);
        if(i>=2) {
            if(!(a&15)) break;
            if((a&15)==1) {
                uint64_t size=((uint64_t)(d&0xfffff)<<32)|(c&0xfffff000);
                total+=size;
            }
        }
    }
    printf("CPUID EPC section bytes=%"PRIu64" (enumerated, not free or available EPC)\n",total);
    if(max>=7) { __cpuid_count(7,2,a,b,c,d); printf("DDP control enumeration=%u\n",(d>>3)&1); }
    return 0;
}
