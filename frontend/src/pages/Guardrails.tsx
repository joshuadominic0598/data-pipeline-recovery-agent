import { ShieldCheck } from "lucide-react";
import { PageTitle } from "../components/ui";
import type { Obj } from "../types";

export function Guardrails({ policy }: { policy: Obj | undefined }) {
  return (
    <>
      <PageTitle
        eyebrow="AUTONOMY WITH BOUNDARIES"
        title="Let the agent act. Keep the judgment."
        text="The model proposes a repair. Evidence, code policy, sandbox checks, and owner approval decide what runs."
      />
      <div className="policy-grid">
        {Object.entries(policy?.recipes || {}).map(([id, p]: any) => (
          <section key={id} className="panel policy-card">
            <span className={"permission " + (p.approval ? "manual" : "auto")}>
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
          This is a single-owner loopback demo. Production needs identity-backed
          approvals, a deployment service, durable managed storage, and isolated
          execution.
        </p>
      </section>
    </>
  );
}
