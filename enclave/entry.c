#include "Rob_t.h"
#include "common.h"
int rob_init(size_t bytes,uint64_t seed,unsigned stride) {
    return setup_memory(bytes,seed,stride,ROB_PAGES_DEFAULT);
}
uint64_t rob_run(unsigned n,unsigned dependent,uint64_t iterations,unsigned nop_bytes,unsigned alignment) {
    return run_kernel(n,dependent,iterations,nop_bytes,alignment);
}
void rob_free(void) { release_memory(); }
