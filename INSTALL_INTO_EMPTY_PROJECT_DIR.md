# Install this Phase 1 workspace into the supplied Ubuntu project directory

The user-provided target directory was:

```text
~/Acadimics/3.Semister3/Projects/Sparse Quantum State Preperation Reduced TOffi COst/SPeed Run
```

The environment that assembled this package cannot directly access that host path. On the Ubuntu laptop, extract the workspace archive into that **empty** directory.

Example (adjust the download location if your browser saves elsewhere):

```bash
PROJECT_DIR="$HOME/Acadimics/3.Semister3/Projects/Sparse Quantum State Preperation Reduced TOffi COst/SPeed Run"
mkdir -p "$PROJECT_DIR"
unzip -q Sparse_State_Preparation_Phase_1_Bundle.zip -d "$PROJECT_DIR"
cd "$PROJECT_DIR"
```

The ZIP has a single top-level folder. Move its contents into the supplied directory:

```bash
shopt -s dotglob
mv Sparse-State-Preparation-Phase-1/* .
rmdir Sparse-State-Preparation-Phase-1
```

The ZIP includes `.git/` and the independent `handoff/phase-01.bundle`, so commit history is present twice: the extracted working repository and a separately verifiable bundle. Verify:

```bash
git status --short --branch
git log --oneline --decorate -10
git remote -v
```

There should be no remote configured. No push has been performed.

Run the local validation suite:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/verify_sources.py
python3 scripts/hardware_probe.py --output environment/laptop-hardware.json
python3 scripts/hardware_probe.py --require-cuda --output environment/laptop-hardware.json
```

`--require-cuda` must pass on the RTX 3050 only after one installed CUDA backend executes a real kernel and validates the output. If it fails, share the complete probe JSON and the output of `nvidia-smi`; do not mark CUDA validation complete.

Fetch the official reference artifact:

```bash
python3 scripts/fetch_reference_artifact.py --output reference/authors-artifact/official-artifact.zip
```

The script verifies the Zenodo-recorded MD5. Do not extract or run the official artifact until this verification succeeds. Preserve its `uv.lock` unchanged.
