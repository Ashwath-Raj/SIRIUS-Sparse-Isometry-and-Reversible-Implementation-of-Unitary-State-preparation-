# Actual Phase 1 check results

- unit tests: PASS (exit 0) — `/opt/pyvenv/bin/python3 -m unittest discover -s tests -v`
- source verifier: PASS (exit 0) — `/opt/pyvenv/bin/python3 scripts/verify_sources.py`
- hardware probe: PASS (exit 0) — `/opt/pyvenv/bin/python3 scripts/hardware_probe.py --output environment/agent-probe.json`

The hardware probe is the agent container, not the user's RTX 3050. The agent container has no `nvidia-smi`.
