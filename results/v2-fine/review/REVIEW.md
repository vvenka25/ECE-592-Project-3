# First fine-spacing sweep

Follow-up: the matched repeat below is now complete. See [its review](../../v2-fine-repeat/review/REVIEW.md) and [the consolidated Artemisia findings](../../../ROB_RESULTS_ARTEMISIA.md). This first campaign's findings and historical repeat command remain recorded here.

Both user-run jobs completed: 1,980 samples on Artemisia, CPU 1, memory bind:0, 256 MiB footprint/span, pointer seed 42, stride 64, one-byte NOPs, loop offset 0, 100,000 iterations and 15 samples per condition. N ranges from 448 through 576 in steps of four. Order seed is 1. Source build is `bcd9d621feed36f6`; all four manifest binary hashes match the overhead and frontend campaigns. Native and enclave results remain separate. Original observations and benchmark code/binaries were not changed by this review.

## Transition resolved within the coarse bracket

Both environments retain lower independent timing at N=492, show a partial rise at N=496, and reach approximately the dependent timing at N=500. The largest adjacent independent increase is **496→500** in all-sample medians, sample minima, and separately labeled unflagged-sample medians.

All-sample medians, host TSC ticks per load:

| Environment | NOPs per gap | Independent | Dependent | Independent/dependent |
| --- | ---: | ---: | ---: | ---: |
| Native | 492 | 179.55 | 279.27 | 0.643 |
| Native | 496 | 215.28 | 286.55 | 0.751 |
| Native | 500 | 288.09 | 287.76 | 1.001 |
| SGX | 492 | 214.67 | 379.20 | 0.566 |
| SGX | 496 | 274.12 | 359.38 | 0.763 |
| SGX | 500 | 365.20 | 370.80 | 0.985 |

The largest step is 72.81 ticks/load natively and 91.08 in SGX. It is preceded by another rise from 492→496, so the overall observed change should be described as a **492–500 NOP transition region**, rather than reduced to the largest four-NOP step alone. This refines the earlier sampled 480–512 bracket. It is a descriptive interval in the tested parameter, not a confidence interval or an established ROB-entry count.

Every independent observation at these three points falls into separated timing ranges within each environment:

| Environment | N=492 observed min–max | N=496 observed min–max | N=500 observed min–max |
| --- | ---: | ---: | ---: |
| Native | 178.99–182.62 | 214.86–217.30 | 287.57–294.13 |
| SGX | 211.92–219.97 | 268.03–279.39 | 360.59–379.54 |

This supports a change involving the whole sampled condition, rather than a median moved by one isolated slow observation. The samples within each condition were consecutive and do not constitute independent campaign replications. The unflagged median is only a sensitivity diagnostic: unrecorded interrupts or other activity can remain.

## Noise, placement and accounting limits

The native post-transition curve is relatively smooth; the SGX curve has substantial excursions, including independent N=524 and N=536 and dependent points elsewhere. Independent/dependent ratios can consequently fall below one again after N=500. The two modes were collected separately, and such ratios do not establish restored overlap or another capacity boundary. Absolute SGX timing is also higher and more variable than in the preceding frontend campaign. Retain this campaign separately; do not pool it with that earlier campaign or silently remove elevated observations.

There are zero migration-tagged samples. Six native dependent N=516 samples (IDs 8, 9, 10, 12, 13, 14) contain 20 minor-fault increments in total; no major faults are recorded. No ordinary faults occur at the key 492/496/500 points. There are 524 samples with context-switch deltas (232 native, 292 SGX). All 1,980 samples remain in the primary results. Sibling CPU 57 was uncontrolled and records 31 busy ticks over the native job and 182 over the SGX job. These observations do not identify a cause for the SGX variability or exclude interrupts/AEX and frequency changes.

The native arena has full 262144 KiB RSS, zero AnonHugePages, reported 4 KiB pages, and all 65,536 data pages on node 0 before and after. EPC placement/residency remains unestablished. The previous remote-node full-THP comparison remains a separate control.

N counts NOP instructions in each load-to-load gap. The shared loop contains **2N NOPs, two loads, a decrement, and a conditional branch per iteration**. The wraparound gap includes loop control. Guard/padding/cursor stores/return are outside the loop. Counting the full loop's `2N+4` architectural instructions as the ROB capacity, or directly calling N=500 a 500-entry ROB, would be unjustified. Instruction/uop accounting, resource attribution, and the distinction between an effective overlap limit and total ROB size remain necessary.

## Next: independent repeat with changed condition order

Repeat the same range and workload in fresh processes with order seed 2. Keep pointer seed 42 and all other controlled parameters unchanged so the comparison tests repeatability and collection-order sensitivity. The existing runner randomizes the (N, mode) condition order; it does not reserve the SMT sibling or control other users' workloads.

```bash
python3 scripts/run_rob.py \
  --stage fine \
  --cpu 1 --numa-node 0 \
  --environment both \
  --footprint-mib 256 \
  --lo 448 --hi 576 \
  --order-seed 2 \
  --out results/v2-fine-repeat \
  --execute
```

This is two jobs and another 1,980 samples. Review both campaigns separately, compare the 492/496/500 region and the raw disturbance/drift evidence, and check whether the SGX variability persists. The command was checked in planning mode; this review did not execute the repeat. A matching repeat would strengthen the measured transition claim; it would not automatically settle every resource-attribution question.

## Reproduce the review

```bash
MPLCONFIGDIR=/tmp/rob-mpl python3 analysis/review_sweep.py results/v2-fine
```

`summary.csv` retains every point's statistics and disturbance counts. `adjacent-changes.csv` and `largest-sensitivity-changes.csv` expose the descriptive step and estimator sensitivity. `audit.json` records input CSV/manifest hashes and mapping evidence. `curves.png/pdf` and `relative-timing.png/pdf` preserve the noisy SGX points. Bands are observed p10–p90 ranges, not confidence intervals; ratios divide separate condition medians. No exact ROB capacity has been inferred.
