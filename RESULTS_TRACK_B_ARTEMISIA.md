# New Track B observations on Artemisia

Selected exercises are **Q1, Q2, Q3, Q4, Q5, Q8 — 105 points**. This document
records actual new-question measurements, separately from the completed Q4
analysis in [ROB_RESULTS_ARTEMISIA.md](ROB_RESULTS_ARTEMISIA.md). The completed
[two-machine comparison](RESULTS_TRACK_B_COMPARISON.md) is recorded separately.

## Collection and interpretation

The new campaigns use CPU 12 and local NUMA node 0. CPU 68, its SMT sibling,
was offline in each collected before/after topology snapshot. The strict
idle-sibling gate passed. Native memory treatments also passed 4 KiB/local
placement gates; Q1 is register-only. This does not exclude interrupts,
unobserved brief interference, frequency changes or enclave AEX.
The SGX process uses the same requested binding, but host mappings do not
verify physical EPC NUMA placement.

Each condition has two fresh-process repetitions with 15 raw samples per
repetition. The tables show each process median separately. All primary
samples remain included. Units are **host TSC ticks**, not core cycles;
native PMU core-cycle diagnostics are explicitly labeled. The timer includes
dispatch/return and, for the enclave, ECALL/runtime costs. Setup, warming and
PMU control are outside the timer. See [methods](trackb/METHODS.md), the
retained manifests, exact commands, source snapshots and copied binaries.

All five custom benchmarks passed native/hardware-enclave semantic checks.
The separate 92-sample smoke campaign is validation, not measurement evidence.

## Q3: branch prediction

[Campaign](results/q3-artemisia/manifest.json),
[raw summary](results/q3-artemisia/review/summary.csv),
[plot](results/q3-artemisia/review/Q3.pdf).

Each sample processes 1,048,576 decisions over a warmed 64 KiB pattern.

| Treatment | Native ticks/decision, repetitions 1 / 2 | Hardware SGX ticks/decision, repetitions 1 / 2 |
| --- | ---: | ---: |
| Conditional, alternating | 3.3457 / 3.3465 | 3.3767 / 3.3747 |
| Conditional, shuffled seed 42 | 11.3628 / 11.4457 | 11.3539 / 11.3775 |
| Conditional, shuffled seed 271828 | 11.3293 / 11.4062 | 11.3117 / 11.3375 |
| Branchless, alternating | 1.2936 / 1.2938 | 1.3156 / 1.3132 |
| Branchless, shuffled seed 42 | 1.2941 / 1.2941 | 1.3151 / 1.3145 |
| Branchless, shuffled seed 271828 | 1.2938 / 1.2944 | 1.3142 / 1.3135 |

Native shuffled branch misses are 0.469–0.473 per decision; alternating is
about 0.000006–0.000007. Constant-direction native controls take about 3.903
ticks for zero and 2.379 for one; their difference is retained, rather than
assuming taken/fall-through layout has zero cost. The balanced alternating
comparison controls the overall fraction of outcomes. Assembly verifies the
conditional branch and equal-length observable arms.

The large conditional pattern effect, native miss events and stable branchless
controls support successful regular-stream prediction and frequent shuffled
prediction failures. This is not a calibrated misprediction penalty. The
enclave has a similar timing contrast, but its branch counts are only about
0.0003/decision versus about 3 natively: they do not cover the enclave kernel.
Zero ordinary faults and 27 samples with context-switch deltas are retained
among the 480 raw observations.

## Q1: pipelining

[Campaign](results/q1-artemisia/manifest.json),
[raw summary](results/q1-artemisia/review/summary.csv),
[plot](results/q1-artemisia/review/Q1.pdf).

Each nonzero sample performs 100,000 iterations of exactly 32 integer IMULs.

| Chains | Native ticks/IMUL, repetitions 1 / 2 | Native core cycles/IMUL, repetitions 1 / 2 | Hardware SGX ticks/IMUL, repetitions 1 / 2 |
| --- | ---: | ---: | ---: |
| 1 | 2.2314 / 2.2308 | 3.0005 / 3.0005 | 2.2435 / 2.2456 |
| 2 | 1.1156 / 1.1155 | 1.5003 / 1.5003 | 1.1249 / 1.1251 |
| 4 | 0.7440 / 0.7435 | 1.0002 / 1.0002 | 0.7500 / 0.7502 |

Native dependency latency is about three core cycles/IMUL; enough independent
chains permit about one core cycle/IMUL, with fixed work and a ratio near
three. Zero-work median invocation controls are 64 native and 11,046 SGX ticks
in both repetitions. The plotted per-IMUL measurements are not overhead
subtracted. All 240 raw observations remain, including those controls;
zero ordinary faults and 13 samples with context-switch deltas were recorded.

Independent-work speedup alone cannot exclude multiple execution units.
The separately linked LLVM resource models in METHODS.md assign this IMUL
form to one eligible port-1 resource on both target CPUs. The measured
latency/initiation-interval gap together with that model supports pipelined
multiplication. The model is not a measured unit count, and timing cannot
exclude arbitrary undocumented replication or measure whole-CPU pipeline
depth. Enclave PMU coverage is not assumed from native diagnostics.

## Q2: out-of-order execution

[Accepted campaign](results/q2-artemisia-retry/manifest.json),
[raw summary](results/q2-artemisia-retry/review/summary.csv),
[plot](results/q2-artemisia-retry/review/Q2.pdf).

Each sample has 100,000 blocks. Cold means a full randomized 256 MiB ring;
hot means 16 KiB. The older multiply is blocked behind the pointer load,
before the younger multiply chain in program order. All blocks end with
LFENCE, preventing overlap with the next block's load.

| Treatment | Native ticks/block, repetitions 1 / 2 | Hardware SGX ticks/block, repetitions 1 / 2 |
| --- | ---: | ---: |
| Cold independent, K=0 | 287.97 / 287.11 | 361.41 / 372.15 |
| Cold independent, K=64 | 292.72 / 295.18 | 387.02 / 369.17 |
| Cold dependency-serialized, K=64 | 432.31 / 430.24 | 542.05 / 522.43 |
| Cold fence-serialized, K=64 | 439.04 / 440.26 | 584.86 / 545.50 |
| Hot independent, K=64 | 153.91 / 153.85 | 154.93 / 154.87 |
| Hot dependency-serialized, K=64 | 158.44 / 158.58 | 159.52 / 159.50 |
| Hot fence-serialized, K=64 | 167.31 / 167.33 | 168.15 / 168.00 |

Native independent cold K=64 adds about 5–8 ticks to K=0; forcing the younger
chain to depend on the older blocked multiply adds about 135–140 ticks
relative to independent K=64. Extra cold K=0 fence costs are about 9–11 ticks,
much smaller than the K=64 contrast. The enclave also shows an overlap
advantage, with more cold timing variation. Given the assembly ordering and
block-isolation controls, this supports younger ready arithmetic executing
ahead of an older blocked arithmetic instruction, rather than merely
independent-stream throughput. It is not exact instruction tracing or an
exact additive latency model.

The accepted collection retains 540 observations, zero ordinary faults and
71 samples with context-switch deltas. The preceding partial campaign failed
its declared NUMA gate and remains intact with
[collection notes](results/q2-artemisia/COLLECTION_NOTES.md). The rejected
early pilot without the common end fence is also preserved separately.

## Q5: integer destination-allocation pressure

[Complete coarse campaign](results/q5-scaled-residency-artemisia/manifest.json)
has 9,900 raw observations over N=0..512 in steps of 16. Its own transition
motivated the [fine campaign](results/q5-fine-artemisia/manifest.json), with
3,300 observations over N=192..232 in steps of four. Both use 10,000
iterations/sample, two load-to-load gaps, and one/four/eight-chain scaled
LEA, length-matched NOP, and serialized-load controls. The native page query
accounted for all 65,536 pages on node 0 before and after every job. See the
[coarse plot](results/q5-scaled-residency-artemisia/review/Q5.pdf) and
[fine plot](results/q5-fine-artemisia/review/Q5.pdf).

Fine native medians in TSC ticks/load, repetitions 1 / 2:

| N writes per gap | Four chains | Eight chains | NOP window | Serialized LEA |
| ---: | ---: | ---: | ---: | ---: |
| 200 | 168.5 / 171.0 | 164.4 / 163.5 | 142.7 / 143.0 | 276.4 / 276.8 |
| 204 | 183.2 / 185.9 | 167.5 / 168.2 | 142.7 / 142.7 | 277.4 / 276.8 |
| 208 | 254.5 / 261.8 | 184.2 / 186.0 | 142.9 / 142.2 | 286.0 / 283.7 |
| 212 | 273.4 / 276.3 | 278.6 / 272.7 | 142.0 / 142.5 | 286.8 / 287.4 |
| 216 | 290.3 / 290.6 | 292.2 / 290.0 | 143.3 / 142.4 | 292.6 / 289.5 |

Both multi-chain treatments lose overlap across roughly **N=200–216** and
converge near the serialized-load control at N=216. NOPs remain near 142–143
ticks here and lose overlap much later, around the coarse N=496–512 samples.
This separates integer-destination pressure from the NOP instruction-window
limit. The onset differs between four and eight chains, and the one-chain
curve is execution-limited earlier: dependency/scheduler effects still matter.

The register class is **64-bit integer GPR**. The defensible measurement is an
effective destination-pressure window of about 200–216 attempted writes per
gap under this protocol. If the bottleneck is ordinary register allocation,
this brackets an operational speculative-allocation budget; it does **not**
directly measure the total PRF. Precise PRF-versus-scheduler attribution and
the committed/live/other-in-flight occupancy correction remain unresolved.
Neither 2N nor N+16 is asserted as total PRF size. Published capacities are
not substituted for that missing conversion.

Hardware SGX shows the same broad early transition: four-chain N=200 is
203.2 / 203.0 ticks/load and N=216 is 359.0 / 362.7; eight-chain N=200 is
198.0 / 209.8 and N=212 is 343.7 / 332.6. Its data are noisier, and the
N=216 eight-chain first repetition has a retained 402.7-tick median. The
coarse campaign records 22 observations with ordinary faults and 288 with
context-switch deltas; the fine campaign records zero ordinary faults and
77 with context-switch deltas. All remain in the primary summaries.

The earlier constant-offset LEA experiment and stopped accounting attempts
remain diagnostics, not final capacity evidence; see their interpretation
and collection notes. Charnwood now has its own measured interval; exact
total PRF inference remains unresolved.

## Q8: additional L1-DTLB miss cost when served by the STLB

[Final four-counter campaign](results/q8-clock-artemisia/manifest.json),
[raw summary](results/q8-clock-artemisia/review/summary.csv),
[qualified contrasts](results/q8-clock-artemisia/review/contrasts.csv),
[cost plot](results/q8-clock-artemisia/review/Q8-cost-core-cycles.pdf).

Each sample has 100,000 dependent loads. These are **additional** costs
relative to a compact translation-resident ring with the same cache lines.
The final estimate uses simultaneous active core cycles, with miss/cache
qualification and normalization by additional STLB services. Each cell gives
repetitions 1 / 2:

| Nodes/cache lines | Additional core cycles/STLB service | Additional TSC ticks/service, clock proxy qualified |
| ---: | ---: | ---: |
| 128 | 7.00157 / 7.00148 | 5.19761 / 5.19847 |
| 256 | 7.00068 / 7.00235 | 5.19737 / 5.21227 |
| 384 | 7.00241 / 7.00205 | 5.21781 / 5.19779 |

All native event/cache criteria pass, supporting **about 7.00 additional
active core cycles per L1 data-TLB miss served by the STLB**. The effective
cycle/TSC proxies also pass the declared 2% stability/matching check here,
yielding about 5.20 additional TSC ticks/service. The wider PMU bracket and
event semantics limit precision. This is not page-walk cost, full load
latency, or TLB hierarchy reconstruction. Charnwood's final corresponding
estimate is about 9.00 core cycles; most of its TSC costs are withheld for
clock/preemption mismatch rather than treating a shifted baseline as latency.

Hardware SGX compact/scattered medians are approximately 3.83–3.85 versus
9.06–9.44 ticks/load, but
its host event counts do not cover the kernel: no independently qualified
enclave STLB-miss cost is claimed. The comparison is a translation-working-set
contrast with that limitation. The collector runs on CPU 0 while the workload
runs on CPU 12. All 360 observations remain; zero ordinary faults and six
observations with context-switch deltas were recorded. Earlier three-counter
measurements remain as diagnostics: they qualify the native miss-class
treatment but do not establish simultaneous clock comparability for a final
TSC-difference estimate.
