#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build separate source and local-runtime archives; never include games or state."""
import gzip,hashlib,json,sys,tarfile
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
OUT=Path(sys.argv[1]).expanduser().resolve() if len(sys.argv)>1 else Path('/mnt/d/Temp/RG35XX/Out')
OUT.mkdir(parents=True,exist_ok=True)
SOURCE=['README.md','LICENSE','.gitignore','.gitattributes','rg35xx','src','scripts','tests','docs']
def entries(ready):
    for name in SOURCE+(['build','runtime'] if ready else []):
        path=BASE/name
        for f in ([path] if path.is_file() else sorted(path.rglob('*'))):
            if not f.is_file() and not f.is_symlink():continue
            if '__pycache__' in f.parts or f.suffix=='.pyc':continue
            if name=='build' and f.name not in ['demo','probe','devices.so']:continue
            yield f,'QEMU/'+f.relative_to(BASE).as_posix()
    yield BASE/'docs/ROOT-README-QEMU.md','README-QEMU.md'
    yield BASE/'docs/QEMU-README.patch','QEMU-README.patch'
def forbidden(name):
    parts=Path(name).parts
    return any(v in parts for v in ['state','reports','Content','.git','Saves']) or Path(name).name in ['jazz2','Prebaked.pak','libopenmpt.so.0','libopenmpt.so.0.2.2']
results=[]
for ready,label in [(False,'github'),(True,'ready-local')]:
    target=OUT/f'RG35XX-QEMU-v0.1.0-{label}.tar.gz'
    with target.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as tar:
        for f,name in entries(ready):
            if forbidden(name):raise RuntimeError('Forbidden payload: '+name)
            info=tar.gettarinfo(str(f),arcname=name);info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
            if info.isfile():
                with f.open('rb') as data:tar.addfile(info,data)
            else:tar.addfile(info)
    with tarfile.open(target) as tar:
        names=tar.getnames()
        assert not any(forbidden(n) for n in names)
        if not ready:assert not any(n.startswith(('QEMU/build/','QEMU/runtime/')) for n in names)
    digest=hashlib.sha256(target.read_bytes()).hexdigest();results.append((digest,target.name))
    print(f'{target.name}: {target.stat().st_size} bytes; {len(names)} files; SHA256 {digest}')
(OUT/'SHA256SUMS').write_text(''.join(f'{h}  {n}\n' for h,n in results))
