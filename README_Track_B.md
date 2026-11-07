# Homework 3 — Track B — current 105-point scope

> GitHub checkout: first follow [REPRODUCING.md](REPRODUCING.md) and run `python3 data/unpack_results.py` from the project root to restore raw evidence. Public preservation uses the source-only Q4 derivative; the full original archive and submission ZIP remain unchanged locally.

## Selected questions and status

The report's first page must state **Q1, Q2, Q3, Q4, Q5, Q8 — 105 points**.
The former Q4/Q5/Q6 selection is superseded. Q6 (TLB hierarchy reconstruction) is dropped.
The user's revised selection is the authority for this scope; the assignment PDF is not present in this workspace for a fresh independent check.

| Question | Task | Points | Status |
| --- | --- | ---: | --- |
| Q1 | Experimentally confirm pipelining | 10 | Both native machines and Artemisia HW SGX measured; latency/throughput and unit-replication qualification documented |
| Q2 | Experimentally confirm out-of-order execution | 10 | Both native machines and Artemisia HW SGX measured with older-blocked/younger-ready dependency controls |
| Q3 | Experimentally confirm branch prediction | 10 | Both native machines and Artemisia HW SGX measured; actual branch verified, native miss/cycle evidence retained |
| Q4 | Reverse engineer ROB size | 30 | **Completed work preserved; missing Charnwood coarse/fine/repeat comparison added using unchanged code** |
| Q5 | Reverse engineer physical register file size; identify register class | 35 | 64-bit integer GPR pressure windows measured on both machines and SGX; total PRF conversion remains unproved |
| Q8 | Measure additional cost of a TLB miss | 10 | Native STLB-served miss costs about 9 core cycles on Charnwood / 7 on Artemisia; SGX timing contrast has unqualified miss attribution |
| **Total** | **Six selected exercises** | **105** | **Implementation/collection order Q3 → Q1 → Q2 → Q5 → Q8** |

Implementation, functional validation, hardware-enclave validation, and completed experimental conclusions are distinct milestones. No measured results are invented for the remaining questions. See [TASKS.md](TASKS.md) and [report/OUTLINE.md](report/OUTLINE.md).

Actual Artemisia observations, including separate repetition medians and links to raw evidence/plots, are in [RESULTS_TRACK_B_ARTEMISIA.md](RESULTS_TRACK_B_ARTEMISIA.md). Cross-machine conclusions and scientific limits are recorded separately below.

The [two-machine findings](RESULTS_TRACK_B_COMPARISON.md) and [PDF report](report/report.pdf) contain the completed comparisons and explicit inference limits. Author: **Varunaditya Venkatesan**. Selection is 105 points; no grade or exact physical capacity is asserted by that total.

## Preserve completed Q4

Keep the root Makefile, src/, enclave/, scripts/, analysis/, tests/, build/ and existing Q4 results intact. Q4 build inputs are unchanged by the new suite. The pre-revision source, binaries, raw data, plots, analysis, documentation and AI log are also archived in `preserved/q4-20261106.tar.gz`, with an inventory and archive hash in `preserved/q4-20261106.sha256.json`.

- [ROB implementation and reproduction](ROB_BENCHMARK.md)
- [Measured Artemisia findings and limitations](ROB_RESULTS_ARTEMISIA.md)
- Raw Q4 campaigns and per-stage reviews remain under results/.

Q4's completed Artemisia work remains unchanged, including its effective N=492–500 finding and exact-total-ROB attribution limits. The user subsequently clarified that Charnwood Q4 had not yet been done. Its missing native comparison was collected from the unchanged source/build ID `bcd9d621feed36f6` in a separate host-local worktree: coarse, fine and an order-shuffled fine repeat. Both fine processes place the largest step at N=220→224. See [Q4_CHARNWOOD_RESULTS.md](Q4_CHARNWOOD_RESULTS.md) and [the ratio comparison](results/q4-comparison/curves.pdf). No Artemisia Q4 rerun or original-file rewrite occurred. Historical Q4 instructions/analysis remain frozen as their original record.

## Machines and enclave setup

Use Charnwood (Intel Core i7-6700, Skylake, 4 cores/8 threads) and Artemisia (Intel Xeon Gold 5420+, Sapphire Rapids, two sockets, 56 physical cores, SMT and two NUMA nodes) for native comparisons on **every selected question**. Recheck topology and allowed CPUs before selection. Current Artemisia inventory still has CPU 68 offline. CPU 12 is online on node 0 and its sibling is CPU 68, so CPU 12 is the recommended new-experiment choice while that sibling remains offline. Q4 and the initial pilots used CPU 1 (sibling 57); retain those configurations separately. Recheck this at collection time.

```bash
lscpu -e=CPU,CORE,SOCKET,NODE,ONLINE
python3 scripts/preflight.py 12
```

Choose a permitted online CPU and bind native allocation to its local NUMA node. Collection needs Python 3 standard-library facilities; plotting additionally needs Matplotlib. The runner reuses Q4's read-only preflight and platform identification and records fresh topology, affinity, sibling activity and memory snapshots. The suite holds a cooperative per-user core lock; this prevents its own runs colliding but does not reserve the core against other users. Arrange a reservation where possible. `--require-idle-sibling` stops and retains evidence if coarse sibling busy ticks are observed; zero ticks are not proof of zero interference. Frequency and interrupt/AEX limitations remain explicit.

Artemisia has successfully executed Intel SampleEnclave with SGX_MODE=HW and SGX_DEBUG=1, and the custom Q4 enclave. Its SDK is `/opt/intel/sgxsdk`:

```bash
source /opt/intel/sgxsdk/environment
make -C trackb native enclave
make -C trackb check
TEST_CPU=12 TEST_SGX=1 make -C trackb check
```

The new Makefile always builds hardware-debug SGX; there is no simulation fallback. All five custom benchmarks pass hardware semantic checks, shared-byte comparisons and separate native/enclave-host timer inspection. An early 30-job/92-sample smoke campaign is retained as functional history; later scaled-index/eight-chain, page-geometry/residency and four-counter revisions have their own successful checks. The coding sandbox hides SGX, so authorized host-level execution supplied access. See `results/trackb-four-counter-hardware-check.log` and the per-campaign evidence. Charnwood's current/legacy SGX device paths are absent; its native results are retained and applicable enclave comparisons use Artemisia. Crux's prior user-device-access check failed and it is not a substitute comparison machine.

The SDK link-time placeholder must not become the runtime library. No SDK RPATH is embedded; inspect `ldd trackb/build/trackb-enclave` for the installed PSW runtime. The new 384 MiB enclave heap is separate from Q4's unchanged configuration; signing reports configured required memory, not free EPC. Current Q8 native/enclave arenas are both page aligned and hardware checks verify their pointer geometry. Host process binding does not verify physical EPC NUMA placement.

## New experiment collection

[trackb/METHODS.md](trackb/METHODS.md) defines each experiment, exact dependencies, normalizations, controls, inference limits and primary references. Kernels are assembled once and linked into native and enclave builds. The new host retains Q4's affinity, warm-up, continuous cursor, host LFENCE/RDTSCP/LFENCE timing, ordinary-fault/context-switch recording, snapshots and immutable output-directory approach.

Smoke and pilot collections are **validation only**. Complete measurement campaigns and their plots now exist for every selected question on both native machines and for Artemisia SGX. The rejected cross-iteration Q2 prototype, constant-offset LEA diagnostic, stopped snapshot/SMT attempts and shifted three-counter Q8 baseline remain separately documented. See `trackb/VALIDATION.md`. Q3 native core cycles expose elapsed-time/frequency drift on Charnwood; Q8's final fourth counter supports a cycle-cost estimate and clock-proxy qualification for any TSC estimate.

For a new collection, recheck topology and validate the selected build first. Use fresh output paths; existing evidence is never overwritten:

```bash
python3 trackb/run.py --question all --stage smoke \
  --cpu 12 --numa-node 0 --environment both \
  --out results/repro-artemisia-smoke --execute
```

Then reproduce in Q3 → Q1 → Q2 → Q5 → Q8 order. For example:

```bash
python3 trackb/run.py --question Q3 --cpu 12 --numa-node 0 \
  --require-idle-sibling --environment both --out results/repro-q3-artemisia --execute
python3 trackb/review.py results/repro-q3-artemisia
```

For Charnwood, select its currently allowed CPU/local node and use `--environment native` with a fresh machine-specific output directory. Follow the question order Q3, Q1, Q2, Q5, Q8. Default measurement campaigns include two fresh-process repetitions with shuffled job order; all raw observations remain separate. Review each question before moving to the next. Q5 defaults to a coarse range; choose its fine interval from its own allocation-pressure observations rather than Q4's NOP transition. Q8 uses a few fixed translation treatments, not a hierarchy reconstruction.

Charnwood was reached at `vvenka25@charnwood.ece.ncsu.edu`. Because neither session had a saved key, its first offered key was pinned in `results/charnwood-ssh-known_hosts`, followed by strict checking; no independent external fingerprint authentication is claimed. Its public fingerprint is SHA256:8c5klIU2j7b26gUYtfczpDu0fVWpAE0BebWdvX0e1BA. A source-only bundle is at `submissions/trackb-charnwood-source.tar.gz`, with inventory/hash. Extract into a fresh **host-local** directory, inspect topology, and run `bash report/collect_charnwood.sh CPU results/charnwood-new`. This uses required private core scheduling and a separate controller core. Kernel/interrupt contexts and other cores' cache/memory traffic remain possible. No sibling is offlined or global configuration file changed.

The recorded Q5 batches use 10,000 iterations/sample; fine intervals were Artemisia N=192..232 and Charnwood N=120..160. Reproduce a different observed bracket if your own coarse result changes. For exact historical builds, extract each campaign's `source-snapshot.tar.gz` into a fresh tree, use its metadata/toolchain and recorded command with fresh output paths, and retain the build/binary hashes. Current-source reruns are not silently pooled with older snapshots.

Q4 has a separate safe reproduction helper, `report/reproduce_q4_charnwood.py`, which verifies the original archive, uses an isolated worktree and refuses to run on Artemisia. For example, first plan `--stage coarse --cpu 1 --workdir /tmp/q4-repro --out results/repro-q4-coarse`; add `--execute` on Charnwood, review, then supply the measured `--stage fine --lo ... --hi ...` and repeat with `--order-seed 2`. The recorded Charnwood fine bounds were 192..240.

Omit `--execute` to inspect commands without creating output. The runner builds only trackb targets and never overwrites an existing campaign. It records command/configuration, source and binary hashes, a source snapshot, copied binaries, platform records, maps, raw CSV, failures and sibling activity. Analysis accepts several directories to place both machines/environments side by side without pooling repetitions:

Current native placement uses read-only per-page node queries (`move_pages` with `nodes=NULL`) before and after timing, plus full VMA/RSS/no-THP checks. It accepts no unknown/remote pages. `numa_maps` snapshots are also retained: several earlier collections stopped when those snapshots accounted for a few fewer pages despite full RSS, and warming alone did not resolve that discrepancy. The partial campaigns stay rejected; the direct-query protocol is recorded in fresh campaigns. Unsupported query access stops collection, rather than claiming verified placement.

```bash
python3 trackb/review.py results/q3-charnwood-private results/q3-artemisia \
  --out results/repro-q3-comparison
```

The default PMU policy is auto: unsupported/denied counters are explicitly unavailable, with blank fields. `--pmu required` fails before timing if opening fails; `--pmu off` supports a perturbation check. Counts bracket slightly more host-user work than the TSC interval; enabled/running times are retained. Q8's final four-event group adds active core cycles. Its native cycle cost requires the declared miss/cache/coverage gates; TSC cost additionally requires stable/matched effective cycle/TSC ratios within 2%. Enclave miss-event coverage remains unqualified. Earlier three-event results are retained as diagnostics.

## Report and submission

The report must include actual code snippets, timing boundaries/units, repeated measurements and plots, CPU/microarchitecture identification, native comparisons on both machines, applicable same-machine enclave comparisons, assumptions and unresolved limitations for each selected exercise. Keep measured findings separate from published models/specifications. TSC ticks are acceptable and must not be relabeled as core cycles.

Use [report/OUTLINE.md](report/OUTLINE.md) and `report/report.tex`. The report records qualified conclusions, including unresolved total-PRF attribution and enclave TLB-event coverage. The ZIP contains the PDF, source, raw observations, figures/scripts, reproduction instructions and [AI_USE_LOG.md](AI_USE_LOG.md), including Q4's immutable archive. The preservation verifier checks active originals byte-for-byte; source ZIPs may verify omitted original build outputs from that archive. Understand and be able to explain the submitted code and conclusions.

PRF class is explicitly **64-bit integer GPR**. Its speculative allocation budget is not automatically total PRF size. Q8 targets **additional L1 data-TLB miss cost when resolved by the STLB**, conditional on evidence; page-walk cost or a complete TLB hierarchy must not be silently substituted. Cache/prefetcher hierarchy reconstruction and unselected questions remain outside scope.
