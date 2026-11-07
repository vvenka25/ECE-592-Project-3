#ifndef ROB_COMMON_H
#define ROB_COMMON_H
#include <stdint.h>
#include <stddef.h>
#define ROB_METHOD "rob-v2"
enum { ROB_PAGES_DEFAULT=0, ROB_PAGES_4K=1, ROB_PAGES_HUGE=2, ROB_PAGES_COLLAPSE=3 };
#define ROB_HUGE_SIZE (2UL*1024*1024)
struct rob_cursor { void *a, *b; };
typedef void (*kernel_fn)(void *, void *, uint64_t, struct rob_cursor *);
kernel_fn get_kernel(unsigned n, unsigned dependent, unsigned nop_bytes, unsigned alignment);
int setup_memory(size_t footprint, uint64_t seed, unsigned stride, unsigned pages);
uintptr_t run_kernel(unsigned n, unsigned dependent, uint64_t iterations, unsigned nop_bytes, unsigned alignment);
void release_memory(void);
void *memory_base(void);
size_t memory_span(void);
#endif
