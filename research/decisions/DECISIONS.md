# Decisions

1. Keep official authors' artifact and independent candidate in separate directories.
2. The original PDF is the scientific authority; Markdown/HTML guides are subordinate explanations.
3. Start Phase 1 with standard-library Python scripts; do not pull heavy quantum/GPU frameworks into setup.
4. Hardware probing tests a real CUDA operation through an installed backend when available. `nvidia-smi` alone is not a CUDA smoke test.
5. The current agent environment is a container with no `nvidia-smi`; it is not the user's RTX 3050.
6. CPU is the deterministic correctness reference/fallback; RTX 3050 CUDA is the primary local accelerator target per the roadmap.
7. Zenodo's official artifact archive is not included until the expected MD5 passes. A retrieval helper is provided because DNS was unavailable in the agent runtime.
8. No project algorithm is implemented in Phase 1. That work begins in later authorized phases.
9. Local Git bundle and commits are created for this candidate build; no remote operation is permitted.
