# Artemisia v2 N=0 calibration review

Follow-up: the requested repeat is complete. See `../../v2-calibration-repeat/review/REVIEW.md` for the comparison and the decision to use 256 MiB for the next controls. The initial observations and decision below remain as recorded at this review.

This reviews the user's completed `results/v2-calibration` campaign. All ten jobs succeeded, including five hardware-debug SGX jobs. The 300 samples share build ID `3547cc1ae6021325`; the current native, platform-info, enclave-host and signed-enclave binaries matched the manifest's saved SHA-256 hashes at review time. No raw observations were changed or excluded for this review.

## Measured results

Median host TSC ticks per load, computed as elapsed_ticks / (2 * iterations), with 100,000 iterations and 15 samples per mode:

| Full-cycle line footprint | Native independent | Native dependent | Enclave independent | Enclave dependent |
| --- | ---: | ---: | ---: | ---: |
| 16 KiB | 1.86 | 3.72 | 1.91 | 3.77 |
| 1 MiB | 7.62 | 15.26 | 7.79 | 15.51 |
| 64 MiB | 109.99 | 234.83 | 149.08 | 302.25 |
| 128 MiB | 133.23 | 271.75 | 164.41 | 325.34 |
| 256 MiB | 136.47 | 278.23 | 172.36 | 342.84 |

Independent execution is approximately twice as fast as dependent execution at 256 MiB (dependent/independent medians: native 2.04, enclave 1.99). This supports the intended overlap mechanism. Large-footprint delay is much greater than the cache-resident controls. Neither observation identifies a ROB size, guarantees a particular data source for every load, or isolates the cost of translation from other memory service.

## Stationarity and placement

At 256 MiB, the change from the first-five median to the last-five median is native independent +4.81%, native dependent +0.42%, enclave independent +0.25%, enclave dependent +0.10%. The native independent trend needs replication. At 128 MiB, native dependent timing rises +13.82% and enclave dependent +3.71%, so accepting the smaller footprint as an interchangeable stationary blocker would be premature. Native independent timing at 64 MiB ranges from 80.28 to 123.65 ticks/load; this is the least stable independent large-footprint case in this campaign.

Native data mappings before and after measurement have 4 KiB pages, zero AnonHugePages, no-huge-page advice, and all resident pages on node 0 under bind:0. This verifies actual native placement/page-policy controls for these runs. Enclave mappings show the SGX device and bind:0 but do not report per-node resident EPC page counts; their Rss=0 values are not evidence of zero EPC residency. EPC placement, available EPC and absence of reclamation are not established by these snapshots.

There were zero migration-tagged samples, zero samples with recorded ordinary page-fault deltas, and 35 samples with recorded context-switch deltas. All remain in the statistics. Sibling CPU 57 has nonzero coarse busy ticks in eight of ten jobs; the manifest truthfully labels sibling control as uncontrolled. These counters cover the whole job and cannot locate sibling activity within a timed sample. Frequency snapshots do not establish fixed active core frequency. Zero ordinary fault deltas do not prove absence of all SGX exits or EPC activity.

The metadata identifies the installed PSW runtime package as libsgx-urts-2.23.100.2-1.el9.x86_64, and the loader selects /lib64/libsgx_urts.so.2. Do not infer the separate SDK version from that runtime package.

## Decision and next experiment

256 MiB is the best provisional blocker footprint among those tested. Calibration is promising but not yet a demonstrated repeatable baseline: repeat the same parameters in fresh processes with a different condition/job order, keeping all samples. Do not proceed directly to capacity inference or label the smaller footprint timings as a measured cache/TLB capacity.

```bash
python3 scripts/run_rob.py --stage calibration --cpu 1 --numa-node 0 \
  --environment both --order-seed 2 --out results/v2-calibration-repeat --execute
```

Use a controlled idle sibling if the machine allocation mechanism permits it, and record the actual reservation using --sibling-state reserved-idle only when true. If the drift repeats, investigate it before adopting the blocker. If the baseline repeats sufficiently consistently for the intended resolution, proceed to the prefetch/layout and translation controls, followed by instruction-delivery and overhead controls.

## Reproduce the review

```bash
MPLCONFIGDIR=/tmp/rob-mpl python3 analysis/review_calibration.py results/v2-calibration
```

`summary.csv` preserves all descriptive statistics, sample counts and disturbance counts. Early/late comparison uses the first/last five samples; it is a descriptive drift metric, not a prevalidated universal acceptance threshold. `audit.json` retains mapping details, sibling counters and input hashes. `footprint-summary.png/.pdf` plots medians and observed p10–p90 bars on logarithmic axes. `large-footprint-samples.png/.pdf` shows all 128/256 MiB samples with context-switch deltas marked, using different panel y-scales. Bars are observed spread, not confidence intervals. No causal interpretation is assigned merely because a red marker coincides with a timing change.
