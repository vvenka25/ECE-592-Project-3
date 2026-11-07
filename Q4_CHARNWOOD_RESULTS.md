# Q4 Charnwood comparison using preserved code

The user confirmed that no Charnwood Q4 data existed. This follow-up fills
that submission requirement using the unchanged completed implementation;
Artemisia's source, measurements, figures, analysis and instructions remain
unchanged. All 825 protected files and the original archive hash still verify.

The original source/build ID is **bcd9d621feed36f6**, matching the preserved
implementation. An isolated host-local tree was built and the original
3,084-kernel semantic/NOP checks passed. The new native main's two
LFENCE/RDTSCP/LFENCE boundaries were independently inspected; source and binary
snapshots, disassembly and the check record accompany the fine campaigns.

Measurements use Charnwood's i7-6700, CPU 1/node 0, a randomized 256 MiB
footprint, 100,000 iterations/sample, 15 samples/condition, one-byte NOPs,
64-byte stride and the original independent/serialized full-ring control.
A private inherited core-scheduling group excludes unrelated userspace
co-scheduling. The legacy collector/helper mask is CPUs 0 and 1 and can
preempt the benchmark; kernel/interrupt activity is not excluded. Raw
preemptions remain included. The machine has one NUMA node and native
NOHUGEPAGE backing/snapshots are retained.

- [Coarse N=0..1024, step 16](results/q4-coarse-charnwood/manifest.json): 1,950 observations.
- [Fine N=192..240, step 4](results/q4-fine-charnwood/manifest.json): 390 observations.
- [Order-seed-2 fine repeat](results/q4-fine-repeat-charnwood/manifest.json): 390 observations.

The fine interval comes from this machine's coarse 208→224 change, not from
Artemisia's measured region. Fine medians in host TSC ticks/load:

| N | Independent first / repeat | Serialized first / repeat |
| ---: | ---: | ---: |
| 216 | 282.844 / 284.436 | 389.352 / 389.210 |
| 220 | 323.444 / 325.026 | 395.995 / 397.681 |
| 224 | 398.810 / 398.941 | 409.600 / 398.887 |
| 228 | 399.087 / 400.862 | 410.589 / 400.855 |

Both repetitions have their largest adjacent rise at **220→224**, also under
minimum and unflagged-median diagnostics. The ratios at N=224 are about
0.974 and 1.000. This is a repeatable effective overlap-loss window. It does
not prove that N, 2N, or a guessed overhead-corrected count is total ROB size.
The coarse data record two observations with ordinary faults and 540 with
context-switch deltas; the fine pair has zero ordinary faults and 67/75
context-switch observations. None are deleted from the primary summaries.

Artemisia's preserved effective transition remains **N=492–500**. Its original
CPU/SMT conditions and exact-total-ROB attribution limits remain in
[ROB_RESULTS_ARTEMISIA.md](ROB_RESULTS_ARTEMISIA.md). Cross-host TSC ticks are
not assumed to have equal duration. The [two-machine ratio plot](results/q4-comparison/curves.pdf)
compares within-host independent/serialized medians; it uses Artemisia's
actual full-range baseline from its preserved frontend-control campaign,
not a nonexistent or synthesized coarse run.

For a new reproduction directory on Charnwood, use
`report/reproduce_q4_charnwood.py`; it verifies/extracts original source into
a separate tree and refuses to run on Artemisia. Start with coarse, review
its interval, then fine and an order-seed-2 repeat. The recorded fine bounds
were 192..240. The original Q4 instructions remain preserved verbatim.
