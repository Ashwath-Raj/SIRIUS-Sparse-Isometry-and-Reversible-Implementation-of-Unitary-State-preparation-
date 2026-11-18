# Resumable campaigns

Every attempt is appended to its track-specific canonical JSONL file and flushed with `fsync`. The run manifest records selected jobs, selection seed, exclusions, plan version, and machine manifest. A stable `job_id` hashes the full job description.

Resume by rerunning with the exact same run ID:

```bash
PYTHONPATH=candidate_ai/src .venv/bin/python scripts/run_ubuntu_campaign.py --run-id pilot-EXISTING-ID
```

Already-recorded job IDs are not re-executed. Failed, skipped, timed-out, and schema-invalid records remain immutable attempts. To retry failures, begin a new run ID; this keeps every attempt auditable and prevents duplicate-job pooling. Interruption between jobs leaves a valid prefix that can resume. A job that exceeds the 180-second limit is recorded as `timed_out`; resource-guard skips remain visible.
