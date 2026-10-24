# Local setup

Use macOS or Linux with Python 3.11+, Node.js 22.12+ (24 recommended), Git, and Java 17. `make setup` installs the Python environment and frontend packages and can download project-local Java/Node runtimes. Spark and Java together require roughly 650 MB of downloads; Ollama model weights are optional and larger. Windows is supported through WSL2.

```bash
git clone https://github.com/joshuadominic0598/data-pipeline-recovery-agent.git
cd data-pipeline-recovery-agent
make setup
make start
```

The app opens at [127.0.0.1:8180](http://127.0.0.1:8180). It runs one Spark worker. Start only one server for each `STATE_DIR`. Run `make build` after frontend changes and restart the server. `Ctrl+C` stops the server; pending approvals remain on disk.

## Local model

Install [Ollama](https://ollama.com/) and run:

```bash
ollama pull qwen3:8b
```

Choose **Local model · Qwen** in the dashboard. The model uses Ollama's tool API to select diagnostics and propose a reviewed repair. It does not generate unrestricted Python. If the model is unavailable or exceeds its budget, the incident becomes **Blocked**; there is no silent fallback. Select **Runbook · deterministic** for the same real Spark/code/deployment flow without an LLM. This mode is explicitly labelled throughout the trace.

Configuration is in `.env`, copied from `.env.example`. `AGENT_MAX_TURNS` is capped at 10 and `AGENT_TIMEOUT_SECONDS` at 180 seconds per model request. Two explicit operator retries are allowed for blocked runs. Local inference has no API bill; hardware, electricity, and downloads still use resources.

## Daily data

Every partition has 192 deterministic synthetic hospital shipment events across four fictional facilities and three fictional cold-chain products. A different day creates a different batch. Raw JSON landing snapshots and their checksums are retained. Source simulation uses Python; every tabular transformation, join, business rule, profile, and validation uses PySpark DataFrames.

Set `DAILY_SCHEDULE_ENABLED=true` to run a healthy refresh daily at `DAILY_HOUR_IST` (default 07:00 Asia/Kolkata). The process must stay running. A restart after the scheduled hour catches up today's partition once using a persistent idempotency key; it does not invent jobs for every day the computer was off. No scheduler or cloud automation is installed outside the app.

`WEATHER_LIVE=true` (the default) enriches today's batch with daily maximum ambient temperature forecasts from [Open-Meteo](https://open-meteo.com/en/docs). Set it to `false` for a fully offline demo. This public feed is optional, requires no key for the documented free non-commercial use, and is cached in the source snapshot. Historical partitions and network failures use explicitly labelled synthetic weather. Shipments are always synthetic. Open-Meteo attribution is saved in the manifest. Weather affects context, not the medical release decision. This is a daily batch demonstration, not a continuous event stream.

## Gmail

The default **outbox** mode persists failure, approval, rejection, and recovery notifications addressed to `NOTIFY_TO`. Nothing is sent automatically without app-owned credentials. The Notifications page shows delivery state; queued messages are not called sent.

For autonomous Gmail delivery, create your own Google OAuth client and obtain an offline refresh token with the `https://www.googleapis.com/auth/gmail.send` scope for the intended sending account. Follow [Google's OAuth guide](https://developers.google.com/identity/protocols/oauth2/web-server) and [Gmail sending guide](https://developers.google.com/workspace/gmail/api/guides/sending). Put these values in the ignored `.env` file:

```dotenv
EMAIL_MODE=gmail
GMAIL_CLIENT_ID=your-client-id
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REFRESH_TOKEN=your-refresh-token
NOTIFY_TO=joshuadominic747@gmail.com
```

Restart after configuration. The next worker cycle flushes queued notifications. Deliberately captured test messages are also queued, so review the outbox before enabling delivery. A send attempt is marked before the network request. An ambiguous result is retained as `delivery_unknown` and is not blindly retried. Outbox uniqueness prevents duplicate notifications for the same run/event. Delivery is at-most-one automatic attempt, not exactly-once email delivery. App-owned Gmail authorization is separate from the connected Gmail account in Codex; connector credentials cannot be exported into this app.

## Validation

```bash
make test
make lint
make evaluate                         # real Spark, deterministic investigator
python3 scripts/run.py evaluate --mode ollama --output artifacts/ollama-evaluation.json
```

Evaluations explicitly act as a test owner to approve policy-gated candidates. Application runs always stop for an actual operator decision. Results are written locally under `artifacts/` and excluded from Git. The UI metrics use recorded runs and known injected causes, with elapsed time including approval waits. They are demonstration measurements, not production reliability claims.

Tests and evaluations force outbox mode and cannot send Gmail messages, even if the interactive app is configured for delivery.

State lives in `.state/`: SQLite, raw snapshots, Parquet checkpoints, quarantine outputs, tested code, local Git histories, releases, and the published-data pointer. Treat this directory as private runtime state. The repository contains only synthetic-generation code and sanitized evidence.

GitHub Actions is **manual-only**. Pushing this repository does not start a hosted job. If you run the workflow yourself, check your GitHub plan's included runner minutes first. All checks can run locally without hosted runners.
