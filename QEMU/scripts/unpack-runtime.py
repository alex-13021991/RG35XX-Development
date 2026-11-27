#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib,json,sys,tarfile
from pathlib import Path
base=Path(__file__).resolve().parents[1]
metadata=json.loads((base/'docs/provenance.json').read_text())
archive=Path(sys.argv[1]);digest=hashlib.sha256(archive.read_bytes()).hexdigest()
if digest!=metadata['sysroot_sha256']:sys.exit('Sysroot SHA-256 mismatch; refusing unknown runtime')
(base/'runtime').mkdir(exist_ok=True)
with tarfile.open(archive) as tar:tar.extractall(base/'runtime',filter='data')
print('Verified and extracted sysroot',digest)
