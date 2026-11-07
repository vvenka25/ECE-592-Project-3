# Artemisia pointer-layout control review

All eight prefetch/layout jobs completed successfully: three pointer seeds (42, 271828, 314159) at stride 64, plus seed 42 at stride 128, each native and hardware-debug enclave. Each job has 33 spacing points (N=0..1024, step 32), two dependency modes and 15 samples per mode/point: 7,920 observations in total. Binary identities match the preceding calibration campaigns, and raw samples share build ID 3547cc1ae6021325. All observations remain in the primary summaries.

## Shared transition

Every case has its largest adjacent increase in independent-chain median timing between N=480 and N=512. These are sampled NOP spacings, not an inferred interval of exact ROB entry counts. At N=512 the independent and dependent medians converge, consistent with loss of useful overlap:

| Environment / layout | Independent N=480 | Independent N=512 | Dependent N=512 | Independent/dependent at N=512 |
| --- | ---: | ---: | ---: | ---: |
| Native seed 42, stride 64 | 176.8 | 287.2 | 287.6 | 0.999 |
| Native seed 271828, stride 64 | 177.2 | 286.8 | 287.0 | 0.999 |
| Native seed 314159, stride 64 | 176.5 | 287.4 | 287.4 | 1.000 |
| Native seed 42, stride 128 | 180.9 | 297.1 | 296.4 | 1.002 |
| Enclave seed 42, stride 64 | 210.2 | 354.2 | 355.3 | 0.997 |
| Enclave seed 271828, stride 64 | 210.0 | 353.2 | 354.1 | 0.997 |
| Enclave seed 314159, stride 64 | 210.8 | 354.8 | 354.5 | 1.001 |
| Enclave seed 42, stride 128 | 218.6 | 369.6 | 370.9 | 0.996 |

Times are host TSC ticks per load, elapsed_ticks / 200,000. The independent adjacent increase is about 110–116 ticks/load native and 143–151 enclave, while the dependent curve increases by much less across the same interval. The independent/dependent ratio is approximately 0.5 at N=0, grows gradually with filler work, and approaches 1 after the sharp transition. The gradual rise is not itself a ROB capacity measurement.

The common transition is unlikely to be an accident of one pointer permutation. It survives the tested spatial layout too, despite that layout changing absolute timing. This is evidence supporting an instruction-window hypothesis; it does not demonstrate that all prefetching is absent or distinguish ROB allocation from every instruction-delivery/resource effect.

## Layout and mapping effects

At N=0, increasing stride from 64 to 128 raises independent median time by about 4.6% native and 5.4% enclave; dependent time rises about 3.8% and 4.9%. The fully traversed explicitly visited line footprint remains 256 MiB, but address span grows from 256 to 512 MiB. That changes translation pressure and physical placement as well as possible neighboring-line prefetch effects. A timing difference between these layouts cannot be assigned to a prefetcher without the next translation control.

Native smaps/numa_maps snapshots verify 4 KiB pages, zero AnonHugePages, full resident spans of 256/512 MiB as applicable, and node-0 data placement before and after. The 512 MiB resident span at stride 128 includes entire resident pages, even though only alternate cache lines are explicitly visited. SGX device mappings do not establish physical EPC node placement or available EPC.

## Disturbance sensitivity

There are zero migration-tagged samples, ten samples with minor-fault deltas (135 minor faults total, zero major faults) and 2,103 samples with context-switch deltas. The faulted conditions are native seed 314159 independent at N=32, and native stride 128 dependent at N=160. No faulted samples occur at any tested spacing from N=448 through N=576. Fault counters bracket a slightly wider region than the timer; they are not proof that a pointer-chase load itself faulted.

As a sensitivity diagnostic, recomputing each condition's median from samples without recorded faults or context switches leaves 480->512 as the largest independent adjacent increase in all eight jobs. Those diagnostic medians are recorded separately; they do not replace the primary all-sample results. All-sample independent minima also retain a large increase at that interval. This reduces the likelihood that the common step consists solely of occasional recorded disturbances. Interrupts without a context switch, active frequency variation, and SMT effects remain possible; sibling CPU 57 shows nonzero whole-job busy ticks in every job. No exact hardware capacity is claimed.

## Decision and next experiment

Keep 256 MiB as the working footprint. The transition passes the tested pointer-seed/layout sensitivity controls at the coarse resolution. Proceed to native page-policy controls, with an enclave baseline under the same other parameters:

```bash
python3 scripts/run_rob.py --stage translation --cpu 1 --numa-node 0 \
  --environment both --footprint-mib 256 --out results/v2-translation --execute
```

This runs three jobs: native 4K policy, native huge-page advice and an enclave baseline. Confirm actual native huge-page backing in smaps before interpreting the comparison; successful MADV_HUGEPAGE advice is not proof that huge pages were allocated. Check whether baseline timing and the transition change with translation conditions. Then perform instruction-width/alignment and overhead controls before fine-spacing inference. A persistent feature near a published capacity is not a substitute for those controls or loop/uop accounting.

## Reproduce

```bash
MPLCONFIGDIR=/tmp/rob-mpl python3 analysis/review_sweep.py results/v2-prefetch
```

`summary.csv` records every condition's median, min/max, p10/p90, early/late comparison and disturbance counts. `adjacent-changes.csv` and `largest-adjacent-changes.csv` describe observed steps, not automatic capacity estimates. `audit.json` records input hashes and mapping observations. `curves.png/.pdf` plots all-sample medians with observed p10–p90 bands, not confidence intervals. `relative-timing.png/.pdf` plots ratios of separate medians, not paired-sample ratios. Panel y-scales may differ, as stated on the figures.
