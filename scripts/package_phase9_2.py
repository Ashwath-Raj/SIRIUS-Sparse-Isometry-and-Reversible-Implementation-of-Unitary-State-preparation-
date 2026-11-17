#!/usr/bin/env python3
"""Build and verify the clean distribution package SIRIUS_PHASE9_2_READY.zip."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
ARCHIVE_PATH = DIST_DIR / "SIRIUS_PHASE9_2_READY.zip"
CHECKSUM_PATH = DIST_DIR / "SIRIUS_PHASE9_2_READY.zip.sha256"

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "build",
    "dist",
    "target",
    ".cargo",
    "sirius_sparseprep.egg-info",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".prof",
    ".swp",
}


def should_exclude(rel_path: Path) -> bool:
    parts = rel_path.parts
    # Exclude directories
    for part in parts:
        if part in EXCLUDE_DIRS or part.endswith(".egg-info"):
            return True

    # Exclude specific files/extensions
    if rel_path.suffix in EXCLUDE_EXTENSIONS:
        return True

    # Exclude local raw benchmark results and summaries (preserve historical phase2 and READMEs)
    path_str = rel_path.as_posix()
    if path_str.startswith("results/raw/") and not path_str.startswith("results/raw/phase2/"):
        if rel_path.name not in {"README.md", ".gitkeep"}:
            return True

    if path_str.startswith("results/summaries/") and rel_path.name not in {"README.md", ".gitkeep"}:
        return True

    # Exclude local machine hardware manifests
    if path_str.startswith("environment/"):
        if rel_path.name.startswith("local-") or rel_path.name.endswith("-hardware.json") or rel_path.name == "agent-probe.json":
            return True

    return False


def build_archive() -> tuple[Path, str]:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    if ARCHIVE_PATH.exists():
        ARCHIVE_PATH.unlink()

    included_count = 0
    with zipfile.ZipFile(ARCHIVE_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(ROOT.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(ROOT)
            if should_exclude(rel):
                continue
            # Store in zip prefixed by SIRIUS/
            arcname = Path("SIRIUS") / rel
            zf.write(p, arcname)
            included_count += 1

    hasher = hashlib.sha256()
    with ARCHIVE_PATH.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    sha256_hex = hasher.hexdigest()

    CHECKSUM_PATH.write_text(f"{sha256_hex}  {ARCHIVE_PATH.name}\n", encoding="utf-8")
    print(f"Archive created: {ARCHIVE_PATH} ({included_count} files)")
    print(f"SHA-256 Checksum: {sha256_hex}")
    print(f"Wrote checksum file: {CHECKSUM_PATH}")
    return ARCHIVE_PATH, sha256_hex


def verify_archive(archive_path: Path) -> bool:
    print("\n--- Verifying Archive Integrity in Clean Temporary Directory ---")
    with tempfile.TemporaryDirectory() as tmp_dir:
        extract_root = Path(tmp_dir)
        with zipfile.ZipFile(archive_path, "r") as zf:
            # Check for excluded files
            for member in zf.namelist():
                for exc in EXCLUDE_DIRS:
                    if f"/{exc}/" in member or member.endswith(f"/{exc}") or member.startswith(f"SIRIUS/{exc}/"):
                        print(f"ERROR: Found excluded directory in archive: {member}", file=sys.stderr)
                        return False
                if member.endswith(".pyc") or member.endswith(".jsonl"):
                    print(f"ERROR: Found excluded file in archive: {member}", file=sys.stderr)
                    return False
            zf.extractall(extract_root)

        extracted_proj = extract_root / "SIRIUS"
        print(f"Successfully extracted {archive_path.name} to {extracted_proj}")

        # Check required files exist
        required = [
            "pyproject.toml",
            "README.md",
            "LICENSE",
            "CITATION.cff",
            ".gitignore",
            ".python-version",
            "candidate_ai/src/sparseprep/__init__.py",
            "candidate_ai/tests/test_model.py",
            "benchmarking/config/phase9_1_benchmark_plan.json",
            "benchmarking/schemas/run-record.schema.json",
            "benchmarking/runners/run_benchmarks.py",
            "benchmarking/runners/environment_probe.py",
            "benchmarking/adapters/authors_adapter.py",
            "benchmarking/analysis/aggregate.py",
            "reference/authors-artifact/official-artifact.zip",
        ]
        for req in required:
            p = extracted_proj / req
            if not p.exists():
                print(f"ERROR: Required file missing from archive: {req}", file=sys.stderr)
                return False

        # Run test import inside clean directory using current python
        res = subprocess.run(
            [sys.executable, "-c", "import sys; sys.path.insert(0, 'candidate_ai/src'); from sparseprep import SparseStateProblem, run_batched_isometry, run_malvetti_baseline; print('Clean extract import: PASS')"],
            cwd=extracted_proj,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            print(f"ERROR: Clean extract import failed:\n{res.stderr}", file=sys.stderr)
            return False
        print(res.stdout.strip())

        # Run plan validator in clean directory
        res2 = subprocess.run(
            [sys.executable, "scripts/phase9_1_validate.py", "--plan", "benchmarking/config/phase9_1_benchmark_plan.json"],
            cwd=extracted_proj,
            capture_output=True,
            text=True,
            check=False,
        )
        if res2.returncode != 0:
            print(f"ERROR: Clean extract plan validator failed:\n{res2.stderr}", file=sys.stderr)
            return False
        print("Clean extract plan validation: PASS")

    print("Archive integrity verification: ALL CHECKS PASSED!")
    return True


if __name__ == "__main__":
    archive, sha = build_archive()
    ok = verify_archive(archive)
    sys.exit(0 if ok else 1)
