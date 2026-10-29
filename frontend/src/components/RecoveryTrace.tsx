import type React from "react";
import { ArrowDownToLine, Radio, ShieldCheck, Terminal } from "lucide-react";
import { Empty } from "../components/ui";
import { TraceEvent } from "../components/TraceEvent";
import type { Obj, Run } from "../types";

export function RecoveryTrace({
  run,
  filter,
  setFilter,
  follow,
  setFollow,
  timelineRef,
  active,
  trace,
}: {
  run: Run | undefined;
  filter: string;
  setFilter: (filter: string) => void;
  follow: boolean;
  setFollow: (follow: boolean) => void;
  timelineRef: React.RefObject<HTMLDivElement | null>;
  active: boolean | undefined;
  trace: Obj[];
}) {
  return (
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
        Observable actions and decision summaries. Private model reasoning is
        not exposed.
      </div>
    </section>
  );
}
