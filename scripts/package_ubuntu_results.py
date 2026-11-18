#!/usr/bin/env python3
"""Package one completed, track-separated machine run without touching raw data."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--machine-id", default="ubuntu-amd-ryzen6600h-rtx3050-laptop")
    parser.add_argument("--archive-suffix", default="")
    args = parser.parse_args()
    result_files = [
        Path("results/raw") / args.machine_id / "paper_reproduction" / f"{args.run_id}.jsonl",
        Path("results/raw") / args.machine_id / "extensions/symmetry_structured_sparse_supports" / f"{args.run_id}.jsonl",
    ]
    expected_tracks = ("paper_reproduction", "symmetry_structured_sparse_supports")
    record_counts = {}
    for rel, track in zip(result_files, expected_tracks):
        path = ROOT / rel
        if not path.is_file(): raise SystemExit(f"missing raw evidence: {rel}")
        rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
        if not rows or any(r.get("run_id") != args.run_id or r.get("track") != track for r in rows):
            raise SystemExit(f"raw lane identity mismatch: {rel}")
        record_counts[track] = len(rows)
    prefixes = [
        Path("results/raw") / args.machine_id,
        Path("results/summaries") / args.machine_id,
        Path("results/tables") / args.machine_id,
        Path("results/figures") / args.machine_id,
        Path("results/manifests") / args.machine_id,
        Path("results/logs") / args.machine_id,
        Path("results/reports") / args.machine_id,
        Path("results/checkpoints") / args.machine_id,
    ]
    candidates = []
    for prefix in prefixes:
        absolute = ROOT / prefix
        if not absolute.exists(): continue
        for path in absolute.rglob("*"):
            if path.is_file() and args.run_id in path.name:
                candidates.append(path.relative_to(ROOT))
    candidates.extend(result_files)
    candidates += [Path("docs/research/UBUNTU_3050_PILOT_REPORT.md"), Path("docs/research/SYMMETRY_STRUCTURED_SUPPORTS.md"),
                   Path("benchmarking/config/ubuntu_laptop_pilot_v1.json")]
    candidates = sorted(set(candidates))
    suffix = f"_{args.archive_suffix}" if args.archive_suffix else ""
    archive = ROOT / "dist" / f"SIRIUS_UBUNTU_3050_PILOT_RESULTS_{args.machine_id}_{args.run_id}{suffix}.zip"
    checksum = archive.with_suffix(archive.suffix + ".sha256")
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists() or checksum.exists(): raise SystemExit(f"refusing to overwrite existing result archive: {archive}")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for rel in candidates:
            path = ROOT / rel
            if not path.is_file(): raise SystemExit(f"missing expected package file: {rel}")
            zf.write(path, (Path("SIRIUS_RESULTS") / rel).as_posix())
    with zipfile.ZipFile(archive) as zf:
        bad = zf.testzip()
        if bad: raise SystemExit(f"archive integrity error: {bad}")
        members = zf.namelist()
        for rel in result_files:
            if f"SIRIUS_RESULTS/{rel.as_posix()}" not in members: raise SystemExit(f"missing archived raw lane: {rel}")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum.write_text(f"{digest}  {archive.name}\n")
    print(json.dumps({"archive": str(archive.relative_to(ROOT)), "bytes": archive.stat().st_size, "sha256": digest,
                      "record_counts": record_counts, "members": len(candidates)}, indent=2))
    return 0

if __name__ == "__main__": raise SystemExit(main())
