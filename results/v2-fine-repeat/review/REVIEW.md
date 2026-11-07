# Fine-sweep repeat and comparison

Both user-run repeat jobs completed, adding 1,980 samples to the first fine campaign's 1,980. CPU 1, memory bind:0, footprint/span 256 MiB, pointer seed 42, stride 64, one-byte NOPs, loop offset 0, 100,000 iterations, 15 samples per condition and N=448..576 step 4 are matched. The repeat changes condition-order seed from 1 to 2 and uses fresh processes. Source build `bcd9d621feed36f6` and all four manifest binary hashes match. The campaigns remain separate; no samples were pooled, excluded, or overhead-corrected.

## Repeated finding

The previously selected **492–500 NOP transition region repeats in native and SGX execution**. N=496 shows an intermediate timing, and N=500 approaches the dependent-load timing. No shift between native and enclave is resolved at the four-NOP sampling granularity.

Host TSC ticks per load, all-sample independent medians and ratios of separately collected mode medians:

| Environment | N | First independent | Repeat independent | First I/D | Repeat I/D |
| --- | ---: | ---: | ---: | ---: | ---: |
| Native | 492 | 179.55 | 180.02 | 0.643 | 0.638 |
| Native | 496 | 215.28 | 215.96 | 0.751 | 0.746 |
| Native | 500 | 288.09 | 289.73 | 1.001 | 1.004 |
| SGX | 492 | 214.67 | 223.14 | 0.566 | 0.621 |
| SGX | 496 | 274.12 | 284.81 | 0.763 | 0.786 |
| SGX | 500 | 365.20 | 368.36 | 0.985 | 0.994 |

Within each of the four environment/campaign combinations, all independent samples at N=492 are below all samples at N=496, and all at N=496 are below all at N=500. Thus the repeated feature involves entire sampled conditions, rather than a few isolated observations moving a median. Samples within a condition were consecutive; these ranges are descriptive evidence, not confidence intervals or a count of independent replications.

## Important exception: the largest jump is not always the transition

The native repeat's largest independent adjacent increase remains 496→500 under medians, minima and unflagged-median diagnostics. The repeated enclave curve has an isolated elevated N=548 condition: its median rises from 376.90 at N=544 to 528.79 at N=548, then falls to 379.41 at N=552. Its N=548 early/late medians change from 398.48 to 562.79 (+41.24%), while its minimum is 377.85. The first campaign's N=548 independent median is 376.22.

Consequently, **544→548 is the repeat enclave's largest all-sample and unflagged-median step**, while its largest minimum-based step remains 496→500. The spike is retained and is not assigned an unmeasured cause. It is not treated as a second capacity boundary: it is a peak rather than a persistent change and does not repeat at that spacing. Removing samples with recorded context switches does not resolve it. The first campaign likewise has other post-transition excursions. This is why the repeated overall shape and the preselected transition region matter more than automatically reporting the largest jump.

The earlier commentary's statement that the repeat's largest step stayed at 496→500 in both builds was corrected after the full-range summary exposed this exception. The artifacts preserve the actual global maxima.

## Quality and placement

The repeat contains no migration-tagged samples or major faults. Ten native dependent N=472 samples (IDs 0–9) contain 95 minor-fault increments; SGX has no ordinary fault increments. No ordinary faults occur at 492/496/500. The repeat has 541 samples with context-switch deltas (265 native, 276 SGX); the first has 524. Across both campaigns, all 3,960 samples remain in the results, including 16 faulted observations, 115 minor-fault increments, and 1,065 samples with context-switch deltas.

The repeat native data mapping has full 262144 KiB RSS, zero AnonHugePages, reported 4 KiB pages, and all 65,536 pages on node 0 at both snapshots. The first campaign has the same observed treatment. Physical EPC placement/residency remains unestablished. Sibling CPU 57 has nonzero coarse busy ticks in both environments and campaigns: first/repeat native 31/41, SGX 182/308. The sibling was not reserved. Frequency changes and interrupts/AEX remain incompletely observed; absence of a recorded delta is not proof of their absence.

## Consolidated interpretation and stopping point

The supported operational result is loss of independent-load overlap near **500 NOP instructions per load-to-load gap**, with an observed transition over the sampled N=492..500 region. This repeats across condition orders and both environments, alongside the earlier pointer-layout, frontend, page-policy and invocation-overhead controls. SGX changes absolute timing and variability without a resolved shift in this transition.

This is a ROB-sensitive **effective instruction-window measurement**. It does not uniquely determine total ROB entries. The loop's two loads, decrement/branch, wraparound, instruction/uop mapping, and possible coupled allocation limits still matter; `N`, `2N`, and `2N+4` must not be substituted for a hardware capacity without a justified model. A precise published hardware count must remain separate from this measured spacing. No further routine Artemisia runs are proposed for this evidence set. Remaining work is synthesis and, for the course's two-machine requirement, a separately validated experiment on another course machine.

See [the consolidated Artemisia findings](../../../ROB_RESULTS_ARTEMISIA.md).

## Reproduce the analysis

```bash
MPLCONFIGDIR=/tmp/rob-mpl python3 analysis/review_sweep.py results/v2-fine-repeat
MPLCONFIGDIR=/tmp/rob-mpl python3 analysis/compare_sweeps.py \
  results/v2-fine results/v2-fine-repeat --samples-at 492 496 500
```

The first command produces per-campaign summary/adjacent/sensitivity CSVs, mapping/input audit, and PNG/PDF plots. The second independently validates matched raw parameters and binary identities and saves `comparison/point-comparison.csv`, `largest-step-comparison.csv`, an audit with raw-evidence hashes, overlaid `curves.png/pdf`, and `transition-samples.png/pdf`. All selected raw independent observations are shown, with crosses for recorded fault/context-switch deltas. Shading is observed p10–p90, not a confidence interval. Campaigns are compared without pooling their samples.
