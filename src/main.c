#define _GNU_SOURCE
#include "common.h"
#include "build_id.h"
#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include <sched.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <x86intrin.h>
#include <sys/resource.h>
#include <time.h>
#include <limits.h>
#ifdef ENCLAVE
#include "sgx_urts.h"
#include "Rob_u.h"
static sgx_enclave_id_t eid;
static void check(const char *operation, sgx_status_t s) {
    if(s==SGX_SUCCESS) return;
    const char *reason;
    switch(s) {
    case SGX_ERROR_UNEXPECTED: reason="SGX_ERROR_UNEXPECTED (check runtime library selection and runtime diagnostics)"; break;
    case SGX_ERROR_NO_DEVICE: reason="SGX_ERROR_NO_DEVICE (check SGX device availability and permissions)"; break;
    case SGX_ERROR_OUT_OF_EPC: reason="SGX_ERROR_OUT_OF_EPC (insufficient EPC for the configured enclave)"; break;
    case SGX_ERROR_OUT_OF_MEMORY: reason="SGX_ERROR_OUT_OF_MEMORY"; break;
    case SGX_ERROR_ENCLAVE_FILE_ACCESS: reason="SGX_ERROR_ENCLAVE_FILE_ACCESS (run from the project root)"; break;
    case SGX_ERROR_INVALID_ENCLAVE: reason="SGX_ERROR_INVALID_ENCLAVE"; break;
    case SGX_ERROR_INVALID_METADATA: reason="SGX_ERROR_INVALID_METADATA"; break;
    case SGX_ERROR_INVALID_VERSION: reason="SGX_ERROR_INVALID_VERSION (SDK/runtime compatibility)"; break;
    case SGX_ERROR_ENCLAVE_CRASHED: reason="SGX_ERROR_ENCLAVE_CRASHED"; break;
    default: reason="see sgx_error.h in the installed SDK"; break;
    }
    fprintf(stderr,"%s failed: 0x%x: %s\n",operation,s,reason);
    exit(1);
}
#endif
static uint64_t number(const char *s) {
    char *end; errno=0; unsigned long long n=strtoull(s,&end,10);
    if(errno || !*s || *end || strspn(s,"0123456789")!=strlen(s)) { fprintf(stderr,"Invalid number: %s\n",s); exit(2); }
    return n;
}
static uint64_t random_next(uint64_t *s) { *s^=*s<<13; *s^=*s>>7; *s^=*s<<17; return *s; }
static uint64_t invoke(unsigned n,unsigned dep,uint64_t iters,unsigned width,unsigned align) {
#ifdef ENCLAVE
    uint64_t v; check("rob_run",rob_run(eid,&v,n,dep,iters,width,align)); return v;
#else
    return run_kernel(n,dep,iters,width,align);
#endif
}
/* Snapshots occur outside measured regions. smaps includes mapping addresses. */
static void snapshot(const char *prefix,const char *phase) {
    if (!prefix) return;
    const char *names[]={"smaps","numa_maps","status"};
    for (unsigned i=0;i<3;++i) {
        char dst[PATH_MAX],src[80],buf[8192];
        if(snprintf(dst,sizeof(dst),"%s.%s.%s",prefix,phase,names[i])>=(int)sizeof(dst)) {
            fprintf(stderr,"Metadata path too long\n"); exit(2);
        }
        snprintf(src,sizeof(src),"/proc/self/%s",names[i]);
        FILE *in=fopen(src,"r"),*out=fopen(dst,"wx");
        if (!in || !out) { perror("metadata snapshot"); exit(1); }
        size_t len;
        while((len=fread(buf,1,sizeof(buf),in))) {
            if(fwrite(buf,1,len,out)!=len) { perror("metadata write"); exit(1); }
        }
        if(ferror(in) || fclose(out)) { fprintf(stderr,"Metadata I/O error\n"); exit(1); }
        fclose(in);
    }
}
#ifndef ENCLAVE
static void verify_full_thp(const char *phase) {
    FILE *f=fopen("/proc/self/smaps","r");
    if(!f) { perror("THP verification"); exit(1); }
    char line[512]; uintptr_t lo,hi;
    uintptr_t begin=(uintptr_t)memory_base(),end=begin+memory_span();
    int selected=0,found=0; unsigned long long huge_kib=0;
    while(fgets(line,sizeof(line),f)) {
        if(sscanf(line,"%"SCNxPTR"-%"SCNxPTR,&lo,&hi)==2) selected=(lo==begin && hi==end);
        else if(selected && sscanf(line,"AnonHugePages: %llu kB",&huge_kib)==1) { found=1; break; }
    }
    fclose(f);
    fprintf(stderr,"THP verification %s: AnonHugePages=%llu KiB; required=%zu KiB\n",
            phase,huge_kib,memory_span()/1024);
    if(!found || huge_kib!=memory_span()/1024) {
        fprintf(stderr,"Full THP backing could not be verified; this run cannot serve as the strict huge-page control\n");
        exit(1);
    }
}
#endif
static void usage(const char *exe) {
    fprintf(stderr,"Usage: %s CPU MiB iterations samples min_n max_n step seed [options]\n"
        "Options: --kib K --stride 64|128 --pages 4k|huge|collapse|default\n"
        "         --order-seed S --nop-bytes 1|2 --alignment 0|16|32\n"
        "         --metadata PREFIX --run-id ID\n",exe);
}
int main(int argc,char **argv) {
    if(argc<9) { usage(argv[0]); return 2; }
    uint64_t cpu=number(argv[1]),mib=number(argv[2]),iters=number(argv[3]),samples=number(argv[4]);
    uint64_t lo=number(argv[5]),hi=number(argv[6]),step=number(argv[7]),seed=number(argv[8]);
    uint64_t kib=0,stride=64,width=1,alignment=0,order_seed=1;
#ifdef ENCLAVE
    const char *policy="epc";
#else
    unsigned pages=ROB_PAGES_4K;
    const char *policy="4k";
#endif
    const char *metadata=NULL,*run_id=NULL;
    for(int i=9;i<argc;i+=2) {
        if(i+1==argc) { usage(argv[0]); return 2; }
        const char *key=argv[i],*val=argv[i+1];
        if(!strcmp(key,"--kib")) kib=number(val);
        else if(!strcmp(key,"--stride")) stride=number(val);
        else if(!strcmp(key,"--nop-bytes")) width=number(val);
        else if(!strcmp(key,"--alignment")) alignment=number(val);
        else if(!strcmp(key,"--order-seed")) order_seed=number(val);
        else if(!strcmp(key,"--metadata")) metadata=val;
        else if(!strcmp(key,"--run-id")) run_id=val;
        else if(!strcmp(key,"--pages")) {
#ifdef ENCLAVE
            fprintf(stderr,"--pages applies only to native allocations; enclave uses EPC\n"); return 2;
#else
            if(!strcmp(val,"4k")) pages=ROB_PAGES_4K;
            else if(!strcmp(val,"huge")) pages=ROB_PAGES_HUGE;
            else if(!strcmp(val,"collapse")) pages=ROB_PAGES_COLLAPSE;
            else if(!strcmp(val,"default")) pages=ROB_PAGES_DEFAULT;
            else { fprintf(stderr,"Invalid page policy\n"); return 2; }
            policy=val;
#endif
        } else { fprintf(stderr,"Unknown option: %s\n",key); return 2; }
    }
    if(cpu>=CPU_SETSIZE || !mib || mib>512 || kib>512*1024 ||
       samples<1 || samples>1000000 || iters>UINT64_MAX/2 ||
       lo>hi || hi>1024 || lo%4 || hi%4 || !step || step>1024 || step%4 ||
       !seed || !order_seed || (stride!=64 && stride!=128) ||
       (width!=1 && width!=2) || (alignment!=0 && alignment!=16 && alignment!=32)) {
        fprintf(stderr,"Invalid benchmark parameters\n"); return 2;
    }
    size_t footprint=kib?kib*1024:mib*1024*1024;
    if(footprint<8192 || footprint>512UL*1024*1024/(stride/64)) {
        fprintf(stderr,"Footprint must be >=8 KiB and address span <=512 MiB\n"); return 2;
    }
#ifndef ENCLAVE
    if(pages==ROB_PAGES_COLLAPSE && (footprint*(stride/64))%ROB_HUGE_SIZE) {
        fprintf(stderr,"Collapse policy requires an address span that is a multiple of 2 MiB\n"); return 2;
    }
#endif
    char generated_id[80];
    if(!run_id) {
        snprintf(generated_id,sizeof(generated_id),"%ld-%ld",(long)time(NULL),(long)getpid()); run_id=generated_id;
    }
    if(!*run_id || strlen(run_id)>79 || strspn(run_id,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")!=strlen(run_id)) {
        fprintf(stderr,"Run ID must use 1..79 letters, digits, dots, underscores or hyphens\n"); return 2;
    }
    cpu_set_t set; CPU_ZERO(&set); CPU_SET(cpu,&set);
    if(sched_setaffinity(0,sizeof(set),&set)) { perror("affinity"); return 1; }
    int rc;
#ifdef ENCLAVE
    check("sgx_create_enclave",sgx_create_enclave("build/rob.signed.so",SGX_DEBUG_FLAG,NULL,NULL,&eid,NULL));
    check("rob_init",rob_init(eid,&rc,footprint,seed,stride));
    const char *env="sgx-hw-debug";
#else
    rc=setup_memory(footprint,seed,stride,pages);
    const char *env="native";
#endif
    if(rc) {
#ifndef ENCLAVE
        if(rc==-3) fprintf(stderr,"MADV_COLLAPSE failed: %s; no measurements started\n",strerror(errno));
        else
#endif
        fprintf(stderr,"Memory initialization failed: %d\n",rc);
        return 1;
    }
    char host[256]={0}; gethostname(host,sizeof(host)-1);
    fprintf(stderr,"method=%s build=%s run=%s host=%s cpu=%"PRIu64" footprint=%zu span=%zu pages=%s\n",
            ROB_METHOD,ROB_BUILD_ID,run_id,host,cpu,footprint,footprint*(stride/64),policy);
#ifndef ENCLAVE
    fprintf(stderr,"native data mapping: %p..%p; verify THP/NUMA in snapshots\n",
            memory_base(),(unsigned char *)memory_base()+memory_span());
    if(pages==ROB_PAGES_COLLAPSE) verify_full_thp("before");
#endif
    fprintf(stderr,"warmup: full data traversal at N=0 and 64 selected-kernel iterations per condition; continuous cursors\n");
    snapshot(metadata,"before");
    struct condition { unsigned n,dep; } conditions[514];
    unsigned count=0;
    for(unsigned n=lo;n<=hi;n+=step) for(unsigned dep=0;dep<2;++dep) conditions[count++]=(struct condition){n,dep};
    uint64_t shuffle_state=order_seed;
    for(unsigned i=count-1;i>0;--i) {
        unsigned j=random_next(&shuffle_state)%(i+1);
        struct condition t=conditions[i]; conditions[i]=conditions[j]; conditions[j]=t;
    }
    puts("experiment,method,run_id,build_id,machine_id,environment,cpu_id,nops_per_gap,dependent,footprint_bytes,span_bytes,node_stride,seed,order_seed,nop_bytes,loop_alignment,page_policy,iterations,sample_id,collection_order,condition_order,cycle_position,timer_unit,elapsed_ticks,tsc_aux_start,tsc_aux_end,status,minor_faults,major_faults,voluntary_cs,involuntary_cs,checksum");
    uint64_t positions[2]={0,0},sequence=0,nodes=footprint/128;
    volatile uint64_t sink=0;
    for(unsigned k=0;k<count;++k) {
        unsigned n=conditions[k].n,dep=conditions[k].dep;
        sink^=invoke(0,dep,nodes,width,alignment);
        sink^=invoke(n,dep,64,width,alignment);
        positions[dep]=(positions[dep]+64)%nodes;
        for(uint64_t s=0;s<samples;++s) {
            struct rusage before,after;
            if(getrusage(RUSAGE_THREAD,&before)) { perror("getrusage"); return 1; }
            unsigned a,b; _mm_lfence(); uint64_t start=__rdtscp(&a); _mm_lfence();
            uint64_t v=invoke(n,dep,iters,width,alignment);
            _mm_lfence(); uint64_t end=__rdtscp(&b); _mm_lfence();
            if(getrusage(RUSAGE_THREAD,&after)) { perror("getrusage"); return 1; }
            sink^=v;
            printf("rob,%s,%s,%s,%s,%s,%"PRIu64",%u,%u,%zu,%zu,%"PRIu64",%"PRIu64",%"PRIu64",%"PRIu64",%"PRIu64",%s,%"PRIu64",%"PRIu64",%"PRIu64",%u,%"PRIu64",tsc_ticks,%"PRIu64",%u,%u,%s,%ld,%ld,%ld,%ld,%"PRIu64"\n",
                   ROB_METHOD,run_id,ROB_BUILD_ID,host,env,cpu,n,dep,footprint,footprint*(stride/64),stride,seed,order_seed,width,alignment,policy,iters,s,sequence++,k,positions[dep],end-start,a,b,a==b?"ok":"migration",
                   after.ru_minflt-before.ru_minflt,after.ru_majflt-before.ru_majflt,
                   after.ru_nvcsw-before.ru_nvcsw,after.ru_nivcsw-before.ru_nivcsw,v);
            positions[dep]=(positions[dep]+iters%nodes)%nodes;
        }
    }
    snapshot(metadata,"after");
#ifndef ENCLAVE
    if(pages==ROB_PAGES_COLLAPSE) verify_full_thp("after");
#endif
#ifdef ENCLAVE
    check("rob_free",rob_free(eid)); check("sgx_destroy_enclave",sgx_destroy_enclave(eid));
#else
    release_memory();
#endif
    (void)sink; return 0;
}
