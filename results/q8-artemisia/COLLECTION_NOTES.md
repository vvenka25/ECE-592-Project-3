# No measurement samples: controller/preflight integration attempt

This attempt created its manifest/source snapshot but stopped at the
preserved preflight helper's allowed-affinity check before starting any
benchmark job. Collector isolation had narrowed the inherited helper mask.
The helper is now additionally allowed onto the selected benchmark CPU only
for before/after checks, while its SMT sibling stays excluded. Q4's helper
source remains unchanged. A fresh corrected Q8 collection is separate.
