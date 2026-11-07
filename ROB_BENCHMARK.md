# ROB experiment, method v2

The Artemisia native/SGX control sequence and fine repeat are complete. The measured overlap-loss transition repeats across N=492–500; see [the consolidated findings](ROB_RESULTS_ARTEMISIA.md). No additional routine Artemisia repeats are proposed for this effective instruction-window result. Exact total ROB attribution and the course's separate second-machine result remain outstanding.

The purpose is to measure a repeatable loss of overlap attributable to the instruction window. A bend in a timing curve is a candidate, not an automatic ROB count. `rob-v2` replaces the original repeated-prefix sampling. Preserve `results/artemisia-run1`: those native/enclave results are exploratory v1 evidence and must remain separate from v2 inference.

## Build and functional checks

Run from the HW3 project root, not `build/`:

```bash
source /opt/intel/sgxsdk/environment
make native enclave
make check
TEST_SGX=1 make check
TEST_THP=1 make check                 # optional: real strict-THP allocation check
```

Native needs GCC, GNU assembler/binutils, make, Python 3. SGX additionally needs Intel's installed SDK, the real PSW runtime, OpenSSL, and permitted hardware SGX. There is no simulation fallback. Prefix make with `CCACHE_DISABLE=1` if a sandbox prevents ccache temporary writes. Debug signing keys stay under `build/`.

The SDK's `lib64/libsgx_urts.so` is a link-time placeholder. No SDK runtime path is embedded in the executable. On Artemisia, `ldd build/rob-enclave` should select `/lib64/libsgx_urts.so.2`. The smoke test prints subprocess diagnostics and the application reports the failing SGX operation/code. A missing SGX device inside the coding sandbox does not negate hardware support in the user's shell.

## Shared kernel and matched control

All variants are assembled at build time and the same `kernels.o` is linked into native and enclave binaries. Each independent iteration is:

```asm
mov (%rdi), %rdi        # next node in A
# N NOP instructions
mov (%rsi), %rsi        # next node in B
# N NOP instructions
dec %rdx
jnz loop
```

Every node has an independent link at byte 0 and a dependent link at byte 8, in the same cache line. Two independent shuffled rings use all nodes in two halves of the arena. A second set of links connects `A[i] -> B[i] -> A[i+1] -> B[i+1] ...` into one ring over exactly the same set of lines. The dependent kernel replaces both loads with `mov 8(%rdi),%rdi`; their addresses are serialized. The independent and dependent variants each visit the entire line set in `footprint_bytes/128` iterations. The shuffles are different for A and B, reproducible from the supplied seed, and identical between native/enclave setup.

The dependent control is matched in full-cycle line footprint and load count, not necessarily cache-hit distribution at every short prefix or physical-memory placement. Its addressing operands/encoding differ from the independent loads. Both use the same NOP count, alignment setting and loop control. Compare trends; do not blindly subtract the curves to obtain a capacity.

The assembly writes ending pointers to a cursor after the loop. Each mode retains its cursor across calls. It does not restart a 12 MiB prefix every sample. `cycle_position` records the starting iteration position modulo a full traversal. Each condition performs an untimed full traversal with N=0, then 64 iterations of the selected kernel to warm its code. A full data traversal brings the previous condition's short prefix out of cache when the footprint sufficiently exceeds cache capacity; **this is not a guarantee that every subsequent load misses LLC**. Short-prefix reuse, prefetching, cache residency, and translation behavior still require controls below.

N sweeps 0..1024 in multiples of four. Each iteration has 2N NOPs, two loads, a decrement and a conditional branch. There are N NOPs between the first two loads; the wraparound gap additionally includes decrement/branch. Fusion and uop mapping must be accounted for in a final inference. The guard, alignment padding, cursor stores, and return are outside the loop but inside the timed call.

## Footprint, spacing and page policy

`footprint_bytes` counts distinct cache lines explicitly visited over a full traversal, at 64 bytes per line. It is not a count of distinct lines in every short sample and does not include prefetched lines. Each independent ring holds half that footprint. `span_bytes = footprint_bytes * stride/64` is the address span. Stride 64 uses every line; stride 128 uses one line per aligned 128-byte region, testing sensitivity to neighboring-line fetches. The 128-byte layout does not prove that all prefetchers are defeated. Doubling the span also changes translation/physical mapping: attribute any difference using the page controls too.

Maximum span is 512 MiB; for stride 128 the maximum footprint is 256 MiB. Shuffle workspaces together add footprint/8 bytes during setup, then are freed. Native uses a separate anonymous mmap after affinity binding. Its default is per-mapping `MADV_NOHUGEPAGE` (`--pages 4k`), without changing global policy. `--pages huge` requests `MADV_HUGEPAGE`; allocation is best effort, not guaranteed. `--pages default` leaves the mapping policy unchanged. Actual THP use must be checked in smaps, especially AnonHugePages and VmFlags; getconf PAGESIZE alone is insufficient. Native `--pages collapse` additionally aligns the span to 2 MiB, populates it, and requests synchronous `MADV_COLLAPSE` (Linux 6.1+). It requires a span divisible by 2 MiB and verifies full AnonHugePages coverage before and after the run. Incomplete allocation, unsupported collapse, or inability to verify the exact mapping fails the run. Collapse/verification and any compaction are outside timing; no global page policy is changed. This boundary verification does not prove that backing never changed during the measured interval.

The enclave allocates its arena through trusted malloc, with protected EPC backing. `--pages` is rejected for enclave runs; CSV records `epc`. The maximum enclave heap remains 768 MiB. Signing currently reports 811,008,000 bytes total required memory (about 773.4 MiB), not free EPC or the actively chased footprint. The platform tool enumerates CPUID EPC sections but cannot measure free EPC. Account for other enclaves, code/heap pages and possible reclamation. Reducing the configured heap requires rebuilding/signing and retaining the new config/hash.

## Run a stage, review it, then advance

`run_rob.py` prints commands by default. With `--execute`, it first runs make for the requested native/enclave targets and verifies that the build is up to date, including signing and host relinking. Build failures stop before creating the results directory or taking measurements. It then creates a **fresh** output directory and executes only the requested stage. It does not run later stages automatically. Case order and spacing/mode order are shuffled reproducibly. Samples within a condition remain consecutive so drift is visible. Every job saves raw CSV, stderr, memory snapshots, preflight before/after, and a manifest with parameters, binary hashes, status and coarse sibling CPU activity. Failed jobs retain their partial evidence and stop the stage. Existing results are never overwritten.

Choose a permitted CPU and inspect its sibling/node first:

```bash
python3 scripts/preflight.py 1
```

CPU 1 is an example, not a reserved core. On the supplied Artemisia topology it is local to node 0 and has sibling CPU 57. CPU 68 is offline. Avoid CPU 0 where practical, verify current allowed CPUs, and arrange an idle sibling through the course machine's normal allocation mechanism. `--sibling-state reserved-idle` records your assertion; it does not reserve a core. Otherwise leave the truthful default `uncontrolled`. Coarse /proc/stat busy ticks can reveal sibling activity, but zero ticks do not prove uninterrupted idleness. No sibling workload, host prefetcher toggle, firmware change or global page policy change is performed by these tools.

The commands below assume CPU 1/node 0 are permitted and available. `numactl --membind=0` is requested explicitly. If that policy is denied, preserve the error and investigate permission/placement; omitting the option changes the control and must be recorded. CPU affinity and first touch alone do not override an existing memory policy. NUMA binding of the process also does not prove EPC placement. Use native mapping addresses from the log to find the relevant smaps/numa_maps records; enclave EPC placement may remain less observable.

| Stage | Changed variable | Evidence to inspect before advancing |
| --- | --- | --- |
| smoke | Tiny workload, both modes | Functional execution, CSV and snapshots; not blocker validation. |
| calibration | 16 KiB, 1 MiB, 64/128/256 MiB at N=0 | Stable samples across collection order; large-footprint delay distinct from cache-resident delay; independent-load overlap. A plateau across two large footprints is useful evidence, not proof of DRAM service. |
| prefetch | Three shuffle seeds, then stride 128 | Does a candidate feature survive seeds/layout? Span and TLB effects must be considered alongside prefetching. |
| translation | Native 4K policy versus synchronous collapse, plus enclave baseline | Full native THP backing is required at both snapshots; inspect whether a feature shifts with translation conditions. No native/enclave huge-page equivalence is claimed. |
| frontend | Small and large footprints, NOP widths 1/2, loop offsets 0/16/32 | Separate an instruction-delivery feature from a capacity feature. A feature that follows bytes/alignment or appears with fast loads needs investigation. |
| overhead | 0, 1,000, 10,000, 100,000 iterations at 16 KiB | Bound host call/ECALL overhead and batch-length dependence; zero-work rows remain raw but are not normalized per load. |
| coarse | N=0..1024, step 16 | Candidate overlap loss after earlier controls pass, with a sufficiently slow blocker. |
| fine | User-selected interval, step 4 | Repeat with different order seeds and fresh processes; report an uncertainty interval with accounting, not just one spacing. |

Start with the smoke test and the N=0 calibration; the other stages can take minutes:

```bash
python3 scripts/run_rob.py --stage smoke --cpu 1 --numa-node 0 --environment both --out results/v2-smoke --execute
python3 scripts/run_rob.py --stage calibration --cpu 1 --numa-node 0 --environment both --out results/v2-calibration --execute
python3 scripts/plot_rob.py results/v2-calibration/*-native.csv results/v2-calibration/*-enclave.csv --samples-at 0 --output results/v2-calibration/sample-order.png
```

Inspect the sample-order plot before deciding that the blocker is stable. All stages retain outliers and context-switch/fault diagnostics. Do not simply discard the slow initial samples after seeing the answer you prefer. A reproducible settling trend requires a revised warm-up or workload, while isolated disturbance needs a stated reporting rule.

After accepting calibration, prepare each control separately (append `--execute` when ready):

```bash
python3 scripts/run_rob.py --stage prefetch --cpu 1 --numa-node 0 --environment both --out results/v2-prefetch
python3 scripts/run_rob.py --stage translation --cpu 1 --numa-node 0 --environment both --out results/v2-translation-strict
python3 scripts/run_rob.py --stage frontend --cpu 1 --numa-node 0 --environment both --out results/v2-frontend
python3 scripts/run_rob.py --stage overhead --cpu 1 --numa-node 0 --environment both --out results/v2-overhead
python3 scripts/run_rob.py --stage coarse --cpu 1 --numa-node 0 --environment both --out results/v2-coarse
```

If full collapse fails under local NUMA binding, record the failure; do not substitute a smaller footprint without revalidating the blocker. On Artemisia, full node-0 collapse failed at 64/128/256 MiB while a fully verified 256 MiB allocation on node 1 worked. A native pair with both page policies on node 1 has now been collected as a remote control, separate from local/enclave baselines; the frontend controls on node 0 are now complete and preserve the coarse transition; the overhead stage is also complete (240 samples), and both fine sweeps are complete and the Artemisia evidence is consolidated in `ROB_RESULTS_ARTEMISIA.md`; no additional routine repeats are proposed. The translation stage now defaults to verified collapse; `--huge-policy advice` reproduces the earlier best-effort allocation. The first advice-only campaign achieved just 6/256 MiB THP and is inconclusive as a full page-size control; see `results/v2-translation/review/REVIEW.md`. Keep it as recorded and use a fresh strict-run directory. The control sweeps use step 32, the coarse sweep step 16. Use `--lo`/`--hi` to restrict a control sweep after the initial full range. `--footprint-mib` selects the large footprint; use the smallest sufficiently slow, stable footprint supported by calibration, and retain confirmation at another large footprint. The defaults do not assert that 256 MiB is suitable. Small calibration footprints should remain clearly labeled controls.

For a fine run, supply an interval from the accepted coarse observations, e.g. `--stage fine --lo 448 --hi 576` **only if your measurements justify that interval**. Repeat a stage using `--order-seed 2` and a fresh result directory to test drift/order dependence. Repeating seed/layout controls around a candidate is necessary; do not treat a single randomized sweep as independent replication. Repeat native work on Charnwood too.

## Other structures, SMT, frequency and interrupts

NOP filler avoids generating a destination-register allocation stream or a large stream of memory requests. Two pointer chains limit demand memory-level parallelism, and node links are aligned 8-byte loads inside one line. These choices reduce competing PRF/scheduler/load-buffer/miss-buffer demands; they do not experimentally prove that all competing resources are irrelevant. The tight loop has no stores, so do not automatically invoke a load-after-store alias explanation. The two cursor stores occur at the end of the call.

A useful blocker must remain unresolved long enough for allocation to fill the candidate window. If load latency becomes too short, instruction throughput can hide the ROB transition. Neither total address span nor the fact that a pointer order is random establishes the required delay.

Preflight records frequency snapshots/governor and sibling topology. It does not hold frequency fixed or prove that the sibling stayed idle. CSV includes before/after getrusage deltas for minor/major faults and voluntary/involuntary context switches; those brackets are slightly wider than the timer. Interrupts/AEX can remain unobserved with zero context-switch deltas. TSC_AUX equality only checks the two boundary observations, not absence of all disturbances.

For additional diagnostics where PMU access is permitted, inspect `perf list` for the actual processor before selecting events. Optional `--perf-events 'cycles:u,ref-cycles:u,instructions:u'` wraps each job in `perf stat` and saves a separate .perf.csv. **These counts cover initialization and warm-up as well as samples**, so they cannot be normalized using only timed loads. They are supporting diagnostics, not region-specific proof. Use a separate diagnostic run at one N with long batches, and compare with/without counters to assess perturbation. Permission/unsupported-event errors stop and remain recorded; counters are never silently fabricated or treated as zero.

Sapphire Rapids' Intel event list includes `DTLB_LOAD_MISSES.WALK_COMPLETED`, `MEM_LOAD_RETIRED.L3_MISS`, and `IDQ_UOPS_NOT_DELIVERED.CORE` (alias IDQ_BUBBLES.CORE). Kernel perf aliases and counter restrictions vary. Do not borrow a ROB-stall event name from another CPU without verifying it. Enclave counter coverage must be verified separately; a missing/zero count is not evidence of no enclave activity. Avoid large multiplexed event groups and retain enabled/running ratios. If hardware evidence or controls cannot distinguish another resource, report the result as an effective instruction-window limit, not an established total ROB size.

## Direct CLI and timing

The original eight positional arguments remain accepted, with revised v2 semantics:

```text
build/rob-native CPU MiB iterations samples min_n max_n step seed [options]
--kib K                 override MiB, permitting the small cache control (minimum 8 KiB)
--stride 64|128          distance in bytes between nodes
--pages 4k|huge|collapse|default  native only; huge is advice, collapse verifies full backing
--order-seed S          nonzero seed for shuffled (spacing,mode) conditions
--nop-bytes 1|2         90 or 66 90, one instruction per filler item
--alignment 0|16|32     loop offset within a 64-byte aligned region
--metadata PREFIX      save before/after smaps, numa_maps and status; prefix must be unused
--run-id ID             optional short identifier, otherwise timestamp/PID
```

Timing is host `LFENCE; RDTSCP; LFENCE` before/after the invocation. Units are TSC ticks, not active core cycles. The native region includes dispatch, call, cursor update and return; SGX additionally includes the SDK ECALL/transition path. No enclave timer is used. Setup, snapshots, rusage calls, warm-up and printing are outside the timer. Each nonzero sample executes exactly two loads per iteration. Zero iterations are an overhead control and cannot be divided by a load count.

CSV records method, source build ID, run ID, CPU, footprint/span, stride, both seeds, encoding/alignment, requested page policy, iterations, sample/condition/collection order, cycle position, raw elapsed ticks, AUX, fault/context-switch deltas and a checksum. The build ID hashes source/build inputs, not runtime hardware state. The manifest additionally hashes actual binaries and records machine metadata. Source changes require rebuilding.

`plot_rob.py` groups by method, build, run and all control parameters so it does not silently pool v1/v2, different seeds or page policies. It skips migration rows and zero-work rows, otherwise retains samples. Default curves show medians with observed p10–p90 shading; `--band range` shows min/max. Neither band is a confidence interval. A .summary.csv retains min/max, p10/p90, early/late medians and their change. `--samples-at N` plots individual observations at one N in collection order. Derived .summary.csv files are ignored if included by a file glob.

## Validation and sources

Implementation validation: native and SGX builds compile and sign; tests check 3,084 kernel bodies, loop alignment, identical linked native/enclave bytes, explicit pointer traversal, equal full-cycle line sets, cursor continuation, native 4K mapping, CSV and metadata. A small native campaign and plots were exercised under /tmp. The user subsequently completed all ten v2 calibration jobs on Artemisia, including five hardware-debug enclave runs. Review of the 300 samples is saved in `results/v2-calibration/review/REVIEW.md`, with a reproducible analyzer in `analysis/review_calibration.py`. The coding sandbox still exposes no SGX device. A second order-shuffled calibration is also complete, giving 600 samples across two campaigns with matching binaries. The 256 MiB repeat is stable enough to proceed to layout controls; see `results/v2-calibration-repeat/review/REVIEW.md` and `analysis/compare_calibrations.py`. The eight pointer-seed/layout jobs are now complete (7,920 samples), with the same largest independent timing step between the tested N=480 and N=512 points in every case. See `results/v2-prefetch/review/REVIEW.md` and `analysis/review_sweep.py`. The first native page-advice control completed (2,970 samples), but only 6/256 MiB had THP backing. It is inconclusive for a full page-size comparison. A synchronous-collapse/verification repair is implemented and tested. The local strict campaign then completed its enclave baseline but failed native full collapse under node-0 binding. Feasibility probes and a separately collected native page-policy pair on memory node 1 resolved a usable remote-NUMA control; all 256 MiB of THP versus zero THP were verified, and both cases preserve the coarse transition. See `results/v2-thp-feasibility/REVIEW.md`, `results/v2-translation-strict/review/REVIEW.md`, and `results/v2-translation-node1/review/REVIEW.md`. The user also completed all 16 instruction-width/alignment jobs on the original local 4K-policy configuration (15,840 samples). All eight large-footprint variants preserve the sampled 480–512 transition in all-sample medians, minima, and unflagged-sample diagnostic medians, while the small-footprint controls show no comparable step. See `results/v2-frontend/review/REVIEW.md` and the separate footprint plots; recorded faults, context switches and elevated/isolated timings remain retained. The user completed all eight host call/ECALL overhead jobs (240 samples, no recorded migrations, faults or context switches). The SGX zero-work median is about 10,760 total TSC ticks, a scale of about 0.054 ticks/load at the retained 100,000-iteration batch length. Primary timings remain uncorrected. See `results/v2-overhead/review/REVIEW.md` and `analysis/review_overhead.py`; zero-work samples are never normalized per load. The first fine sweep over N=448..576 in steps of four is complete (1,980 samples): both environments show a partial rise at N=496 and near-convergence of independent/dependent timing at N=500, with the largest adjacent increase at 496→500 under all three summary diagnostics. The observed overall transition spans 492–500; SGX has substantial additional variability. See `results/v2-fine/review/REVIEW.md`. The matched order-seed-2 repeat is now complete (another 1,980 samples), preserving the observed 492–500 transition region in both environments. Its SGX curve also contains a larger isolated median spike at N=548, so the global largest-jump diagnostic is not a reliable capacity estimator. See `results/v2-fine-repeat/review/REVIEW.md`, the separate-campaign comparison from `analysis/compare_sweeps.py`, and `ROB_RESULTS_ARTEMISIA.md`. The Artemisia sequence is complete for an effective instruction-window claim; no exact total ROB-entry count is inferred. Physical EPC placement and local full-THP availability remain limitations. Sibling activity and other attribution limits remain. Calibration and layout-control measurements now exist; no ROB capacity estimate is claimed.

Method references: [Wong's original instruction-window experiments](https://blog.stuffedcow.net/2013/05/measuring-rob-capacity/), [Intel Sapphire Rapids prefetch guidance](https://www.intel.com/content/www/us/en/support/articles/000101878/processors/intel-xeon-processors.html), [Linux THP controls and observation](https://docs.kernel.org/admin-guide/mm/transhuge.html), [Linux SGX EPC/reclamation documentation](https://docs.kernel.org/arch/x86/sgx.html), and [Intel's Sapphire Rapids event definitions](https://github.com/intel/perfmon/blob/main/SPR/events/sapphirerapids_core.json). Additional allocation reference: [Linux madvise](https://man7.org/linux/man-pages/man2/madvise.2.html). These explain controls and interpretations; they are not substitutes for the course-machine measurements. Prefetch behavior remains an experimental control, not a separate cache/prefetcher reverse-engineering submission.
