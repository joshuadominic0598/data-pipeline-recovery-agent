import React from "react";
import {
  Activity,
  ArrowRight,
  Check,
  CheckCheck,
  ChevronRight,
  CircleDot,
  Database,
  ExternalLink,
  Layers3,
  LoaderCircle,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  Workflow,
  Zap,
} from "lucide-react";
import { Badge, Stat } from "../components/ui";
import { RecoveryTrace } from "../components/RecoveryTrace";
import { RunInspector } from "../components/RunInspector";
import { api } from "../lib/api";
import { pretty, stages, stageLabels } from "../lib/presentation";
import type { Obj, Run } from "../types";

export function MissionControl({
  config,
  runs,
  run,
  awaiting,
  selected,
  setRun,
  setSelected,
  evaluation,
  scenario,
  setScenario,
  day,
  setDay,
  mode,
  setMode,
  model,
  submitting,
  trigger,
  decide,
  filter,
  setFilter,
  follow,
  setFollow,
  timelineRef,
  tab,
  setTab,
  setError,
  recovered,
  active,
  trace,
  report,
}: {
  config: Obj | undefined;
  runs: Run[];
  run: Run | undefined;
  awaiting: number;
  selected: string | undefined;
  setRun: (run: Run | undefined) => void;
  setSelected: (id: string) => void;
  evaluation: Obj | undefined;
  scenario: string;
  setScenario: (scenario: string) => void;
  day: string;
  setDay: (day: string) => void;
  mode: string;
  setMode: (mode: string) => void;
  model: Obj | undefined;
  submitting: boolean;
  trigger: () => Promise<void>;
  decide: (approve: boolean) => Promise<void>;
  filter: string;
  setFilter: (filter: string) => void;
  follow: boolean;
  setFollow: (follow: boolean) => void;
  timelineRef: React.RefObject<HTMLDivElement | null>;
  tab: string;
  setTab: (tab: string) => void;
  setError: (message: string) => void;
  recovered: number;
  active: boolean | undefined;
  trace: Obj[];
  report: Obj | undefined;
}) {
  const isAwaiting = run?.status === "awaiting_approval";
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="tiny-line" /> OPERATIONS, UNINTERRUPTED
          </div>
          <h1>Every pipeline deserves a recovery.</h1>
          <p>
            From a broken daily feed to trusted hospital supply intelligence.
            Watch the agent work.
          </p>
        </div>
        <a
          className="text-link"
          href="https://github.com/joshuadominic0598/data-pipeline-recovery-agent"
          target="_blank"
          rel="noreferrer"
        >
          View source <ExternalLink size={14} />
        </a>
      </div>
      <section className="hero">
        <div className="hero-copy">
          <div className="hero-kicker">
            <span className="small-dot" /> HOSPITAL COLD CHAIN{" "}
            <span className="hero-tag">DAILY REFRESH</span>
          </div>
          <h2>
            A delayed feed.
            <br />
            <span>Not a delayed decision.</span>
          </h2>
          <p>
            Shipments, sensor readings, and product references become a
            validated data product. When a stage breaks, recovery starts.
          </p>
          <div className="hero-meta">
            <span>
              <Database size={14} />
              192 daily shipment events
            </span>
            <span>
              <Layers3 size={14} />5 PySpark stages
            </span>
            <span>
              <ShieldCheck size={14} />7 quality gates
            </span>
          </div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="orbit orbit-three" />
          <div className="pulse-core">
            <Activity size={47} />
          </div>
          <div className="orbit-label label-one">
            <Database size={14} />
            Source feed
          </div>
          <div className="orbit-label label-two">
            <Sparkles size={14} />
            Recovery agent
          </div>
          <div className="orbit-label label-three">
            <CheckCheck size={14} />
            Trusted data
          </div>
          <div className="hero-art-caption">
            <span className="small-dot" /> DETECT. REPAIR. VERIFY. RESUME.
          </div>
        </div>
      </section>
      <div className="stats">
        <Stat
          label="Verified recoveries"
          value={String(recovered).padStart(2, "0")}
          note={`${runs.length} total pipeline runs`}
          icon={<RotateCcw size={17} />}
        />
        <Stat
          label="Diagnosis accuracy"
          value={
            evaluation?.completed
              ? `${Math.round((evaluation.correct_diagnosis / evaluation.completed) * 100)}%`
              : "—"
          }
          note={
            evaluation?.completed
              ? `Across ${evaluation.completed} completed incidents`
              : "Measured against injected causes"
          }
          icon={<CircleDot size={17} />}
        />
        <Stat
          label="Waiting for a human"
          value={String(awaiting).padStart(2, "0")}
          note="Changes that need your judgment"
          icon={<ShieldCheck size={17} />}
        />
        <Stat
          label="Inference API spend"
          value={`$${runs.reduce((n, r) => n + (r.agent_metrics?.cost_usd || 0), 0).toFixed(2)}`}
          note="Local inference · hardware excluded"
          icon={<Zap size={17} />}
        />
      </div>
      <section className="panel launch-panel">
        <div className="section-title">
          <div>
            <span className="section-icon">
              <Play size={16} />
            </span>
            <h3>Launch a daily refresh</h3>
          </div>
          <span className="muted small">
            Fictional logistics data · no patient data
          </span>
        </div>
        <div className="launch-controls">
          <label className="scenario-control">
            Scenario
            <select
              aria-label="Failure scenario"
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
            >
              {config &&
                Object.entries(config.scenarios).map(([id, s]: any) => (
                  <option value={id} key={id}>
                    {s.label}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Partition date
            <input
              aria-label="Partition date"
              type="date"
              value={day}
              max={config?.today}
              onChange={(e) => setDay(e.target.value)}
            />
          </label>
          <label>
            Investigator
            <select
              aria-label="Investigator"
              value={mode}
              onChange={(e) => setMode(e.target.value)}
            >
              <option value="ollama">Local model · Qwen</option>
              <option value="runbook">Runbook · deterministic</option>
            </select>
          </label>
          <button
            className="primary"
            disabled={!config || submitting}
            onClick={trigger}
          >
            {submitting ? (
              <LoaderCircle className="spin" size={16} />
            ) : (
              <Play size={15} />
            )}
            Trigger pipeline
            <ArrowRight size={15} />
          </button>
        </div>
        <div className="launch-foot">
          <span>
            <TriangleAlert size={13} />
            {config?.scenarios?.[scenario]?.description ||
              "Loading source scenarios…"}
          </span>
          <span
            className={
              mode === "ollama" && !model?.available ? "amber" : "muted"
            }
          >
            <span className="small-dot" />
            {mode === "runbook"
              ? "No model required"
              : model?.available
                ? `${model.model} connected`
                : "Ollama model unavailable · use runbook mode"}
          </span>
        </div>
      </section>
      <div className="run-heading">
        <div>
          <h3>Live workflow</h3>
          {run ? (
            <>
              <span className="mono muted">{run.id}</span>
              <Badge status={run.status} />
            </>
          ) : (
            <span className="muted">Ready for the first run</span>
          )}
        </div>
        {runs.length > 0 && (
          <select
            aria-label="Select pipeline run"
            value={selected}
            onChange={(e) => {
              setRun(undefined);
              setSelected(e.target.value);
            }}
          >
            {runs.map((r) => (
              <option value={r.id} key={r.id}>
                {r.id} · {pretty(r.scenario)}
              </option>
            ))}
          </select>
        )}
      </div>
      <section className="panel pipeline-map">
        {stages.map((stage, i) => {
          const state = run?.stages?.[stage] || "pending";
          return (
            <React.Fragment key={stage}>
              <div className={"stage " + state}>
                <span className="stage-node">
                  {state === "passed" ? (
                    <Check size={19} />
                  ) : state === "failed" ? (
                    <TriangleAlert size={18} />
                  ) : state === "running" ? (
                    <LoaderCircle className="spin" size={18} />
                  ) : i === 0 ? (
                    <Database size={18} />
                  ) : i === 4 ? (
                    <Layers3 size={18} />
                  ) : (
                    <Workflow size={18} />
                  )}
                </span>
                <div>
                  <span className="stage-number">0{i + 1}</span>
                  <strong>{stageLabels[i]}</strong>
                  <small>
                    {state === "pending"
                      ? "Waiting"
                      : state === "passed"
                        ? "Checkpoint saved"
                        : state === "failed"
                          ? "Recovery activated"
                          : "Processing"}
                  </small>
                </div>
              </div>
              {i < 4 && (
                <div
                  className={
                    "stage-connector " + (state === "passed" ? "passed" : "")
                  }
                >
                  <ChevronRight size={12} />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </section>
      {isAwaiting && (
        <section className="approval-callout">
          <div className="approval-symbol">
            <ShieldCheck size={25} />
          </div>
          <div>
            <span className="eyebrow">YOUR JUDGMENT, AT THE RIGHT MOMENT</span>
            <h3>Tested repair. Waiting for your approval.</h3>
            <p>
              {run.proposal.impact} All sandbox checks passed. This checkpoint
              survives a restart.
            </p>
          </div>
          <div className="approval-actions">
            <button
              className="secondary"
              disabled={submitting}
              onClick={() => decide(false)}
            >
              Reject
            </button>
            <button
              className="primary"
              disabled={submitting}
              onClick={() => decide(true)}
            >
              <ShieldCheck size={15} />
              Approve & resume
            </button>
          </div>
        </section>
      )}
      {run?.status === "blocked" && (
        <div className="blocked-callout">
          <TriangleAlert size={18} />
          <div>
            <strong>Recovery needs an owner</strong>
            <p>{run.blocker}</p>
          </div>
          <button
            className="secondary"
            disabled={run.manual_retries >= 2}
            onClick={() =>
              api(`/runs/${run.id}/retry`, {}).catch((e) => setError(e.message))
            }
          >
            Retry investigation
          </button>
        </div>
      )}
      <div className="workbench">
        <RecoveryTrace
          run={run}
          filter={filter}
          setFilter={setFilter}
          follow={follow}
          setFollow={setFollow}
          timelineRef={timelineRef}
          active={active}
          trace={trace}
        />
        <RunInspector run={run} tab={tab} setTab={setTab} report={report} />
      </div>
      <footer className="page-footer">
        <span>BUILT TO RECOVER. DESIGNED TO EXPLAIN.</span>
        <span>
          Real Spark execution <i /> Local Git releases <i /> Cloud promotion
          blueprint
        </span>
      </footer>
    </>
  );
}
