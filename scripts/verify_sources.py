#!/usr/bin/env python3
"""Hash project source files and emit a SHA-256 manifest."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

DEFAULT_ROOT=Path(__file__).resolve().parents[1]
INCLUDED={'.pdf','.md','.html','.txt'}

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def build_manifest(root: Path) -> dict:
    files=[]
    for p in sorted((root/'reference'/'sources').rglob('*')):
        if p.is_file() and p.suffix.lower() in INCLUDED:
            files.append({"path":p.relative_to(root).as_posix(),"size_bytes":p.stat().st_size,"sha256":sha256(p)})
    return {"algorithm":"SHA-256","files":files,"file_count":len(files)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,default=DEFAULT_ROOT); ap.add_argument('--output',type=Path); a=ap.parse_args()
    manifest=build_manifest(a.root); out=a.output or a.root/'research'/'maintenance'/'source_manifest.json'
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest,indent=2)); print(f'Wrote {out}')
    return 0 if manifest['file_count']>=1 else 2
if __name__=='__main__': raise SystemExit(main())
