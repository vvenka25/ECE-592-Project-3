# Instruction-width and loop-alignment control

Follow-up: the overhead campaign below is now complete; see [its review](../../v2-overhead/review/REVIEW.md) for the current decision and next fine-spacing command. The frontend findings and historical next-stage command remain recorded here.

The user completed all 16 frontend jobs on Artemisia: 15,840 samples, CPU 1, requested memory node 0, method `rob-v2`, source build `bcd9d621feed36f6`. The manifest's four binary hashes match the preceding strict translation campaign. Each job uses pointer seed 42, stride 64, 100,000 iterations, 15 samples per condition, order seed 1, and N=0..1024 in steps of 32. The analyzer checks raw workload parameters against the manifest. Original measurements and binaries were not changed by this review.

At each of two footprints (16 KiB and 256 MiB), the variants are a baseline one-byte NOP with loop offset 0, a two-byte NOP with offset 0, and one-byte NOPs with offsets 16 and 32 within a 64-byte aligned region. Native and hardware-debug SGX use the shared assembly kernels. These are one-factor comparisons with the baseline; the campaign does not cross every NOP width with every alignment.

## Main observation

Every 256 MiB variant retains its largest independent adjacent median increase between the sampled spacings **N=480 and N=512**. Doubling NOP encoding width does not halve the observed NOP-count location, and moving the loop start does not move it outside this coarse interval.

All-sample medians, host TSC ticks per load; ratios divide separate independent and dependent medians:

| Environment | NOP bytes / loop offset | Independent N=480 | Independent N=512 | I/D at 480 | I/D at 512 |
| --- | --- | ---: | ---: | ---: | ---: |
| Native | 1 / 0 | 176.18 | 287.92 | 0.634 | 0.995 |
| Native | 2 / 0 | 179.54 | 287.84 | 0.647 | 0.988 |
| Native | 1 / 16 | 176.46 | 286.77 | 0.639 | 1.000 |
| Native | 1 / 32 | 176.43 | 287.46 | 0.636 | 0.999 |
| SGX | 1 / 0 | 209.68 | 352.32 | 0.613 | 0.999 |
| SGX | 2 / 0 | 209.90 | 353.85 | 0.611 | 1.004 |
| SGX | 1 / 16 | 210.50 | 353.76 | 0.614 | 0.995 |
| SGX | 1 / 32 | 210.39 | 353.74 | 0.612 | 1.001 |

The step is about 108–112 ticks/load natively and 143–144 in SGX. The same largest-step interval persists in the sample minima and in separately calculated medians from samples without recorded fault/context-switch deltas. These are sensitivity diagnostics, not replacements for the all-sample estimates; unflagged observations can still contain interruptions or other perturbations.

The 16 KiB curves rise approximately linearly with N and show no comparable discontinuity at 480–512: their independent medians increase by only 3.66–4.42 ticks/load across that interval. Independent and dependent timings are already close by N=480. This is consistent with an instruction-throughput cost when loads are fast. It helps distinguish that ordinary cost from the much larger overlap loss with slow loads. It does not identify which frontend path supplies instructions.

The combined evidence supports an instruction-window candidate whose coarse location survives the tested byte-layout changes. It does not prove that all frontend effects are absent, distinguish every possible resource constraint, or establish a total ROB entry count. A feature can shift within the 32-NOP sampling interval without being resolved here. Fine sampling, repetition, and instruction/uop accounting remain necessary.

## Placement and sample quality

All eight native mappings have the requested size and full RSS, AnonHugePages=0, 4 KiB reported page size, and all reported data pages on node 0 before and after. Large mappings have 65,536 pages; small mappings have four. SGX EPC placement/residency cannot be established from the device mappings, and native binding does not prove matching EPC placement.

There are zero migration-tagged samples and zero major faults. Eighteen samples contain 255 minor-fault increments in total; 2,668 samples have context-switch deltas. Faulted conditions are:

- Native, 256 MiB, two-byte NOP: N=448 independent, sample IDs 6–14.
- Native, 256 MiB, baseline: N=512 dependent, sample IDs 5–8.
- Native, 16 KiB: isolated faults in baseline N=1024 independent, two-byte NOP N=96 dependent, and offset-32 N=928 independent.

All samples remain in the primary curves. The 256 MiB baseline SGX N=0 dependent median is elevated (407.05 ticks/load, versus roughly 343 in the other three variants); it is not explained away by dropping samples with recorded switches. Other isolated excursions remain, including the wide-NOP SGX independent curve around N=736. Neither is interpreted as a capacity boundary. Sibling CPU 57 has nonzero coarse busy ticks in 15 of 16 jobs and was not reserved. Frequency, interrupts/AEX, and other activity remain possible timing influences; these observations do not identify their causes.

## Decision and next experiment

Continue with the original 256 MiB, one-byte NOP, offset-0 configuration for the main local experiment. The tested frontend controls do not require a new kernel. Next measure host call/ECALL overhead and batch-length sensitivity using the existing overhead stage:

```bash
python3 scripts/run_rob.py \
  --stage overhead \
  --cpu 1 --numa-node 0 \
  --environment both \
  --out results/v2-overhead \
  --execute
```

This prepares eight jobs: native/enclave at N=0, a 16 KiB footprint, and batch lengths 0, 1,000, 10,000, and 100,000 iterations, with 15 samples in each mode. Report zero-work controls in total TSC ticks per invocation; never divide them by a load count. Compare longer batches before deciding whether any overhead correction is warranted. Do not assume a zero-work ECALL estimates every cost of a nonzero enclave measurement. The next command was checked in planning mode; this review did not execute it. Coarse/fine repeat measurements remain after overhead review.

## Reproduce and inspect

```bash
MPLCONFIGDIR=/tmp/rob-mpl python3 analysis/review_sweep.py results/v2-frontend
```

The review includes `summary.csv`, `adjacent-changes.csv`, `largest-adjacent-changes.csv`, `largest-sensitivity-changes.csv`, and `audit.json`, plus combined and footprint-specific PNG/PDF figures. Use `curves-262144KiB` and `relative-timing-262144KiB` for the slow-load candidate, and `curves-16KiB` for the fast-load control. Shading is the observed p10–p90 range, not a confidence interval. The audit hashes the original CSVs and manifest and records native mapping snapshots. Different campaigns and footprints are not pooled.
