# Phase 1 validation record

This file is an execution record for the package-building agent container, not the user's RTX 3050 laptop.

## Environment inspection (agent runtime)

- OS: Linux x86_64 container.
- Kernel: `6.18.57+` (see captured agent report).
- Python: 3.13.5.
- CPU exposed to container: AMD EPYC 9V74, 5 logical CPUs exposed by container.
- RAM visible to container: approximately 5.8 GiB.
- `nvidia-smi`: unavailable in this runtime.
- CUDA device: not detected in this runtime.
- User's RTX 3050: not accessed; local validation remains pending.

## Zenodo artifact

Official record was inspected. Record identifies the exact ZIP and MD5. Binary download from this container failed because DNS resolution for `zenodo.org` was unavailable. Run the included fetch script on the Ubuntu laptop.

## Test commands

Run from repository root:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/verify_sources.py
python3 scripts/hardware_probe.py --output environment/laptop-hardware.json
python3 scripts/hardware_probe.py --require-cuda --output environment/laptop-hardware.json
```

The final command is expected to pass only on a host where one of PyTorch, CuPy, or Numba CUDA is installed and can execute a validated CUDA kernel.
