# AI assistance record

Retained background: AI assisted the earlier ROB mechanism discussion, reference-code review and Track A planning; those were not course-machine capacity measurements. AI assisted the Track B Q4/Q5/Q6 plan, platform-record interpretation, and the SGX sample commands described in README_Track_B.md. The user's Artemisia sample execution established hardware debug SGX functionality.

2026-11-06: Codex read README_Track_B.md and generated the ROB assembly generator, shared pointer-cycle initialization, native runner, SGX EDL/entry/config/build, raw CSV output, metadata collection, plotting script and verification tests. It compiled native and hardware-mode enclave targets and signed the debug enclave with the installed SDK. It debugged test disassembly parsing. Functional verification and limitations are recorded in ROB_BENCHMARK.md; no ROB capacity estimate is established by this implementation work. The student must review the assembly, dependency/spacing accounting, timer boundaries, EPC/footprint controls, and test the custom enclave on Artemisia before using measurements in the report.

2026-11-06 follow-up: After the user reported an enclave smoke-test failure,
Codex reproduced the SDK placeholder runtime error and used `ldd` to identify
an incorrect SDK runtime path embedded by the generated Makefile. It removed
that path, verified selection of `/lib64/libsgx_urts.so.2`, made Makefile changes
trigger a host-executable rebuild, and added visible subprocess output plus
operation-specific SGX errors. Native checks passed again. Hardware execution
still requires the user's SGX-enabled environment; this sandbox has no SGX
device. No heap or benchmark kernel changes were made for this repair.

2026-11-06 methodology revision: Codex inspected the saved Artemisia v1 CSVs
and identified repeated-prefix cache reuse, correlated ring layouts and a
half-footprint dependent control. It implemented method rob-v2: persistent
cursors, independent shuffles, a dependent link cycle covering the same lines,
full-traversal/data and selected-kernel warm-up, native mmap page advice,
stride/NOP-width/alignment controls, randomized condition order, raw
fault/context-switch diagnostics, source/build identifiers and memory snapshots.
It added CPUID/preflight records and a staged experiment runner with truthful
sibling-control labels, optional NUMA binding and optional whole-process perf
counts, plus plots that preserve method/run/control distinctions and sample
order. It consulted Intel and kernel primary documentation and Wong's original
measurements to define controls and inference limits. Native semantic/code,
CSV/mapping tests and a tiny /tmp campaign passed; SGX v2 compiled and signed
but cannot be hardware-run in the coding sandbox. The original v1 raw results
remain unchanged. The student must review the new accounting and staged gates,
validate v2 hardware execution, obtain course-machine calibration/controls, and
justify any final capacity inference independently of specifications.

2026-11-06 build follow-up: The calibration runner rejected a stale build before
collecting samples. Codex inspected timestamps and make's dependency output:
the unsigned enclave was newer than its signed counterpart. It updated
--execute to run make for the selected targets, then verify freshness before
hashing binaries or creating the result directory. This preserves the check
against mixing source/build versions while handling rebuild/sign/link work
automatically. No earlier experiment data was modified.

2026-11-06 completed-calibration review: The user ran ten rob-v2 calibration
jobs on Artemisia, including hardware-debug enclaves, and saved 300 samples.
Codex inspected CSVs, manifests, logs, smaps, numa_maps and platform snapshots;
verified current binary hashes against the recorded identities; generated a
reproducible analyzer, summary CSV, mapping/input-hash audit and PNG/PDF plots;
and recorded the findings in results/v2-calibration/review/REVIEW.md. It found
approximately twofold independent-chain overlap, verified native 4K/node-0
mapping, and identified remaining sample drift and uncontrolled sibling
activity. It selected 256 MiB only as a provisional blocker and recommended
an order-changed independent repetition. No samples were discarded and no ROB
capacity was inferred. EPC residency/node placement cannot be concluded from
SGX device mapping RSS/numa records. The student must review these distinctions
and the uncertainty before using the results in the report.

2026-11-06 repeat calibration review: The user completed the second ten-job
calibration with order seed 2. Codex reviewed the additional 300 samples and
memory audits, checked matched binary identities and workload parameters,
and added analysis/compare_calibrations.py plus per-campaign and comparison
CSV/JSON/PNG/PDF artifacts. At 256 MiB the repeat's early/late changes are below
0.4% in all four conditions, and medians differ from the first campaign by at
most 2.44%; the 128 MiB native dependent drift persists. Codex selected 256 MiB
as a working baseline for the next prefetch/layout sensitivity stage, retained
all 600 samples (66 with context-switch deltas), and documented uncontrolled
sibling activity and attribution limits. It prepared and checked the eight-job
next-stage command without running the hardware campaign in the coding
sandbox. No ROB capacity was inferred. Original raw data and benchmark
binaries were not changed by this review.

2026-11-06 pointer-layout review: The user completed eight native/hardware-debug
SGX spacing sweeps, producing 7,920 samples across three pointer seeds and two
node spacings. Codex added analysis/review_sweep.py and generated descriptive
CSV/JSON and PNG/PDF artifacts. All eight cases show their largest independent
adjacent median increase between the tested NOP spacings 480 and 512, and
independent/dependent medians converge after the step. The step also persists
in minima and separately labeled unflagged-sample sensitivity medians. All
samples were retained in the primary results, including ten with minor-fault
deltas and 2,103 with context-switch deltas. Native 4K/node-0 mapping and the
stride-128 span increase were checked; matching calibration binary hashes were
verified. The interpretation is a surviving instruction-window candidate, not
an exact ROB capacity or proof that prefetching is absent. Codex prepared the
three-job translation control as the next user-run experiment. No benchmark
code or original raw observations were changed by this review.

2026-11-06 translation-control repair: The user completed three translation
jobs (2,970 samples). Codex reviewed the raw data and actual mappings, finding
only 6144/262144 KiB AnonHugePages in the advised native mapping. It labeled
this a partial/inconclusive full-page-size control, retained all raw data and
archived the preceding sources under its review directory. It consulted Linux
THP/madvise documentation and kernel UAPI, added native aligned synchronous
MADV_COLLAPSE with full-backing checks before/after measurement, and changed
the translation stage default to collapse while retaining an advice-only
reproduction option. Native fault-injection tests reject both allocation
failure and falsely reported success with incomplete backing; a real 8 MiB
check passed, and a separate 256 MiB sandbox native probe verified full THP at
both boundaries. This probe is functional setup evidence, not a paired NUMA
controlled capacity result. Native and SGX builds compile/sign and shared
kernel bytes remain matched. A fresh three-condition user-run hardware cohort
is required after the new build identity; no translation-insensitivity or ROB
capacity conclusion was inferred from the partial advice run.

2026-11-06 NUMA-specific allocation follow-up: The user completed a local
hardware-enclave baseline (990 samples) before native MADV_COLLAPSE failed
under bind:0. Codex inspected the saved earlier unbound probe and found
22 MiB on node 0 and 234 MiB on node 1, explaining why that success had not
established local allocation feasibility. It ran short, explicitly bound
native allocation checks: node-0 64/128/256 MiB failed, node-1 256 MiB passed
full backing and placement checks. These are functional allocation diagnostics,
not capacity results. Codex then executed two complete native page-policy
sweeps on CPU 1 with both mappings bound to node 1 (1,980 samples); full THP
versus zero THP and node-1 placement were verified at both boundaries. The
coarse 480->512 overlap-loss step persists in both page policies. This remote
control remains separate from local/enclave timing comparisons. It updated
the analysis helper to review explicitly selected completed jobs of an
incomplete campaign with clear labels, and to plot native-only cohorts without
inventing enclave data. The noisy partial enclave run, original failure, and
all observations were retained. Source/binaries were not changed by this
follow-up; the next stage is local 4K instruction-width/alignment controls.

2026-11-06 instruction-delivery review: The user completed 16 frontend jobs
(15,840 samples), with matched preceding binary identities. Codex reviewed
one-/two-byte NOP encodings and loop offsets 0/16/32 at 16 KiB and 256 MiB,
checked native 4K/node-0 placement and raw parameters, and retained all samples,
including 18 with minor faults and 2,668 with context-switch deltas. All eight
large-footprint curves preserve the largest independent timing step between
sampled N=480 and N=512 in medians, minima, and separately labeled unflagged
medians. Small-footprint curves show no comparable step. Elevated baseline
and isolated timings remain documented rather than removed or attributed to
an unmeasured cause. Codex extended analysis/review_sweep.py with separate
footprint plots, parameter validation and sensitivity CSVs, then exercised it
on the frontend, native-only and incomplete-campaign data. Benchmark sources,
binaries and original observations were unchanged. The result supports a
surviving instruction-window candidate, not an exact ROB count. Codex prepared
and checked the eight-job overhead stage in planning mode; the user must run
its enclave cases in the hardware-enabled shell. Overhead and finer/repeated
spacing measurements remain before capacity inference.

2026-11-06 overhead review: The user completed eight batch-length controls
(240 samples), with the same binary identities as the frontend campaign.
Codex added analysis/review_overhead.py, validated raw parameters/sample IDs,
audited native 4K/node-0 placement, and retained every observation. Zero-work
controls remain in total TSC ticks per invocation, with blank per-load fields.
The measured native/SGX zero-work medians are about 70–74/10,758–10,764 ticks.
At 100,000 iterations the SGX zero-work scale is about 0.054 ticks/load;
long-batch slopes support dilution of this mostly fixed invocation cost in
the fast-load control. Primary timings remain uncorrected, and subtraction
diagnostics are explicitly labeled. The campaign records no migration,
ordinary faults or context switches but does not establish interrupt/AEX
absence, controlled sibling activity, or complete large-footprint batch
independence. Codex generated CSV/JSON and PNG/PDF artifacts, checked syntax
and actual-data invariants, and prepared the fine N=448..576 step-4 command
in planning mode. Existing full-range controls supply its coarse bracket;
an independent repeat and accounting remain before a capacity conclusion.
No benchmark source, binary, or original sample was changed by this review.

2026-11-06 first fine-spacing review: The user completed two fine jobs
(1,980 samples) over N=448..576 in steps of four, with matching preceding
binary hashes. Codex reused analysis/review_sweep.py to summarize all samples
and generate CSV/JSON and PNG/PDF artifacts. Both environments have a partial
independent timing rise at N=496 and near-convergence with the dependent
control at N=500. The largest adjacent step is 496->500 in medians, minima,
and separately labeled unflagged medians; the broader observed transition
region is 492–500. Codex checked the raw observations at these points and
native 4K/node-0 mapping. All samples remain included, including six native
dependent N=516 samples with 20 minor-fault increments and 524 samples with
context-switch deltas. Significant SGX variability is retained and is not
assigned an unmeasured cause or interpreted as additional capacity bounds.
The review distinguishes NOP spacing and the loop's 2N+4 architectural
instructions from an inferred total ROB-entry count. Codex prepared and
checked the matched fine repeat with order seed 2 in planning mode, updated
the experiment status, and retained original data and benchmark binaries.
No exact ROB capacity or independent replication has yet been established.

2026-11-06 fine-repeat consolidation: The user completed the two order-seed-2
repeat jobs (1,980 additional samples). Codex reviewed the raw evidence and
verified matching workload/binary identities, reused the sweep analyzer,
and added analysis/compare_sweeps.py to compare campaigns without pooling.
It generated overlaid curves, selected raw-transition sample plots, per-point
CSV comparisons, global-step diagnostics and hashed mapping/input audits.
The previously selected 492–500 transition region repeats in native and SGX,
but the repeat enclave's largest median/unflagged-median step is an isolated
544->548 peak, not 496->500; the minimum diagnostic still selects 496->500.
Codex corrected its initial commentary about that global maximum and retained
the peak with no cause assigned. All 3,960 fine observations remain included,
including 16 with 115 minor-fault increments and 1,065 with context-switch
deltas. Native 4K/node-0 mapping and separated raw 492/496/500 timing ranges
were checked. Codex consolidated ROB_RESULTS_ARTEMISIA.md, distinguishing the
effective NOP-spacing/window result from total ROB entries, and stopped the
routine Artemisia run sequence for this claim. It checked analysis syntax,
actual-data invariants and evidence hashes; benchmark code/binaries and raw
data were unchanged. No new benchmark campaign was executed. The second
course-machine result, PRF/TLB work and final assignment deliverable remain
separate outstanding work.

2026-11-06 revised 105-point scope: The user selected Q1/Q2/Q3/Q4/Q5/Q8,
dropped Q6 and designated Q4 completed. Codex preserved that status and
archived 827 original files under preserved/, including source, binaries,
raw data, figures, analysis and instructions. The archive hash and 825
immutable Q4 files were verified; only the project README and this AI log
are scope-update exceptions. No Q4 implementation/data/plot/analysis file
was changed and no Q4 experiment was rerun. Missing repository Charnwood
Q4 evidence was flagged as a submission gap, without inventing a result or
reopening the completed Artemisia design.

Codex implemented the new suite under trackb/ in Q3 -> Q1 -> Q2 -> Q5 -> Q8
order, adapting Q4's timing, affinity, pointer-graph/cursor, sampling, SGX,
raw-output and mapping-audit designs and reusing read-only platform code.
The original root Makefile/build inputs remain unchanged. It generated 795
shared assembly kernels, native and hardware-debug enclave builds, semantic
and linked-byte tests, separate host timer inspections, a fresh-directory
collector with source/binary snapshots, native NUMA/page checks, SMT records
and cooperative locking, grouped PMU diagnostics, and per-campaign plotting
and contrasts. It consulted primary LLVM processor models, Intel instruction
and event references, and Linux perf documentation, linked in METHODS.md.
Q5 explicitly targets 64-bit integer GPR destinations using nonidentity LEA,
one/four-chain controls and four-byte NOPs matching count and encoded length.
Q8 explicitly targets added L1-DTLB/STLB service cost with matched cache-line
footprints and declared counter/cache qualification; no full TLB hierarchy
reconstruction or unconditional total PRF conversion is claimed.

Native smoke and short pilot validation were executed and retained (504 raw
validation observations across six collections, not completed exercise
comparisons). The first Q2 pilot exposed unwanted overlap across iterations;
Codex retained the rejected prototype and added a common end-of-block LFENCE,
then checked the corrected nine-job pilot. Q5's one-chain-only upper-range
slowdown was explicitly not inferred as a PRF boundary. Native Q8 pilot event
rates support the intended miss/cache treatment, but final repeated estimates
and enclave coverage remain pending. Test-only denied-perf and synthetic
analysis fixtures are labeled tests, not measured hardware results. Native
checks, all shared kernel bytes, result/cursor checks and separate native/
enclave-host timing boundaries pass. Current topology was rechecked: CPU 12
is online on node 0 and sibling 68 is offline, so new Artemisia guidance uses
that core with collection-time checks and no host configuration changes.

The new enclave compiles, links and signs, but this coding environment has no
SGX device. Its custom kernels have not been represented as hardware-executed;
the user's SampleEnclave/Q4 successes remain separate valid setup evidence.
Charnwood new-question measurements were not performed here. Codex updated
the README, task list and report outline and produced a visibly draft PDF
with the six selected questions and 105 points on its first page, retaining
the measured Q4 content. A packaging tool requires actual two-machine/custom
enclave evidence and a final report before a final ZIP; draft packaging is
explicit. Student verification/understanding and the remaining full native/
enclave measurements, inferences and final report are still required.

2026-11-06 hardware-access follow-up: After completing the concrete code and
native validation, Codex checked host-level access outside the device-hiding
sandbox. Artemisia's SGX device is accessible there. All five custom native/
hardware-enclave semantic checks passed, including deterministic cross-build
result checks; the retained log and binary hashes are under
results/trackb-hardware-check.*. A separate 30-job native/enclave hardware
smoke campaign completed with 92 raw validation samples on CPU 12/node 0,
with the idle-sibling gate satisfied. This supersedes the earlier build-only
runtime status for the new kernels, without treating smoke data as completed
performance results. Codex attempted a read-only BatchMode/strict-host-key
SSH check to Charnwood; it stopped because this session has no trusted
ED25519 key for that host. Codex did not disable verification or invent
remote results, and requested trusted connection details or user collection
while continuing independent Artemisia work. Draft packaging was tested
(all artifact groups included); final packaging correctly rejects missing
measurement evidence and the draft report. Q4 preservation remains verified.

2026-11-06 measurement follow-up: Codex collected and reviewed complete
Artemisia native/hardware-enclave Q3 (480 observations), Q1 (240 including
invocation controls), and corrected Q2 (540) measurement campaigns on CPU 12,
node 0, with sibling 68 offline in snapshots and strict idle/placement gates.
It added their actual separate-repetition medians, plots and qualified
interpretations to RESULTS_TRACK_B_ARTEMISIA.md and the draft PDF. Native
branch counters support the Q3 contrast; enclave branch counts do not cover
the kernel and were not interpreted as its miss rate. Charnwood remains
pending. A source-only collection bundle/helper was prepared and validated
with a fresh extraction/native build; no remote result was synthesized.

The first Q2 full campaign stopped at job 31 because its before numamaps
snapshot accounted for two fewer pages than expected. The cause is not
established. The partial campaign and all rows remain intact with collection
notes, and an identical fresh retry passed all declared gates. The first
complete Q5 sweep retained 7,920 observations using constant-offset LEA.
Its one/four-chain curves tracked NOPs and its one-chain cost contradicted
the ordinary execution-dependency assumption. Codex therefore rejected this
as an isolated PRF estimate; the prior claim that nonidentity constant-offset
LEA necessarily avoids allocation ambiguity is superseded. The exact hardware
optimization was not established. Codex changed only the new Q5 filler to
scaled-index LEA computing 3*x, updated modular-result checks and methods,
and passed native/hardware-enclave semantic and byte checks. Q1/Q2/Q3/Q8
kernel bytes remain unchanged by that revision. The revised Q5 assay is
being validated separately; it is not pooled with the first sweep. Codex
also improved Q2 plot readability and tightened final-package checks to
reject incomplete or failed-placement campaigns and smoke-only evidence.

Further Q5 control validation: the scaled four-chain pilot showed a separate
early transition, while one-chain arithmetic was execution-limited. Codex
added an eight-chain control with identical initialization, saved registers,
filler widths and matched NOP function lengths. The suite now contains 1,053
shared kernel functions. Native and hardware-enclave result/ABI/byte checks
pass. Warming before snapshots did not eliminate occasional partial numamaps
inventories; those later pilot/coarse attempts were also stopped and retained.
Codex replaced their exact-accounting role with complete read-only per-page
node queries (move_pages with nodes=NULL, no migration), retaining original
maps as ancillary evidence and requiring every page to be resident/local,
with full RSS and no THP. The method change is recorded in fresh campaigns;
old failed campaigns were not retroactively approved. Synthetic acceptance
tests reject partial, remote and error statuses. Codex also corrected Q8's
enclave arena to page alignment and checked actual base/seed/cursor-derived
pointer geometry in compact/scattered native and hardware-SGX execution.
Timing boundaries still pass separately, and all setup/query operations
remain outside timing. Review outputs now retain the exact analysis script,
its hash, runtime versions and input hashes. No final PRF total has been
inferred from the diagnostic curves.

2026-11-06 completed comparisons and report: The user supplied
vvenka25@charnwood.ece.ncsu.edu and confirmed no saved known_hosts entry.
Codex used first-connection pinning in results/charnwood-ssh-known_hosts,
then strict checking (public fingerprint SHA256:8c5klIU2j7b26gUYtfczpDu0fVWpAE0BebWdvX0e1BA).
This was not independent external-fingerprint authentication. Existing
noninteractive authentication worked; no login secret was requested. Sources
and builds ran in a separate Charnwood /tmp worktree, avoiding shared-home
build overwrites. Inventory confirmed i7-6700/model 94, and no current or
legacy SGX device path. Setup and collection logs are retained under
results/charnwood-session/ and its archive.

Charnwood's strict zero-sibling-tick attempts stopped on actual user/nice
activity. Codex isolated the collector/helpers from the benchmark core,
corrected an intermediate legacy-preflight affinity integration error that
took no samples, and used a required nonzero private Linux core-scheduling
cookie inherited by benchmark children. Completed work uses CPU 1/node 0,
with the orchestrator/collector on CPU 0 and kernel/interrupt limitations
documented. No sibling CPU was offlined or global configuration file changed.
Q3/Q1/Q2/Q5/Q8 all have actual repeated native measurements on both named
hosts and hardware-SGX counterparts on Artemisia. Native Q3 core cycles
expose Charnwood elapsed-time/frequency drift without discarding its data;
branch and branchless evidence is interpreted accordingly. Q1 reports
approximately 3/1.5/1 native core cycles per IMUL at fixed work, with the
replication alternative explicit. Q2's matched blocked-older/ready-younger
control supports within-block out-of-order execution on both machines.

Q5 fine intervals came from each host's own coarse observations: Charnwood
120..160 and Artemisia 192..232, using 10,000-iteration batches. Effective
integer-GPR destination-pressure regions are about 128–144 and 200–216
writes per gap, respectively. Total PRF size and precise PRF-versus-scheduler
attribution remain unproved; no N+16, 2N or published total is substituted.
One/four/eight-chain, NOP and serialized-load controls and all disturbances
remain in the report/data. Earlier constant-offset and stopped variants stay
separate rather than being pooled or deleted.

The initial three-counter Q8 Charnwood data exposed a shifted compact TSC
baseline despite valid miss/cache rates. Codex added a simultaneous fourth
active-core-cycle counter, appended its CSV fields without rewriting older
rows, and collected fresh final campaigns on both hosts. Miss/cache criteria
support about 9 additional active core cycles per STLB-served L1-DTLB miss on
Charnwood and 7 on Artemisia. A TSC estimate additionally requires effective
cycle/TSC medians matching within 2% and each ratio's p90/p10 <=1.02; failing
comparisons have that estimate withheld while qualified cycle costs remain.
Artemisia's six native pairs pass; four of Charnwood's six TSC estimates are
withheld. Protected miss-event coverage remains unqualified, so enclave
timings are not presented as verified TLB-miss penalties. Native/hardware-SGX
semantic, geometry, denied-PMU, timer and 1,053 linked-byte checks pass;
synthetic tests cover clock-drift rejection, cost normalization and placement
gates. All performance rows are genuine hardware observations, not fixtures.

The user clarified that Charnwood Q4 had not yet been done and supplied the
report author name, Varunaditya Venkatesan. Codex collected the missing native
comparison using the unchanged preserved source/build ID bcd9d621feed36f6:
1,950 coarse observations and two 390-observation fine processes. Both fine
processes place the largest step at N=220→224 under median/minimum/unflagged
diagnostics. The original 3,084-kernel tests and a separate compiled native
timer inspection pass on Charnwood. Source/binary snapshots and external
private-core-group controls accompany the new data. No Artemisia Q4 rerun,
source edit, raw-data edit, plot rewrite or analysis rewrite occurred; all
825 protected files and the original archive hash still verify.

Codex wrote the two-machine findings, updated scope/task/report documentation,
created safe isolated Q4 reproduction and comparison helpers outside legacy
build inputs, and assembled the PDF report with the six selected questions,
105 points and the supplied author on its first page. Figures use actual
data and keep repetitions separate; no confidence interval or exact physical
capacity is invented. The report records unresolved attribution, frequency,
EPC placement, interrupt/AEX and host-wide interference limits. Packaging
requires actual evidence for all six questions, a final first page and Q4
preservation. Source packages keep original build artifacts in the immutable
archive, with archive-backed hash verification when active originals are
omitted. Source-only collection bundles are explicitly not final submissions.

Final artifact validation (November 6, 2026): Codex inspected the 15-page
PDF, including its author, selected-question table, figures and layout; the
LaTeX log has no layout/undefined-reference warnings. All 12 native evidence
cells and six Artemisia hardware-enclave cells pass packaging checks; partial
and smoke campaigns are rejected as completed evidence. A clean extraction
of the candidate ZIP passes CRC, required-artifact and Q4 preservation checks:
825 original files verify, including 20 omitted active build files verified
from the immutable archive. The extracted 28-file source collection bundle
builds and passes native functional, assembly, geometry, read-only page-query
and denied-PMU checks on CPU 13. Hardware-SGX result/byte/timer validation is
recorded separately; this native extraction check is not an SGX rerun.
The final archive is named HW3_Track_B_105_Varunaditya_Venkatesan.zip; its
checksum is provided beside it. The source-only bundle records the snapshot
before final ZIP packaging; current task completion is in the outer README
and TASKS.md. Scientific limitations, including Q5's unproved total PRF
conversion and Q8's unqualified enclave miss attribution, remain explicit.


## GitHub publication — November 7, 2026

At the user's explicit request, Codex prepared the reproducibility materials for publication to
vvenka25/ECE-592-Project-3. The user also explicitly requested
relevant Markdown, the AI-use log, activity logs and checklists. Publication
was prepared in a separate temporary tree; the existing local Q4 archive,
original source/data/plots and final submission ZIP were not changed.

The publication includes source and assembly generators, timing/SGX/affinity/
NUMA/PMU runners, analysis/plot scripts, report source/PDF, existing Markdown,
checklists and validation/activity logs. Raw observations and full mapping/
configuration audits are losslessly archived with per-file hashes and a
safe, idempotent unpacker. Historical source snapshots are retained. Generated
ELF binaries, signing keys, credential/configuration directories, SSH host-key
cache and the duplicate final ZIP are excluded. No GitHub credentials are
stored in the project.

Because the original Q4 preservation archive includes a debug signing key,
Codex created a separately named source-only derivative retaining the exact
807 original non-build members and original hashes. The public verifier and
isolated Charnwood reproduction helper accept this derivative; the original
full archive remains intact locally. No original Q4 experimental source or
measurement was edited. Public preservation checks cover 805 immutable
non-build files; this scope differs explicitly from the full local 825-file
check. Publication tests restore the data, check idempotence and overwrite
refusal, verify preservation, regenerate all six figures/report and build/check
the native suite from a clean tree. These are engineering/reproduction checks,
not fresh performance campaigns or new measured findings.


The initial GitHub upload attempt was rejected with HTTP 403, "Resource not
accessible by integration," despite repository metadata reporting the user's
push permission. No repository file was created by that attempt. The host's
GitHub CLI is not logged in and no local client SSH key is available. Codex
requested host-side GitHub authentication from the user and prepared a local
Git commit/bundle so the verified work remains ready for upload. No token was
requested in chat, extracted from the connector or written into project files.
