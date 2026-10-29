import { useEffect, useRef, useState } from "react";
import { Bell, ChevronRight, TriangleAlert, X } from "lucide-react";
import { Sidebar } from "./components/Sidebar";
import { History } from "./pages/History";
import { Guardrails } from "./pages/Guardrails";
import { Notifications } from "./pages/Notifications";
import { MissionControl } from "./pages/MissionControl";
import { api, setOperatorToken } from "./lib/api";
import { busy } from "./lib/presentation";
import type { Obj, Run } from "./types";

export function App() {
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
        setOperatorToken(c.operator_token);
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
  useEffect(() => {
    if (follow && timelineRef.current) {
      timelineRef.current.scrollTop = timelineRef.current.scrollHeight;
    }
  }, [run?.events?.length, follow, filter, page]);
  return (
    <div className="shell">
      <Sidebar page={page} awaiting={awaiting} setPage={setPage} />
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
            <MissionControl
              selected={selected}
              setRun={setRun}
              config={config}
              runs={runs}
              run={run}
              awaiting={awaiting}
              setSelected={setSelected}
              evaluation={evaluation}
              scenario={scenario}
              setScenario={setScenario}
              day={day}
              setDay={setDay}
              mode={mode}
              setMode={setMode}
              model={model}
              submitting={submitting}
              trigger={trigger}
              decide={decide}
              filter={filter}
              setFilter={setFilter}
              follow={follow}
              setFollow={setFollow}
              timelineRef={timelineRef}
              tab={tab}
              setTab={setTab}
              setError={setError}
              recovered={recovered}
              active={active}
              trace={trace}
              report={report}
            />
          )}
          {page === "Run history" && (
            <History
              config={config}
              runs={runs}
              setPage={setPage}
              setSelected={setSelected}
              evaluation={evaluation}
            />
          )}
          {page === "Guardrails" && <Guardrails policy={policy} />}
          {page === "Notifications" && (
            <Notifications config={config} emails={emails} />
          )}
        </div>
      </main>
    </div>
  );
}
