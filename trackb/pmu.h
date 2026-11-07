#ifndef TB_PMU_H
#define TB_PMU_H
#include <stdint.h>
struct tb_pmu {
    int fd[4];unsigned count;const char *name[4];char status[80];
    uint64_t value[4],enabled,running,previous_enabled,previous_running;
};
int pmu_open(struct tb_pmu *p,unsigned question,const char *policy);
int pmu_start(struct tb_pmu *p);
int pmu_stop(struct tb_pmu *p);
void pmu_close(struct tb_pmu *p);
#endif
