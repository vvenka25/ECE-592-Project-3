Functional native smoke test only: 1 MiB total footprint, 100 iterations,
2 samples, N=0,4,8, both dependency variants. This validates execution and
CSV/plot handling; it does not establish a long-latency blocker or ROB size.
The host identifies as Artemisia, but this execution sandbox exposes no
/dev/sgx_enclave. The custom enclave was built/signed, not hardware-run here.
