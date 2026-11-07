#define _GNU_SOURCE
#include "bench.h"
#include "pmu.h"
#include "build_id.h"
#include <errno.h>
#include <getopt.h>
#include <inttypes.h>
#include <limits.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <x86intrin.h>
#ifdef ENCLAVE
#include "sgx_urts.h"
#include "enclave_u.h"
static sgx_enclave_id_t eid;
static void check(const char *op,sgx_status_t rc) {
    if(rc!=SGX_SUCCESS) { fprintf(stderr,"%s failed: SGX status 0x%x; check device permission, PSW runtime, signed path and EPC\n",op,rc);exit(1); }
}
#endif
static uint64_t number(const char *s) {
    char *end;errno=0;unsigned long long n=strtoull(s,&end,10);
    if(errno || !*s || *end || strspn(s,"0123456789")!=strlen(s)) { fprintf(stderr,"Invalid number: %s\n",s);exit(2); }return n;
}
static uint64_t next(uint64_t *s) { *s^=*s<<13;*s^=*s>>7;*s^=*s<<17;return *s; }
static uint64_t invoke(unsigned mode,unsigned param,uint64_t iters) {
#ifdef ENCLAVE
    uint64_t value;check("suite_run",suite_run(eid,&value,mode,param,iters));return value;
#else
    return tb_run(mode,param,iters);
#endif
}
static uint64_t result(unsigned i) {
#ifdef ENCLAVE
    uint64_t value;check("suite_result",suite_result(eid,&value,i));return value;
#else
    return tb_result(i);
#endif
}
static void warm(unsigned mode,unsigned param) {
    int rc;
#ifdef ENCLAVE
    check("suite_warm",suite_warm(eid,&rc,mode,param));
#else
    rc=tb_warm(mode,param);
#endif
    if(rc) { fprintf(stderr,"Warm-up failed\n");exit(1); }
}
static void snapshot(const char *prefix,const char *phase) {
    if(!prefix)return;
    const char *names[]={"smaps","numa_maps","status"};
    for(int i=0;i<3;++i) {
        char dst[PATH_MAX],src[80],buf[8192];
        if(snprintf(dst,sizeof(dst),"%s.%s.%s",prefix,phase,names[i])>=(int)sizeof(dst))exit(2);
        snprintf(src,sizeof(src),"/proc/self/%s",names[i]);FILE *in=fopen(src,"r"),*out=fopen(dst,"wx");
        if(!in || !out) { perror("snapshot");exit(1); }
        size_t n;while((n=fread(buf,1,sizeof(buf),in))) if(fwrite(buf,1,n,out)!=n)exit(1);
        if(ferror(in) || fclose(out))exit(1);
        fclose(in);
    }
#ifndef ENCLAVE
    if(tb_span()) {
        char dst[PATH_MAX];
        if(snprintf(dst,sizeof(dst),"%s.%s.page_nodes.csv",prefix,phase)>=(int)sizeof(dst))exit(2);
        FILE *out=fopen(dst,"wx");if(!out) { perror("page-node snapshot");exit(1); }
        fputs("first_page,page_count,node_or_error\n",out);
        size_t count=(tb_span()+4095)/4096,start=0,run=0;int previous=-1000000,invalid=0;
        for(size_t first=0;first<count;first+=256) {
            void *pages[256];int status[256];size_t batch=count-first<256?count-first:256;
            for(size_t i=0;i<batch;++i) { pages[i]=(unsigned char *)tb_base()+(first+i)*4096;status[i]=-1000000; }
            /* nodes=NULL queries residency; it never requests page migration. */
            if(syscall(SYS_move_pages,0,batch,pages,NULL,status,0)<0) { perror("read-only page-node query");fclose(out);exit(1); }
            for(size_t i=0;i<batch;++i) {
                if(status[i]<0)invalid=1;
                if(run && status[i]!=previous) { fprintf(out,"%zu,%zu,%d\n",start,run,previous);run=0; }
                if(!run) { start=first+i;previous=status[i]; }
                ++run;
            }
        }
        if(run)fprintf(out,"%zu,%zu,%d\n",start,run,previous);
        if(fclose(out))exit(1);
        if(invalid) { fputs("Page-node residency query returned unresolved pages; stopped\n",stderr);exit(1); }
    }
#endif
}
static void usage(void) {
    fputs("Usage: trackb-native|enclave --question 1|2|3|5|8 --cpu C --mode M --param P [--footprint-kib K --iterations N --samples S --seed S --order-seed S --lo L --hi H --step D --metadata PREFIX --run-id ID --pmu auto|required|off]\n",stderr);
}
int main(int argc,char **argv) {
    uint64_t q=0,cpu=UINT64_MAX,mode=0,param=0,kib=16,iters=100000,samples=15,seed=42,order_seed=1;
    uint64_t lo=UINT64_MAX,hi=UINT64_MAX,step=4;const char *metadata=NULL,*run_id="direct",*policy="auto";
    static struct option opts[]={{"question",1,0,'q'},{"cpu",1,0,'c'},{"mode",1,0,'m'},{"param",1,0,'p'},
        {"footprint-kib",1,0,'k'},{"iterations",1,0,'i'},{"samples",1,0,'s'},{"seed",1,0,'r'},
        {"order-seed",1,0,'o'},{"lo",1,0,'l'},{"hi",1,0,'h'},{"step",1,0,'d'},
        {"metadata",1,0,'a'},{"run-id",1,0,'n'},{"pmu",1,0,'u'},{0,0,0,0}};
    int opt;while((opt=getopt_long(argc,argv,"",opts,NULL))!=-1) {
        switch(opt) {
        case 'q':q=number(optarg);break;case 'c':cpu=number(optarg);break;case 'm':mode=number(optarg);break;
        case 'p':param=number(optarg);break;case 'k':kib=number(optarg);break;case 'i':iters=number(optarg);break;
        case 's':samples=number(optarg);break;case 'r':seed=number(optarg);break;case 'o':order_seed=number(optarg);break;
        case 'l':lo=number(optarg);break;case 'h':hi=number(optarg);break;case 'd':step=number(optarg);break;
        case 'a':metadata=optarg;break;case 'n':run_id=optarg;break;case 'u':policy=optarg;break;default:usage();return 2;
        }
    }
    if(optind!=argc || cpu>=CPU_SETSIZE || q>UINT_MAX || mode>UINT_MAX || param>UINT_MAX ||
       !seed || !order_seed || !samples || samples>100000 || iters>1000000000 || kib>262144 ||
       !tb_lookup(q,mode,param) || (q==3 && param>3) ||
       (strcmp(policy,"auto") && strcmp(policy,"required") && strcmp(policy,"off")) ||
       !*run_id || strlen(run_id)>79 || strspn(run_id,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")!=strlen(run_id)) { usage();return 2; }
    int sweeping=lo!=UINT64_MAX || hi!=UINT64_MAX;
    if(sweeping && (q!=5 || lo==UINT64_MAX || hi==UINT64_MAX)) { usage();return 2; }
    if(!sweeping)lo=hi=param;
    if(hi==UINT64_MAX || lo>hi || hi>512 || !step || step>512 || (lo!=hi && q!=5) ||
       (q==5 && (lo%4 || hi%4 || step%4))) { usage();return 2; }
    cpu_set_t set;CPU_ZERO(&set);CPU_SET(cpu,&set);if(sched_setaffinity(0,sizeof(set),&set)) { perror("affinity");return 1; }
    struct tb_config cfg={q,mode,param,kib*1024,seed};int rc;
#ifdef ENCLAVE
    check("sgx_create_enclave",sgx_create_enclave("trackb/build/suite.signed.so",SGX_DEBUG_FLAG,NULL,NULL,&eid,NULL));
    check("suite_init",suite_init(eid,&rc,q,mode,param,cfg.footprint,seed));
    const char *env="sgx-hw-debug",*pages="epc";
#else
    rc=tb_init(&cfg);const char *env="native",*pages="4k";
#endif
    if(rc) { fprintf(stderr,"Initialization failed: %d\n",rc);return 1; }
    size_t actual_span;
    if(q==1)actual_span=0;
    else if(q==8)actual_span=mode?param*4096:((param*64+4095)&~(size_t)4095);
    else actual_span=cfg.footprint;
    uint64_t footprint=q==1?0:q==8?param*64:cfg.footprint,nodes=q==3?footprint:q==8?param:footprint/64;
    char machine[256]={0};gethostname(machine,sizeof(machine)-1);
    fprintf(stderr,"question=Q%"PRIu64" method=%s build=%s host=%s cpu=%"PRIu64" pages=%s span=%zu\n",q,TB_METHOD,TB_BUILD_ID,machine,cpu,pages,actual_span);
#ifndef ENCLAVE
    if(tb_span())fprintf(stderr,"native data mapping: %p..%p\n",tb_base(),(unsigned char *)tb_base()+tb_span());
#else
    if(actual_span)fprintf(stderr,"enclave data mapping: 0x%"PRIx64"..0x%"PRIx64"\n",result(3),result(3)+actual_span);
#endif
    struct tb_pmu pmu;if(pmu_open(&pmu,q,policy))return 1;
    /* Audit the warmed treatment rather than freshly allocated mappings.
       Each condition is warmed again after the snapshot, outside timing. */
    if(metadata && q!=1)warm(mode,param);
    snapshot(metadata,"before");
    unsigned params[129],count=0;
    for(uint64_t p=lo;p<=hi;p+=step) { if(!tb_lookup(q,mode,p) || count>=129)return 2;params[count++]=p; }
    uint64_t rng=order_seed;
    for(unsigned i=count-1;i>0;--i) { unsigned j=next(&rng)%(i+1),t=params[i];params[i]=params[j];params[j]=t; }
    puts("question,method,build_id,run_id,machine_id,environment,cpu_id,mode,param,footprint_bytes,span_bytes,node_count,page_policy,seed,order_seed,iterations,work_per_iteration,work_unit,sample_id,collection_order,condition_order,elapsed_ticks,timer_unit,tsc_aux_start,tsc_aux_end,status,minor_faults,major_faults,voluntary_cs,involuntary_cs,result0,result1,cursor_index,checksum,pmu_status,pmu_scope,pmu_name0,pmu_name1,pmu_name2,pmu0,pmu1,pmu2,pmu_time_enabled,pmu_time_running,pmu_name3,pmu3");
    uint64_t sequence=0;volatile uint64_t sink=0;
    for(unsigned condition=0;condition<count;++condition) {
        unsigned p=params[condition];warm(mode,p);
        for(uint64_t sample=0;sample<samples;++sample) {
            struct rusage before,after;if(getrusage(RUSAGE_THREAD,&before))return 1;
            if(pmu_start(&pmu)) { perror("PMU enable");return 1; }
            unsigned a,b;_mm_lfence();uint64_t start=__rdtscp(&a);_mm_lfence();
            uint64_t value=invoke(mode,p,iters);
            _mm_lfence();uint64_t end=__rdtscp(&b);_mm_lfence();
            if(pmu_stop(&pmu)) { perror("PMU stop/read");return 1; }
            if(getrusage(RUSAGE_THREAD,&after))return 1;
            sink^=value;
            printf("Q%"PRIu64",%s,%s,%s,%s,%s,%"PRIu64",%"PRIu64",%u,%"PRIu64",%zu,%"PRIu64",%s,%"PRIu64",%"PRIu64",%"PRIu64",%d,%s,%"PRIu64",%"PRIu64",%u,%"PRIu64",tsc_ticks,%u,%u,%s,%ld,%ld,%ld,%ld,%"PRIu64",%"PRIu64",%"PRIu64",%"PRIu64",%s,%s,%s,%s,%s,",
                q,TB_METHOD,TB_BUILD_ID,run_id,machine,env,cpu,mode,p,footprint,actual_span,nodes,pages,seed,order_seed,iters,
                q==1?32:q==5?2:1,q==1?"imul":q==3?"branch_decision":"load",sample,sequence++,condition,end-start,a,b,a==b?"ok":"migration",
                after.ru_minflt-before.ru_minflt,after.ru_majflt-before.ru_majflt,after.ru_nvcsw-before.ru_nvcsw,after.ru_nivcsw-before.ru_nivcsw,
                result(0),result(1),result(2),value,pmu.status,
#ifdef ENCLAVE
                "host-user-enclave-coverage-unverified",
#else
                "calling-thread-user-bracket-wider-than-timer",
#endif
                pmu.name[0],pmu.name[1],pmu.name[2]);
            if(pmu.fd[0]>=0)printf("%"PRIu64",%"PRIu64",%"PRIu64",%"PRIu64",%"PRIu64,pmu.value[0],pmu.value[1],pmu.value[2],pmu.enabled,pmu.running);
            else fputs(",,,,",stdout);
            printf(",%s,",pmu.name[3]);
            if(pmu.fd[0]>=0 && pmu.count==4)printf("%"PRIu64,pmu.value[3]);
            putchar('\n');
        }
    }
    snapshot(metadata,"after");pmu_close(&pmu);
#ifdef ENCLAVE
    check("suite_free",suite_free(eid));check("sgx_destroy_enclave",sgx_destroy_enclave(eid));
#else
    tb_free();
#endif
    (void)sink;return 0;
}
