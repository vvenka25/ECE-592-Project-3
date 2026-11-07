# Partial pilot: placement gate failed

The first scaled-index pilot stopped after job 3. The native dependent-load
job's immediate post-allocation snapshot accounted for 65,531 of 65,536 pages;
its RSS and VMA size were complete, and the after snapshot accounted for all
pages. The exact cause is not established. The existing gate rejected this
unverified placement; the partial raw observations are preserved and are not
completed measurement evidence.

The revised host observes the pre-run mapping after an initial untimed warm-up,
then warms each condition again after the snapshot. The exact page-count and
local-node gate remains unchanged. A separate fresh pilot validates that
readiness protocol and the scaled-index treatment.
