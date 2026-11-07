#ifndef TRACKB_BENCH_H
#define TRACKB_BENCH_H
#include <stddef.h>
#include <stdint.h>
#define TB_METHOD "trackb-v1"
/* Layout is checked against the assembly generator. */
struct tb_state {
    void *a, *b;
    unsigned char *pattern;
    uint64_t mask, index, out0, out1, out2;
};
struct tb_config { uint64_t question, mode, param, footprint, seed; };
typedef uint64_t (*tb_fn)(struct tb_state *,uint64_t);
tb_fn tb_lookup(unsigned question,unsigned mode,unsigned param);
int tb_init(const struct tb_config *config);
uint64_t tb_run(unsigned mode,unsigned param,uint64_t iterations);
int tb_warm(unsigned mode,unsigned param);
void tb_free(void);
void *tb_base(void);
size_t tb_span(void);
uint64_t tb_result(unsigned which);
#endif
