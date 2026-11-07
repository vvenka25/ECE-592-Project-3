# Revised Homework 3 report

The [19-page report](report.pdf) is written from the completed Homework 3
evidence. The supplied Project 1 PDF was read only for format, structure and
explanation style, especially its numbered methodology panels on pages 3–6.
No Project 1 prose, numbers, code, artwork, conclusions or assignment phases
are used. `Homework_3.pdf` is the submission-requirements authority.

The first page names Varunaditya Venkatesan, ECE 592, Track B, the six questions
and 105-point total, and includes the GitHub and normal Overleaf project URLs.
The body follows Q1, Q2, Q3, Q4, Q5, Q8. Original Q4 source, raw observations,
figures and analyses are unchanged. The previous report is retained in
`history/20261106-before-reference-revision/`; the earlier submission ZIP is
also unchanged.

## Rebuild from the repository root

```bash
# In the public checkout, first restore the raw evidence:
python3 data/unpack_results.py
python3 -m pip install -r requirements.txt
MPLCONFIGDIR=/tmp/hw3-mpl python3 report/make_report_artifacts.py
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=report report/report.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=report report/report.tex
python3 report/package_overleaf.py
```

The original local workspace already contains the raw files and does not need
the first command. No benchmark or fresh performance collection is executed
by these report commands.

`make_report_artifacts.py` validates/loads the completed raw campaigns through
the existing analysis helpers, then generates LaTeX tables, seven result/control
plots, six original five-part methodology diagrams and the shared timer diagram.
It extracts actual generated-kernel instructions, with omitted repeated bodies
explicitly marked. PDF/SVG/PNG assets are in `figures/`, tables/processed rows
and per-input hashes in `generated/`, and listing inputs in `snippets/`.

## Overleaf

Project: https://www.overleaf.com/project/6aeeb80e5d4ccedd231a327b

`HW3_Track_B_Overleaf_Source.zip` is a self-contained, locally compile-tested
bundle with `main.tex`, all vector figure/table/listing dependencies, figure
sources, provenance and the AI-use log. Extract and upload its files/folders
into the existing project, preserve directories, and select `main.tex` with
pdfLaTeX. The agent currently has no authenticated Overleaf editing session;
no direct upload is claimed. The sharing token is excluded from published files.

## Scientific limits retained

Q4 reports the actual overlap-loss window. Q5 identifies 64-bit integer GPR
destination pressure and conditional speculative-allocation bounds; exact
PRF-versus-scheduler attribution and conversion to total PRF size are unproved.
Q8's native STLB-served miss estimate is qualified, while enclave protected
counter coverage remains unqualified. The user confirmed that the original
SampleEnclave console output was not saved; its success is marked as user
confirmation, separate from retained custom hardware-enclave checks.
