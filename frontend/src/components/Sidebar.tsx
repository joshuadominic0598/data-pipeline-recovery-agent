import {
  Activity,
  Bell,
  ChevronDown,
  Clock3,
  Radio,
  ShieldCheck,
  Workflow,
} from "lucide-react";

export function Sidebar({
  page,
  awaiting,
  setPage,
}: {
  page: string;
  awaiting: number;
  setPage: (page: string) => void;
}) {
  return (
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
  );
}
