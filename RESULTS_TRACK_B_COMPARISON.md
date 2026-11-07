# Track B comparison — Q1, Q2, Q3, Q4, Q5, Q8 — 105 points

Author: **Varunaditya Venkatesan**. All values below come from retained raw
measurements. Published resource models are supporting interpretation, not
replacement measurements. Each pair gives process repetitions 1 / 2.

Charnwood is the i7-6700/Skylake; Artemisia is the Xeon Gold 5420+/Sapphire
Rapids. New Artemisia work uses CPU 12/node 0, with sibling 68 offline.
Completed Charnwood work uses CPU 1/node 0 and an inherited private Linux
core-scheduling group; its collector is on CPU 0. Kernel/interrupt activity
and other cores' cache/memory traffic remain limitations. Charnwood has none
of `/dev/sgx_enclave`, `/dev/sgx/enclave`, or `/dev/isgx`; hardware-enclave
comparisons therefore use Artemisia. See the retained inventory/session logs.

## Q3 — branch prediction

Native active core cycles/decision:

| Machine | Conditional alternating | Conditional shuffled, seed 42 | Branchless alternating | Branchless shuffled, seed 42 |
| --- | ---: | ---: | ---: | ---: |
| Charnwood | 6.0015 / 6.0026 | 17.6524 / 17.6466 | 2.7628 / 2.7640 | 2.7921 / 2.8002 |
| Artemisia | 4.5009 / 4.5009 | 15.2814 / 15.2738 | 1.7397 / 1.7397 | 1.7397 / 1.7398 |

Both CPUs predict the regular stream well and miss on roughly half of the
shuffled decisions (about 0.496–0.497 on Charnwood, 0.469–0.473 on Artemisia).
The branchless pattern effect is small in core cycles. Assembly retains the
conditional branch and observable, equal-length arms. A pattern contrast is
not a calibrated single-branch misprediction penalty.

Charnwood's raw TSC timings drift: alternating conditional medians are
5.5566 / 7.3413 ticks, and branchless alternating is 2.5604 / 3.9602. Their
core-cycle medians remain stable. This prevents attributing the whole elapsed
timing shift to the pattern or comparing raw TSC duration across hosts.
Artemisia SGX retains the predictable/shuffled timing contrast, but its branch
counters do not cover the protected kernel. [Comparison plot](results/q3-comparison/Q3.pdf).

## Q1 — pipelining

At exactly 32 IMULs/iteration, native core cycles/IMUL are approximately
**3.00, 1.50, 1.00** for one, two and four dependency chains on both CPUs.
This separates dependency latency from initiation interval at fixed work.
The measured ratio is near three; Artemisia SGX has the same chain-count
trend. Zero-work controls and all observations are retained.

Independence alone cannot exclude multiple execution units. The separately
cited LLVM models assign this IMUL form to one eligible port-1 resource.
Together, that resource bound and the measured latency/throughput gap support
pipelined multiplication. The resource model is not an experimentally counted
unit, and the experiment does not measure whole-CPU pipeline depth.
[Comparison plot](results/q1-comparison/Q1.pdf).

## Q2 — out-of-order execution

Native cold K=64 medians, TSC ticks/block:

| Machine | Younger independent | Dependency serialized | Fence serialized |
| --- | ---: | ---: | ---: |
| Charnwood | 359.96 / 360.08 | 599.72 / 599.63 | 598.99 / 602.43 |
| Artemisia | 292.72 / 295.18 | 432.31 / 430.24 | 439.04 / 440.26 |

The older load-dependent IMUL precedes the younger ready IMUL chain in actual
assembly. The matched dependency change and extra-fence control increase
timing, while hot-data controls expose the available arithmetic work. A common
end LFENCE prevents overlap with the next iteration. This supports younger
ready work bypassing an older unready arithmetic instruction, beyond merely
showing independent-stream throughput.

Charnwood's cold K=0 medians are 402.88 / 403.50, exceeding its independent
K=64 timings; the experiment therefore does not assume exact additive
load-plus-compute identities. Frequency, memory-state variation and fence
costs remain qualifications. The inference rests on matched K=64 variants
and verified instruction order. Artemisia's enclave supports the same
direction. The rejected early cross-iteration prototype remains separate.
[Comparison plot](results/q2-comparison/Q2.pdf).

## Q4 — completed work preserved; missing Charnwood comparison added

The user clarified that Charnwood Q4 had not yet been collected. Its new
coarse/fine/order-repeat runs use unchanged preserved code and build ID
`bcd9d621feed36f6`. Artemisia Q4 was neither rerun nor rewritten.

Charnwood's largest fine step is **N=220→224** in both repetitions, including
minimum and unflagged-median diagnostics; independent/dependent timing nearly
converges there. Artemisia's preserved effective transition remains
**N=492–500**. N is NOPs per load-to-load gap, not an asserted total ROB-entry
count. [Charnwood detail](Q4_CHARNWOOD_RESULTS.md),
[two-machine ratio plot](results/q4-comparison/curves.pdf).

## Q5 — 64-bit integer GPR destination pressure

The current filler computes 3*x with scaled-index LEA and no FLAGS destination.
Four/eight-chain variants, a length-matched NOP window and serialized-load
control are retained; one-chain execution limits are diagnostic, not capacity.

The measured multi-chain pressure transition is approximately **N=128–144 on
Charnwood**, versus **N=200–216 on Artemisia**, well before their respective
NOP windows. Charnwood four-chain medians rise from 261.9 / 262.8 ticks/load
at N=128 to 437.5 / 434.0 at N=144; eight chains show the same broad change.
Artemisia multi-chain curves converge near the serialized control at N=216.
The enclave shows the same broad early region with greater noise.

These are effective destination-pressure windows. Under an allocation-limit
model they bracket an operational speculative integer-GPR allocation budget;
precise PRF-versus-scheduler attribution and total physical capacity are not
proved. Neither 2N nor N+16 is a justified total PRF size. Other live mappings,
in-flight destinations, reclamation and reserved capacity require accounting.
The constant-offset LEA diagnostic is preserved separately because its
assumed ordinary allocation/execution behavior failed validation.
[Fine comparison plot](results/q5-comparison/Q5.pdf).

## Q8 — additional L1-DTLB miss cost, STLB served

The final four-counter campaigns measure STLB services, completed 4 KiB walks,
L1D misses and simultaneous active core cycles. Both native CPUs pass the
declared service/cache criteria. Additional active core cycles per added
STLB service, after subtracting the compact baseline:

| Matched nodes/cache lines | Charnwood, repetitions 1 / 2 | Artemisia, repetitions 1 / 2 |
| ---: | ---: | ---: |
| 128 | 9.0014 / 9.0029 | 7.0016 / 7.0015 |
| 256 | 9.0052 / 9.0014 | 7.0007 / 7.0023 |
| 384 | 9.0101 / 9.0043 | 7.0024 / 7.0020 |

Thus the supported native estimate is **about 9 core cycles on Charnwood and
7 on Artemisia** for this miss class. This is additional cost, not total load
latency or page-walk cost. These cycle counts do not establish nanoseconds or
whole-program speed across hosts with different clocks.

Artemisia's paired TSC estimates pass the clock-proxy gate and are about
5.20 ticks/service. Charnwood's TSC estimate is withheld in four of six
comparisons because effective clock/preemption ratios differ or drift; the
core-cycle estimates remain available. Earlier three-counter campaigns and
their shifted compact baseline are retained as diagnostics, not silently
filtered final cost measurements. Enclave timings remain a translation-set
contrast: protected STLB-event coverage is unqualified, so no independently
verified enclave miss penalty is asserted.
[Cost plot](results/q8-clock-comparison/Q8-cost-core-cycles.pdf),
[raw timing plots](results/q8-clock-comparison/Q8.pdf).

## Reproduction and limitations

Use [METHODS.md](trackb/METHODS.md), campaign manifests/source snapshots,
[the current README](README_Track_B.md), and the maintained [AI-use log](AI_USE_LOG.md).
Exact historical builds should be reconstructed from their own snapshots,
not silently pooled with the final suite. Native and enclave ASM bytes match
within each shared build. All raw observations, disturbances, unsuccessful
attempts, plots and analysis scripts remain available. No total PRF number,
exact-total ROB attribution, verified enclave TLB-event coverage, fixed
frequency or host-wide quiescence is invented.
