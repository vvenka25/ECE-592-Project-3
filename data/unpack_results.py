#!/usr/bin/env python3
"""Restore hash-verified raw results without replacing existing observations."""
import hashlib
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[1]

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    record=json.loads((ROOT/'data/raw-results.sha256.json').read_text())
    archive=ROOT/record['archive']
    assert sha(archive.read_bytes())==record['archive_sha256'],'Raw archive hash mismatch'
    expected=record['files_sha256']
    with tarfile.open(archive) as tar:
        members=tar.getmembers()
        assert len(members)==len(expected) and {m.name for m in members}==set(expected),'Archive inventory mismatch'
        # Validate every path, byte hash and existing file before writing any.
        for member in members:
            path=Path(member.name)
            assert member.isfile() and not path.is_absolute() and '..' not in path.parts
            assert path.parts[0]=='results'
            target=ROOT/path
            assert ROOT in target.resolve().parents,'Archive path escapes checkout'
            assert not target.is_symlink(),'Existing symlink: '+str(path)
            content=tar.extractfile(member).read()
            assert sha(content)==expected[member.name],'Raw file hash mismatch: '+str(path)
            if target.exists():assert target.is_file() and sha(target.read_bytes())==expected[member.name],'Existing observations differ: '+str(path)
        written=0
        for member in members:
            target=ROOT/member.name
            if target.exists():continue
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as output:output.write(tar.extractfile(member).read())
            written+=1
    print(f'Verified {len(expected)} raw/audit/source-snapshot files; restored {written}. Existing matching observations preserved.')

if __name__=='__main__':main()
