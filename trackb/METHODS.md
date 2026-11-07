# Remaining Track B experiments

> GitHub checkout: first follow [REPRODUCING.md](../REPRODUCING.md) and run `python3 data/unpack_results.py` from the project root to restore raw evidence. Public preservation uses the source-only Q4 derivative; the full original archive and submission ZIP remain unchanged locally.

Selected scope: **Q1, Q2, Q3, Q4, Q5, Q8 — 105 points**. Q4 is completed and preserved. This suite implements the remaining questions in order Q3 → Q1 → Q2 → Q5 → Q8; Q6 is not implemented as a selected exercise.

## Common protocol and validation

`make -C trackb native enclave` creates separate artifacts under trackb/build without changing Q4's root Makefile, source, scripts or binaries. The current assembly generator emits 1,053 functions in one kernel object, linked into native and enclave builds (the earlier build had 795). `make -C trackb check` checks their bytes and semantics in the requested question order, including the live outputs and address traversal. It inspects the host timer's actual compiled ordering; setup, warm-up, metadata, rusage and PMU ioctl/read operations are outside the host TSC interval. Dispatch, cursor/result updates and return are inside; SGX additionally includes ECALL/runtime transition and marshalling. The same host LFENCE/RDTSCP/LFENCE boundary protocol used by Q4 is retained. TSC ticks are not active core cycles, and the timed region does not claim global store persistence.

The native engine copies/adapts Q4's tested anonymous-mmap/NOHUGEPAGE, deterministic shuffled pointer graph, continuous cursors and full-traversal warm-up design. Trusted allocation uses SGX malloc in the new enclave. CPU affinity is established before allocation. The runner reuses Q4's platform/preflight and mapping-audit helpers, binds native allocation to the selected CPU's current local node, snapshots mappings, records ordinary faults/context switches/AUX and coarse sibling activity, and holds a cooperative per-user core lock. It cannot reserve a lab CPU against other users. `--require-idle-sibling` stops on observed busy ticks, retaining the data. Frequency, short sibling bursts, interrupts and AEX remain incompletely controlled without external reservation/instrumentation.

Current collectors pin themselves and ordinary helpers to one CPU on a different physical core from the benchmark; `controller_affinity` records that CPU. Before/after topology and CPUID checks additionally permit the selected benchmark CPU, as required by the preserved preflight helper, but exclude its SMT sibling after isolation. They run only while the benchmark is not executing. The benchmark explicitly pins itself to its requested CPU before allocation, overriding inherited controller affinity. The initial allowed-CPU inventory precedes controller pinning; later helper `allowed_cpus` fields reflect that helper's narrower affinity, while actual benchmark affinity is checked by its call/CPU records and TSC AUX. Earlier Artemisia campaigns had an offline SMT sibling and retain their observed preemption flags; Charnwood's first attempted Q3 collection stopped on sibling activity before this controller-isolation change and is retained separately. An intermediate isolation attempt stopped at the legacy helper's affinity check before taking samples; the helper mask above corrects that integration issue without modifying Q4 code.

On Charnwood, low but nonzero user/nice activity persisted in the coarse sibling snapshots, so zero observed ticks could not serve as a practical reservation. `--core-scheduling private` requires a new nonzero Linux core-scheduling cookie for the collector's task group; benchmark children inherit it across fork/exec. Together with controller isolation, this excludes unrelated userspace tasks from simultaneous SMT execution with the benchmark. The cookie/policy and raw sibling ticks are recorded. No sibling CPU is offlined and no system-wide configuration file is changed. [Linux core-scheduling documentation](https://docs.kernel.org/admin-guide/hw-vuln/core-scheduling.html) describes both inheritance and the limitation that kernel/interrupt contexts may still share a core. This policy is distinct from `--require-idle-sibling`, which still rejects any observed busy tick if explicitly requested. Private-group collections retain raw activity as a disturbance record and do not claim zero interrupt/kernel interference. Unsupported private-cookie setup stops before collection rather than falling back silently.

Each measurement command defaults to two independent process repetitions, 15 raw samples per condition, seed 42, and shuffled job order. Q5 additionally shuffles spacings using a recorded order seed. Samples within a condition are consecutive. All primary samples remain included; unflagged medians are a separate diagnostic and do not prove clean execution. `cursor_index` records the ending cycle position, not the starting position; assembly state persists between calls. Zero iterations are an invocation-cost control and remain total ticks/invocation.

Collection uses Python's standard library; Matplotlib is required only for analysis/plots. `node_count` is the byte-pattern length for Q3, zero for register-only Q1, and the number of distinct pointer nodes for the memory experiments. Current native placement uses a complete per-page [move_pages residency query](https://man7.org/linux/man-pages/man2/move_pages.2.html) with `nodes=NULL`, so it requests **no migration**. Run-length encoded page statuses are retained for both snapshots; every page must be present on the requested node, with no errors or omissions, and VMA size/RSS/no-THP checks must also pass. An unverified treatment stops the campaign. A sub-page pattern is rounded to the mapped page size. Denied query access stops collection rather than claiming verified placement.

For current collections the initial memory warm-up precedes the pre-timing mapping snapshot; the per-condition warm-up then runs after that snapshot, also outside timing. Earlier `numa_maps` snapshots occasionally accounted for a few fewer pages despite full VMA size/RSS, including after warm-up. Those campaigns were stopped and retained, not relabeled as passing. The exact cause is unresolved. The current gate uses direct per-page node statuses to resolve placement, and retains `numa_maps` as ancillary evidence instead of requiring its accounting to serve as a precise page inventory. This still requires exact complete resident/local placement, with no tolerance for an unknown or remote page.

The runner snapshots source and copied binaries plus command/configuration, hashes, current topology, maps and failures in a fresh directory. `review.py` retains machines, environments, source identities, conditions and repetitions separately. PNG/PDF plots use medians with observed p10–p90, not confidence intervals. `--stage smoke` results are explicitly functional-only; they do not satisfy experimental conclusions. Different batch lengths or controls are not pooled.

PMU counting uses calling-thread user events around a slightly wider interval than the timer, excluding setup/warm-up. Groups preserve enabled/running times per sample and are not silently scaled; the analyzer requires >=98% scheduling for its PMU qualification. Auto mode records unsupported/denied counters with blank fields. Required mode fails before timing if the group cannot open. Enclave coverage is unverified even if counts are nonzero; zero counts never establish absence of enclave events. Compare PMU-on and PMU-off timing if instrumentation effects matter. The Linux interface is documented in [perf_event_open](https://man7.org/linux/man-pages/man2/perf_event_open.2.html).

TSC frequency is not calibrated by this suite. Tick duration can differ between hosts; retain per-machine tick units and within-machine ratios, or perform a separately documented frequency calibration before converting to time or comparing durations directly. Native core-cycle counter diagnostics are labeled separately from TSC ticks. CPU MHz snapshots must not be substituted for TSC frequency.

## Q3 — branch prediction, 10 points

One shared assembly branch kernel sequentially reads a power-of-two byte array. Patterns are all zero, all one, alternating, and shuffled balanced 50/50. Two recorded shuffle seeds check access-pattern sensitivity. Pattern generation and full-pattern training are untimed; default 64 KiB patterns are longer than a tiny memorized loop. All patterns use identical addresses and the same array size. The unpredictable designation describes the randomized treatment, not proof that a particular predictor cannot learn it.

```asm
movzbl (pattern,index), %edx
test %edx,%edx
jz zero
add $1,ones
jmp join
zero:
add $1,zeros
jmp join
join:
# increment/wrap index, decrement iteration counter, loop
```

Both arms have one counter addition and one unconditional jump, with equal encoded arm lengths. The conditional decision remains actual assembly; the compiler cannot turn this body into CMOV/setcc or remove it. Observable one/zero counts are checked against exact patterns. An explicit branchless kernel reads the same patterns and accumulates the same counts as a sensitivity control, not as an instruction-for-instruction identical baseline.

Report ticks per branch decision. Compare balanced shuffled vs alternating timing and native branch-miss counters, then inspect the equivalent pattern contrast in the branchless control. The latter helps expose memory-pattern effects. The total branch counter includes loop/unconditional/control branches; the target conditional branch is not the only event source. A timing difference alone is not a calibrated per-misprediction penalty. Hardware SGX execution must be validated independently.

```bash
python3 trackb/run.py --question Q3 --cpu 12 --numa-node 0 --environment both --out results/repro-q3-artemisia --execute
python3 trackb/review.py results/q3-artemisia
```

## Q1 — pipelining, 10 points

Use exactly **32 `imul $3,reg,reg` instructions per iteration**, distributed over one, two or four independent 64-bit integer dependency chains. Fixed total work removes instruction-count changes as the explanation. Inputs are odd integers, arithmetic wraps modulo 2^64, no FP exceptions occur, and all chain results contribute to an observable checksum. Multiplication is written in assembly, so a compiler cannot strength-reduce it to LEA. A zero-work call provides invocation-cost evidence.

One chain gives a dependency-latency-dominated ticks/IMUL estimate; sufficient independent chains approach reciprocal throughput. Report both, plus their ratio and any remaining loop/call/frequency effects. Multiple execution units can also improve independent-work throughput: **independence alone does not prove pipelining**. This instruction was chosen because the [LLVM Skylake client model](https://raw.githubusercontent.com/llvm/llvm-project/main/llvm/lib/Target/X86/X86SchedSkylakeClient.td) and [Sapphire Rapids model](https://raw.githubusercontent.com/llvm/llvm-project/main/llvm/lib/Target/X86/X86SchedSapphireRapids.td) each assign this immediate/register IMUL form to the single port-1 resource. Treat that as a separately cited resource model, not a measured unit count. A measured latency exceeding initiation interval, together with the supported resource bound, is the intended pipeline evidence. Timing alone cannot rule out arbitrary undisclosed replicated hardware, and it does not measure whole-CPU pipeline depth.

```bash
python3 trackb/run.py --question Q1 --cpu 12 --numa-node 0 --environment both --out results/repro-q1-artemisia --execute
```

## Q2 — out-of-order execution, 10 points

An older dependent multiply is deliberately placed immediately after a randomized pointer load. Younger work uses the same integer-multiply instruction class:

```asm
mov (%r8), %r8       # older pointer load
imul $3,%r8,%rax     # older operation blocked on that load
xor %r11,%r9        # ready constant in overlap case
# K times: imul $3,%r9,%r9   (younger independent chain)
xor %rax,%r10       # consume the older result
lfence              # common boundary before the next block's load
```

The serialized control replaces the XOR source with `%rax`, forcing the younger chain to wait for the older result. A third variant inserts LFENCE after the older multiply before the independent work. **All three variants also end every block with LFENCE**, before the next iteration's load. This prevents a nominally serialized chain from overlapping the next block's load, which would otherwise hide the intended comparison in steady-state throughput. Counts, fence positions and live outputs are checked. The large-footprint K=0 controls expose baseline/fence costs; K=64 large-footprint variants test within-block overlap, and 16 KiB variants expose cache-resident behavior. The pointer cycle visits the entire requested footprint and continues between samples, with full-cycle warm-up before timing.

The key inference is that younger work progresses despite an earlier **unready arithmetic instruction**, not merely that two independent streams run faster. In an in-order issue interpretation, that older instruction blocks the younger one. Compare overlap, dependency-serialized and fence-serialized timings, considering the K=0 fence cost and hot-data control. Qualitative max-vs-sum behavior is supporting evidence; it is not an exact additive latency identity. LFENCE changes execution and may have its own cost. Precondition: the large-footprint load must be demonstrably slower than the hot control.

The block boundary uses Intel's documented instruction-ordering behavior of LFENCE; see the [instruction reference](https://www.intel.com/content/dam/www/public/us/en/documents/manuals/64-ia-32-architectures-software-developer-vol-2a-manual.pdf). It isolates execution within a trial without claiming global store persistence. The first native pilot lacked this common boundary and allowed cross-iteration overlap; that Q2 prototype is retained as a diagnostic failure, not positive OOO evidence. A separate corrected pilot validates the final block design.

```bash
python3 trackb/run.py --question Q2 --cpu 12 --numa-node 0 --environment both --out results/repro-q2-artemisia --execute
```

## Q5 — speculative integer GPR allocation, 35 points

Register class: **64-bit integer general-purpose registers**. Extend Q4's two-load/two-gap resource-pressure layout using scaled-index `lea (reg,reg,2),reg` writes, computing 3*x modulo 2^64. Odd inputs remain nonzero. This operation is neither a constant-offset update, plain register move nor zero idiom, and does not write FLAGS. One-, four- and eight-accumulator variants vary execution dependency depth at equal destination-write counts. The NOP baseline uses one four-byte NOP per filler, matching both the LEA filler count and encoded length without ordinary destination allocation; tests verify the matching function lengths. All variants initialize the same eight accumulators and preserve the same callee-saved registers outside the hot loop. A dependent-load LEA control traverses the same full line set. Results include the final eight-accumulator checksum, checked against modular exponentiation.

```asm
mov (A), A
# N writes: lea (%r8,%r8,2),%r8 (or rotate four/eight accumulators)
mov (B), B
# N more writes
dec iterations
jnz loop
```

Use a slow full-footprint blocker, inspect the LEA/NOP curves, compare four/eight-chain behavior, and select a fine interval from the new observations. The one-chain variant is a dependency-cost diagnostic and can become execution-limited before capacity. A transition below the NOP instruction-window limit that survives the four/eight-chain change supports a speculative GPR allocation constraint; scheduler/throughput/translation effects remain alternatives if controls disagree. The analyzer exports matched-N contrasts and adjacent changes, not an automatic PRF count.

The default complete coarse range is N=0..512 in steps of 16, so it covers the surrounding NOP window as well as a possible earlier allocation limit. The optional short pilot stops at 256 in steps of 32 and is not sufficient to estimate capacity. If GPR and NOP limits coincide, report an unresolved coupled bound; do not force a separate PRF size from that curve.

The observed budget concerns physical destinations that cannot yet be reclaimed while retirement is blocked. Converting it into total PRF size requires a justified model for committed architectural mappings, other live in-flight destinations, allocation/reclamation timing, granularity and reserved registers. The conditional accounting is `total = observed speculative allocation budget + other live mappings/occupancy + unavailable/reserved capacity`. Those additions are not measured just by counting N or adding a fixed architectural-register count. If they are unresolved, report the speculative budget/bound and its class rather than inventing total PRF size. Shared kernels do not imply native/enclave mappings occupy identical physical register state at entry.

The first complete Artemisia Q5 sweep (`results/q5-artemisia/`) used the earlier constant-offset `lea 1(reg),reg`. Its one-chain and four-chain curves track the NOP window, and its one-chain cycle count is below the ordinary one-cycle-dependency expectation. Thus nonidentity syntax alone did not validate ordinary destination allocation. Those observations are preserved as a diagnostic, not an isolated PRF estimate. The scaled-index treatment has a different source/build identity and must be validated and collected separately; the datasets must not be pooled. The exact optimization behind the earlier behavior is not established here.

```bash
python3 trackb/run.py --question Q5 --iterations 10000 --cpu 12 --numa-node 0 --environment both --out results/repro-q5-scaled-artemisia --execute
# After reviewing the coarse data, supply its actual bracket:
# python3 trackb/run.py --question Q5 --stage fine --lo L --hi H ...
```

## Q8 — additional L1 data-TLB miss cost, 10 points

Target class: **L1 data-TLB misses resolved by the shared second-level TLB**, rather than a generic mixture of page walks, faults and cache misses. The baseline is a compact translation-resident dependent ring with the same number of data cache lines and randomized traversal order as a scattered ring. Fixed node counts are 128, 256 and 384; they are controls for the requested cost, not a complete hierarchy-capacity sweep.

Compact nodes occupy consecutive 64-byte lines. Scattered node i occupies `i*4096 + (i%64)*64`: one node per 4 KiB page, with line offsets distributed over all 64 L1 sets. **Both native and enclave Q8 arenas are page aligned**; the actual arena base is logged outside timing, and hardware semantic checks validate pointer/cursor geometry in both layouts. This avoids page-sharing artifacts from a merely cache-line-aligned enclave malloc. The paired data footprint is 8/16/24 KiB in both layouts, sized to fit the reported L1 data caches; only the translation footprint expands. Sequential dependent loads prevent memory-level parallelism from hiding the added latency. Native NOHUGEPAGE policy and before/after maps/residency queries are recorded. Full-ring warming populates data/page tables before timing; warm data does not mean warm translations for the oversized translation set.

For native Skylake model 94/78 and Sapphire Rapids model 143, counters are selected from Intel's [Skylake event list](https://raw.githubusercontent.com/intel/perfmon/main/SKL/events/skylake_core.json) and [Sapphire Rapids event list](https://raw.githubusercontent.com/intel/perfmon/main/SPR/events/sapphirerapids_core.json): STLB hits, completed 4 KiB walks and retired L1 data-cache misses. A fourth simultaneous counter records active core cycles (not reference/TSC cycles). Unknown CPU/event maps are rejected for PMU qualification. These events are supporting diagnostics with their published semantics/errata, not perfect instruction-specific tracing. The fourth counter is appended as `pmu_name3,pmu3`; older raw CSVs remain readable and are not rewritten.

The declared miss-class qualification requires native scheduled counter coverage >=98%, additional STLB services/load >0.5, compact STLB services/load <0.05, and both completed walks/load and L1D misses/load <0.01 in both layouts. These are practical acceptance criteria, not universal constants. With the simultaneous cycle counter, the primary estimate is `(scattered core cycles/load - compact core cycles/load) / (scattered STLB services/load - compact STLB services/load)`. It measures **additional active core cycles per added STLB service**, with small wider-bracket host overhead, rather than assuming one miss per access or treating core cycles as TSC ticks.

A TSC-difference estimate uses the analogous ticks/load formula only if the effective core-cycles/TSC-tick medians match within 2%, and each condition's ratio p90/p10 is <=1.02. This is a declared practical clock/preemption stability check on the central 80%, not proof of fixed frequency or a confidence interval. Earlier Charnwood three-counter data had a compact-baseline timing shift despite unchanged miss/cache rates; Q3's simultaneous native cycles also exposed elapsed-time/frequency drift. Legacy Q8 class rates alone therefore do not qualify a final TSC cost. Those rows and earlier analysis scripts remain, while fresh four-counter campaigns provide the controlled cycle-cost estimate. All raw samples remain included, and TSC contrasts whose proxy fails remain descriptive with the cost withheld. Cache/PTE residency, counter semantics and wider brackets still limit precision.

If counters are denied, multiplexed excessively, or indicate page walks/cache misses, preserve the timing difference as a **translation-working-set contrast with inconclusive miss-class attribution**. Do not label it a verified TLB-miss latency. Enclave counters are not qualified by default, and native event coverage cannot prove the enclave's exact miss mix; retain that limitation in the same-machine comparison. No total TLB hierarchy reconstruction is selected.

```bash
python3 trackb/run.py --question Q8 --cpu 12 --numa-node 0 --environment both --out results/repro-q8-artemisia --execute
```

## Two-machine comparison and packaging

Use each machine's current allowed CPU/local node; the examples above use Artemisia CPU 12/node 0, whose sibling 68 is currently offline, and are not universal Charnwood assignments. Retain before/after online-sibling records and recheck availability before each collection. Collect each question natively on both named hosts, then review directories together, e.g. `python3 trackb/review.py results/q3-charnwood results/q3-artemisia --out results/q3-comparison`. All custom enclave runs belong on a hardware-enabled host, with successful runtime status and retained configuration. A missing access path is a documented limitation, not an emulated enclave result.

Preserve all source snapshots, raw repetitions, relevant snippets/assembly checks, plots, hashes, platform/configuration records and reproduction commands. See the project task list and report outline for the PDF/ZIP requirements and the specific missing repository Q4 second-machine evidence. The pre-revision Q4 archive and original working paths remain intact.

Final observations and two-machine comparison are in RESULTS_TRACK_B_COMPARISON.md. Exact historical observations use their own source snapshots; the final driver adds CSV/counter diagnostics and is not silently pooled with earlier builds.
