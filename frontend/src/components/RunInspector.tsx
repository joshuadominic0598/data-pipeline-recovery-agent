import {
  Check,
  Code2,
  Database,
  FlaskConical,
  GitCommitHorizontal,
  Layers3,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { Empty } from "../components/ui";
import { pretty } from "../lib/presentation";
import type { Obj, Run } from "../types";

export function RunInspector({
  run,
  tab,
  setTab,
  report,
}: {
  run: Run | undefined;
  tab: string;
  setTab: (tab: string) => void;
  report: Obj | undefined;
}) {
  const metrics = report?.metrics;
  return (
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
                  (run.proposal.requires_approval && !run.approval?.approved
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
                    (s: string) => !s.startsWith("---") && !s.startsWith("+++"),
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
                    <strong>{run.deployment.commit.slice(0, 10)}</strong>
                    <small>Local Git release · tested artifact deployed</small>
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
                  tokens · {run.agent_metrics?.latency_seconds || 0}s
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
                {run?.report ? "PRODUCTION VERIFICATION" : "ISOLATED SANDBOX"}
              </div>
              <h3>
                {report.checks.filter((c: Obj) => c.passed).length} of{" "}
                {report.checks.length} checks passed
              </h3>
              <p>
                A green Spark job is only the first check. The data product must
                earn its recovery.
              </p>
              <div className="checks">
                {report.checks.map((c: Obj) => (
                  <div className="quality-check" key={c.name}>
                    {c.passed ? <Check size={15} /> : <X size={15} />}
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
                  <strong>{metrics.usable_units.toLocaleString()}</strong>
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
                    {report?.sample.slice(0, 7).map((r: Obj) => (
                      <tr key={r.event_id}>
                        <td>{r.facility}</td>
                        <td>{r.temperature_c}</td>
                        <td>
                          <span
                            className={
                              "action " +
                              (r.action === "hold_for_review" ? "hold" : "")
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
                Parquet output for reports, APIs, or ML features. Fictional
                products and demonstration rules.
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
  );
}
