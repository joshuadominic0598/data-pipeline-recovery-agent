import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  Bell,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleDot,
  Clock3,
  Code2,
  Database,
  ExternalLink,
  FlaskConical,
  GitCommitHorizontal,
  Layers3,
  LoaderCircle,
  Mail,
  Play,
  Radio,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Terminal,
  TriangleAlert,
  Workflow,
  X,
  Zap,
} from "lucide-react";
import "./style.css";

type Obj = Record<string, any>;
type Run = Obj & {
  id: string;
  status: string;
  date: string;
  scenario: string;
  stages: Obj;
  events?: Obj[];
  emails?: Obj[];
};
const stages = [
  "ingestion",
  "cleaning",
  "preprocessing",
  "business_rules",
  "consumption",
];
const stageLabels = ["Ingest", "Clean", "Preprocess", "Apply rules", "Publish"];
const busy = [
  "queued",
  "running",
  "investigating",
  "testing",
  "approved",
  "applying",
  "verifying",
];
const pretty = (s: string) =>
  s.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
const time = (s?: string) =>
  s
    ? new Date(s).toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        timeZone: "Asia/Kolkata",
      })
    : "—";
let operatorToken = "";
async function api(path: string, body?: Obj) {
  const r = await fetch(
    "/api" + path,
    body
      ? {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Operator-Token": operatorToken,
          },
          body: JSON.stringify(body),
        }
      : {},
  );
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(e.detail || "Request failed");
  }
  return r.json();
}

function Badge({ status }: { status: string }) {
  return (
    <span className={"badge " + status}>
      <i />
      {pretty(status)}
    </span>
  );
}
function Json({ value }: { value: any }) {
  return <pre className="json">{JSON.stringify(value, null, 2)}</pre>;
}
function App() {
  const [config, setConfig] = useState<Obj>();
  const [runs, setRuns] = useState<Run[]>([]);
  const [selected, setSelected] = useState<string>();
  const [run, setRun] = useState<Run>();
  const [page, setPage] = useState("Mission control");
  const [scenario, setScenario] = useState("schema_drift");
  const [day, setDay] = useState("");
  const [mode, setMode] = useState("ollama");
  const [filter, setFilter] = useState("all");
  const [follow, setFollow] = useState(true);
  const timelineRef = useRef<HTMLDivElement>(null);
  const [tab, setTab] = useState("Repair");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [model, setModel] = useState<Obj>();
  const [evaluation, setEvaluation] = useState<Obj>();
  const [policy, setPolicy] = useState<Obj>();
  const [emails, setEmails] = useState<Obj[]>([]);
  useEffect(() => {
    api("/bootstrap")
      .then((c) => {
        operatorToken = c.operator_token;
        setConfig(c);
        setDay(c.today);
        setMode(c.default_mode);
      })
      .catch((e) => setError(e.message));
    api("/model").then(setModel);
    api("/policy").then(setPolicy);
  }, []);
  useEffect(() => {
    let cancelled = false;
    const refresh = async () => {
      try {
        const rs = await api("/runs");
        if (cancelled) return;
        setRuns(rs);
        if (!selected && rs.length) setSelected(rs[0].id);
        if (selected) {
          const r = await api("/runs/" + selected);
          if (!cancelled) setRun(r);
        }
        const ev = await api("/evaluation");
        if (!cancelled) setEvaluation(ev);
        if (page === "Notifications") {
          const em = await api("/notifications");
          if (!cancelled) setEmails(em);
        }
      } catch (e: any) {
        if (!cancelled) setError(e.message);
      }
    };
    refresh();
    const id = setInterval(refresh, 1500);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [selected, page]);
  async function trigger() {
    setSubmitting(true);
    setError("");
    try {
      const r = await api("/runs", {
        scenario,
        date: day,
        agent_mode: mode,
        request_key: crypto.randomUUID(),
      });
      setRun(undefined);
      setSelected(r.id);
      setPage("Mission control");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }
  async function decide(approve: boolean) {
    if (!run) return;
    setSubmitting(true);
    try {
      await api(`/runs/${run.id}/decision`, {
        digest: run.proposal.digest,
        approve,
        actor: "Local pipeline owner",
      });
      setRun(await api("/runs/" + run.id));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }
  const report = run?.report || run?.sandbox;
  const events = run?.events || [];
  const trace =
    filter === "agent"
      ? events.filter((e) =>
          [
            "agent",
            "model",
            "tool_start",
            "tool_result",
            "diagnosis",
            "proposal",
            "policy",
            "policy_rejection",
            "approval",
            "human_decision",
          ].includes(e.kind),
        )
      : events;
  const active = run && busy.includes(run.status);
  const recovered = runs.filter((r) => r.status === "recovered").length;
  const awaiting = runs.filter((r) => r.status === "awaiting_approval").length;
  const isAwaiting = run?.status === "awaiting_approval";
  useEffect(() => {
    if (follow && timelineRef.current) {
      timelineRef.current.scrollTop = timelineRef.current.scrollHeight;
    }
  }, [run?.events?.length, follow, filter, page]);
  const metrics = report?.metrics;
  return (
    <div className="shell">
      <aside className="sidebar">
        <a
          href="#"
          aria-label="VitalRoute mission control"
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            setPage("Mission control");
          }}
        >
          <span className="brandmark">
            <Activity size={23} />
          </span>
          <span>
            vitalroute<span className="brand-dot">.</span>
            <small>DATA RECOVERY AGENT</small>
          </span>
        </a>
        <div className="workspace">
          <span className="workspace-avatar">V</span>
          <span>
            Healthcare operations<small>Local workspace</small>
          </span>
          <ChevronDown size={14} />
        </div>
        <p className="nav-label">WORKSPACE</p>
        <nav>
          {[
            ["Mission control", Workflow],
            ["Run history", Clock3],
            ["Guardrails", ShieldCheck],
            ["Notifications", Bell],
          ].map(([label, Icon]: any) => (
            <button
              key={label}
              aria-label={label}
              title={label}
              onClick={() => setPage(label)}
              className={page === label ? "selected" : ""}
            >
              <Icon size={17} />
              <span>{label}</span>
              {label === "Notifications" && awaiting > 0 && <b>{awaiting}</b>}
            </button>
          ))}
        </nav>
        <div className="sidebar-section">
          <p className="nav-label">
            YOUR PIPELINE <span>01</span>
          </p>
          <button
            className="pipeline-nav"
            onClick={() => setPage("Mission control")}
          >
            <span className="small-dot" />
            <span>
              Cold-chain intelligence<small>Daily hospital supply feed</small>
            </span>
          </button>
        </div>
        <div className="sidebar-bottom">
          <div className="local-card">
            <Radio size={17} />
            <span>
              Runs on your machine<small>PySpark · SQLite · Ollama</small>
            </span>
            <span className="small-dot" />
          </div>
          <div className="user">
            <div className="avatar">JD</div>
            <span>
              Joshua Dominic<small>Pipeline owner</small>
            </span>
            <ShieldCheck size={16} />
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <span className="breadcrumb">Workspace</span>
            <ChevronRight size={14} />
            <strong>{page}</strong>
          </div>
          <div className="topbar-right">
            <span className="env">
              <span className="small-dot" />
              LOCAL DEMO
            </span>
            <span className="divider" />
            <span className="clock">IST · {config?.today || "Connecting"}</span>
            <button
              className="icon-button"
              aria-label="View notifications"
              onClick={() => setPage("Notifications")}
            >
              <Bell size={18} />
            </button>
          </div>
        </header>
        <div className="content">
          {error && (
            <div role="alert" className="error-banner">
              <TriangleAlert size={16} />
              {error}
              <button onClick={() => setError("")} aria-label="Dismiss error">
                <X size={16} />
              </button>
            </div>
          )}
          {page === "Mission control" && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">
                    <span className="tiny-line" /> OPERATIONS, UNINTERRUPTED
                  </div>
                  <h1>Every pipeline deserves a recovery.</h1>
                  <p>
                    From a broken daily feed to trusted hospital supply
                    intelligence. Watch the agent work.
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
                    validated data product. When a stage breaks, recovery
                    starts.
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
                    <span className="small-dot" /> DETECT. REPAIR. VERIFY.
                    RESUME.
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
                            "stage-connector " +
                            (state === "passed" ? "passed" : "")
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
                    <span className="eyebrow">
                      YOUR JUDGMENT, AT THE RIGHT MOMENT
                    </span>
                    <h3>Tested repair. Waiting for your approval.</h3>
                    <p>
                      {run.proposal.impact} All sandbox checks passed. This
                      checkpoint survives a restart.
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
                      api(`/runs/${run.id}/retry`, {}).catch((e) =>
                        setError(e.message),
                      )
                    }
                  >
                    Retry investigation
                  </button>
                </div>
              )}
              <div className="workbench">
                <section className="panel trace-panel">
                  <div className="section-title">
                    <div>
                      <span className="section-icon">
                        <Terminal size={17} />
                      </span>
                      <h3>Recovery trace</h3>
                      {active && (
                        <span className="live-pill">
                          <i />
                          LIVE
                        </span>
                      )}
                    </div>
                    <div className="trace-tools">
                      <button
                        className={filter === "all" ? "active-filter" : ""}
                        onClick={() => setFilter("all")}
                      >
                        All actions
                      </button>
                      <button
                        className={filter === "agent" ? "active-filter" : ""}
                        onClick={() => setFilter("agent")}
                      >
                        Agent
                      </button>
                      {run && (
                        <a
                          aria-label="Download complete trace"
                          href={`/api/runs/${run.id}/export`}
                        >
                          <ArrowDownToLine size={16} />
                        </a>
                      )}
                    </div>
                  </div>
                  <div className="trace-summary">
                    <span>
                      <span className="small-dot" />
                      {trace.length} recorded events
                    </span>
                    <button
                      className={follow ? "follow active" : "follow"}
                      onClick={() => setFollow(!follow)}
                      aria-pressed={follow}
                    >
                      {follow ? "Following latest" : "Follow latest"}
                    </button>
                  </div>
                  <div
                    className="timeline"
                    ref={timelineRef}
                    role="log"
                    aria-label="Recovery execution timeline"
                    tabIndex={0}
                  >
                    {!trace.length ? (
                      <Empty
                        icon={<Radio size={27} />}
                        title="Ready when your pipeline is."
                        text="Trigger a refresh to follow the failure, investigation, code change, and verified recovery in real time."
                      />
                    ) : (
                      trace.map((event, i) => (
                        <TraceEvent
                          event={event}
                          key={event.seq}
                          last={i === trace.length - 1}
                        />
                      ))
                    )}
                  </div>
                  <div className="trace-footer">
                    <ShieldCheck size={13} />
                    Observable actions and decision summaries. Private model
                    reasoning is not exposed.
                  </div>
                </section>
                <section className="panel inspector">
                  <div className="inspector-tabs">
                    {["Repair", "Quality", "Data"].map((t) => (
                      <button
                        key={t}
                        className={tab === t ? "active-tab" : ""}
                        onClick={() => setTab(t)}
                      >
                        {t === "Repair" ? (
                          <Code2 size={15} />
                        ) : t === "Quality" ? (
                          <ShieldCheck size={15} />
                        ) : (
                          <Database size={15} />
                        )}{" "}
                        {t}
                      </button>
                    ))}
                  </div>
                  <div className="inspector-content">
                    {tab === "Repair" &&
                      (run?.proposal ? (
                        <>
                          <div className="inspector-eyebrow">
                            <Sparkles size={14} /> PROPOSED REPAIR
                          </div>
                          <h3>{run.proposal.label}</h3>
                          <p>{run.proposal.rationale}</p>
                          <span
                            className={
                              "permission " +
                              (run.proposal.requires_approval &&
                              !run.approval?.approved
                                ? "manual"
                                : "auto")
                            }
                          >
                            <ShieldCheck size={13} />
                            {run.approval?.approved
                              ? "Owner approved tested repair"
                              : run.proposal.requires_approval
                                ? "Owner approval required"
                                : "Policy permits automatic repair"}
                          </span>
                          <div className="code-title">
                            <span>
                              <Code2 size={14} />
                              pipeline/transform.py
                            </span>
                            <span>Python · PySpark</span>
                          </div>
                          <div className="diff">
                            {run.proposal.diff
                              .split("\n")
                              .filter(
                                (s: string) =>
                                  !s.startsWith("---") && !s.startsWith("+++"),
                              )
                              .map((line: string, i: number) => (
                                <div
                                  key={i}
                                  className={
                                    line.startsWith("+")
                                      ? "added"
                                      : line.startsWith("-")
                                        ? "removed"
                                        : "context"
                                  }
                                >
                                  <span>{line || " "}</span>
                                </div>
                              ))}
                          </div>
                          <div className="impact">
                            <strong>Expected impact</strong>
                            <p>{run.proposal.impact}</p>
                          </div>
                          {run.deployment && (
                            <div className="deployment">
                              <GitCommitHorizontal size={17} />
                              <div>
                                <strong>
                                  {run.deployment.commit.slice(0, 10)}
                                </strong>
                                <small>
                                  Local Git release · tested artifact deployed
                                </small>
                              </div>
                              <Check size={15} />
                            </div>
                          )}
                          <div className="agent-budget">
                            <span>
                              {run.agent_metrics?.mode === "ollama"
                                ? run.agent_metrics.model
                                : "Deterministic runbook"}
                            </span>
                            <span>
                              {run.agent_metrics?.input_tokens +
                                run.agent_metrics?.output_tokens || 0}{" "}
                              tokens · {run.agent_metrics?.latency_seconds || 0}
                              s
                            </span>
                          </div>
                        </>
                      ) : (
                        <Empty
                          icon={<Code2 size={26} />}
                          title="Evidence before edits."
                          text="The proposed diff, policy decision, and tested release will appear here when the agent identifies a repair."
                        />
                      ))}
                    {tab === "Quality" &&
                      (report ? (
                        <>
                          <div className="inspector-eyebrow">
                            <FlaskConical size={14} />
                            {run?.report
                              ? "PRODUCTION VERIFICATION"
                              : "ISOLATED SANDBOX"}
                          </div>
                          <h3>
                            {report.checks.filter((c: Obj) => c.passed).length}{" "}
                            of {report.checks.length} checks passed
                          </h3>
                          <p>
                            A green Spark job is only the first check. The data
                            product must earn its recovery.
                          </p>
                          <div className="checks">
                            {report.checks.map((c: Obj) => (
                              <div className="quality-check" key={c.name}>
                                {c.passed ? (
                                  <Check size={15} />
                                ) : (
                                  <X size={15} />
                                )}
                                <div>
                                  <strong>{c.name}</strong>
                                  <small>{c.detail}</small>
                                </div>
                              </div>
                            ))}
                          </div>
                        </>
                      ) : (
                        <Empty
                          icon={<FlaskConical size={28} />}
                          title="Success needs proof."
                          text="Row counts, duplicates, freshness, source validity, business rules, and event conservation are checked after execution."
                        />
                      ))}
                    {tab === "Data" &&
                      (metrics ? (
                        <>
                          <div className="inspector-eyebrow">
                            <Layers3 size={14} />
                            COLD-CHAIN INTELLIGENCE
                          </div>
                          <h3>Ready for the next decision.</h3>
                          <p>
                            {run?.report
                              ? "Verified consumption data"
                              : "Sandbox preview · not published"}{" "}
                            · {metrics.partition}
                          </p>
                          <div className="product-metrics">
                            <div>
                              <strong>{metrics.rows}</strong>
                              <span>accepted events</span>
                            </div>
                            <div>
                              <strong>
                                {metrics.usable_units.toLocaleString()}
                              </strong>
                              <span>usable units</span>
                            </div>
                            <div>
                              <strong>{metrics.holds}</strong>
                              <span>cold-chain holds</span>
                            </div>
                            <div>
                              <strong>{metrics.quarantined}</strong>
                              <span>quarantined</span>
                            </div>
                          </div>
                          <div className="data-table">
                            <table>
                              <thead>
                                <tr>
                                  <th>Facility</th>
                                  <th>°C</th>
                                  <th>Decision</th>
                                </tr>
                              </thead>
                              <tbody>
                                {report.sample.slice(0, 7).map((r: Obj) => (
                                  <tr key={r.event_id}>
                                    <td>{r.facility}</td>
                                    <td>{r.temperature_c}</td>
                                    <td>
                                      <span
                                        className={
                                          "action " +
                                          (r.action === "hold_for_review"
                                            ? "hold"
                                            : "")
                                        }
                                      >
                                        {r.action === "hold_for_review"
                                          ? "Hold"
                                          : pretty(r.action)}
                                      </span>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                          <p className="data-note">
                            Parquet output for reports, APIs, or ML features.
                            Fictional products and demonstration rules.
                          </p>
                        </>
                      ) : (
                        <Empty
                          icon={<Database size={27} />}
                          title="A trustworthy data product."
                          text="Verified shipments, usable inventory, cold-chain holds, and a quarantine ledger will appear after a successful test."
                        />
                      ))}
                  </div>
                </section>
              </div>
              <footer className="page-footer">
                <span>BUILT TO RECOVER. DESIGNED TO EXPLAIN.</span>
                <span>
                  Real Spark execution <i /> Local Git releases <i /> Cloud
                  promotion blueprint
                </span>
              </footer>
            </>
          )}
          {page === "Run history" && (
            <>
              <PageTitle
                eyebrow="EVERY RUN LEAVES EVIDENCE"
                title="A record of what actually happened."
                text="Inspect daily partitions, diagnoses, recovery outcomes, and local inference usage."
              />
              <div className="stats">
                <Stat
                  label="Completed incidents"
                  value={String(evaluation?.completed || 0)}
                  note="Recovered, rejected, or blocked"
                  icon={<Workflow size={17} />}
                />
                <Stat
                  label="Verified recoveries"
                  value={String(evaluation?.verified_recoveries || 0)}
                  note="All downstream quality gates passed"
                  icon={<CheckCheck size={17} />}
                />
                <Stat
                  label="Unnecessary changes"
                  value={String(evaluation?.unnecessary_changes || 0)}
                  note="Deployment with mismatched diagnosis"
                  icon={<GitCommitHorizontal size={17} />}
                />
                <Stat
                  label="Daily schedule"
                  value={config?.schedule_enabled ? "On" : "Off"}
                  note={`${config?.schedule_hour || 7}:00 IST · process must be running`}
                  icon={<Clock3 size={17} />}
                />
              </div>
              <section className="panel history">
                <table>
                  <thead>
                    <tr>
                      <th>Run / partition</th>
                      <th>Scenario</th>
                      <th>Status</th>
                      <th>Investigator</th>
                      <th>Quality</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {runs.map((r) => (
                      <tr
                        key={r.id}
                        onClick={() => {
                          setSelected(r.id);
                          setPage("Mission control");
                        }}
                      >
                        <td>
                          <strong className="mono">{r.id}</strong>
                          <small>{r.date}</small>
                        </td>
                        <td>{config?.scenarios[r.scenario]?.label}</td>
                        <td>
                          <Badge status={r.status} />
                        </td>
                        <td>
                          {r.agent_metrics?.mode === "ollama"
                            ? r.agent_metrics.model
                            : r.agent_mode === "runbook"
                              ? "Runbook"
                              : "—"}
                        </td>
                        <td>
                          {r.report
                            ? `${r.report.checks.length} / ${r.report.checks.length} passed`
                            : "—"}
                        </td>
                        <td>
                          <ArrowRight size={15} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!runs.length && (
                  <Empty
                    icon={<Clock3 />}
                    title="Your first run starts the story."
                    text="Launch a refresh from Mission control."
                  />
                )}
              </section>
              <p className="footnote">{evaluation?.note}</p>
            </>
          )}
          {page === "Guardrails" && (
            <>
              <PageTitle
                eyebrow="AUTONOMY WITH BOUNDARIES"
                title="Let the agent act. Keep the judgment."
                text="The model proposes a repair. Evidence, code policy, sandbox checks, and owner approval decide what runs."
              />
              <div className="policy-grid">
                {Object.entries(policy?.recipes || {}).map(([id, p]: any) => (
                  <section key={id} className="panel policy-card">
                    <span
                      className={
                        "permission " + (p.approval ? "manual" : "auto")
                      }
                    >
                      <ShieldCheck size={14} />
                      {p.approval
                        ? "Requires approval"
                        : "Automatic after verification"}
                    </span>
                    <h3>{p.label}</h3>
                    <p>{p.impact}</p>
                    <div className="mono">
                      {p.setting} = {JSON.stringify(p.value)}
                    </div>
                  </section>
                ))}
              </div>
              <section className="panel boundary">
                <h3>Changes outside the playbook stop here.</h3>
                <p>{policy?.unsupported.join(" · ")}</p>
                <strong>{policy?.enforcement}</strong>
                <p>
                  This is a single-owner loopback demo. Production needs
                  identity-backed approvals, a deployment service, durable
                  managed storage, and isolated execution.
                </p>
              </section>
            </>
          )}
          {page === "Notifications" && (
            <>
              <PageTitle
                eyebrow="NO SILENT FAILURES"
                title="The right person stays in the loop."
                text={`Failure, approval, and recovery notifications are addressed to ${config?.notify_to || "the pipeline owner"}.`}
              />
              <div className="email-mode">
                <Mail size={20} />
                <div>
                  <strong>
                    {config?.email_mode === "gmail"
                      ? "Gmail delivery configured"
                      : "Durable outbox mode"}
                  </strong>
                  <p>
                    {config?.email_mode === "gmail"
                      ? "Messages are sent using app-owned Gmail OAuth credentials. Delivery receipts appear below."
                      : "Messages are captured locally. Add your own Gmail OAuth credentials to enable autonomous delivery; your Codex connection is separate."}
                  </p>
                </div>
              </div>
              {emails.length ? (
                emails
                  .slice()
                  .reverse()
                  .map((e) => (
                    <section key={e.id} className="panel email-card">
                      <div>
                        <span className="mono muted">
                          {e.run_id} · {time(e.created)} IST
                        </span>
                        <Badge status={e.status} />
                      </div>
                      <h3>{e.document.subject}</h3>
                      <p className="muted">To: {e.document.to}</p>
                      <details>
                        <summary>View notification</summary>
                        <pre>{e.document.body}</pre>
                        {e.document.provider_id && (
                          <p>Provider receipt: {e.document.provider_id}</p>
                        )}
                      </details>
                    </section>
                  ))
              ) : (
                <section className="panel">
                  <Empty
                    icon={<Mail size={28} />}
                    title="Quiet until something matters."
                    text="Pipeline failures, approval requests, and verified recoveries create durable notifications."
                  />
                </section>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}

function Stat({
  label,
  value,
  note,
  icon,
}: {
  label: string;
  value: string;
  note: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="stat">
      <div>
        <span>{label}</span>
        {icon}
      </div>
      <strong>{value}</strong>
      <small>{note}</small>
    </div>
  );
}
function Empty({
  icon,
  title,
  text,
}: {
  icon: React.ReactNode;
  title: string;
  text: string;
}) {
  return (
    <div className="empty">
      <div>{icon}</div>
      <h4>{title}</h4>
      <p>{text}</p>
    </div>
  );
}
function PageTitle({
  eyebrow,
  title,
  text,
}: {
  eyebrow: string;
  title: string;
  text: string;
}) {
  return (
    <div className="page-heading secondary-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{text}</p>
      </div>
    </div>
  );
}
function TraceEvent({ event: e, last }: { event: Obj; last: boolean }) {
  const icons: Obj = {
    failure: TriangleAlert,
    complete: CheckCheck,
    tool_start: Terminal,
    tool_result: Database,
    model: Sparkles,
    diagnosis: Sparkles,
    proposal: Code2,
    deploy: GitCommitHorizontal,
    approval: ShieldCheck,
    human_decision: ShieldCheck,
    notification: Mail,
    sandbox: FlaskConical,
    sandbox_passed: CheckCheck,
    resume: RotateCcw,
    trigger: Play,
    stage_done: Check,
  };
  const Icon = icons[e.kind] || CircleDot;
  const useful = [
    "tool_result",
    "diagnosis",
    "proposal",
    "deploy",
    "quality",
    "failure",
    "blocked",
    "human_decision",
    "approval",
    "model",
  ].includes(e.kind);
  return (
    <div className={"trace-event " + e.kind + (last ? " latest" : "")}>
      <div className="event-icon">
        <Icon size={14} />
      </div>
      <div className="event-main">
        <div className="event-label">
          <span>{e.body.phase || e.kind}</span>
          <time>{time(e.time)}</time>
        </div>
        {useful ? (
          <details open={last || ["failure", "diagnosis"].includes(e.kind)}>
            <summary>
              {e.title}
              <ChevronDown size={13} />
            </summary>
            {e.kind === "diagnosis" ? (
              <p className="event-text">{e.body.rationale}</p>
            ) : e.kind === "failure" ? (
              <p className="event-text">
                <code>{e.body.code}</code> · {e.body.message}
              </p>
            ) : (
              <Json value={e.body.result || e.body} />
            )}
          </details>
        ) : (
          <>
            <h4>{e.title}</h4>
            {e.body.detail && <p className="event-text">{e.body.detail}</p>}
            {e.body.rows !== undefined && (
              <span className="event-note">
                {e.body.rows} rows · Parquet checkpoint saved
              </span>
            )}
          </>
        )}
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
