# Track B task list — 105 points

> GitHub checkout: first follow [REPRODUCING.md](REPRODUCING.md) and run `python3 data/unpack_results.py` from the project root to restore raw evidence. Public preservation uses the source-only Q4 derivative; the full original archive and submission ZIP remain unchanged locally.

Selected questions: **Q1, Q2, Q3, Q4, Q5, Q8 — 105 points**.
Implementation order: **Q3 → Q1 → Q2 → Q5 → Q8**. Q6 is dropped.

| Question | Points | Project status | Evidence and inference limits |
| --- | ---: | --- | --- |
| Q4 ROB | 30 | **Completed; original work preserved** | User-confirmed missing Charnwood coarse/fine/repeat comparison added using unchanged source; effective window, not exact-total ROB attribution. |
| Q3 Branch prediction | 10 | Both native machines / Artemisia SGX measured | Retained branch, balanced predictable/shuffled patterns, branchless sensitivity, native miss/cycle evidence; Charnwood TSC drift documented. |
| Q1 Pipelining | 10 | Both native machines / Artemisia SGX measured | Fixed-work latency/throughput evidence plus the explicit execution-unit replication qualification. |
| Q2 Out-of-order execution | 10 | Both native machines / Artemisia SGX measured | Older blocked IMUL preceding younger ready work; dependency, fence and hot-data controls; common block boundary. |
| Q5 Integer physical registers | 35 | Effective pressure bounds measured | Class: 64-bit integer GPR; four/eight-chain transition windows about N=128–144 Charnwood / 200–216 Artemisia. Precise PRF attribution and total conversion remain unproved. |
| Q8 TLB-miss cost | 10 | Native cost qualified; SGX timing compared | About 9 / 7 additional active core cycles for STLB-served L1-DTLB misses on Charnwood / Artemisia. Enclave event coverage remains unqualified. |

- [x] Preserve Q4 implementation, raw observations, figures, analysis and instructions.
- [x] Create a pre-revision Q4 archive and SHA-256 inventory under `preserved/`.
- [x] Adopt the revised 105-point selection and requested implementation order.
- [x] Implement and functionally validate Q3, Q1, Q2, Q5 and Q8 in that order; native/SGX build and shared-byte checks pass.
- [x] Run native smoke and short pilot validation; retain the rejected Q2 prototype and corrected block-isolation pilot separately.
- [x] Build a clearly marked draft PDF with the six-question list and 105-point total on its first page.
- [x] Collect repeated native campaigns on Charnwood and Artemisia for every selected exercise.
- [x] Validate all new custom kernels in Artemisia hardware SGX and retain actual same-machine performance comparisons; final revisions pass 1,053 shared-byte/result/timer checks.
- [x] Document CPU/SMT/NUMA placement, units, boundaries, disturbances, private core scheduling, direct native page queries and unresolved limitations.
- [x] Write exercise-specific conclusions from actual evidence, with published resource models separated from measurements.
- [x] Fill the Q4 Charnwood gap after the user confirmed it was still required, without changing or rerunning completed Artemisia work.
- [x] Finish and inspect the 15-page PDF; author, selected list and 105-point total appear on its first page, with no layout warnings.
- [x] Package PDF, source, raw evidence, plots/scripts, reproduction instructions and AI-use log; the clean candidate extraction passes CRC/artifact/evidence/Q4 checks and the source bundle builds and passes native validation.

SMT affinity alone does not reserve a core. Artemisia's new CPU 12 runs have sibling 68 offline; completed Charnwood runs use private inherited core scheduling, which excludes unrelated userspace co-scheduling but permits kernel/interrupt contexts. Topology must be rechecked on reproduction. Total PRF conversion, exact-total ROB attribution, protected TLB-event coverage, physical EPC NUMA placement and host-wide quiescence remain scientific limitations, not fabricated results.
