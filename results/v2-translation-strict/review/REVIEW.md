# Local strict translation campaign: preserved partial result

The user's campaign successfully completed the hardware-debug enclave baseline (990 samples), then stopped when native 256 MiB MADV_COLLAPSE under memory bind:0 returned ENOMEM. The failed condition emitted no timing samples. The native 4K job was not started. The original manifest, CSV and diagnostics remain as recorded; no full page-size comparison can be made within this incomplete campaign.

A completed-job review can be reproduced explicitly:

```bash
MPLCONFIGDIR=/tmp/rob-mpl python3 analysis/review_sweep.py results/v2-translation-strict --completed-only
```

The review keeps the campaign labeled incomplete and lists failed/unstarted jobs. The completed enclave observations are not discarded, but they contain notable variability: N=608 independent median is 596.47 ticks/load (minimum 365.87) versus 367.84 at N=576, making 576->608 the largest adjacent median increase in this noisy run. It falls back to 375.82 at N=640. This later excursion must not automatically be interpreted as a second capacity boundary. The recurring candidate step is also present: independent median 210.23 at N=480 versus 360.32 at N=512. No exact ROB estimate follows from this run.

There are zero migration-tagged and ordinary-fault-delta samples in this enclave job, and 281 samples with context-switch deltas. Sibling CPU 57 has 217 busy ticks over the whole job; those coarse observations do not establish when interference occurred. Interrupts, frequency changes and other effects remain possible and are not assigned as proven causes.

Further native feasibility checks could not obtain full THP under node-0 binding at 64, 128 or 256 MiB, but could at 256 MiB under node-1 binding. The earlier unbound successful probe had placed most data on node 1. See ../../v2-thp-feasibility/REVIEW.md for the evidence and scope of this diagnosis. Rather than repeatedly rerunning the local failed campaign, a separately labeled native pair was collected with memory bound to node 1 for both page policies; see ../../v2-translation-node1/review/REVIEW.md. Physical EPC node placement remains unverified, so the remote native pair is not presented as a matched remote enclave timing comparison.
