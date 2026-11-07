#include "enclave_t.h"
#include "bench.h"
int suite_init(uint64_t q,uint64_t mode,uint64_t p,uint64_t footprint,uint64_t seed) {
    struct tb_config c={q,mode,p,footprint,seed};return tb_init(&c);
}
uint64_t suite_run(unsigned mode,unsigned p,uint64_t n) { return tb_run(mode,p,n); }
int suite_warm(unsigned mode,unsigned p) { return tb_warm(mode,p); }
uint64_t suite_result(unsigned which) { return tb_result(which); }
void suite_free(void) { tb_free(); }
