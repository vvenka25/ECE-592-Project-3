from pathlib import Path
import hashlib
import sys
h=hashlib.sha256()
for name in sorted(sys.argv[2:]):h.update(name.encode()+b'\0'+Path(name).read_bytes()+b'\0')
Path(sys.argv[1]).write_text('#define TB_BUILD_ID "'+h.hexdigest()[:16]+'"\n')
