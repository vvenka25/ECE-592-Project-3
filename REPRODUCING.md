# Reproduce the experiments and results

The selected submission is **Q1, Q2, Q3, Q4, Q5, Q8 — 105 points** by
**Varunaditya Venkatesan**. Start with the [report](report/report.pdf),
[findings](RESULTS_TRACK_B_COMPARISON.md), [methods](trackb/METHODS.md),
[checklist](TASKS.md) and [AI-use disclosure](AI_USE_LOG.md).

## Restore the recorded evidence

Requirements: x86-64 Linux for the native benchmark; Python 3.9+ and the
packages in `requirements.txt` for plots; GCC, GNU Make, binutils, OpenSSL,
`numactl` and `lscpu` for collection. Building the report additionally needs
`pdflatex`, `pdftotext` and the LaTeX geometry, graphicx, hyperref, longtable,
amsmath and placeins packages. Hardware SGX needs Intel's SDK and PSW.

```bash
git clone https://github.com/vvenka25/ECE-592-Project-3.git
cd ECE-592-Project-3
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 data/unpack_results.py
python3 trackb/verify_q4.py
```

Raw rows, manifests, complete mapping/NUMA/SMT audits, hardware inventories
and historical source snapshots retain their original paths after unpacking.
The archive and every restored file are SHA-256 checked. A second invocation
does no additional writing; an existing differing file causes failure before
any restoration. Markdown, figures, collection/build/validation logs and
checklists are also directly browseable on GitHub.

The [raw-data inventory](data/raw-results.sha256.json) lists retained files
and omitted generated binary copies. The original Q4 archive and submission
ZIP are unchanged locally; their debug signing key and generated binaries
are excluded from this public repository. The separately named
`preserved/q4-source-only-20261107.tar.gz` retains the exact 807 original
non-build members. Public preservation checks cover 805 immutable files,
excluding the two historically mutable project documents. This differs
explicitly from the 825-file full local check. No original Q4 experimental
source, raw observation or plot was edited. The public verifier and isolated
reproduction helper support this source-only derivative.

## Regenerate analysis and plots from the actual data

Use fresh output directories to retain existing plots and their historical
analysis-script snapshots. No hardware benchmark is run by these commands.

```bash
export MPLCONFIGDIR=/tmp/hw3-matplotlib
python3 trackb/review.py results/q3-artemisia results/q3-charnwood-private --out results/reproduced-q3
python3 trackb/review.py results/q1-artemisia results/q1-charnwood-private --out results/reproduced-q1
python3 trackb/review.py results/q2-artemisia-retry results/q2-charnwood-private --out results/reproduced-q2
python3 report/plot_q4_comparison.py --out results/reproduced-q4
python3 trackb/review.py results/q5-fine-artemisia results/q5-fine-charnwood-private --out results/reproduced-q5
python3 trackb/review.py results/q8-clock-artemisia results/q8-clock-charnwood-private --out results/reproduced-q8
python3 trackb/test_analysis.py
MPLCONFIGDIR=/tmp/hw3-matplotlib python3 report/make_report_artifacts.py
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=report report/report.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=report report/report.tex
```

The report builds against the included historical figures. The commands above
produce new side-by-side figures and summary/contrast tables from raw samples;
they keep hosts, environments and process repetitions separate. Exact prior
plot revisions are stored beside the original figures and in their provenance
records. PDF metadata need not be byte-identical on a new build.

## Build and validate the native/SGX suite

```bash
make -C trackb native
# Replace CPU with a currently permitted online CPU, e.g. 12 on recorded Artemisia.
TEST_CPU=CPU make -C trackb check

# On hardware-SGX Artemisia, with the SDK and PSW installed:
source /opt/intel/sgxsdk/environment
make -C trackb native enclave
TEST_CPU=CPU TEST_SGX=1 make -C trackb check
```

The suite checks 1,053 shared instruction bodies, result semantics, actual
Q8 geometry, denied-PMU behavior and native/enclave-host timing assembly.
Only `TEST_SGX=1` executes custom enclave validation. SGX builds are hardware
debug builds; generated local signing keys stay in ignored `build/` paths.
Native read-only per-page `move_pages` queries must be permitted for placement
validation. Event availability/permission failures are recorded or stop a
required-counter run; do not fabricate counts or substitute SGX simulation.

## Collect fresh experiments

Follow **Q3 → Q1 → Q2 → Q5 → Q8**, inspecting each question's controls before
continuing. Native comparisons use Charnwood (i7-6700, Skylake) and Artemisia
(Xeon Gold 5420+, Sapphire Rapids); same-machine SGX comparisons use Artemisia.
Recheck `lscpu -e=CPU,NODE,SOCKET,CORE,ONLINE`, allowed affinity and SMT siblings.
The recorded Artemisia runs used CPU 12/node 0 with sibling 68 offline;
Charnwood used CPU 1/node 0 with private core scheduling and a separate
controller core. These are recorded settings, not guaranteed current topology.

Example on Artemisia, after checking that CPU 12/node 0 and its offline sibling
are still appropriate:

```bash
python3 trackb/run.py --question Q3 --cpu 12 --numa-node 0 --environment both --require-idle-sibling --out results/new-q3-artemisia
# Review the plan, then run it using the same options plus --execute.
```

The [project README](README_Track_B.md) and [methods](trackb/METHODS.md) give
the remaining per-question commands, iteration lengths, native placement gates
and PMU policy. The collector refuses existing output directories. For a full
native collection on Charnwood, `bash report/collect_charnwood.sh CPU results/new-charnwood`
uses private inherited core scheduling; inspect its choices and fresh topology
first. Choose Q5's fine range from that host's own coarse run. The recorded
fine intervals were 120..160 on Charnwood and 192..232 on Artemisia, with
10,000 iterations/sample. Q8's final campaigns are `q8-clock-*`; earlier
three-counter data are retained as diagnostics.

For exact historical binaries, restore each campaign's `source-snapshot.tar.gz`
into a fresh directory and use its recorded toolchain, options and build hashes.
Current-source reruns are new campaigns and should not be silently pooled with
historical observations. Binary hash metadata remain even though copied ELF
files are omitted from GitHub.

## Q4 preservation and isolated reproduction

The root Q4 implementation remains unchanged. Use the isolated helper so the
completed Artemisia work is preserved and the exact original sources/build
inputs are extracted from the verified archive:

```bash
python3 report/reproduce_q4_charnwood.py --stage coarse --cpu 1 --workdir /tmp/hw3-q4-repro --out results/new-q4-coarse
# Add --execute only on Charnwood after checking topology and the printed plan.
```

Select a fine bracket from the new coarse run, then repeat the helper with
`--stage fine --lo N --hi M` and fresh outputs; use `--order-seed 2` for a fresh
order. The helper refuses execution on Artemisia. The recorded Charnwood fine
bracket was 192..240. The original Q4 methods and instructions remain in
[ROB_BENCHMARK.md](ROB_BENCHMARK.md) and the preserved analyses.

## Interpretation and packaging

The report separates measured findings from published models. Q4 gives an
effective overlap-loss window. Q5 identifies the 64-bit integer GPR class and
effective destination-pressure bounds; precise PRF-versus-scheduler attribution
and conversion to total PRF size remain unproved. Q8 native additional costs
for L1-DTLB misses served by the STLB are about 9 active core cycles on Charnwood
and 7 on Artemisia; protected event coverage remains unqualified, so enclave
timings are a translation-working-set contrast. TSC ticks are not core cycles.

After restoring evidence and building the PDF, a fresh submission archive can
be made with `python3 trackb/package.py --out submissions/reproduced-submission.zip`.
That archive uses the public source-only preservation derivative. The original
full local submission ZIP is a separate historical artifact and is not
overwritten or claimed byte-identical.

## Revised report and Overleaf source

The current 19-page report uses the provided Project 1 PDF only for format and explanation style; its measurements and original artwork come from Homework 3. See [report/README.md](report/README.md), [the revision checklist](report/REVISION_CHECKLIST.md), and `report/make_report_artifacts.py`. `python3 report/package_overleaf.py` creates a self-contained `main.tex` bundle with all vector figures, tables and listings. It is compiled from a clean extraction locally; direct upload to the user-designated Overleaf project requires an authenticated editing connection unavailable to the agent. The normal project URL is on page one. No completed hardware campaign is rerun by the report commands.
