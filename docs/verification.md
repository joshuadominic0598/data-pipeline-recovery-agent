# Verification

Measured locally on **25 October 2026** with macOS arm64, Python 3.12.14, Java 17.0.21, PySpark 4.0.1, and Qwen3 8B through Ollama. These results cover known synthetic failures, not production generalization.

## Automated checks

- **18 tests passed** with actual Spark execution.
- Frontend TypeScript checks and Vite production build passed.
- Ruff checks passed for backend, tests, scripts, and Databricks reference notebooks.
- Five injected failures exercised diagnosis, isolated testing, release creation, checkpoint reuse, and downstream verification.
- Additional checks covered healthy runs without edits, exact output equivalence after replay deduplication, rejected/stale approvals, changed inputs after approval, whole-module patch enforcement, trigger/outbox idempotency, and HTTP host/origin/operator boundaries.
- A successful Spark write containing duplicate rows and corrupt usable inventory failed independent quality validation.

One dependency deprecation warning was emitted by Starlette's current HTTPX test-client integration; it did not fail any check. Hosted GitHub Actions and Databricks validation were not run.

## Live model evaluation

The final recorded evaluation used the five failure cases in one pass. The investigator saw failure/tool evidence, not scenario labels. The harness explicitly supplied owner approval for the two gated repairs.

| Failure | Correct diagnosis | Verified recovery | Elapsed | Total model tokens |
|---|---|---|---:|---:|
| Renamed source column | Yes | Yes | 15.05 s | 3,208 |
| Exact replay duplicates | Yes | Yes | 9.69 s | 3,017 |
| Missing partition | Yes | Yes | 10.17 s | 3,048 |
| Invalid source values | Yes | Yes | 12.89 s | 3,508 |
| Unavailable registry | Yes | Yes | 8.66 s | 3,066 |

**5/5 correct diagnoses, 5/5 verified recoveries, zero mismatched-cause deployments.** Every final scenario used two model turns. Local model API charges were $0; hardware/electricity are excluded. Timing includes local Spark operations and the harness's immediate approvals, not a real human wait. See the [machine-readable evidence](evidence/model-evaluation.json).

An earlier evaluation recovered three cases and stopped two when the model failed to submit an eligible recipe within its tool budget. The policy withheld deployment. The final implementation feeds evidence-eligible recipe IDs back to the model and retains every rejection in the trace. One passing five-case evaluation is not a reliability estimate.

## Live application checks

- A browser-triggered schema-drift incident used the local Qwen model and recovered with all seven production quality checks passing.
- A browser-triggered dependency incident passed sandbox tests and paused for approval. The server process was terminated and restarted while it waited. The same saved proposal remained pending; browser approval then resumed from business rules, reusing ingestion/cleaning/preprocessing checkpoints, and recovered.
- The connected Gmail account accepted one failure and one recovery message addressed to the requested owner account. Receipts were recorded in the local outbox. These two demonstration sends used the Codex Gmail connector; autonomous app delivery still requires its own OAuth credentials.
- The public Open-Meteo endpoint returned current-day forecasts for all four locations; source generation saved the provider attribution in its manifest.

Browser layout, approval controls, code/quality/data views, run history, guardrails, notifications, and trace export were inspected at desktop and narrow viewports. Screenshots are retained under `docs/screenshots/`. Browser inspection is a recorded manual check, not a committed automated browser test suite.

## Remaining production work

No cloud workspace was deployed, no real upstream service was repaired, and no actual hospital data was used. The Databricks notebook/bundle path needs workspace validation plus the identity-backed approval and promotion service described in the [Databricks guide](databricks.md). Arbitrary code repair, distributed orchestration, and enterprise authentication are outside the delivered local scope.
