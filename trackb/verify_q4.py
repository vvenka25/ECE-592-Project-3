#!/usr/bin/env python3
"""Verify full local preservation or the public source-only Q4 derivative."""
import hashlib
import json
import tarfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
record=json.loads((root/'preserved/q4-20261106.sha256.json').read_text())
archive=root/'preserved/q4-20261106.tar.gz'
source_only=not archive.exists()
if source_only:
    record=json.loads((root/'preserved/q4-source-only-20261107.sha256.json').read_text())
    archive=root/record['archive']
assert hashlib.sha256(archive.read_bytes()).hexdigest()==record['archive_sha256'],'Q4 archive changed'
mutable={'README_Track_B.md','AI_USE_LOG.md'}
checked=archived_only=0
with tarfile.open(archive) as tar:
    for name,digest in record['files'].items():
        if name in mutable:continue
        path=root/name
        if path.exists():data=path.read_bytes()
        elif name.startswith('build/'):
            # Source ZIPs keep the original binaries/build outputs in the
            # immutable archive instead of placing them in the active build.
            member=tar.getmember(name);assert member.isfile()
            data=tar.extractfile(member).read();archived_only+=1
        else:raise AssertionError('Missing preserved Q4 file: '+name+'; restore raw evidence with python3 data/unpack_results.py')
        assert hashlib.sha256(data).hexdigest()==digest,'Preserved Q4 file changed: '+name
        checked+=1
kind='public source-only' if source_only else 'original full'
print(f'{checked} preserved Q4 files unchanged; {kind} archive hash verified; {archived_only} build files verified from archive only. Project README/AI log updates are separate.')
