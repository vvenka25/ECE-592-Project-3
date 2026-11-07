#define _GNU_SOURCE
#include "pmu.h"
#include <cpuid.h>
#include <errno.h>
#include <linux/perf_event.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#include <unistd.h>
void pmu_close(struct tb_pmu *p) { for(int i=0;i<4;++i) if(p->fd[i]>=0) { close(p->fd[i]);p->fd[i]=-1; } }
static int failed(struct tb_pmu *p,const char *policy,const char *reason) {
    int saved=errno;pmu_close(p);snprintf(p->status,sizeof(p->status),"unavailable-%s-%d",reason,saved);
    fprintf(stderr,"PMU %s: %s\n",p->status,strerror(saved));return !strcmp(policy,"required")?-1:0;
}
int pmu_open(struct tb_pmu *p,unsigned q,const char *policy) {
    memset(p,0,sizeof(*p));for(int i=0;i<4;++i)p->fd[i]=-1;
    p->name[0]="cycles";p->name[1]="branches";p->name[2]="branch_misses";p->name[3]="";p->count=3;
    if(q==8) { p->name[0]="stlb_hit";p->name[1]="walk4k";p->name[2]="l1d_miss";p->name[3]="cycles";p->count=4; }
    if(!strcmp(policy,"off")) { strcpy(p->status,"off");return 0; }
    uint64_t codes[4]={PERF_COUNT_HW_CPU_CYCLES,PERF_COUNT_HW_BRANCH_INSTRUCTIONS,PERF_COUNT_HW_BRANCH_MISSES,PERF_COUNT_HW_CPU_CYCLES};
    unsigned type=PERF_TYPE_HARDWARE;
    if(q==8) {
        unsigned a,b,c,d;char vendor[13];__cpuid(0,a,b,c,d);
        memcpy(vendor,&b,4);memcpy(vendor+4,&d,4);memcpy(vendor+8,&c,4);vendor[12]=0;
        __cpuid(1,a,b,c,d);unsigned family=(a>>8)&15,model=((a>>4)&15)|((a>>12)&240);
        if(strcmp(vendor,"GenuineIntel") || family!=6 || (model!=94 && model!=78 && model!=143)) {
            errno=ENOTSUP;return failed(p,policy,"unverified-cpu-event-map");
        }
        unsigned event=model==143?0x12:0x08;
        codes[0]=event|(0x20UL<<8);codes[1]=event|(0x02UL<<8);codes[2]=0xd1|(0x08UL<<8);
        p->name[0]="stlb_hit";p->name[1]="walk4k";p->name[2]="l1d_miss";type=PERF_TYPE_RAW;
    }
    for(unsigned i=0;i<p->count;++i) {
        struct perf_event_attr a;memset(&a,0,sizeof(a));a.size=sizeof(a);a.type=i==3?PERF_TYPE_HARDWARE:type;a.config=codes[i];
        a.disabled=1;a.exclude_kernel=1;a.exclude_hv=1;
        a.read_format=PERF_FORMAT_GROUP|PERF_FORMAT_TOTAL_TIME_ENABLED|PERF_FORMAT_TOTAL_TIME_RUNNING;
        p->fd[i]=(int)syscall(SYS_perf_event_open,&a,0,-1,i?p->fd[0]:-1,PERF_FLAG_FD_CLOEXEC);
        if(p->fd[i]<0)return failed(p,policy,"perf_event_open");
    }
    strcpy(p->status,"ok");return 0;
}
int pmu_start(struct tb_pmu *p) {
    if(p->fd[0]<0)return 0;
    return ioctl(p->fd[0],PERF_EVENT_IOC_RESET,PERF_IOC_FLAG_GROUP) || ioctl(p->fd[0],PERF_EVENT_IOC_ENABLE,PERF_IOC_FLAG_GROUP)?-1:0;
}
int pmu_stop(struct tb_pmu *p) {
    if(p->fd[0]<0)return 0;
    if(ioctl(p->fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP))return -1;
    struct { uint64_t nr,enabled,running,values[4]; } r;
    size_t expected=3*sizeof(uint64_t)+p->count*sizeof(uint64_t);
    if(read(p->fd[0],&r,sizeof(r))!=(ssize_t)expected || r.nr!=p->count || !r.running) {
        errno=EIO;return -1;
    }
    memcpy(p->value,r.values,p->count*sizeof(uint64_t));
    p->enabled=r.enabled-p->previous_enabled;p->running=r.running-p->previous_running;
    p->previous_enabled=r.enabled;p->previous_running=r.running;return 0;
}
