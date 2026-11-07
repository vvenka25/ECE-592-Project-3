# Partial campaign: placement gate failed

This first measurement attempt stopped after job 31 of 36. That job,
`Q2-r2-overlap-cold-k64-native`, returned successfully, but its pre-timing
`numa_maps` snapshot accounted for only 65,534 of the expected 65,536 pages.
The VMA size and RSS were complete, all accounted pages were on node 0, and
the post-timing snapshot accounted for all pages. The cause of the transient
two-page discrepancy is not established. The strict placement treatment is
therefore **unverified**, and this campaign is not used as completed evidence.

All collected rows and snapshots remain intact. No row was removed or
retrospectively relabeled as passing. A fresh, identically configured
campaign is recorded separately in `results/q2-artemisia-retry/`; it uses the
same placement gate. The retry was triggered by the declared control failure,
before inferring the Q2 timing result, rather than by its timing values.
