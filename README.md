# Homework 3 — Track B — 105 points

**Q1, Q2, Q3, Q4, Q5, Q8 — 105 points.** Q4 is completed and preserved; Q6 is dropped.

See [the current project README](README_Track_B.md), [task list](TASKS.md), [report outline](report/OUTLINE.md), and [new benchmark methods/reproduction](trackb/METHODS.md).

Implementation order: **Q3 → Q1 → Q2 → Q5 → Q8**. The new suite is isolated under `trackb/` and passes native/hardware-SGX semantic, byte and timer checks. [Two-machine findings](RESULTS_TRACK_B_COMPARISON.md) cover every selected question; the missing Charnwood Q4 comparison uses unchanged source and preserves completed Artemisia work.

See the [report PDF](report/report.pdf) and [AI-use log](AI_USE_LOG.md). Q5 reports effective integer-GPR destination-pressure bounds, with total PRF conversion unproved. Q8 native miss costs are about 9 active core cycles on Charnwood and 7 on Artemisia; enclave miss attribution remains unqualified.


## Read first

- [Reproduction guide](REPRODUCING.md): build, restore raw evidence, regenerate figures and collect new experiments.
- [Project scope and commands](README_Track_B.md), [task checklist](TASKS.md) and [report outline](report/OUTLINE.md).
- [Two-machine findings](RESULTS_TRACK_B_COMPARISON.md), [preserved Artemisia ROB analysis](ROB_RESULTS_ARTEMISIA.md) and [Charnwood ROB comparison](Q4_CHARNWOOD_RESULTS.md).
- [Methods](trackb/METHODS.md), [validation history](trackb/VALIDATION.md), [publication checklist](PUBLICATION_CHECKLIST.md) and [activity/validation logs](results/charnwood-session/).
- [AI-use disclosure](AI_USE_LOG.md), including the publication work.

This public checkout contains source, scripts, report, plots and logs. Raw rows, configuration/mapping audits and historical source snapshots are losslessly compressed in `data/raw-results.tar.gz`; restore their original paths with `python3 data/unpack_results.py` before analysis or preservation checks. The unpacker verifies every hash and refuses to replace different observations.

The original full local Q4 archive and final submission ZIP remain unchanged outside this repository. GitHub contains a separately named source-only preservation archive with all 807 original non-build members, including the original reports/raw data/plots. Its verifier checks 805 immutable files after excluding the historically mutable README and AI log. Compiled binaries and private signing keys are excluded; build commands generate new hardware-debug signing keys locally.

The [revised 19-page report](report/report.pdf) follows the supplied Project 1 reference only for format and explanatory structure. [Report sources and rebuild instructions](report/README.md) include data-generated tables, original methodology diagrams, and a [self-contained Overleaf source ZIP](report/HW3_Track_B_Overleaf_Source.zip). The normal GitHub and Overleaf links appear on the report's first page; direct Overleaf upload was not available.
