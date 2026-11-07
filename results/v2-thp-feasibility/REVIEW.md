# NUMA-specific huge-page feasibility

After the user's node-0 strict-collapse failure, Codex ran short native checks under explicit memory binding, CPU 1, pointer seed 42, 100 timed iterations, one sample per dependency mode and N=0. These are allocation diagnostics, not ROB capacity measurements. Logs, successful mapping snapshots and manifest.json preserve each result. Every allocation was released by its process before the next check.

| Requested memory node | Footprint | Result |
| --- | ---: | --- |
| 0 | 64 MiB | MADV_COLLAPSE returned ENOMEM; no timed samples |
| 0 | 128 MiB | MADV_COLLAPSE returned ENOMEM; no timed samples |
| 0 | 256 MiB | MADV_COLLAPSE returned ENOMEM; no timed samples |
| 1 | 256 MiB | Full AnonHugePages coverage verified before/after; all mapped pages reported on node 1 |

The previous successful unbound 256 MiB functional check did not validate the node-0 policy: its saved numa_maps line reports 22 MiB on node 0 and 234 MiB on node 1. That earlier result established functional collapse/verification, while this matrix establishes the observed NUMA-bound feasibility. The saved placement evidence is earlier-unbound-placement.json and its source snapshot. Memory availability may change over time; none of these checks promises future allocation success.

Read-only buddy/memory snapshots are retained. At the before snapshot node 0's Normal zone had no free order-9/order-10 blocks while node 1's Normal zone did. This is consistent with NUMA-local high-order allocation constraints; it is not a proof that fragmentation was the only cause or that all zone/cgroup constraints were eliminated. A large global MemAvailable value or zero reserved HugePages_Free is not a conclusive test of anonymous THP feasibility.

The selected workaround is a separate native page-policy comparison on CPU 1 with **both** mappings bound to node 1. CPU 1 belongs to node 0, so this is a remote-NUMA control, explicitly labeled and not pooled with local-node timing baselines. See ../v2-translation-node1/review/REVIEW.md. No host-wide memory policy, core state or firmware setting was changed.
