#!/usr/bin/env python3
"""Create a self-contained Overleaf LaTeX ZIP; no external upload is attempted."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PROJECT='https://www.overleaf.com/project/6aeeb80e5d4ccedd231a327b'
REPO='https://github.com/vvenka25/ECE-592-Project-3'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'report/HW3_Track_B_Overleaf_Source.zip')
    args=parser.parse_args()
    files={'main.tex':ROOT/'report/report.tex','AI_USE_LOG.md':ROOT/'AI_USE_LOG.md',
        'requirements.txt':ROOT/'requirements.txt',
        'figure-source/make_report_artifacts.py':ROOT/'report/make_report_artifacts.py',
        'provenance/artifact-audit.json':ROOT/'report/generated/artifact-audit.json',
        'provenance/source-excerpts.json':ROOT/'report/generated/source-excerpts.json'}
    for pattern,folder in (('*.pdf','figures'),('*.svg','figures'),('*.tex','generated'),('*','snippets')):
        for path in sorted((ROOT/'report'/folder).glob(pattern)):
            if path.is_file():files[folder+'/'+path.name]=path
    assert len(files)+2<=180,'Exceeds a single Overleaf upload batch'
    for name,path in files.items():
        assert path.is_file(),path
        assert path.stat().st_size<50*1024*1024,path
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
    readme=f'''# ECE 592 Homework 3 — Overleaf source

Author: Varunaditya Venkatesan. Selected questions: Q1, Q2, Q3, Q4, Q5, Q8 — 105 points.

Project: {PROJECT}
Full source, raw evidence and reproduction: {REPO}

## Compile

Set the main document to `main.tex` and use pdfLaTeX. Figures, generated tables
and source excerpts are included; compilation needs no Python, shell escape,
network fetch or files outside this ZIP. Locally, run pdfLaTeX twice.

## Put these files in the existing Overleaf project

Extract this ZIP and use the project's Upload files interface to upload the
extracted files/folders, preserving `figures/`, `generated/` and `snippets/`.
Select `main.tex` as the main document. Overleaf's separate Upload Project
operation creates a new project; use the existing project's file uploader
when updating the user-designated project.

Official instructions:
https://docs.overleaf.com/managing-projects-and-files/adding-files-to-a-project/uploading-files-to-a-project

No authenticated Overleaf editing connection was available to the agent;
this source archive was created and locally compile-tested, not directly
uploaded. The project link is the normal URL and omits its sharing token.

## Regenerate the figures

The included SVGs and `figure-source/make_report_artifacts.py` document the
original HW3 diagrams/plots. To rerun the Python generator, use the full
repository checkout, restore its raw data, and execute
`python3 report/make_report_artifacts.py` there. The minimal Overleaf bundle
does not contain the benchmark's raw data or all source imports.
`provenance/` records input hashes and excerpt origins. The AI-use log is
included for disclosure. Project 1 data/prose/artwork are excluded.
'''
    metadata={'main_document':'main.tex','compiler':'pdfLaTeX','project':PROJECT,'repository':REPO,
        'direct_upload':False,'files_sha256':{name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in files.items()}}
    output=args.out.resolve();output.parent.mkdir(parents=True,exist_ok=True)
    assert output not in files.values(),'Cannot overwrite a bundle input'
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,path in sorted(files.items()):archive.write(path,name)
        archive.writestr('README.md',readme)
        archive.writestr('BUNDLE_MANIFEST.json',json.dumps(metadata,indent=2)+'\n')
    with zipfile.ZipFile(output) as archive:assert archive.testzip() is None
    checksum=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix+'.sha256').write_text(checksum+'  '+output.name+'\n')
    print(f'Overleaf source ZIP: {output} ({len(files)+2} files, {output.stat().st_size} bytes); no external upload attempted.')

if __name__=='__main__':main()
