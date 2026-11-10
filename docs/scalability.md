# Scalability: what we measured

Everything here was measured with `backend/tools/loadtest.py` against the real API: each virtual user posts a prepared synthetic application and waits for the decision (policy, risk model, fraud, 15 controls, encrypted storage, audit write). The cases are synthetic, the feeds are simulated, and no bureau or bank latency is included, which in production dominates.

## Results

| Machine | Worker processes | Users | Decisions per second | p50 ms | p95 ms | Errors |
|---|---|---|---|---|---|---|
| Laptop (8 cores, busy with other apps) | 1 | 1 | 68 | 14 | 16 | 0 |
| Laptop | 1 | 8 | 53 to 58 | 106 to 130 | 153 to 302 | 0 |
| Laptop | 2 | 8 | 133 | 82 | 93 | 0 |
| Laptop | 4 | 8 | 185 | 46 | 64 | 0 |
| Free-tier cloud server (t3.micro, 2 vCPU, 1 GB) | 1 | 1 | 6.6 | 154 | 189 | 0 |
| Free-tier cloud server | 1 | 8 | 14.6 | 426 | 1,101 | 0 |
| Free-tier cloud server | 2 | 8 | not viable: out of memory | | | errors |

What these say, plainly:
- One process is CPU-bound. More users do not add throughput, they add queueing, so latency rises with the queue.
- Adding worker processes scales it: on the laptop about 2x with two workers and about 3x with four, with no errors, one hash chain, and exactly one key per case.
- The 1 GB free-tier server runs one worker. Two do not fit in memory. It decides at roughly 7 to 15 a second, about ten times slower than the laptop.
- These are 12-second bursts. A burstable cloud instance (t3) earns CPU credits and is throttled when they run out, so its sustained rate is lower than what we measured. We did not measure sustained load.
- For scale: one million decisions a day is 11.6 a second on average. Peak-to-average ratio, bureau latency and database size would decide the real number. We have not shown one million a day.

## What makes it scale out

- **Stateless workers.** A worker holds no case data that another cannot rebuild. The audit database is the source of truth; each worker projects it into memory and catches up from it on a cache miss or a list call (`_sync_cases`). Tested: a case made by one worker is served and reviewed by another.
- **One transactional store.** The audit log and the key vault are SQLite (WAL). An append reads the current head hash inside a `BEGIN IMMEDIATE` transaction, so concurrent writers cannot fork the chain. Case keys are created with an atomic get-or-create, so two workers racing on the same case end up with the same key. Erasure by one worker is seen by all at once.
- **The honest limit.** SQLite serves workers on one machine. Several machines need Postgres with the same schema (a locked head row in place of `BEGIN IMMEDIATE`). That move is a storage change, not a redesign, but it is not built.
- **Durable workflow.** With Temporal the stages run as retried activities on any number of workers (`ops/start.sh`); the hosted demo runs without it.

## Bugs the load test found (and fixed)

1. **Lost case keys under several workers.** The key store was a JSON file that every process rewrote whole, so two workers could overwrite each other's keys and make a case unreadable forever. Keys are now rows in SQLite.
2. **Startup race.** Several processes creating the session key, the master key or the database at the same moment crashed one of them. Creation is now race-safe and retried. Tests start real processes together.
3. **Case table in private memory.** A second worker could not see cases made by the first. Cases are now a projection of the shared audit database.

## Reproduce

```bash
cd backend
GRIHA_API_LIMIT=1000000 GRIHA_ORCHESTRATOR=inline GRIHA_DATA_DIR=/tmp/lt uv run uvicorn griha.api:app --port 8001 --workers 2
uv run python -m tools.loadtest --url http://127.0.0.1:8001 --levels 1,4,8 --seconds 12
```

## Sustained run (10 Nov 2026)
A 120-second closed-loop run on the laptop, 2 worker processes, 8 virtual users, inline orchestrator, synthetic applications:

| Decisions | Per second | p50 | p95 | p99 | Errors |
|---|---|---|---|---|---|
| 13,718 | 113.7 | 93 ms | 136 ms | 170 ms | 0 |

- The hash chain verified afterwards: 13,718 entries, intact, in about 2 seconds, so concurrent writers from two processes did not corrupt it.
- The audit database grew to 282 MB, roughly 20 KB per decision. A million decisions would be about 20 GB, so retention and archiving would be needed well before that.
- This is a laptop and two minutes, not the free-tier server, and not a day of traffic. It supports "no errors or chain breaks under sustained concurrent load", not a daily capacity claim.
