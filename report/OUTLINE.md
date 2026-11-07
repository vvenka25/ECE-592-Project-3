# Report outline

> GitHub checkout: first follow [REPRODUCING.md](../REPRODUCING.md) and run `python3 data/unpack_results.py` from the project root to restore raw evidence. Public preservation uses the source-only Q4 derivative; the full original archive and submission ZIP remain unchanged locally.

First page: **Homework 3, Track B — Q1, Q2, Q3, Q4, Q5, Q8 — 105 points**.
Author: **Varunaditya Venkatesan**. The report includes native evidence on both machines, applicable Artemisia hardware-SGX comparisons and the qualified conclusions below.

1. Machines and common protocol: Charnwood i7-6700/Skylake and Artemisia Xeon Gold 5420+/Sapphire Rapids; current topology/affinity, Artemisia offline sibling and Charnwood private core scheduling, controller isolation, local NUMA verification, toolchain/SDK/runtime, separate host timer checks, native core-cycle diagnostics, warm-up and raw metadata.
2. Q3 (10): branch patterns and matched work, retained conditional-branch assembly, branchless sensitivity control, timing and optional miss-counter evidence; native/native and Artemisia enclave comparisons.
3. Q1 (10): one dependency chain vs several chains at fixed instruction count, latency and reciprocal throughput, single eligible integer-multiply resource model and the alternative of replicated units; conclusions and limits.
4. Q2 (10): blocked older IMUL immediately after a pointer load, younger independent IMUL chain, dependency-serialized and LFENCE controls, cache-resident control; explain why this tests bypass of an older blocked instruction rather than independence alone.
5. Q4 (30, completed): preserve ROB_BENCHMARK.md / ROB_RESULTS_ARTEMISIA.md and all original work. The user-confirmed missing Charnwood comparison was added from unchanged source/build ID, with coarse/fine/repeat and a separate native timer audit. Compare its 220→224 main step with preserved Artemisia N=492–500; neither is silently converted into an exact total ROB count.
6. Q5 (35): 64-bit integer GPR class, scaled-index LEA destinations without flag writes, one/four/eight accumulator controls and length-matched NOP window control, matched two-ring memory blocker; retain the rejected constant-offset diagnostic separately. Report speculative allocation capacity/bounds and a justified conditional conversion model for any claimed total PRF size.
7. Q8 (10): additional L1-DTLB/STLB service cost relative to a compact ring with identical cache lines. Four simultaneous native events support about 9 active core cycles on Charnwood and 7 on Artemisia. TSC differences additionally require matched/stable effective cycle/TSC proxies. Protected event coverage remains unqualified, so enclave timing is a translation-set contrast. Full hierarchy reconstruction is not selected.
8. Limitations and reproducibility: native/SGX timer comparability, counters and enclave visibility, cache/translation confounds, disturbances, input/binary hashes, precise reproduction commands.
9. AI-use disclosure and source references; final artifact inventory.

For each selected exercise include the actual snippet, parameter choices, repeated raw evidence, side-by-side machine plots, same-machine enclave comparison or specific access limitation, normalization, inference and uncertainty. Do not fill pending result sections with expected or published numbers.

Build the report from the project root:

```bash
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=report report/report.tex
```

The report's source and actual evidence paths are tracked by `report/submission-status.json`. Final packaging (`python3 trackb/package.py --out submissions/HW3_Track_B_105_Varunaditya_Venkatesan.zip`) checks the selection, first page, native evidence on both machines, Artemisia hardware-enclave evidence and Q4 preservation. `--draft` is reserved for explicitly incomplete future work. Scientific attribution limits remain stated in the report rather than filled with guessed or published counts.
