#!/usr/bin/env python3
"""Download the official Zenodo ZIP and verify its record-published MD5."""
from __future__ import annotations
import argparse, hashlib, os, sys, tempfile, urllib.request
from pathlib import Path

URL='https://zenodo.org/records/18234600/files/Code_for_Sparse_quantum_state_preparation_with_improved_Toffoli_cost.zip?download=1'
EXPECTED_MD5='c58634ba415b4e3fb729648460f32ad7'

def md5(path:Path)->str:
    h=hashlib.md5()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--output',type=Path,default=Path('reference/authors-artifact/official-artifact.zip')); ap.add_argument('--timeout',type=int,default=90); a=ap.parse_args()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    tmp=a.output.with_suffix(a.output.suffix+'.part')
    try:
        req=urllib.request.Request(URL,headers={'User-Agent':'sparse-state-preparation-research/1.0'})
        with urllib.request.urlopen(req,timeout=a.timeout) as resp, tmp.open('wb') as out:
            while True:
                block=resp.read(1024*1024)
                if not block: break
                out.write(block)
        actual=md5(tmp)
        if actual != EXPECTED_MD5:
            tmp.unlink(missing_ok=True)
            print(f'ERROR: MD5 mismatch: expected {EXPECTED_MD5}, got {actual}',file=sys.stderr); return 3
        tmp.replace(a.output)
        print(f'VERIFIED: {a.output} ({a.output.stat().st_size} bytes), MD5 {actual}')
        print('Do not modify the extracted reference source or regenerate its uv.lock.')
        return 0
    except Exception as e:
        tmp.unlink(missing_ok=True)
        print(f'DOWNLOAD FAILED: {type(e).__name__}: {e}',file=sys.stderr)
        print('No artifact has been installed or marked verified.',file=sys.stderr)
        return 2
if __name__=='__main__': raise SystemExit(main())
