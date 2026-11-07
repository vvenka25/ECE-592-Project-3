# Partial coarse campaign: exact snapshot-accounting gate failed

This attempt stopped at job 13 (`Q5-r2-gpr-lea1-native`). Its before
`numa_maps` snapshot accounted for 65,524 of 65,536 pages, despite a full RSS
and VMA; the after snapshot accounted for all pages. All accounted pages were
on node 0. Warming before the initial snapshot did not eliminate this
accounting discrepancy. The cause is unresolved, and this attempt is not
completed measurement evidence. All rows and source/binary snapshots remain.

Subsequent collections use read-only per-page node queries (`move_pages`
with `nodes=NULL`) as the exact resident/local-page inventory, while retaining
the original snapshots. They still require every page to be present locally
and no THP. This is a different recorded placement-verification method, not
retroactive approval of this partial campaign. Fresh final coarse/fine
measurements belong in separately named directories.
