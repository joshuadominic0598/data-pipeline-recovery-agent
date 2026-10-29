import { Mail } from "lucide-react";
import { Badge, Empty, PageTitle } from "../components/ui";
import { time } from "../lib/presentation";
import type { Obj } from "../types";

export function Notifications({
  config,
  emails,
}: {
  config: Obj | undefined;
  emails: Obj[];
}) {
  return (
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
  );
}
