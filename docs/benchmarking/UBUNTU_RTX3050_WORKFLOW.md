# Ubuntu RTX 3050 pilot workflow

The laptop plan is `benchmarking/config/ubuntu_laptop_pilot_v1.json`. It is a separate, versioned plan; the historical Phase 9.1 random-support plan is unchanged. The pilot selects 14 paper-track attempts and 48 symmetry-extension attempts (62 total), below the 64-attempt cap.

```bash
SIRIUS_PYTHON="$PWD/.venv-ubuntu-3.12/bin/python" bash scripts/ubuntu/preflight.sh
SIRIUS_PYTHON="$PWD/.venv-ubuntu-3.12/bin/python" bash scripts/ubuntu/run_laptop_pilot.sh
```

The runner uses one in-process CPU worker, a 180-second per-attempt timeout, and resource guards. It checkpoints each attempt by appending and syncing one JSONL record. Exact `job_id`s already present for the same run are not repeated on resume. Use `SIRIUS_RUN_ID=EXISTING_ID` to resume via the wrapper. The default GPU budget is at most 35% of currently free VRAM; execution is chunked, synchronized, CPU-parity checked, and records transfer/kernel/total intervals separately. GPU runs cover only emitted reversible gates over uint64 computational-basis rows. Construction and exact complex-statevector checks remain CPU work.

Generate summaries and plots after a run:

```bash
PYTHONPATH=candidate_ai/src "$SIRIUS_PYTHON" scripts/summarize_ubuntu_results.py --run-id RUN_ID
```

Run only one track with `scripts/ubuntu/run_campaign.sh paper_reproduction` or `scripts/ubuntu/run_campaign.sh symmetry_structured_sparse_supports`. `benchmarking/config/ubuntu_workstation_campaign_v1.json` defines later scaling/stress research workloads; it is not part of the laptop pilot and must be resource-reviewed before execution.
