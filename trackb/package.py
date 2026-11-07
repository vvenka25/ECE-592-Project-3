#!/usr/bin/env python3
"""Package a declared draft, or check required evidence before a final ZIP."""
import argparse
import csv
import json
from pathlib import Path
import re
import subprocess as sp
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
QUESTIONS=[1,2,3,4,5,8]
def evidence(paths,q,environment,machine=None):
    for name in paths:
        path=ROOT/name
        if not path.exists():continue
        m=json.loads(path.read_text())
        if q!=4 and m.get('purpose')!='measurement':continue
        if q!=4:
            jobs=m.get('jobs',[])
            if not jobs or any(j.get('status')!='success' or j.get('placement_verified') is False or j.get('sibling_gate_passed') is False for j in jobs):continue
            if len({j['repetition'] for j in jobs if j['environment']==environment and j['parameters']['question']==q})<2:continue
            private=m.get('core_scheduling',{})
            offline=not m.get('initial_platform',{}).get('active_siblings',[True])
            controlled=(private.get('policy')=='private' and private.get('cookie',0)>0) or (offline and m.get('require_idle_sibling') and all(j.get('sibling_gate_passed') for j in jobs))
            if not controlled:continue
        for job in m.get('jobs',[]):
            if job.get('status')!='success' or job['environment']!=environment:continue
            raw=path.parent/(job['name']+'.csv')
            if not raw.exists():continue
            with raw.open() as f:rows=list(csv.DictReader(f))
            if not rows or any(r['status']!='ok' for r in rows):continue
            if q!=4 and len(rows)!=job.get('sample_count'):continue
            if q!=4 and environment=='native' and int(rows[0]['span_bytes']) and job.get('placement_verified') is not True:continue
            if q==4 and any(r.get('experiment')!='rob' for r in rows):continue
            if q!=4 and any(r.get('question')!=f'Q{q}' for r in rows):continue
            if machine and any(machine.lower() not in r['machine_id'].lower() for r in rows):continue
            if environment=='enclave' and any(r['environment']!='sgx-hw-debug' for r in rows):continue
            return True
    return False

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path);p.add_argument('--draft',action='store_true')
    a=p.parse_args();status=json.loads((ROOT/'report/submission-status.json').read_text())
    if status['selected_questions']!=QUESTIONS or status['total_points']!=105:p.error('Selection must be Q1/Q2/Q3/Q4/Q5/Q8, 105 points')
    pdf=ROOT/status['report_pdf']
    if not pdf.exists():p.error('Build the report PDF first; see report/OUTLINE.md')
    gaps=[]
    if not status['report_is_final']:gaps.append('report is still a draft')
    for q in QUESTIONS:
        for machine in ('Charnwood','Artemisia'):
            if not evidence(status['native_evidence'][f'Q{q}'][machine],q,'native',machine):gaps.append(f'Q{q} native {machine} evidence')
        if not evidence(status['enclave_evidence'][f'Q{q}'],q,'enclave','Artemisia'):gaps.append(f'Q{q} custom Artemisia hardware-enclave evidence')
    if gaps and not a.draft:p.error('Final submission is incomplete: '+', '.join(gaps)+'. Use --draft only for a clearly labeled draft archive')
    if not a.draft:
        first=sp.check_output(['pdftotext','-f','1','-l','1',str(pdf),'-'],text=True)
        if '105' not in first or any(f'Q{q}' not in first for q in QUESTIONS) or re.search(r'\bDRAFT\b',first):p.error('First page must identify all six questions/105 points and be final')
    sp.run([sys.executable,str(ROOT/'trackb/verify_q4.py')],check=True)
    output=a.out.resolve()
    if output.exists():p.error('Output ZIP exists; choose a fresh path')
    output.parent.mkdir(parents=True,exist_ok=True)
    candidates=list(ROOT.glob('*.md'))+[ROOT/'Makefile',ROOT/'.gitignore',ROOT/'requirements.txt']
    candidates += [ROOT/'submissions'/name for name in ('trackb-charnwood-source.tar.gz','trackb-charnwood-source.tar.gz.json','q4-preserved-source.tar.gz','q4-preserved-source.tar.gz.json')]
    for folder in ('src','enclave','scripts','analysis','tests','results','trackb','report','preserved','data'):
        candidates.extend((ROOT/folder).rglob('*'))
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(set(candidates)):
            if not path.is_file():continue
            rel=path.relative_to(ROOT)
            if any(part in ('.git','.agents','.codex','.aws','__pycache__') for part in rel.parts):continue
            if rel.parts[0]=='build' or rel.parts[:2]==('trackb','build'):continue
            if path.suffix in ('.zip','.pyc') or path.resolve()==output:continue
            z.write(path,str(rel))
        z.writestr('PACKAGE_STATUS.json',json.dumps(dict(draft=a.draft,selection=QUESTIONS,total_points=105,remaining_submission_gaps=gaps),indent=2)+'\n')
    print(('DRAFT' if a.draft else 'Final')+' ZIP: '+str(output))
    if gaps:print('Outstanding: '+', '.join(gaps))

if __name__=='__main__':main()
