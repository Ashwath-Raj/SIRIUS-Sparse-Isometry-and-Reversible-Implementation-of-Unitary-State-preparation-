#!/usr/bin/env python3
"""Portable hardware probe with genuine optional CUDA kernel smoke tests.

Supported optional CUDA backends: PyTorch, CuPy, Numba CUDA.
No backend is installed or modified by this script.
"""
from __future__ import annotations
import argparse, importlib.util, json, os, platform, shutil, subprocess, sys, time
from pathlib import Path
from typing import Any


def run_cmd(args: list[str], timeout: int = 8) -> dict[str, Any]:
    exe = shutil.which(args[0])
    if not exe:
        return {"available": False, "command": args, "reason": f"{args[0]} not found"}
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return {"available": True, "returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except Exception as e:
        return {"available": True, "error": f"{type(e).__name__}: {e}"}


def parse_nvidia_smi_csv(output: str) -> list[dict[str, str]]:
    devices=[]
    for line in output.splitlines():
        cols=[c.strip() for c in line.split(",")]
        if len(cols) >= 4:
            devices.append({"name":cols[0],"uuid":cols[1],"memory_total":cols[2],"driver_version":cols[3]})
    return devices


def memory_info() -> dict[str, Any]:
    # Linux MemTotal is the most portable source in this environment.
    p=Path('/proc/meminfo')
    if p.exists():
        vals={}
        for line in p.read_text(errors='replace').splitlines():
            if ':' in line:
                k,v=line.split(':',1); vals[k]=v.strip()
        total_kb=None
        if 'MemTotal' in vals:
            try: total_kb=int(vals['MemTotal'].split()[0])
            except Exception: pass
        return {"total_bytes": total_kb*1024 if total_kb is not None else None,
                "mem_total_proc":vals.get('MemTotal'),"mem_available_proc":vals.get('MemAvailable')}
    return {"total_bytes":None,"reason":"/proc/meminfo unavailable"}


def cuda_probe_torch() -> dict[str, Any]:
    if importlib.util.find_spec('torch') is None:
        return {"installed":False,"available":False,"backend":"torch","reason":"PyTorch not installed"}
    import torch
    result={"installed":True,"available":bool(torch.cuda.is_available()),"backend":"torch","torch_version":torch.__version__,"torch_cuda_build":torch.version.cuda}
    if not result['available']:
        result['reason']='torch.cuda.is_available() returned False'; return result
    t0=time.perf_counter()
    x=torch.arange(1024,device='cuda',dtype=torch.float32)
    y=x*2+3
    torch.cuda.synchronize()
    ok=bool(torch.allclose(y, x*2+3))
    result.update({"kernel_smoke_test":"passed" if ok else "failed","device":torch.cuda.get_device_name(0),"device_count":torch.cuda.device_count(),"memory_allocated_bytes":torch.cuda.memory_allocated(0),"elapsed_seconds":time.perf_counter()-t0})
    return result


def cuda_probe_cupy() -> dict[str, Any]:
    if importlib.util.find_spec('cupy') is None:
        return {"installed":False,"available":False,"backend":"cupy","reason":"CuPy not installed"}
    import cupy as cp
    count=cp.cuda.runtime.getDeviceCount()
    result={"installed":True,"available":count>0,"backend":"cupy","cupy_version":cp.__version__,"device_count":count}
    if count<=0: result['reason']='CuPy sees no CUDA device'; return result
    t0=time.perf_counter(); x=cp.arange(1024,dtype=cp.float32); y=x*2+3; cp.cuda.Stream.null.synchronize()
    ok=bool(cp.allclose(y,x*2+3).item())
    props=cp.cuda.runtime.getDeviceProperties(0)
    name=props.get('name',b'unknown'); name=name.decode(errors='replace') if isinstance(name,bytes) else str(name)
    result.update({"kernel_smoke_test":"passed" if ok else "failed","device":name,"elapsed_seconds":time.perf_counter()-t0})
    return result


def cuda_probe_numba() -> dict[str, Any]:
    if importlib.util.find_spec('numba') is None:
        return {"installed":False,"available":False,"backend":"numba","reason":"Numba not installed"}
    import numpy as np
    from numba import cuda
    result={"installed":True,"available":bool(cuda.is_available()),"backend":"numba"}
    if not result['available']:
        result['reason']='numba.cuda.is_available() returned False'; return result
    @cuda.jit
    def kernel(a,b):
        i=cuda.grid(1)
        if i<a.size: b[i]=a[i]*2+3
    t0=time.perf_counter(); a=np.arange(1024,dtype=np.float32); b=np.zeros_like(a)
    da=cuda.to_device(a); db=cuda.to_device(b); kernel[4,256](da,db); got=db.copy_to_host()
    ok=bool(np.array_equal(got,a*2+3))
    result.update({"kernel_smoke_test":"passed" if ok else "failed","device":str(cuda.get_current_device().name),"elapsed_seconds":time.perf_counter()-t0})
    return result


def probe() -> dict[str, Any]:
    nvidia=run_cmd(['nvidia-smi','--query-gpu=name,uuid,memory.total,driver_version','--format=csv,noheader'])
    devices=parse_nvidia_smi_csv(nvidia.get('stdout','')) if nvidia.get('returncode')==0 else []
    backends=[]
    for fn in (cuda_probe_torch,cuda_probe_cupy,cuda_probe_numba):
        try: backends.append(fn())
        except Exception as e: backends.append({"backend":fn.__name__.replace('cuda_probe_',''),"installed":True,"available":False,"kernel_smoke_test":"error","error":f"{type(e).__name__}: {e}"})
    successful=[b for b in backends if b.get('kernel_smoke_test')=='passed']
    try:
        import multiprocessing
        cpu_count=multiprocessing.cpu_count()
    except Exception: cpu_count=os.cpu_count()
    try:
        import psutil
        vm=psutil.virtual_memory(); mem={"total_bytes":int(vm.total),"available_bytes":int(vm.available)}
    except Exception: mem=memory_info()
    return {
        "schema_version":1,"captured_at_utc":time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        "machine_role":"agent_runtime_unclassified_until_operator_runs_probe",
        "is_user_rtx3050_machine":False,
        "platform":{"system":platform.system(),"release":platform.release(),"version":platform.version(),"machine":platform.machine(),"python":sys.version},
        "cpu":{"logical_cpus":cpu_count,"processor":platform.processor()},"memory":mem,
        "nvidia_smi":nvidia,"nvidia_devices":devices,
        "cuda_backends":backends,
        "cuda_kernel_verified":bool(successful),"verified_cuda_backends":[b.get('backend') for b in successful],
        "cpu_fallback_available":True,
        "notes":["nvidia-smi visibility alone is not treated as proof of CUDA execution.","CUDA is verified only when an installed backend executes a kernel and validates its output.","This report describes the machine on which the script is run; do not relabel it as another host."]
    }


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,help='Write JSON report to this path (also prints JSON).')
    ap.add_argument('--require-cuda',action='store_true',help='Exit non-zero unless a CUDA kernel smoke test passes.')
    args=ap.parse_args(); data=probe(); rendered=json.dumps(data,indent=2,sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(rendered+'\n',encoding='utf-8')
    print(rendered)
    return 0 if (not args.require_cuda or data['cuda_kernel_verified']) else 2

if __name__=='__main__': raise SystemExit(main())
