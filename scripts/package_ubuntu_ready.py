#!/usr/bin/env python3
"""Build and clean-extract verify SIRIUS_UBUNTU_BENCH_READY.zip."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "dist/SIRIUS_UBUNTU_BENCH_READY.zip"
CHECKSUM = ROOT / "dist/SIRIUS_UBUNTU_BENCH_READY.zip.sha256"
EXCLUDED_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules", "build", "dist", "target", ".cargo"}

def include(rel: Path) -> bool:
    if any(part in EXCLUDED_DIRS or part.startswith(".venv-") or part.endswith(".egg-info") for part in rel.parts): return False
    if rel.suffix in {".pyc", ".pyo", ".pyd", ".prof", ".swp"}: return False
    path = rel.as_posix()
    # Keep tracked historical root-level results/evidence; exclude nested machine runs.
    if path.startswith("results/raw/") and len(rel.parts) > 3 and not path.startswith("results/raw/phase2/"): return False
    if path.startswith("results/summaries/") and len(rel.parts) > 3: return False
    if any(path.startswith(prefix) for prefix in ("results/tables/", "results/manifests/", "results/logs/", "results/reports/", "results/checkpoints/")): return False
    if path.startswith("results/figures/") and len(rel.parts) > 2 and rel.name not in {".gitkeep", "README.md"}: return False
    if path.startswith("benchmarking/results/") and rel.name not in {".gitkeep", "README.md"}: return False
    return True

def main() -> int:
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file(): continue
            rel = path.relative_to(ROOT)
            if not include(rel): continue
            info = zipfile.ZipInfo((Path("SIRIUS") / rel).as_posix())
            info.external_attr = (path.stat().st_mode & 0xFFFF) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())
            count += 1
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    CHECKSUM.write_text(f"{digest}  {ARCHIVE.name}\n")
    with zipfile.ZipFile(ARCHIVE) as zf:
        bad = zf.testzip()
        if bad: raise RuntimeError(f"zip integrity failure at {bad}")
        names = zf.namelist()
        assert not any("/.git/" in x or "/.venv" in x or x.endswith(".pyc") for x in names)
        for required in ("SIRIUS/pyproject.toml", "SIRIUS/reference/authors-artifact/official-artifact.zip", "SIRIUS/scripts/ubuntu/run_laptop_pilot.sh", "SIRIUS/benchmarking/config/ubuntu_laptop_pilot_v1.json"):
            assert required in names, f"missing archive member: {required}"
        for rel in ("scripts/ubuntu/setup.sh", "scripts/ubuntu/preflight.sh", "scripts/ubuntu/run_laptop_pilot.sh", "scripts/ubuntu/run_campaign.sh", "scripts/ubuntu/package.sh"):
            info = zf.getinfo(f"SIRIUS/{rel}")
            assert (info.external_attr >> 16) & 0o111, f"not executable in archive: {rel}"
    with tempfile.TemporaryDirectory(prefix="sirius-ubuntu-zip-") as tmp:
        with zipfile.ZipFile(ARCHIVE) as zf: zf.extractall(tmp)
        extracted = Path(tmp) / "SIRIUS"
        env = dict(os.environ, PYTHONPATH=f"{extracted/'candidate_ai/src'}:{extracted}")
        commands = [
            [sys.executable, "-c", "from sparseprep import SparseStateProblem, run_batched_isometry; from benchmarking.extensions.symmetry_workloads import fixed_hamming_weight_support; print('extracted imports PASS')"],
            [sys.executable, "scripts/validate_ubuntu_plans.py"],
            [sys.executable, "-m", "pytest", "-o", "addopts=", "-q", "tests/test_symmetry_workloads.py", "tests/test_phase9_2_infrastructure.py"],
            [sys.executable, "scripts/run_ubuntu_campaign.py", "--dry-run", "--max-attempts", "64"],
        ]
        for command in commands:
            result = subprocess.run(command, cwd=extracted, env=env, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(f"clean extraction command failed: {command}\n{result.stdout}\n{result.stderr}")
        print("Clean extraction imports, plan validation, focused CPU tests and benchmark dry-run: PASS")
    print(f"Archive: {ARCHIVE} ({ARCHIVE.stat().st_size} bytes; {count} files)")
    print(f"SHA-256: {digest}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
