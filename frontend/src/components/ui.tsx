import type React from "react";
import { pretty } from "../lib/presentation";

export function Badge({ status }: { status: string }) {
  return (
    <span className={"badge " + status}>
      <i />
      {pretty(status)}
    </span>
  );
}

export function Json({ value }: { value: any }) {
  return <pre className="json">{JSON.stringify(value, null, 2)}</pre>;
}

export function Stat({
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

export function Empty({
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

export function PageTitle({
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
