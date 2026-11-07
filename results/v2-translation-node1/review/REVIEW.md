# Native page-policy control with memory on node 1

Codex executed this native-only control after the user's full-THP request under node-0 binding failed. It comprises two complete jobs (1,980 samples), CPU 1, memory bind:1, 256 MiB footprint/span, pointer seed 42, stride 64, identical assembly parameters and the same native binary/source build as the failed local campaign (build ID bcd9d621feed36f6). Only native page policy changes within this pair. This is an explicitly remote-NUMA control because CPU 1 is on node 0; do not pool its absolute timings with local-node baselines or assert equivalent enclave placement.

## Verified treatment

Both mappings show all 65,536 reported 4K-accounting pages on node 1 before/after. In the collapse case AnonHugePages=262144 KiB, matching the entire 256 MiB mapping at both boundaries. In the small-page case AnonHugePages=0. The collapse log also records successful full-coverage checks before and after execution. Actual page treatment is therefore much stronger than the earlier 6/256 MiB advice-only allocation. Boundary snapshots still do not prove backing was constant at every intermediate instant.

All-sample medians, host TSC ticks per load:

| Condition | Independent N=0 | Dependent N=0 | Independent N=480 | Independent N=512 | Dependent N=512 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 4K policy, node 1 | 230.99 | 460.28 | 268.92 | 470.13 | 469.39 |
| Full THP, node 1 | 217.90 | 437.82 | 258.08 | 445.69 | 445.93 |

Both cases' largest independent adjacent median increase is between the sampled spacings N=480 and N=512. The independent/dependent ratio changes from 0.584 to 1.002 for 4K and from 0.591 to 0.999 for THP. Thus the tested full page-size change affects absolute time but preserves the observed coarse overlap-loss location. This supports the instruction-window hypothesis under this control; it neither infers TLB size nor proves that translation was the only source of the timing difference. Huge pages also change physical packing/placement details.

There are zero migration-tagged and ordinary-fault-delta samples and 712 samples with context-switch deltas. All 1,980 observations remain in the primary results. Separately computed medians from samples without those recorded disturbances preserve the same largest adjacent step in both cases. Sibling CPU 57 still has nonzero busy ticks (39 over the huge-page job, 99 over the 4K job); its activity is not controlled. Frequency and interrupts/SGX behavior are not fully established by these data. The existing local enclave comparison remains separate.

## Decision and next stage

The native page-size sensitivity control is usable under its recorded remote placement. Keep the local 256 MiB, 4K-policy configuration for the main instruction-width/alignment experiment, since the required pages there are available and those local baselines already exist. Preserve the local huge-page allocation failure as a limitation rather than repeatedly requiring the unavailable treatment.

```bash
python3 scripts/run_rob.py --stage frontend --cpu 1 --numa-node 0 \
  --environment both --footprint-mib 256 --out results/v2-frontend --execute
```

This comprises cache-resident and 256 MiB cases, one-/two-byte NOP encodings and loop offsets 0/16/32, each native and enclave. Check whether the overlap-loss location tracks instruction count or changes with byte layout; use the small-footprint curves to identify competing instruction-throughput effects. Overhead and fine-spacing validation remain after that stage. No exact ROB capacity is claimed yet.

## Reproduce this review

```bash
MPLCONFIGDIR=/tmp/rob-mpl python3 analysis/review_sweep.py results/v2-translation-node1
```

The review directory contains summary and adjacent-change CSVs, an input/mapping audit and PNG/PDF curves and relative-timing plots. No enclave curve is synthesized for this native-only campaign. Bands represent observed p10–p90, not confidence intervals, and ratios divide separate condition medians rather than paired sample values.
