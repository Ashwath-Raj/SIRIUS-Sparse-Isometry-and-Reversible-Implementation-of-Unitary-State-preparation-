"""Environment probe for SIRIUS benchmarking.

Collects sanitized machine manifests and run-record environment descriptors.
Adheres strictly to benchmarking/schemas/machine-manifest.schema.json and
benchmarking/schemas/run-record.schema.json.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "machine-manifest.schema.json"


def get_git_commit(cwd: Path | None = None) -> str:
    root = cwd or Path(__file__).resolve().parents[2]
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return "unknown_or_no_git"


def get_git_dirty(cwd: Path | None = None) -> bool:
    root = cwd or Path(__file__).resolve().parents[2]
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if res.returncode == 0:
            return bool(res.stdout.strip())
    except Exception:
        pass
    return False


def get_cpu_info() -> dict[str, Any]:
    logical = os.cpu_count()
    physical: int | None = None
    model = platform.processor() or "Unknown CPU"

    # Try Linux /proc/cpuinfo
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        try:
            text = cpuinfo.read_text(encoding="utf-8", errors="replace")
            cores_set: set[str] = set()
            for line in text.splitlines():
                if line.startswith("model name") and ":" in line:
                    model = line.split(":", 1)[1].strip()
                elif line.startswith("core id") and ":" in line:
                    cores_set.add(line.split(":", 1)[1].strip())
            if cores_set:
                physical = len(cores_set)
        except Exception:
            pass

    return {
        "model": model,
        "logical_cores": logical,
        "physical_cores": physical or logical,
        "architecture": platform.machine(),
    }


def get_memory_info() -> dict[str, int | None]:
    mem_total: int | None = None
    swap_total: int | None = None

    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        try:
            for line in meminfo.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("MemTotal:") and ":" in line:
                    parts = line.split(":", 1)[1].strip().split()
                    mem_total = int(parts[0]) * 1024
                elif line.startswith("SwapTotal:") and ":" in line:
                    parts = line.split(":", 1)[1].strip().split()
                    swap_total = int(parts[0]) * 1024
        except Exception:
            pass

    return {
        "ram_total_bytes": mem_total,
        "swap_total_bytes": swap_total,
    }


def get_gpu_devices() -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []

    # 1. Try nvidia-smi query
    smi = shutil.which("nvidia-smi")
    if smi:
        try:
            res = subprocess.run(
                [
                    smi,
                    "--query-gpu=index,name,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                for line in res.stdout.strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 3:
                        idx = int(parts[0])
                        name = parts[1]
                        mem_mb = int(parts[2])
                        devices.append({
                            "device_id": idx,
                            "name": name,
                            "memory_bytes": mem_mb * 1024 * 1024,
                        })
                if devices:
                    return devices
        except Exception:
            pass

    # 2. Fallback to CuPy runtime if available
    try:
        import cupy as cp
        count = cp.cuda.runtime.getDeviceCount()
        for idx in range(count):
            props = cp.cuda.runtime.getDeviceProperties(idx)
            name = props.get("name", b"GPU").decode(errors="replace") if isinstance(props.get("name"), bytes) else str(props.get("name"))
            total_mem = props.get("totalGlobalMem", None)
            devices.append({
                "device_id": idx,
                "name": name,
                "memory_bytes": int(total_mem) if total_mem is not None else None,
            })
    except Exception:
        pass

    return devices


def get_software_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {
        "nvidia_driver": None,
        "cuda_runtime": None,
        "cuda_toolkit": None,
        "cupy": None,
        "numpy": None,
        "git": get_git_commit(),
    }

    # Driver version from nvidia-smi
    smi = shutil.which("nvidia-smi")
    if smi:
        try:
            res = subprocess.run(
                [smi, "--query-gpu=driver_version", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                versions["nvidia_driver"] = res.stdout.strip().splitlines()[0]
        except Exception:
            pass

    # CuPy and CUDA version
    try:
        import cupy as cp
        versions["cupy"] = cp.__version__
        cuda_v = cp.cuda.runtime.runtimeGetVersion()
        versions["cuda_runtime"] = f"{cuda_v // 1000}.{(cuda_v % 1000) // 10}"
    except Exception:
        pass

    # NumPy version
    try:
        import numpy as np
        versions["numpy"] = np.__version__
    except Exception:
        pass

    # nvcc / cuda toolkit
    nvcc = shutil.which("nvcc")
    if nvcc:
        try:
            res = subprocess.run([nvcc, "--version"], capture_output=True, text=True, timeout=5, check=False)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if "release" in line:
                        versions["cuda_toolkit"] = line.strip()
                        break
        except Exception:
            pass

    return versions


def probe_machine_manifest(machine_id: str | None = None, notes: str | None = None) -> dict[str, Any]:
    """Collects and returns a sanitized machine manifest validating against machine-manifest.schema.json."""
    alias = machine_id or f"host-{platform.system().lower()}-{platform.machine().lower()}"
    now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    os_info = {
        "name": platform.system(),
        "version": platform.version(),
        "kernel": platform.release(),
    }

    python_info = {
        "implementation": platform.python_implementation(),
        "version": platform.python_version(),
        "executable": "python",  # Sanitized to prevent leaking absolute user directories
    }

    cpu_info = get_cpu_info()
    mem_info = get_memory_info()
    gpu_list = get_gpu_devices()
    software_info = get_software_versions()

    manifest: dict[str, Any] = {
        "manifest_version": "1.0.0",
        "machine_id": alias,
        "captured_at_utc": now_utc,
        "os": os_info,
        "python": python_info,
        "cpu": cpu_info,
        "memory": mem_info,
        "gpu_devices": gpu_list,
        "software": software_info,
        "notes": notes or "Automated environment probe by SIRIUS Phase 9.2 runner.",
    }
    return manifest


def probe_run_environment(hostname_alias: str | None = None) -> dict[str, Any]:
    """Collects and returns an environment dictionary for run-record.schema.json."""
    alias = hostname_alias or f"host-{platform.system().lower()}-{platform.machine().lower()}"
    cpu_info = get_cpu_info()
    mem_info = get_memory_info()
    gpu_list = get_gpu_devices()
    software_info = get_software_versions()

    # Shape required by run-record.schema.json
    sanitized_gpus = [
        {"name": d["name"], "memory_bytes": d.get("memory_bytes")}
        for d in gpu_list
    ]

    return {
        "hostname_alias": alias,
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "cpu_model": cpu_info["model"],
        "gpu_devices": sanitized_gpus,
        "cuda_version": software_info.get("cuda_runtime"),
        "cupy_version": software_info.get("cupy"),
        "ram_bytes": mem_info.get("ram_total_bytes"),
    }


def validate_manifest(manifest: dict[str, Any], schema_file: Path | None = None) -> list[str]:
    schema_path = schema_file or SCHEMA_PATH
    if not schema_path.exists():
        return [f"Schema file not found: {schema_path}"]

    try:
        import jsonschema
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        errors = [f"{e.json_path}: {e.message}" for e in validator.iter_errors(manifest)]
        return errors
    except ImportError:
        # Fallback basic structural checks if jsonschema is not installed
        required = ["manifest_version", "machine_id", "captured_at_utc", "os", "python", "cpu", "memory", "gpu_devices", "software"]
        missing = [k for k in required if k not in manifest]
        return [f"Missing required key: {k}" for k in missing]


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect sanitized environment manifest for SIRIUS.")
    parser.add_argument("--machine-id", type=str, default=None, help="Machine identifier or alias")
    parser.add_argument("--output", type=Path, default=None, help="Output JSON path")
    parser.add_argument("--notes", type=str, default=None, help="Optional user notes")
    parser.add_argument("--validate", action="store_true", default=True, help="Validate against schema")
    args = parser.parse_args()

    manifest = probe_machine_manifest(machine_id=args.machine_id, notes=args.notes)

    if args.validate:
        errors = validate_manifest(manifest)
        if errors:
            print("Environment manifest validation errors:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1
        print("Manifest schema validation: PASS")

    payload = json.dumps(manifest, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(f"Wrote sanitized machine manifest to {args.output}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
