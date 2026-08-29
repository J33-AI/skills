# Why We Stopped Trusting Retry Counts

Our ingestion worker retried failed jobs three times and then gave up. For two
years that looked fine on the dashboard: the retry counter stayed low, the
failure rate stayed under one percent, and nobody looked closer.

Then a customer asked why an invoice from March had never arrived.

The worker pulled a job off Redis, called the vendor API, and on a non-2xx
response incremented `attempts` and pushed the job back. The bug was that the
increment happened in the worker, not in Redis. When the worker itself died —
OOM, deploy, spot reclaim — the job went back on the queue with `attempts`
still at whatever it had been when the worker read it. A job that crashed the
worker every time would retry forever and never once show up as a failure,
because it never reached the third increment.

```python
job = redis.blpop("ingest")
try:
    call_vendor(job)
except VendorError:
    job["attempts"] += 1          # lives only in this process
    if job["attempts"] < 3:
        redis.rpush("ingest", job)
```

We moved the counter into Redis with `HINCRBY`, keyed by job id, with a TTL
longer than the longest plausible retry window. The counter now survives the
worker. Within a day we found 41 jobs that had been circulating for months.

The lesson is not "use HINCRBY". It is that a retry counter held in the
process doing the retrying cannot count the failures that kill the process.
