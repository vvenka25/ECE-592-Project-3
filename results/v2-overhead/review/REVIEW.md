# Host call and ECALL overhead control

Follow-up: the first fine sweep below is now complete; see [its review](../../v2-fine/review/REVIEW.md) for the measured transition and next repeat command. The overhead findings and historical next-stage command remain recorded here.

The user completed all eight jobs (240 samples) on Artemisia, CPU 1, memory bind:0, source build `bcd9d621feed36f6`. All four manifest binary hashes match the frontend campaign. Each job uses a 16 KiB footprint, seed 42, stride 64, one-byte NOP encoding, loop offset 0, N=0, order seed 1, and 15 samples per mode. Only batch length changes within each environment: 0, 1,000, 10,000, or 100,000 iterations. Original raw observations and benchmark binaries remain unchanged.

## Observed timing

All-sample medians:

| Iterations | Native independent | Native dependent | SGX independent | SGX dependent | Units |
| ---: | ---: | ---: | ---: | ---: | --- |
| 0 | 70 | 74 | 10,758 | 10,764 | Total host TSC ticks per invocation |
| 1,000 | 1.8910 | 3.7470 | 7.4880 | 9.2570 | Host TSC ticks per load |
| 10,000 | 1.8600 | 3.7152 | 2.4015 | 4.2767 | Host TSC ticks per load |
| 100,000 | 1.8562 | 3.7129 | 1.9130 | 3.7741 | Host TSC ticks per load |

Zero iterations execute no timed pointer-chase loads, so their timings are never normalized per load. They still include the host timer brackets and dispatch/cursor/return path; the SGX invocation also includes ECALL transition and SDK/marshalling costs. The SGX value is not a measurement of a hardware transition alone. Initialization and warm-up remain outside the timed bracket, including in zero-work jobs.

The large short-batch SGX penalty decreases as work per invocation increases. At the main 100,000-iteration batch length, dividing the zero-work median by 200,000 loads gives a scale of 0.05379 ticks/load for independent SGX and 0.05382 for dependent SGX. Native scales are 0.00035 and 0.00037 ticks/load. The SGX scale is still 2.81%/1.43% of these fast-load timings, so it should not be ignored when discussing small native/enclave differences in the 16 KiB control.

For comparison, the previously recorded 256 MiB frontend campaign's SGX independent step at 480–512 is about 143–144 ticks/load. The measured zero-work cost scale is under 0.04% of that change. Thus this fixed-cost scale cannot explain the large step on its own. This is a scale comparison, not a claim that every cost of a nonzero large-footprint invocation is bounded by its zero-work cost.

As a diagnostic, the slope between 10,000 and 100,000 iterations, computed as the difference of the two median total timings divided by the difference in executed load counts, is:

| Environment | Independent | Dependent | Units |
| --- | ---: | ---: | --- |
| Native | 1.85574 | 3.71263 | Incremental host TSC ticks per load |
| SGX | 1.85870 | 3.71824 | Incremental host TSC ticks per load |

These close incremental timings support dilution of a mostly fixed invocation cost in this fast-load control. They are differences of separately collected medians, not paired observations or a fitted confidence interval. Similarly, subtracting the corresponding zero-work median gives independent SGX diagnostic values of 1.86360 and 1.85919 ticks/load at 10,000 and 100,000 iterations. The 1,000-iteration value is 2.10900, so exact constant-cost subtraction is not assumed across all batch lengths.

## Quality and decision

All 240 observations have status `ok`, with zero ordinary fault and context-switch deltas. All four native arenas have full 16 KiB RSS, zero AnonHugePages, reported 4 KiB pages, and four pages on node 0 before and after. Actual EPC placement remains unestablished. Sibling CPU 57 has nonzero coarse busy ticks in the 1,000- and 100,000-iteration SGX jobs; it was not reserved. The measured brackets do not establish the absence of interrupts/AEX or frequency changes. Occasional longer observations remain visible, including SGX 100,000-iteration tails, and all are retained.

Keep 100,000 iterations for the next main sweep and keep primary timings uncorrected. The zero-work subtraction and incremental slopes are supporting diagnostics only. This stage measures N=0 with cache-resident data; it does not establish complete batch-length independence for every large-footprint/N condition or resolve every microarchitectural attribution issue. It does not infer ROB capacity.

The prior repeated full-range spacing controls already give a coarse 480–512 bracket, so the next experiment can use the existing fine stage over a wider surrounding interval rather than duplicate a full-range coarse sweep:

```bash
python3 scripts/run_rob.py \
  --stage fine \
  --cpu 1 --numa-node 0 \
  --environment both \
  --footprint-mib 256 \
  --lo 448 --hi 576 \
  --out results/v2-fine \
  --execute
```

This prepares two jobs, 33 spacings in steps of four, two modes and 15 samples per point: 1,980 samples total. The range includes pre- and post-transition shoulders. The command was checked in planning mode; this review did not execute the campaign. Review its raw curves before an independent repeat with order seed 2 and a fresh output directory. Repetition, instruction/uop accounting, and remaining attribution limits must precede any exact capacity conclusion.

## Reproduce the review

```bash
MPLCONFIGDIR=/tmp/rob-mpl python3 analysis/review_overhead.py results/v2-overhead
```

`summary.csv` retains the separate modes and batch lengths, total timing statistics, nonzero-work normalization, and explicitly labeled zero-work diagnostics. Zero-work per-load fields are blank. `long-batch-slopes.csv` contains the two-longest-batch diagnostics. `audit.json` hashes the original manifest, CSVs, logs, platform records, and memory snapshots and records placement and disturbance counts. `batch-timing.png/pdf` separates total and normalized timing; `zero-work-samples.png/pdf` shows every zero-work observation. Bands are observed p10–p90, not confidence intervals. No raw data, conditions, or campaigns are pooled or excluded.
