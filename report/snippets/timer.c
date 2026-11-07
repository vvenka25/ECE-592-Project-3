unsigned a,b;_mm_lfence();uint64_t start=__rdtscp(&a);_mm_lfence();
uint64_t value=invoke(mode,p,iters);
_mm_lfence();uint64_t end=__rdtscp(&b);_mm_lfence();
