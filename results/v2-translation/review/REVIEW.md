# Artemisia translation advice control: incomplete huge-page backing

Follow-up: the node-0 strict rerun failed to obtain full native THP. A separate native pair with both page policies bound to node 1 completed successfully; see `../../v2-translation-node1/review/REVIEW.md`. The historical advice-only observations and requested next run below remain as recorded.

The user completed three 256 MiB spacing jobs (2,970 samples): native MADV_NOHUGEPAGE, native MADV_HUGEPAGE advice, and a hardware-debug enclave baseline. The same binary identities as the preceding calibration/layout campaigns were recorded. All raw observations are retained. This campaign supplies a repeat of the transition but does not complete the intended full-small-page versus full-huge-page control.

## Actual allocation

The native huge-page-advice data mapping has Size=262144 kB and AnonHugePages=6144 kB both before and after measurement. Thus only **6 MiB out of 256 MiB (2.34375%)** has PMD-sized THP backing. VmFlags includes hg and THPeligible is 1; these report eligibility/advice, not successful full allocation. The native 4K-policy mapping has AnonHugePages=0, nh, and THPeligible=0. Both data mappings report resident pages on node 0 under bind:0.

KernelPageSize/MMUPageSize remain reported as 4 kB for the advised VMA; those VMA fields alone are insufficient to decide THP coverage. Use the mapping's AnonHugePages accounting. The enclave mapping is not an equivalent huge-page control, and its physical EPC placement remains unverified.

## Timing observations

All-sample median host TSC ticks per load:

| Condition | Independent N=0 | Independent N=480 | Independent N=512 | Dependent N=512 |
| --- | ---: | ---: | ---: | ---: |
| Native 4K policy | 137.89 | 176.42 | 287.82 | 287.88 |
| Native huge-page advice, only 2.34% THP | 139.10 | 177.08 | 286.55 | 286.90 |
| Enclave baseline | 172.38 | 210.19 | 352.83 | 352.84 |

The largest independent adjacent median increase remains between the sampled N=480 and N=512 points in all three jobs. Their near-identical native curves **cannot establish insensitivity to translation** because the purported huge-page case remained mostly small pages. The occasional enlarged tails/median in other points also remain recorded; no single transient is assigned a capacity interpretation.

There are zero migration-tagged samples, ten samples with minor-fault deltas (122 minor faults, zero major faults), and 726 with context-switch deltas. The faulted conditions are native huge advice independent at N=960 and native 4K dependent at N=416. No faulted samples occur at tested spacings 448..576. All three jobs have nonzero coarse sibling busy ticks. These counts do not capture every interrupt/SGX exit or prove stable active frequency.

## Repair and next run

The implementation now offers native --pages collapse. It allocates a 2 MiB aligned span, populates the graph, requests synchronous MADV_COLLAPSE outside timing, and verifies that the exact data VMA's AnonHugePages equals its entire span before measuring. The same verification runs after the experiment. Failure or incomplete coverage causes a failed job, preserving any existing evidence rather than silently accepting a mixed backing condition. This does not promise that the kernel can always satisfy the request or prove the state at every intermediate instant.

The native functional probe in the coding sandbox obtained and verified 262144 KiB THP before and after a short 256 MiB run; its diagnostic log is collapse-functional-check.log. It is a functional allocation test with CPU affinity, not a replacement for the paired course-machine experiment or explicit NUMA control. Regression checks also reject a failed collapse and an injected false-success result with no huge backing. Native/SGX builds compile and the shared assembly checks pass.

The translation stage now defaults to collapse; --huge-policy advice reproduces this campaign's old best-effort request. Use a fresh directory to collect a coherent new build for all three conditions:

```bash
python3 scripts/run_rob.py --stage translation --cpu 1 --numa-node 0 \
  --environment both --footprint-mib 256 --out results/v2-translation-strict --execute
```

If collapse or verification fails, retain the diagnostic and treat this control as unavailable/inconclusive rather than disabling global host policies or claiming full huge-page allocation. Do not advance to a translation-insensitivity conclusion from the current data. Instruction-width/alignment and overhead controls remain subsequent work.

## Reproduction and provenance

```bash
MPLCONFIGDIR=/tmp/rob-mpl python3 analysis/review_sweep.py results/v2-translation
```

The audit identifies the partial THP coverage, and plot legends show the achieved 2.34% backing. Summary CSVs and PNG/PDF figures preserve all samples. source-before-collapse.tar.gz archives the benchmark/build sources used before the allocation repair; the new source/build identity must not be pooled blindly with this earlier cohort.

See the Linux [madvise documentation](https://man7.org/linux/man-pages/man2/madvise.2.html) for synchronous collapse behavior and its lack of a future mapping guarantee, and [THP documentation](https://docs.kernel.org/admin-guide/mm/transhuge.html) for observing coverage. No global page policy is changed by this repair.
