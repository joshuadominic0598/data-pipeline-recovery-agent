import {
  Check,
  CheckCheck,
  ChevronDown,
  CircleDot,
  Code2,
  Database,
  FlaskConical,
  GitCommitHorizontal,
  Mail,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Terminal,
  TriangleAlert,
} from "lucide-react";
import { Json } from "../components/ui";
import { time } from "../lib/presentation";
import type { Obj } from "../types";

export function TraceEvent({ event: e, last }: { event: Obj; last: boolean }) {
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
