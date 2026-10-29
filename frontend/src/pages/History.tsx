import {
  ArrowRight,
  CheckCheck,
  Clock3,
  GitCommitHorizontal,
  Workflow,
} from "lucide-react";
import { Badge, Stat, Empty, PageTitle } from "../components/ui";
import type { Obj, Run } from "../types";

export function History({
  config,
  runs,
  setPage,
  setSelected,
  evaluation,
}: {
  config: Obj | undefined;
  runs: Run[];
  setPage: (page: string) => void;
  setSelected: (id: string) => void;
  evaluation: Obj | undefined;
}) {
  return (
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
  );
}
