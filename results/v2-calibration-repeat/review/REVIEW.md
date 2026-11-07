# Artemisia calibration repeat and decision

The user completed all ten repeat jobs on CPU 1 with node-0 memory binding and order seed 2. This adds 300 raw samples to the first campaign's 300. Both campaigns used identical binary SHA-256 identities, identical workload parameters and pointer seed 42. Job/condition order and fresh process allocations changed. No samples were removed or pooled across campaigns.

## 256 MiB comparison

Median host TSC ticks per load (elapsed_ticks / 200,000), and descriptive within-run drift from the first-five median to the last-five median:

| Environment / mode | First median | Repeat median | Median change | First drift | Repeat drift |
| --- | ---: | ---: | ---: | ---: | ---: |
| Native independent | 136.47 | 139.80 | +2.44% | +4.81% | -0.01% |
| Native dependent | 278.23 | 277.90 | -0.12% | +0.42% | +0.31% |
| Enclave independent | 172.36 | 173.95 | +0.93% | +0.25% | +0.16% |
| Enclave dependent | 342.84 | 347.15 | +1.26% | +0.10% | -0.38% |

The native independent settling trend did not recur. All four repeat conditions have an absolute early/late change below 0.4%, and their medians differ from the first campaign by less than 2.5%. The repeat's dependent/independent ratio is approximately 1.99 for native and 2.00 for enclave execution. This supports useful memory-level overlap and a sufficiently repeatable working baseline for the next experimental controls. It is not a universal precision guarantee or an inferred ROB capacity.

The smaller large-footprint cases remain less attractive: native dependent 128 MiB drift is +9.76% in the repeat, following +13.82% initially. Several 64 MiB medians differ substantially between campaigns (up to about 21%). Retain these observations rather than using them as interchangeable blocker conditions.

## Recorded controls and limitations

Native data mappings again have 4 KiB pages, zero AnonHugePages and all reported resident data pages on node 0 before/after measurement. Both manifests retain the same requested CPU/node policy and an uncontrolled sibling label. Sibling CPU 57 has coarse busy ticks in nine of the ten repeat jobs; these whole-job observations cannot identify activity within individual samples or prove an idle sibling.

The repeat has zero migration-tagged samples, zero samples with ordinary page-fault deltas and 31 with context-switch deltas; the two campaigns together have 600 samples and 66 with context-switch deltas. All are retained. Active frequency, SGX exit/reclamation behavior and physical EPC placement are not proven controlled by these metadata. Native and SGX mapping observations must not be interpreted as equivalent residency accounting.

## Next stage

Adopt 256 MiB as the working baseline for prefetch/layout controls, while retaining the first-run drift and remaining hardware-control limitations in subsequent interpretation. Run the full spacing control sweep using three pointer permutations at stride 64 and a stride-128 layout with pointer seed 42. The latter doubles address span while retaining the explicitly visited line footprint; a change therefore signals layout sensitivity and cannot alone identify prefetching rather than translation or physical placement.

```bash
python3 scripts/run_rob.py --stage prefetch --cpu 1 --numa-node 0 \
  --environment both --footprint-mib 256 --out results/v2-prefetch --execute
```

This prepares eight jobs: four cases in native and hardware-debug enclave execution, N=0..1024 in steps of 32, with both dependency modes. No capacity estimate follows until the layout, translation, instruction-delivery and timing-overhead controls have been assessed.

## Reproduce

```bash
MPLCONFIGDIR=/tmp/rob-mpl python3 analysis/review_calibration.py results/v2-calibration-repeat
MPLCONFIGDIR=/tmp/rob-mpl python3 analysis/compare_calibrations.py results/v2-calibration results/v2-calibration-repeat
```

The per-campaign summary and mapping audit are summary.csv and audit.json. The comparison preserves campaign separation in comparison.csv and hashes its raw inputs in comparison-inputs.json. The PNG/PDF 256MiB-comparison figures show both campaigns' full sample sequences; crosses mark recorded context-switch deltas, not a proven cause of a timing variation. Each panel has its own y-scale. These are descriptive repeated observations, not confidence intervals or independent hardware reservations.
